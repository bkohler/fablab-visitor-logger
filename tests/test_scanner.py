from unittest.mock import AsyncMock, patch

import pytest
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from fablab_visitor_logger.config import Config
from fablab_visitor_logger.scanner import BLEScanner

# --- Test Data Fixtures ---


@pytest.fixture
def mock_advertisement_data_valid() -> AdvertisementData:
    """Creates a mock AdvertisementData object with typical valid data."""
    # Provide dummy values for required positional args tx_power and platform_data
    return AdvertisementData(
        local_name="Test Device",
        manufacturer_data={0xFFFF: b"test_manu"},
        service_uuids=["0000180a-0000-1000-8000-00805f9b34fb"],
        service_data={"0000180d-0000-1000-8000-00805f9b34fb": b"test_serv"},
        rssi=-50,
        tx_power=-20, # Dummy value, bleak calculates this internally usually
        platform_data=(), # Dummy value
    )


@pytest.fixture
def mock_ble_device_valid(mock_advertisement_data_valid) -> BLEDevice:
    """Creates a mock BLEDevice with valid AdvertisementData."""
    device = BLEDevice(
        address="AA:BB:CC:DD:EE:FF",
        name="Test Device",
        details={},  # Platform specific details, mock as empty
        rssi=-50,  # RSSI is often part of BLEDevice too
    )
    # In tests, we'll simulate discover returning (device, ad_data) tuples
    return device


@pytest.fixture
def mock_advertisement_data_invalid() -> AdvertisementData:
    """Creates mock AdvertisementData with data that might cause conversion issues."""
    # Note: Bleak's parsing is generally robust, so "invalid" here means data
    # that our _safe_convert methods might need to handle (like empty bytes).
    # Provide dummy values for required positional args tx_power and platform_data
    return AdvertisementData(
        local_name="Invalid Device",
        manufacturer_data={0xAAAA: b""},  # Empty bytes
        service_uuids=[],
        service_data={"0000180f-0000-1000-8000-00805f9b34fb": b""}, # Empty bytes
        rssi=-60,
        tx_power=-127, # Dummy value
        platform_data=(), # Dummy value
    )


@pytest.fixture
def mock_ble_device_invalid(mock_advertisement_data_invalid) -> BLEDevice:
    """Creates a mock BLEDevice with potentially problematic AdvertisementData."""
    device = BLEDevice(
        address="11:22:33:44:55:66",
        name="Invalid Device",
        details={},
        rssi=-60,
    )
    # In tests, we'll simulate discover returning (device, ad_data) tuples
    return device


# --- Test Class ---


