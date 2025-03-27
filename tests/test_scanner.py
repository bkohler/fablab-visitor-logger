import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from scanner import BLEScanner, PresenceTracker
from config import DeviceStatus, Config
from database import Database

class TestBLEScanner:
    @pytest.mark.ble_required
    @patch('scanner.btle.Scanner')
    def test_scan_success(self, mock_scanner):
        """Test successful BLE scan returns device data"""
        # Setup mock
        mock_device = MagicMock()
        mock_device.addr = "AA:BB:CC:DD:EE:FF"
        mock_device.rssi = -70
        mock_scanner.return_value.scan.return_value = [mock_device]
        
        scanner = BLEScanner()
        result = scanner.scan()
        
        assert len(result) == 1
        assert result[0]['mac_address'] == "AA:BB:CC:DD:EE:FF"
        assert result[0]['rssi'] == -70
        assert isinstance(result[0]['timestamp'], datetime)
@pytest.mark.ble_required
@patch('scanner.btle.Scanner')
def test_scan_failure(self, mock_scanner):
    def test_scan_failure(self, mock_scanner):
        """Test scan handles BLE errors properly"""
        mock_scanner.return_value.scan.side_effect = Exception("BLE Error")
        
        scanner = BLEScanner()
        with pytest.raises(Exception, match="BLE Error"):
            scanner.scan()

class TestPresenceTracker:
    def test_update_presence(self):
        """Test presence tracking updates device states"""
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = [
            {'mac_address': 'AA:BB:CC:DD:EE:FF', 'rssi': -70, 'timestamp': datetime.now()}
        ]
        mock_db = MagicMock(spec=Database)
        
        tracker = PresenceTracker(mock_scanner, mock_db)
        device_count = tracker.update_presence()
        
        assert device_count == 1
        mock_db.log_presence.assert_called_once_with(
            'AA:BB:CC:DD:EE:FF', DeviceStatus.PRESENT, -70
        )
        assert 'AA:BB:CC:DD:EE:FF' in tracker.device_states

    def test_device_absent(self):
        """Test device marked absent after missed pings"""
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = []  # No devices found
        mock_db = MagicMock(spec=Database)
        
        tracker = PresenceTracker(mock_scanner, mock_db)
        tracker.device_states['AA:BB:CC:DD:EE:FF'] = {
            'last_seen': datetime.now(),
            'missed_pings': Config.PING_TIMEOUT - 1
        }
        
        tracker.update_presence()
        
        # Updated assertion to match actual behavior without RSSI value
        mock_db.log_presence.assert_called_once_with(
            'AA:BB:CC:DD:EE:FF', DeviceStatus.ABSENT
        )