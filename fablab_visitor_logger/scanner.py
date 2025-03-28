import logging
from datetime import datetime

from bluepy import btle

from fablab_visitor_logger.config import Config, DeviceStatus


class BLEScanner:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scanner = btle.Scanner()

    def scan(self, duration=None):
        """Scan for BLE devices and return their
        MAC addresses and RSSI values"""
        if duration is None:
            duration = Config.SCAN_INTERVAL

        try:
            devices = []
            for dev in self.scanner.scan(duration):
                if dev.rssi < Config.RSSI_THRESHOLD:
                    continue
                    
                device_data = {
                    "mac_address": dev.addr,
                    "rssi": dev.rssi,
                    "timestamp": datetime.now(),
                    "device_name": dev.getValueText(btle.ScanEntry.COMPLETE_LOCAL_NAME),
                    "service_uuids": [str(uuid) for uuid in dev.scanData.get(0x07, [])],  # 0x07 is SERVICE_UUIDS
                    "manufacturer_data": self._safe_convert_manufacturer_data(dev.scanData.get(btle.ScanEntry.MANUFACTURER)),
                    "tx_power": dev.scanData.get(0x0A),  # 0x0A is TX_POWER_LEVEL
                    "appearance": dev.scanData.get(0x19),  # 0x19 is APPEARANCE
                    "service_data": self._safe_convert_service_data(dev.scanData.get(0x16))
                }
                devices.append(device_data)
            return devices

        except Exception as e:
            self.logger.error(f"BLE scan failed: {str(e)}")
            raise Exception(f"BLE scan failed: {str(e)}")


    def _safe_convert_manufacturer_data(self, data):
        """Safely convert manufacturer data to serializable format"""
        if not data:
            return {}
            
        try:
            if isinstance(data, dict):
                # Only convert if values are bytes
                if all(isinstance(v, bytes) for v in data.values()):
                    return {str(k): v.hex() for k, v in data.items()}
                return {}
            elif isinstance(data, bytes):
                return {"0": data.hex()}
            return {}
        except Exception:
            return {}

    def _safe_convert_service_data(self, data):
        """Safely convert service data to serializable format"""
        if not data:
            return {}
            
        try:
            if isinstance(data, dict):
                # Only convert if values are bytes
                if all(isinstance(v, bytes) for v in data.values()):
                    return {str(k): v.hex() for k, v in data.items()}
                return {}
            elif isinstance(data, bytes):
                return {"0": data.hex()}
            return {}
        except Exception:
            return {}

    def scan(self, duration=None):
        """Scan for BLE devices and return their
        MAC addresses and RSSI values"""
        if duration is None:
            duration = Config.SCAN_INTERVAL

        try:
            devices = []
            for dev in self.scanner.scan(duration):
                if dev.rssi < Config.RSSI_THRESHOLD:
                    continue
                    
                device_data = {
                    "mac_address": dev.addr,
                    "rssi": dev.rssi,
                    "timestamp": datetime.now(),
                    "device_name": dev.getValueText(btle.ScanEntry.COMPLETE_LOCAL_NAME),
                    "service_uuids": [str(uuid) for uuid in dev.scanData.get(0x07, [])],
                    "manufacturer_data": self._safe_convert_manufacturer_data(
                        dev.scanData.get(btle.ScanEntry.MANUFACTURER)
                    ),
                    "tx_power": dev.scanData.get(0x0A),
                    "appearance": dev.scanData.get(0x19),
                    "service_data": self._safe_convert_service_data(
                        dev.scanData.get(0x16)
                    )
                }
                devices.append(device_data)
            return devices

        except Exception as e:
            self.logger.error(f"BLE scan failed: {str(e)}")
            raise Exception(f"BLE scan failed: {str(e)}")

    def _get_vendor_name(self, mac):
        """Get vendor name from MAC address OUI"""
        # First 3 bytes of MAC are OUI (Organizationally Unique Identifier)
        oui = mac[:8].upper().replace(':', '')
        
        # Common vendor OUIs
        vendors = {
            '4C0B3E': 'Google',
            'A4C138': 'Apple',
            'D4F057': 'Samsung',
            'B827EB': 'Raspberry Pi',
            'F0F8F2': 'Xiaomi'
        }
        
        return vendors.get(oui[:6], 'Unknown')
class PresenceTracker:
    def __init__(self, scanner, database):
        self.scanner = scanner
        self.db = database
        self.logger = logging.getLogger(__name__)
        self.device_states = (
            {}
        )  # {mac: {'last_seen': datetime, 'missed_pings': int}}

    def update_presence(self):
        """Perform scan and update presence status for all devices"""
        try:
            devices = self.scanner.scan()
            current_time = datetime.now()

            # Update seen devices
            for device in devices:
                mac = device["mac_address"]
                if mac in self.device_states:
                    self.device_states[mac]["missed_pings"] = 0
                    self.device_states[mac]["last_seen"] = current_time
                else:
                    self.device_states[mac] = {
                        "last_seen": current_time,
                        "missed_pings": 0,
                    }
                # Log presence and device info
                self.db.log_presence(mac, DeviceStatus.PRESENT, device["rssi"])
                device_info = {
                    "device_name": device.get("device_name"),
                    "device_type": "BLE",
                    "vendor_name": self._get_vendor_name(mac),
                    "model_number": None,
                    "service_uuids": device.get("service_uuids", []),
                    "manufacturer_data": device.get("manufacturer_data", {}),
                    "tx_power": device.get("tx_power"),
                    "appearance": device.get("appearance"),
                    "service_data": device.get("service_data", {})
                }
                self.db.log_device_info(mac, device_info)

            # Check for absent devices
            for mac in list(self.device_states.keys()):
                if mac not in [d["mac_address"] for d in devices]:
                    self.device_states[mac]["missed_pings"] += 1

                    if (
                        self.device_states[mac]["missed_pings"]
                        >= Config.DEPARTURE_THRESHOLD
                    ):
                        self.db.log_presence(mac, DeviceStatus.DEPARTED)
                        del self.device_states[mac]
                    elif (
                        self.device_states[mac]["missed_pings"]
                        >= Config.PING_TIMEOUT
                    ):
                        self.db.log_presence(mac, DeviceStatus.ABSENT)

            return len(devices)

        except Exception as e:
            self.logger.error(f"Presence update failed: {str(e)}")
            raise

    def _get_vendor_name(self, mac_address):
        """Get vendor name from MAC address OUI"""
        try:
            # First 3 bytes of MAC address are OUI
            oui = mac_address[:8].upper().replace(':', '')
            
            # Simple OUI lookup (would be better to use a proper OUI database)
            vendor_map = {
                'AABBCC': 'Test Vendor',
                '001CBF': 'Apple',
                '001D4F': 'Samsung',
                '0022F4': 'Intel'
            }
            
            return vendor_map.get(oui, 'Unknown')
        except Exception:
            return 'Unknown'
