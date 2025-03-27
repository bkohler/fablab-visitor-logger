from datetime import datetime
from unittest.mock import MagicMock, patch

from fablab_visitor_logger.config import DeviceStatus
from fablab_visitor_logger.database import Database


class TestDatabase:
    @patch("sqlite3.connect")
    def test_init_db(self, mock_connect):
        """Test database initialization creates required tables"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        _ = Database()  # Database instance created but not used in this test

        # Verify tables were created
        calls = mock_conn.executescript.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS devices" in calls
        assert "CREATE TABLE IF NOT EXISTS presence_logs" in calls
        assert "CREATE TABLE IF NOT EXISTS occupancy_aggregates" in calls

    @patch("sqlite3.connect")
    @patch("fablab_visitor_logger.database.datetime")
    def test_log_presence(self, mock_datetime, mock_connect):
        """Test logging presence updates device and creates log entry"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        test_time = datetime(2025, 3, 27, 12, 0, 0)
        mock_datetime.now.return_value = test_time

        db = Database()
        db.log_presence("AA:BB:CC:DD:EE:FF", DeviceStatus.PRESENT, -70)

        # Verify device upsert
        device_args = mock_conn.execute.call_args_list[0][0][1]
        assert device_args[0] == "AA:BB:CC:DD:EE:FF"
        assert device_args[3] == test_time
        assert device_args[4] == "present"

        # Verify log entry
        log_args = mock_conn.execute.call_args_list[1][0][1]
        assert log_args[0] == "AA:BB:CC:DD:EE:FF"
        assert log_args[1] == test_time
        assert log_args[2] == "present"
        assert log_args[3] == -70

    @patch("sqlite3.connect")
    def test_cleanup_old_data(self, mock_connect):
        """Test old data is properly cleaned up"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        db = Database()
        db.cleanup_old_data()

        # Verify cleanup queries
        assert mock_conn.execute.call_count == 2
        assert "DELETE FROM presence_logs" in \
            mock_conn.execute.call_args_list[0][0][0]
        assert "DELETE FROM devices" in \
            mock_conn.execute.call_args_list[1][0][0]
