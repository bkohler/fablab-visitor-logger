import json
import hashlib
import sqlite3
from datetime import datetime, timedelta

from fablab_visitor_logger.config import Config


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DATABASE_PATH)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.executescript(
                """
                PRAGMA foreign_keys = ON;
                
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    anonymous_id TEXT,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    status TEXT CHECK(
                        status IN (
                            'present',
                            'absent',
                            'departed'
                        )
                    )
                );
                CREATE TABLE IF NOT EXISTS presence_logs (
                    log_id INTEGER PRIMARY KEY,
                    device_id TEXT,
                    timestamp DATETIME,
                    status TEXT,
                    rssi INTEGER,
                    FOREIGN KEY(device_id) REFERENCES devices(device_id)
                );
                CREATE TABLE IF NOT EXISTS occupancy_aggregates (
                    date DATE,
                    hour INTEGER,
                    present_count INTEGER,
                    PRIMARY KEY(date, hour)
                );
                
                CREATE TABLE IF NOT EXISTS vendors (
                    vendor_id INTEGER PRIMARY KEY,
                    vendor_name TEXT NOT NULL,
                    common_device_types TEXT
                );

                INSERT OR IGNORE INTO vendors VALUES
                    (0x004C, 'Apple', 'iPhone,AirPods,Apple Watch'),
                    (0x0006, 'Microsoft', 'Surface,Xbox'),
                    (0x000F, 'Samsung', 'Galaxy Phones,Galaxy Watch'),
                    (0x0015, 'Google', 'Pixel Phones,Pixel Buds'),
                    (0x0075, 'Sony', 'PlayStation,Headphones'),
                    (0x000D, 'Intel', 'Laptops,Tablets');

                CREATE TABLE IF NOT EXISTS device_info (
                    device_id TEXT PRIMARY KEY,
                    device_name TEXT,
                    device_type TEXT,
                    vendor_id INTEGER,
                    vendor_name TEXT,
                    model_number TEXT,
                    service_uuids TEXT,  -- JSON array of service UUIDs
                    manufacturer_data TEXT,  -- JSON of manufacturer data
                    tx_power INTEGER,
                    appearance INTEGER,
                    service_data TEXT,  -- JSON of service data
                    first_detected DATETIME,
                    last_detected DATETIME,
                    FOREIGN KEY(device_id) REFERENCES devices(device_id),
                    FOREIGN KEY(vendor_id) REFERENCES vendors(vendor_id)
                );
            """
            )

    def _anonymize_id(self, device_id):
        if Config.ANONYMIZE_DEVICES:
            return hashlib.sha256(device_id.encode()).hexdigest()
        return device_id

    def log_presence(self, device_id, status, rssi=None):
        anonymous_id = self._anonymize_id(device_id)
        timestamp = datetime.now()

        with self.conn:
            # Update or insert device
            self.conn.execute(
                """
                INSERT INTO devices (
                    device_id,
                    anonymous_id,
                    first_seen,
                    last_seen,
                    status
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    status = excluded.status
            """,
                (device_id, anonymous_id, timestamp, timestamp, status.value),
            )

            # Log presence event
            self.conn.execute(
                """
                INSERT INTO presence_logs (
                    device_id,
                    timestamp,
                    status,
                    rssi
                ) VALUES (?, ?, ?, ?)
            """,
                (device_id, timestamp, status.value, rssi),
            )

    def cleanup_old_data(self):
        cutoff = datetime.now() - timedelta(days=Config.DATA_RETENTION_DAYS)
        with self.conn:
            self.conn.execute(
                "DELETE FROM presence_logs WHERE timestamp < ?", (cutoff,)
            )
            self.conn.execute(
                """
                DELETE FROM devices
                WHERE last_seen < ?
                AND status = 'departed'
            """,
                (cutoff,),
            )
            self.conn.execute(
                "DELETE FROM device_info WHERE last_detected < ?", (cutoff,)
            )

    def _get_vendor_info(self, vendor_id):
        """Lookup vendor info by ID"""
        if not vendor_id:
            return None, None
            
        with self.conn:
            cursor = self.conn.execute(
                "SELECT vendor_name, common_device_types FROM vendors WHERE vendor_id = ?",
                (vendor_id,)
            )
            return cursor.fetchone() or (None, None)

    def log_device_info(self, device_id, device_info):
        """Log or update device information with BLE characteristics"""
        now = datetime.now()
        
        # Ensure device exists in devices table first
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO devices (device_id, anonymous_id, first_seen, last_seen, status) VALUES (?, ?, ?, ?, ?)",
                (device_id, self._anonymize_id(device_id), now, now, "present")
            )
        
        # Extract vendor info
        vendor_id = device_info.get("manufacturer_data", {}).get("vendor_id")
        vendor_name = device_info.get("vendor_name")
        device_type = device_info.get("device_type")
        
        # Get vendor info if not explicitly provided
        if vendor_name is None or device_type is None:
            v_name, d_type = self._get_vendor_info(vendor_id)
            vendor_name = vendor_name or v_name
            device_type = device_type or d_type
        
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO device_info (
                    device_id,
                    device_name,
                    device_type,
                    vendor_id,
                    vendor_name,
                    model_number,
                    service_uuids,
                    manufacturer_data,
                    tx_power,
                    appearance,
                    service_data,
                    first_detected,
                    last_detected
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    device_name = excluded.device_name,
                    device_type = excluded.device_type,
                    vendor_id = excluded.vendor_id,
                    vendor_name = excluded.vendor_name,
                    model_number = excluded.model_number,
                    service_uuids = excluded.service_uuids,
                    manufacturer_data = excluded.manufacturer_data,
                    tx_power = excluded.tx_power,
                    appearance = excluded.appearance,
                    service_data = excluded.service_data,
                    last_detected = excluded.last_detected
            """,
                (
                    device_id,
                    device_info.get("device_name"),
                    device_info.get("device_type") or device_type,
                    vendor_id,
                    device_info.get("vendor_name"),  # Make vendor_name optional
                    device_info.get("model_number"),
                    json.dumps(device_info.get("service_uuids", [])),
                    json.dumps({
                        k: v.hex() if isinstance(v, bytes) else v
                        for k, v in (device_info.get("manufacturer_data") or {}).items()
                    }) if device_info.get("manufacturer_data") else None,
                    device_info.get("tx_power"),
                    device_info.get("appearance"),
                    json.dumps({
                        k: v.hex() if isinstance(v, bytes) else v
                        for k, v in (device_info.get("service_data") or {}).items()
                    }) if device_info.get("service_data") else None,
                    now,
                    now,
                ),
            )
