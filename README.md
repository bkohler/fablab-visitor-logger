# FabLab Visitor Logger

A Raspberry Pi application that logs visitors via Bluetooth Low Energy (BLE) device detection.

## Features

- Detects BLE devices (MAC addresses)
- Logs timestamps and signal strength (RSSI)
- Stores data in SQLite database
- Runs as a background service
- Graceful shutdown handling

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fablab-visitor-logger.git
cd fablab-visitor-logger
```

2. Install dependencies:
```bash
sudo apt-get install libglib2.0-dev bluez
sudo $(which python) -m pip install -r requirements.txt
```

3. Grant Bluetooth permissions:
```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python))
```

4. Set up as a systemd service (optional for production):
```bash
sudo cp deployment/fablab-logger.service /etc/systemd/system/
sudo systemctl enable fablab-logger
sudo systemctl start fablab-logger
```

## Usage

### Running the Application

#### Continuous Scanning Mode
```bash
sudo $(which python) -m fablab_visitor_logger.main scan
```

#### Reporting Commands

List all detected devices:
```bash
python -m fablab_visitor_logger.main report list-devices
```

List only active devices:
```bash
python -m fablab_visitor_logger.main report list-devices --active
```

Note:
1. Scanning requires sudo for BLE operations
2. Reporting commands should be run as regular user (without sudo) for database access
3. If you encounter permission errors:
1. Ensure bluez is installed: `sudo apt-get install bluez`
2. Verify Python has proper capabilities: `sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python))`
Show visitor statistics:
```bash
python -m fablab_visitor_logger.main report stats
```

Export data to CSV:
```bash
python -m fablab_visitor_logger.main report export-csv --output visitors.csv
```
```

### Viewing Logged Data
The SQLite database contains tables for tracking device presence and information. By default, the database file is excluded from version control.

Query the database:
```bash
sqlite3 fablab_presence.db "SELECT * FROM presence_logs;"
```

### Exporting Data
```bash
sqlite3 -header -csv fablab_presence.db "SELECT * FROM presence_logs;" > visitors.csv
```

## Testing

The test suite uses pytest with 83.74% coverage (as of latest changes).

### Running Tests
```bash
python -m pytest tests/ -v -m "not ble_required" --cov=. --cov-report=term-missing
```

### Recent Test Improvements
- Updated test assertions for data cleanup functionality
- Added more flexible test patterns
- Improved test coverage reporting

### Test Structure
- `test_scanner.py`: Tests BLE scanning functionality
- `test_database.py`: Tests database operations  
- `test_config.py`: Tests configuration settings
- `test_main.py`: Tests main application logic

### Key Test Commands
Run all tests:
```bash
pytest
```

Run with coverage report:
```bash
pytest --cov
```

Run specific test file:
```bash
pytest tests/test_scanner.py
```

## Configuration

Edit `config.py` to adjust:
- `SCAN_DURATION`: BLE scan duration in seconds
- `SCAN_INTERVAL`: Time between scans
- Database path and other settings

## Documentation

See the design documents for architecture details:
- `fablab_visitor_logger_design.md`
- `fablab_visitor_logger_implementation_plan.md`