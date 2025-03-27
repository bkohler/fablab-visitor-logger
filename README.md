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
sudo $(which python) main.py scan
```

#### Reporting Commands

List all detected devices:
```bash
python main.py report list-devices
```

List only active devices:
```bash
python main.py report list-devices --active
```

Note:
1. Scanning requires sudo for BLE operations
2. Reporting commands should be run as regular user (without sudo) for database access
3. If you encounter permission errors:
1. Ensure bluez is installed: `sudo apt-get install bluez`
2. Verify Python has proper capabilities: `sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python))`

Show visitor statistics:
```bash
python main.py report stats
```

Export data to CSV:
```bash
python main.py report export-csv --output visitors.csv
```

### Viewing Logged Data
The SQLite database (`fablab_logger.db`) contains a table `visitor_logs` with:
- MAC addresses
- Timestamps 
- Signal strength (RSSI)

Query the database:
```bash
sqlite3 fablab_logger.db "SELECT * FROM visitor_logs;"
```

### Exporting Data
```bash
sqlite3 -header -csv fablab_logger.db "SELECT * FROM visitor_logs;" > visitors.csv
```

## Testing

The test suite uses pytest with 100% coverage.

### Running Tests
```bash
python -m pytest tests/ -v --cov=main --cov-report=term-missing
```

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