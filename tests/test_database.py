from datetime import datetime
from unittest.mock import MagicMock, patch

from fablab_visitor_logger.config import DeviceStatus
from fablab_visitor_logger.database import Database


class TestDatabase:
    @patch("sqlite3.connect")
    def test_init_db(self, mock_connect):
        """Test database initialization creates all required tables"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Create real database instance to test schema initialization
        db = Database()

        # Verify all tables were created
        calls = mock_conn.executescript.call_args[0][0]
        required_tables = [
            "devices",
            "presence_logs",
            "occupancy_aggregates",
            "device_info"
        ]
        for table in required_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in calls

        # Verify foreign key constraints are enabled
        assert "PRAGMA foreign_keys = ON" in calls

        # Verify indexes exist (if any)
        # assert "CREATE INDEX IF NOT EXISTS" in calls

    @patch("sqlite3.connect")
    @patch("fablab_visitor_logger.database.datetime")
    @patch("fablab_visitor_logger.database.Config")
    def test_log_presence(self, mock_config, mock_datetime, mock_connect):
        """Test logging presence updates device and creates log entry"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        test_time = datetime(2025, 3, 27, 12, 0, 0)
        mock_datetime.now.return_value = test_time

        # Test with anonymization on
        mock_config.ANONYMIZE_DEVICES = True
        db = Database()
        db.log_presence("AA:BB:CC:DD:EE:FF", DeviceStatus.PRESENT, -70)
        
        # Test with anonymization off
        mock_config.ANONYMIZE_DEVICES = False
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
        assert mock_conn.execute.call_count == 3
        assert any(
            "DELETE FROM presence_logs" in call[0][0]
            for call in mock_conn.execute.call_args_list
        )
        assert any(
            "DELETE FROM devices" in call[0][0]
            for call in mock_conn.execute.call_args_list
        )
        assert any(
            "DELETE FROM device_info" in call[0][0]
            for call in mock_conn.execute.call_args_list
        )

    @patch("sqlite3.connect")
    @patch("fablab_visitor_logger.database.datetime")
    def test_log_device_info(self, mock_datetime, mock_connect):
        """Test logging device information with BLE characteristics"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        test_time = datetime(2025, 3, 27, 12, 0, 0)
        mock_datetime.now.return_value = test_time

        db = Database()
        device_info = {
            "device_name": "Test Device",
            "device_type": "Test Type",
            "vendor_name": "Test Vendor",
            "model_number": "12345",
            "service_uuids": ["0000180a-0000-1000-8000-00805f9b34fb"],
            "manufacturer_data": {0xFFFF: b'test'},
            "tx_power": -70,
            "appearance": 0,
            "service_data": {"0000180a-0000-1000-8000-00805f9b34fb": b'test'}
        }
        db.log_device_info("AA:BB:CC:DD:EE:FF", device_info)

        # Verify execute was called with correct parameters
        call_args = mock_conn.execute.call_args[0]
        sql = call_args[0]
        args = call_args[1]
        
        # Check key components of the SQL query
        assert "INSERT INTO device_info" in sql
        assert "VALUES" in sql
        assert "ON CONFLICT" in sql
        
        # Verify all parameters are passed correctly
        assert len(args) == 13
        assert args[0] == "AA:BB:CC:DD:EE:FF"  # device_id
        assert args[1] == "Test Device"  # device_name
        assert args[2] == "Test Type"  # device_type
        assert args[3] == "Test Vendor"  # vendor_name
        assert args[4] == "12345"  # model_number
        assert args[5] == '["0000180a-0000-1000-8000-00805f9b34fb"]'  # service_uuids
        assert args[6] == '{"65535": "74657374"}'  # manufacturer_data (hex encoded)
        assert args[7] == -70  # tx_power
        assert args[8] == 0  # appearance
        assert args[9] == '{"0000180a-0000-1000-8000-00805f9b34fb": "74657374"}'  # service_data (hex encoded)
        assert isinstance(args[10], datetime)  # first_detected
        assert isinstance(args[11], datetime)  # last_detected
