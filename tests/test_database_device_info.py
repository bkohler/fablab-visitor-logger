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
            "vendor_name": "Apple",
            "model_number": "A2882",
        }

        db.log_device_info(device_id, device_info)

        db.conn.execute.assert_called_once()
        args = db.conn.execute.call_args[0][1]
        assert args[0] == device_id
        assert args[1] == "John's iPhone"
        assert args[2] == "iPhone 14"
        assert args[3] == "Apple"
        assert args[4] == "A2882"
        assert isinstance(args[5], datetime)
        assert isinstance(args[6], datetime)

    def test_update_device_info(self, db):
        """Test updating existing device info"""
        device_id = "AA:BB:CC:DD:EE:FF"
        device_info = {"device_name": "Updated Name", "vendor_name": "Apple"}

        db.log_device_info(device_id, device_info)

        db.conn.execute.assert_called_once()
        args = db.conn.execute.call_args[0][1]
        assert args[0] == device_id
        assert args[1] == "Updated Name"
        assert args[3] == "Apple"

        assert isinstance(args[6], datetime)  # last_detected updated
