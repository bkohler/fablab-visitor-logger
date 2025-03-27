import sqlite3
from datetime import datetime, timedelta
from config import Config, DeviceStatus
import hashlib

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DATABASE_PATH)
        self._init_db()
        
    def _init_db(self):
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    anonymous_id TEXT,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    status TEXT CHECK(status IN ('present', 'absent', 'departed'))
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
            """)
    
    def _anonymize_id(self, device_id):
        if Config.ANONYMIZE_DEVICES:
            return hashlib.sha256(device_id.encode()).hexdigest()
        return device_id
    
    def log_presence(self, device_id, status, rssi=None):
        anonymous_id = self._anonymize_id(device_id)
        timestamp = datetime.now()
        
        with self.conn:
            # Update or insert device
            self.conn.execute("""
                INSERT INTO devices (device_id, anonymous_id, first_seen, last_seen, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    status = excluded.status
            """, (device_id, anonymous_id, timestamp, timestamp, status.value))
            
            # Log presence event
            self.conn.execute("""
                INSERT INTO presence_logs (device_id, timestamp, status, rssi)
                VALUES (?, ?, ?, ?)
            """, (device_id, timestamp, status.value, rssi))
    
    def cleanup_old_data(self):
        cutoff = datetime.now() - timedelta(days=Config.DATA_RETENTION_DAYS)
        with self.conn:
            self.conn.execute("DELETE FROM presence_logs WHERE timestamp < ?", (cutoff,))
            self.conn.execute("DELETE FROM devices WHERE last_seen < ? AND status = 'departed'", (cutoff,))