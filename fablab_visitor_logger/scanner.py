import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union

# Use bleak for BLE scanning
from bleak import BleakScanner as BleakScannerClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.exc import BleakError

from fablab_visitor_logger.config import Config, DeviceStatus
from fablab_visitor_logger.database import Database  # Needed for type hint
from fablab_visitor_logger.vendor import get_vendor


# Keep DeviceData TypedDict, adjust fields based on bleak availability
class DeviceData(TypedDict):
    mac_address: str
    rssi: int
    timestamp: str  # ISO format datetime string
    device_name: Optional[str]
    vendor: str
    service_uuids: List[str]  # Use list instead of comma-separated string
    manufacturer_data: Dict[Any, str]  # General key type (int expected from bleak)
    tx_power: Optional[int]
    # Appearance is not directly available in Bleak AdvertisementData
    service_data: Dict[Any, str]  # General key type (str expected from bleak)


class BLEScanner:
    """Handles scanning for BLE devices using Bleak."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        # No scanner instance needed here, BleakScanner is used differently

    async def scan(self, duration: Optional[float] = None) -> List[DeviceData]:
        """Scan for BLE devices asynchronously and return their device data.

        Args:
            duration: Scan duration in seconds. Defaults to Config.SCAN_INTERVAL.

        Returns:
            List of device dictionaries with scan data.

        Raises:
            BleakError: If the scan fails due to BLE issues.
            Exception: For other unexpected errors during processing.
        """
        scan_duration = (
            duration if duration is not None else float(Config.SCAN_INTERVAL)
        )
        self.logger.debug(f"Starting BLE scan for {scan_duration:.1f} seconds...")

        devices_found: List[DeviceData] = []
        try:
            # Use BleakScanner.discover(), requesting advertisement data
            # It returns a dictionary: {address: (BLEDevice, AdvertisementData)}
            print("[DEBUG] scanner.py: Before BleakScannerClient.discover") # DEBUG
            discovered_results: Dict[str, tuple[BLEDevice, AdvertisementData]] = await BleakScannerClient.discover(
                timeout=scan_duration, return_adv=True
            )
            print(f"[DEBUG] scanner.py: After BleakScannerClient.discover, found {len(discovered_results)} results") # DEBUG
            self.logger.debug(
                f"Bleak discovered {len(discovered_results)} devices raw."
            )

            # Iterate through the discovered devices and their advertisement data
            for address, (device, ad_data) in discovered_results.items():
                # Use RSSI from ad_data first, then device
                # Handle cases where ad_data might be minimal
                rssi = ad_data.rssi if ad_data.rssi is not None else device.rssi
                if rssi < Config.RSSI_THRESHOLD:
                    self.logger.debug(
                        f"Device {device.address} RSSI {rssi} below threshold "
                        f"{Config.RSSI_THRESHOLD}"
                    )
                    continue

                try:
                    # Pass both device and ad_data to helper
                    devices_found.append(self._create_device_data(device, ad_data))
                except Exception as e:
                    self.logger.error(
                        f"Failed to process device data for {device.address}: {e}",
                        exc_info=True,
                    )

            self.logger.debug(
                f"Processed {len(devices_found)} devices after filtering."
            )
            return devices_found

        except BleakError as e:
            self.logger.error(f"BLE scan failed with BleakError: {e}")
            # Re-raise Bleak specific error for potentially different handling upstream
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during BLE scan: {e}", exc_info=True)
            # Wrap unexpected errors
            raise Exception(f"Unexpected error during BLE scan: {e}") from e

    # Update signature to accept both device and ad_data
    def _create_device_data(
        self, device: BLEDevice, ad_data: AdvertisementData
    ) -> DeviceData:
        """Create standardized device data dictionary from Bleak objects."""

        # Use RSSI directly from ad_data or device passed in
        rssi = ad_data.rssi if ad_data.rssi is not None else device.rssi

        # Convert manufacturer/service data safely
        manufacturer_data_converted = self._safe_convert_bytes_dict(
            ad_data.manufacturer_data
        )
        service_data_converted = self._safe_convert_bytes_dict(ad_data.service_data)

        return DeviceData(
            mac_address=device.address,
            rssi=rssi,
            timestamp=datetime.now().isoformat(),
            device_name=ad_data.local_name or device.name,
            vendor=get_vendor(device.address),
            service_uuids=ad_data.service_uuids or [],
            manufacturer_data=manufacturer_data_converted,
            tx_power=ad_data.tx_power, # Use tx_power attribute
            # Appearance not available
            service_data=service_data_converted,
        )

    def _safe_convert_bytes_dict(
        self, data: Optional[Dict[Union[int, str], bytes]]
    ) -> Dict[Union[int, str], str]:
        """Safely convert dict values from bytes to hex strings."""
        if not data:
            return {}
        converted = {}
        for key, value in data.items():
            try:
                if isinstance(value, bytes):
                    converted[key] = value.hex()
                # If not bytes, skip or log? For now, skip.
            except Exception as e:
                self.logger.warning(
                    f"Could not convert value for key {key} to hex: {e}"
                )
        return converted


class PresenceTracker:
    """Tracks device presence based on scan results."""

    # Add type hints for dependencies
    def __init__(self, scanner: BLEScanner, database: Database):
        self.scanner = scanner
        self.db = database
        self.logger = logging.getLogger(__name__)
        # Format: {mac: {'last_seen': datetime, 'missed_pings': int}}
        self.device_states: Dict[str, Dict[str, Any]] = {}

    # Make method async as scanner.scan is now async
    async def update_presence(self) -> int:
        """Perform async scan and update presence status for all devices."""
        self.logger.debug("Starting presence update cycle.")
        try:
            # Await the async scan
            devices_seen_data: List[DeviceData] = await self.scanner.scan()
            current_time = datetime.now()
            seen_macs = set()  # Optimize lookup

            # Update seen devices
            for device_data in devices_seen_data:
                mac = device_data["mac_address"]
                seen_macs.add(mac)

                if mac in self.device_states:
                    self.device_states[mac]["missed_pings"] = 0
                else:
                    # New device detected
                    self.logger.info(
                        f"New device detected: {mac} "
                        f"(Vendor: {device_data.get('vendor', 'Unknown')})"
                    )
                    self.device_states[mac] = {"missed_pings": 0}
                self.device_states[mac]["last_seen"] = current_time

                # Log presence and device info
                # Use DeviceStatus enum correctly
                self.db.log_presence(mac, DeviceStatus.PRESENT, device_data["rssi"])

                # Prepare device_info dict for logging
                # Use vendor info obtained during scan
                device_info_to_log = {
                    "device_name": device_data.get("device_name"),
                    "device_type": "BLE",  # Keep simple for now
                    "vendor_name": device_data.get(
                        "vendor"
                    ),  # Use vendor from scan data
                    "model_number": None,  # Not available from scan
                    "service_uuids": device_data.get("service_uuids", []),
                    "manufacturer_data": device_data.get("manufacturer_data", {}),
                    "tx_power": device_data.get("tx_power"),
                    # "appearance": device_data.get("appearance"), # Not available
                    "service_data": device_data.get("service_data", {}),
                }
                # Log device info (consider logging less frequently)
                self.db.log_device_info(mac, device_info_to_log)

            # Check for absent/departed devices (Optimized)
            departed_macs = []
            for mac, state in self.device_states.items():
                if mac not in seen_macs:
                    state["missed_pings"] += 1
                    self.logger.debug(
                        f"Device {mac} missed ping {state['missed_pings']}."
                    )

                    if state["missed_pings"] >= Config.DEPARTURE_THRESHOLD:
                        self.logger.info(f"Device {mac} marked as DEPARTED.")
                        self.db.log_presence(mac, DeviceStatus.DEPARTED)
                        departed_macs.append(mac)  # Mark for removal
                    elif state["missed_pings"] >= Config.PING_TIMEOUT:
                        self.logger.info(f"Device {mac} marked as ABSENT.")
                        self.db.log_presence(mac, DeviceStatus.ABSENT)
                    # Else: still considered present until PING_TIMEOUT

            # Remove departed devices from state tracking
            for mac in departed_macs:
                del self.device_states[mac]

            self.logger.debug(
                f"Presence update cycle finished. Active devices in state: "
                f"{len(self.device_states)}"
            )
            return len(devices_seen_data)  # Return count of devices seen in *this* scan

        except BleakError as e:
            self.logger.error(f"BLE scan failed during presence update: {e}")
            # Decide how to handle scan failures - maybe return 0 or re-raise?
            # For now, log and return 0 to allow main loop to continue.
            return 0
        except Exception as e:
            self.logger.error(
                f"Unexpected error during presence update: {e}", exc_info=True
            )
            raise  # Re-raise unexpected errors to be caught by main loop

    # Removed redundant _get_vendor_name method
