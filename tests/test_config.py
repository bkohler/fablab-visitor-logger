from unittest.mock import patch

from fablab_visitor_logger.config import Config, DeviceStatus


class TestConfig:
    def test_device_status_enum(self):
        """Test DeviceStatus enum values"""
        assert DeviceStatus.PRESENT.value == "present"
        assert DeviceStatus.ABSENT.value == "absent"
        assert DeviceStatus.DEPARTED.value == "departed"

    def test_config_defaults(self):
        """Test configuration default values"""
        assert Config.SCAN_INTERVAL == 30
        assert Config.PING_TIMEOUT == 3
        assert Config.DEPARTURE_THRESHOLD == 5
        assert Config.RSSI_THRESHOLD == -80
        assert Config.DATA_RETENTION_DAYS == 90
        assert Config.ANONYMIZE_DEVICES is True

    @patch("logging.FileHandler")
    @patch("logging.StreamHandler")
    def test_setup_logging(self, mock_stream, mock_file):
        """Test logging configuration setup"""
        Config.setup_logging()
        mock_file.assert_called_once_with("presence_tracker.log")
        mock_stream.assert_called_once()
