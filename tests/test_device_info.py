import json
from unittest.mock import MagicMock, patch

from fablab_visitor_logger.database import Database


class TestDeviceInfo:
    @patch("sqlite3.connect")
    def test_log_device_info(self, mock_connect):
        """Test logging device info with BLE characteristics"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        db = Database()
        device_info = {
            "device_name": "Test Device",
            "device_type": "BLE",
            "vendor_name": "Test Vendor",
            "model_number": "123",
            "service_uuids": ["0000180a-0000-1000-8000-00805f9b34fb"],
            "manufacturer_data": {0xFFFF: b"\x01\x02"},
            "tx_power": -12,
            "appearance": 512,
            "service_data": {"0000180a-0000-1000-8000-00805f9b34fb": b"\x01"},
        }

        db.log_device_info("AA:BB:CC:DD:EE:FF", device_info)

        # Verify the execute call
        args = mock_conn.execute.call_args[0][1]
        assert args[0] == "AA:BB:CC:DD:EE:FF"
        assert args[1] == "Test Device"
        assert args[2] == "BLE"
        assert args[3] == "Test Vendor"
        assert args[4] is None  # vendor_id should be none now
        assert args[5] == "123"  # model_number
        assert args[6] == (json.dumps(device_info["service_uuids"]))  # service_uuids
        assert args[7] == json.dumps({"65535": "0102"})  # manufacturer data
        assert args[8] == -12  # tx_power
        assert args[9] == 512  # appearance
        assert args[10] == json.dumps(
            {"0000180a-0000-1000-8000-00805f9b34fb": "01"}
        )  # service_data
