from enum import Enum

class DeviceStatus(Enum):
    PRESENT = 'present'
    ABSENT = 'absent'
    DEPARTED = 'departed'

class Config:
    # Scanning configuration
    SCAN_INTERVAL = 30  # seconds
    PING_TIMEOUT = 3    # missed pings before 'absent'
    DEPARTURE_THRESHOLD = 5  # 'absent' pings before 'departed'
    RSSI_THRESHOLD = -80  # dBm
    
    # Data handling
    DATA_RETENTION_DAYS = 90
    ANONYMIZE_DEVICES = True
    
    # Database
    DATABASE_PATH = 'fablab_presence.db'
    
    @staticmethod
    def setup_logging():
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('presence_tracker.log'),
                logging.StreamHandler()
            ]
        )