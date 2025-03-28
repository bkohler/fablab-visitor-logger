import unittest
from unittest.mock import MagicMock, patch

from fablab_visitor_logger.config import Config
from fablab_visitor_logger.scanner import BLEScanner


class TestBLEScanner(unittest.TestCase):
    @patch("bluepy.btle.Scanner")
    def test_scan_with_valid_data(self, mock_scanner):
        """Test scanning with valid BLE device data"""
        # Setup mock scanner with test data
        mock_device = MagicMock()
        mock_device.addr = "AA:BB:CC:DD:EE:FF"
        mock_device.rssi = -50
        mock_device.getValueText.return_value = "Test Device"
        mock_device.scanData = {
            0x07: ["0000180a-0000-1000-8000-00805f9b34fb"],  # SERVICE_UUIDS
            0xFF: {0xFFFF: b"test"},  # MANUFACTURER_DATA
            0x0A: -20,  # TX_POWER_LEVEL
            0x19: 0,  # APPEARANCE
            0x16: {
                "0000180a-0000-1000-8000-00805f9b34fb": b"test"
            },  # SERVICE_DATA
        }

        mock_scanner_instance = MagicMock()
        mock_scanner_instance.scan.return_value = [mock_device]
        mock_scanner.return_value = mock_scanner_instance

        # Test scan
        scanner = BLEScanner()
        devices = scanner.scan()

        # Verify results
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["mac_address"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(devices[0]["rssi"], -50)
        self.assertEqual(devices[0]["device_name"], "Test Device")
        self.assertEqual(
            devices[0]["service_uuids"],
            "0000180a-0000-1000-8000-00805f9b34fb"
        )
        self.assertEqual(
            devices[0]["manufacturer_data"],
            {"65535": "74657374"}
        )
        self.assertEqual(devices[0]["tx_power"], -20)
        self.assertEqual(devices[0]["appearance"], 0)
        self.assertEqual(
            devices[0]["service_data"],
            {"0000180a-0000-1000-8000-00805f9b34fb": "74657374"},
        )

    @patch("bluepy.btle.Scanner")
    def test_scan_with_invalid_data(self, mock_scanner):
        """Test scanning with invalid BLE data
        that would cause conversion errors"""
        # Setup mock scanner with problematic data
        mock_device = MagicMock()
        mock_device.addr = "AA:BB:CC:DD:EE:FF"
        mock_device.rssi = -50
        mock_device.getValueText.return_value = "Test Device"
        mock_device.scanData = {
            0x07: ["0000180a-0000-1000-8000-00805f9b34fb"],
            0xFF: b"invalid_data",  # Invalid manufacturer data format
            0x16: b"invalid_service_data",  # Invalid service data format
        }

        mock_scanner_instance = MagicMock()
        mock_scanner_instance.scan.return_value = [mock_device]
        mock_scanner.return_value = mock_scanner_instance

        # Test scan with error handling
        scanner = BLEScanner()
        devices = scanner.scan()

        # Should convert raw bytes to hex strings
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["mac_address"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(
            devices[0]["manufacturer_data"],
            {"0": "696e76616c69645f64617461"}
        )
        self.assertEqual(
            devices[0]["service_data"],
            {
                "0": "696e76616c69645f736572766963655f64617461"
            },
        )

    @patch("bluepy.btle.Scanner")
    def test_scan_with_rssi_filtering(self, mock_scanner):
        """Test RSSI threshold filtering"""
        # Setup mock devices with different RSSI values
        mock_device1 = MagicMock()
        mock_device1.addr = "AA:BB:CC:DD:EE:FF"
        mock_device1.rssi = -70  # Below threshold
        mock_device1.scanData = {}

        mock_device2 = MagicMock()
        mock_device2.addr = "11:22:33:44:55:66"
        mock_device2.rssi = -50  # Above threshold
        mock_device2.scanData = {}

        mock_scanner_instance = MagicMock()
        mock_scanner_instance.scan.return_value = [mock_device1, mock_device2]
        mock_scanner.return_value = mock_scanner_instance

        # Set test RSSI threshold
        original_threshold = Config.RSSI_THRESHOLD
        Config.RSSI_THRESHOLD = -65

        try:
            scanner = BLEScanner()
            devices = scanner.scan()
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]["mac_address"], "11:22:33:44:55:66")

            # Test with custom threshold
            Config.RSSI_THRESHOLD = -75
            devices = scanner.scan()
            self.assertEqual(len(devices), 2)
        finally:
            # Restore original threshold
            Config.RSSI_THRESHOLD = original_threshold
