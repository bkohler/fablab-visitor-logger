import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from fablab_visitor_logger.config import Config
from fablab_visitor_logger.reporting import Reporter


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    db_fd, db_path = tempfile.mkstemp()
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE devices (
            device_id TEXT PRIMARY KEY,
            anonymous_id TEXT,
            first_seen DATETIME,
            last_seen DATETIME,
            status TEXT
        );
        CREATE TABLE presence_logs (
            log_id INTEGER PRIMARY KEY,
            device_id TEXT,
            timestamp DATETIME,
            status TEXT,
            rssi INTEGER
        );
        INSERT INTO devices VALUES
            ('device1', 'anon1', '2025-03-26', '2025-03-27', 'present'),
            ('device2', 'anon2', '2025-03-26', '2025-03-26', 'absent'),
            ('device3', 'anon3', '2025-03-26', '2025-03-27', 'departed');
        INSERT INTO presence_logs VALUES
            (1, 'device1', datetime('now', '-2 hours'), 'present', -50),
            (2, 'device1', datetime('now', '-1 hour'), 'present', -55),
            (3, 'device2', '2025-03-26 12:00', 'absent', -60),
            (4, 'device3', '2025-03-27 13:00', 'departed', -65);
    """
    )
    conn.commit()
    conn.close()

    with patch.object(Config, "DATABASE_PATH", db_path):
        yield

    os.close(db_fd)
    os.unlink(db_path)


def test_list_devices(test_db):
    reporter = Reporter()
    devices = reporter.list_devices()
    assert len(devices) == 3
    assert devices[0]["device_id"] == "device1"
    assert devices[0]["status"] == "present"


def test_list_devices_active_only(test_db):
    reporter = Reporter()
    devices = reporter.list_devices(active_only=True)
    assert len(devices) == 2
    assert all(d["status"] in ["present", "absent"] for d in devices)


def test_get_stats(test_db):
    reporter = Reporter()
    stats = reporter.get_stats()
    assert stats["total_devices"] == 3
    assert stats["present_devices"] == 1
    assert (
        stats["recent_visits"] == 2
    )  # Only 2 visits in last 24 hours (one is from yesterday)


def test_export_csv(test_db):
    reporter = Reporter()
    with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
        reporter.export_csv(tmp.name)
        content = Path(tmp.name).read_text()
        # Use a more flexible assertion that doesn't depend on exact timestamp
        assert "device1" in content
        assert "present,-50" in content
        assert "device3,2025-03-27 13:00,departed,-65" in content


def test_export_csv_invalid_path(test_db):
    reporter = Reporter()
    with pytest.raises(ValueError):
        reporter.export_csv("invalid_path.txt")


@patch("fablab_visitor_logger.reporting.Reporter")
def test_cli_list_devices(mock_reporter, capsys):
    mock_reporter.return_value.list_devices.return_value = [
        {
            "device_id": "test1",
            "status": "present",
            "device_name": "Test Device",
            "vendor_name": "Test Vendor",
            "device_type": "Test Type",
        }
    ]

    from fablab_visitor_logger import reporting

    with patch("sys.argv", ["reporting.py", "list-devices"]):
        reporting.main()

    captured = capsys.readouterr()
    assert (
        "ID: test1 | Status: present | "
        "Name: Test Device | "
        "Vendor: Test Vendor | "
        "Type: Test Type" in captured.out
    )


@patch("fablab_visitor_logger.reporting.Reporter")
def test_cli_stats(mock_reporter, capsys):
    mock_reporter.return_value.get_stats.return_value = {
        "total_devices": 5,
        "present_devices": 2,
        "recent_visits": 10,
        "vendor_breakdown": {"Apple": 2, "Samsung": 1},
        "type_breakdown": {"Phone": 3, "Tablet": 1},
    }

    from fablab_visitor_logger import reporting

    with patch("sys.argv", ["reporting.py", "stats"]):
        reporting.main()

    captured = capsys.readouterr()
    assert "Total unique devices: 5" in captured.out
    assert "Currently present: 2" in captured.out


@patch("fablab_visitor_logger.reporting.Reporter")
def test_cli_export_csv(mock_reporter, capsys):
    with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
        from fablab_visitor_logger import reporting

        with patch("sys.argv", ["reporting.py", "export-csv", tmp.name]):
            reporting.main()

    captured = capsys.readouterr()
    assert f"Data exported to {tmp.name}" in captured.out


def test_cli_error_handling(capsys):
    from fablab_visitor_logger import reporting

    with patch("sys.argv", ["reporting.py", "invalid-command"]):
        with pytest.raises(SystemExit):
            reporting.main()
