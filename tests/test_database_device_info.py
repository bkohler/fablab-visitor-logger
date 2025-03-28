from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from fablab_visitor_logger.database import Database


class TestDatabaseDeviceInfo:
    @pytest.fixture
    def db(self):
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            db = Database()
            db.conn = mock_conn
            return db

    def test_log_device_info(self, db):
        """Test logging device info with all fields"""
        device_id = "AA:BB:CC:DD:EE:FF"
        device_info = {
            "device_name": "John's iPhone",
            "device_type": "iPhone 14",
            "model_number": "A2882",
        }

        db.log_device_info(device_id, device_info)
        
        # Verify both calls were made
        assert db.conn.execute.call_count == 2
        
        # Check devices table insert
        devices_call = db.conn.execute.call_args_list[0]
        assert "INSERT OR IGNORE INTO devices" in devices_call[0][0]
        assert devices_call[0][1][0] == device_id
        
        # Check device_info insert
        device_info_call = db.conn.execute.call_args_list[1]
        args = device_info_call[0][1]
        assert args[0] == device_id
        assert args[1] == "John's iPhone"
        assert args[2] == "iPhone 14"
        assert args[5] == "A2882"  # model_number is 5th parameter
        assert isinstance(args[11], datetime)  # first_detected
        assert isinstance(args[12], datetime)  # last_detected

    def test_update_device_info(self, db):
        """Test updating existing device info"""
        device_id = "AA:BB:CC:DD:EE:FF"
        device_info = {"device_name": "Updated Name"}

        db.log_device_info(device_id, device_info)
        
        # Verify both calls were made
        assert db.conn.execute.call_count == 2
        
        # Check devices table insert
        devices_call = db.conn.execute.call_args_list[0]
        assert "INSERT OR IGNORE INTO devices" in devices_call[0][0]
        assert devices_call[0][1][0] == device_id
        
        # Check device_info update
        device_info_call = db.conn.execute.call_args_list[1]
        args = device_info_call[0][1]
        assert args[0] == device_id
        assert args[1] == "Updated Name"
        assert isinstance(args[11], datetime)  # last_detected updated