# Using a class for structure, but could also be separate functions
class TestBLEScanner:
    @pytest.mark.asyncio
    @patch("fablab_visitor_logger.scanner.get_vendor", return_value="Mock Vendor")
    @patch("fablab_visitor_logger.scanner.BleakScannerClient", new_callable=AsyncMock)
    # Use standard fixture injection (pass fixture names as args)
    async def test_scan_with_valid_data(
        self, mock_bleak_scanner, mock_get_vendor, mock_ble_device_valid, mock_advertisement_data_valid
    ):
        """Test scanning returns correctly formatted data using Bleak."""
        # mock_advertisement_data_valid is now the object returned by the fixture
        mock_bleak_scanner.discover.return_value = {
            mock_ble_device_valid.address: (mock_ble_device_valid, mock_advertisement_data_valid)
        }

        # Instantiate our scanner (which should use BleakScanner internally)
        scanner = BLEScanner()
        devices = await scanner.scan(duration=0.1)  # Use await

        # Verify results (adjust assertions based on expected
        # _create_device_data output)
        assert len(devices) == 1
        dev_data = devices[0]
        assert dev_data["mac_address"] == "AA:BB:CC:DD:EE:FF"
        assert dev_data["rssi"] == -50
        assert dev_data["device_name"] == "Test Device"
        assert dev_data["vendor"] == "Mock Vendor"  # Check mock vendor call
        assert "0000180a-0000-1000-8000-00805f9b34fb" in dev_data["service_uuids"]
        # Key should be integer 65535
        assert dev_data["manufacturer_data"] == {65535: "746573745f6d616e75"}
        assert dev_data["tx_power"] == -20
        # assert dev_data["appearance"] is None # Appearance not handled
        assert dev_data["service_data"] == {
            "0000180d-0000-1000-8000-00805f9b34fb": "746573745f73657276"
        }
        assert isinstance(dev_data["timestamp"], str)  # Check timestamp is generated

        mock_get_vendor.assert_called_once_with("AA:BB:CC:DD:EE:FF")

    @pytest.mark.asyncio
    @patch("fablab_visitor_logger.scanner.get_vendor", return_value="Mock Vendor")
    @patch("fablab_visitor_logger.scanner.BleakScannerClient", new_callable=AsyncMock)
    # Use standard fixture injection
    async def test_scan_handles_potentially_problematic_data(
        self, mock_bleak_scanner, mock_get_vendor, mock_ble_device_invalid, mock_advertisement_data_invalid
    ):
        """Test scanning handles data like empty byte strings."""
        # mock_advertisement_data_invalid is now the object returned by the fixture
        mock_bleak_scanner.discover.return_value = {
             mock_ble_device_invalid.address: (mock_ble_device_invalid, mock_advertisement_data_invalid)
        }

        scanner = BLEScanner()
        devices = await scanner.scan(duration=0.1)

        assert len(devices) == 1
        dev_data = devices[0]
        assert dev_data["mac_address"] == "11:22:33:44:55:66"
        assert dev_data["rssi"] == -60
        assert dev_data["device_name"] == "Invalid Device"
        assert dev_data["vendor"] == "Mock Vendor"
        # Expect an empty list, not an empty string
        assert dev_data["service_uuids"] == []
        # Key should be integer 43690
        assert dev_data["manufacturer_data"] == {43690: ""}
        assert dev_data["tx_power"] == -127 # Correct assertion for tx_power
        # assert dev_data["appearance"] is None # Appearance not handled
        assert dev_data["service_data"] == {"0000180f-0000-1000-8000-00805f9b34fb": ""}

        mock_get_vendor.assert_called_once_with("11:22:33:44:55:66")

    @pytest.mark.asyncio
    @patch("fablab_visitor_logger.scanner.get_vendor", return_value="Mock Vendor")
    @patch("fablab_visitor_logger.scanner.BleakScannerClient", new_callable=AsyncMock)
    # Use standard fixture injection
    async def test_scan_with_rssi_filtering(
        self,
        mock_bleak_scanner,
        mock_get_vendor,
        mock_ble_device_valid,
        mock_ble_device_invalid,
        mock_advertisement_data_valid, # Fixture provides the object
        mock_advertisement_data_invalid # Fixture provides the object
    ):
        """Test RSSI threshold filtering using Bleak."""
        # Create new AdvertisementData instances with modified RSSI for the test
        # Use the objects provided by the fixtures
        ad_data_valid_mod = AdvertisementData(
            local_name=mock_advertisement_data_valid.local_name, manufacturer_data=mock_advertisement_data_valid.manufacturer_data,
            service_data=mock_advertisement_data_valid.service_data, service_uuids=mock_advertisement_data_valid.service_uuids,
            rssi=-50, tx_power=mock_advertisement_data_valid.tx_power, platform_data=mock_advertisement_data_valid.platform_data
        )
        ad_data_invalid_mod = AdvertisementData(
            local_name=mock_advertisement_data_invalid.local_name, manufacturer_data=mock_advertisement_data_invalid.manufacturer_data,
            service_data=mock_advertisement_data_invalid.service_data, service_uuids=mock_advertisement_data_invalid.service_uuids,
            rssi=-70, tx_power=mock_advertisement_data_invalid.tx_power, platform_data=mock_advertisement_data_invalid.platform_data
        )

        mock_bleak_scanner.discover.return_value = {
            mock_ble_device_valid.address: (mock_ble_device_valid, ad_data_valid_mod),
            mock_ble_device_invalid.address: (mock_ble_device_invalid, ad_data_invalid_mod),
        }

        # Set test RSSI threshold
        original_threshold = Config.RSSI_THRESHOLD
        Config.RSSI_THRESHOLD = -65  # Only device_valid should pass

        try:
            scanner = BLEScanner()
            devices = await scanner.scan(duration=0.1)
            assert len(devices) == 1
            assert devices[0]["mac_address"] == "AA:BB:CC:DD:EE:FF"  # device_valid

            # Test with different threshold
            Config.RSSI_THRESHOLD = -75  # Both should pass
            # Need to reset mock return value if discover is called again
            mock_bleak_scanner.discover.return_value = {
                mock_ble_device_valid.address: (mock_ble_device_valid, ad_data_valid_mod),
                mock_ble_device_invalid.address: (mock_ble_device_invalid, ad_data_invalid_mod),
            }
            devices = await scanner.scan(duration=0.1)
            assert len(devices) == 2

        finally:
            # Restore original threshold
            Config.RSSI_THRESHOLD = original_threshold

    @pytest.mark.asyncio
    @patch("fablab_visitor_logger.scanner.BleakScannerClient", new_callable=AsyncMock)
    async def test_scan_exception_handling(self, mock_bleak_scanner):
        """Test exceptions during Bleak scan are caught and re-raised."""
        # Configure the mock discover method to raise an error
        mock_bleak_scanner.discover.side_effect = Exception("BLEak scan failed!")

        scanner = BLEScanner()

        # Use pytest.raises to assert that the wrapped exception is raised
        # Match the actual exception message from scanner.py
        with pytest.raises(Exception, match="Unexpected error during BLE scan: BLEak scan failed!"):
            await scanner.scan(duration=0.1)

        # Verify discover was called
        mock_bleak_scanner.discover.assert_called_once()

    @pytest.mark.asyncio
    @patch("fablab_visitor_logger.scanner.BleakScannerClient", new_callable=AsyncMock)
    async def test_scan_empty_results(self, mock_bleak_scanner):
        """Test scanning when no devices are found."""
        mock_bleak_scanner.discover.return_value = {}  # Simulate no devices found (dict)

        scanner = BLEScanner()
        devices = await scanner.scan(duration=0.1)

        assert len(devices) == 0
        mock_bleak_scanner.discover.assert_called_once()
