import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from reporting import Reporter
from config import Config

@pytest.fixture
def test_db():
    """Create a temporary test database"""
    db_fd, db_path = tempfile.mkstemp()
    conn = sqlite3.connect(db_path)
    conn.executescript("""
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
            (1, 'device1', '2025-03-26 10:00', 'present', -50),
            (2, 'device1', '2025-03-27 11:00', 'present', -55),
            (3, 'device2', '2025-03-26 12:00', 'absent', -60),
            (4, 'device3', '2025-03-27 13:00', 'departed', -65);
    """)
    conn.commit()
    conn.close()
    
    with patch.object(Config, 'DATABASE_PATH', db_path):
        yield
    
    os.close(db_fd)
    os.unlink(db_path)

def test_list_devices(test_db):
    reporter = Reporter()
    devices = reporter.list_devices()
    assert len(devices) == 3
    assert devices[0]['device_id'] == 'device1'
    assert devices[0]['status'] == 'present'

def test_list_devices_active_only(test_db):
    reporter = Reporter()
    devices = reporter.list_devices(active_only=True)
    assert len(devices) == 2
    assert all(d['status'] in ['present', 'absent'] for d in devices)

def test_get_stats(test_db):
    reporter = Reporter()
    stats = reporter.get_stats()
    assert stats['total_devices'] == 3
    assert stats['present_devices'] == 1
    assert stats['recent_visits'] == 3  # Only 3 visits in last 24 hours (one is from yesterday)

def test_export_csv(test_db):
    reporter = Reporter()
    with tempfile.NamedTemporaryFile(suffix='.csv') as tmp:
        reporter.export_csv(tmp.name)
        content = Path(tmp.name).read_text()
        assert 'device1,2025-03-26 10:00,present,-50' in content
        assert 'device3,2025-03-27 13:00,departed,-65' in content

def test_export_csv_invalid_path(test_db):
    reporter = Reporter()
    with pytest.raises(ValueError):
        reporter.export_csv('invalid_path.txt')

@patch('reporting.Reporter')
def test_cli_list_devices(mock_reporter, capsys):
    mock_reporter.return_value.list_devices.return_value = [
        {'device_id': 'test1', 'status': 'present'}
    ]
    
    import reporting
    with patch('sys.argv', ['reporting.py', 'list-devices']):
        reporting.main()
        
    captured = capsys.readouterr()
    assert 'test1 (present)' in captured.out

@patch('reporting.Reporter')
def test_cli_stats(mock_reporter, capsys):
    mock_reporter.return_value.get_stats.return_value = {
        'total_devices': 5,
        'present_devices': 2,
        'recent_visits': 10
    }
    
    import reporting
    with patch('sys.argv', ['reporting.py', 'stats']):
        reporting.main()
        
    captured = capsys.readouterr()
    assert 'Total unique devices: 5' in captured.out
    assert 'Currently present: 2' in captured.out

@patch('reporting.Reporter')
def test_cli_export_csv(mock_reporter, capsys):
    with tempfile.NamedTemporaryFile(suffix='.csv') as tmp:
        import reporting
        with patch('sys.argv', ['reporting.py', 'export-csv', tmp.name]):
            reporting.main()
            
    captured = capsys.readouterr()
    assert f"Data exported to {tmp.name}" in captured.out

def test_cli_error_handling(capsys):
    import reporting
    with patch('sys.argv', ['reporting.py', 'invalid-command']):
        with pytest.raises(SystemExit):
            reporting.main()