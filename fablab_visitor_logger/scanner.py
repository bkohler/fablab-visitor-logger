import logging
from datetime import datetime

from bluepy import btle

from fablab_visitor_logger.config import Config, DeviceStatus


class BLEScanner:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scanner = btle.Scanner()

    def scan(self, duration=None):
        """Scan for BLE devices and return their MAC addresses and RSSI values"""
        if duration is None:
            duration = Config.SCAN_INTERVAL

        try:
            devices = self.scanner.scan(duration)
            return [
                {"mac_address": dev.addr, "rssi": dev.rssi, "timestamp": datetime.now()}
                for dev in devices
                if dev.rssi >= Config.RSSI_THRESHOLD
            ]

        except Exception as e:
            self.logger.error(f"BLE scan failed: {str(e)}")
            raise Exception(f"BLE scan failed: {str(e)}")


class PresenceTracker:
    def __init__(self, scanner, database):
        self.scanner = scanner
        self.db = database
        self.logger = logging.getLogger(__name__)
        self.device_states = {}  # {mac: {'last_seen': datetime, 'missed_pings': int}}

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
                self.db.log_presence(mac, DeviceStatus.PRESENT, device["rssi"])

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
                    elif self.device_states[mac]["missed_pings"] >= Config.PING_TIMEOUT:
                        self.db.log_presence(mac, DeviceStatus.ABSENT)

            return len(devices)

        except Exception as e:
            self.logger.error(f"Presence update failed: {str(e)}")
            raise
