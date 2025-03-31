# FabLab Visitor Logger

A Raspberry Pi application that logs visitors via Bluetooth Low Energy (BLE) device detection. It scans for nearby devices, records their presence (MAC address, timestamp, RSSI), and stores the information in an SQLite database.

## Features

- Detects BLE devices (MAC addresses)
- Logs timestamps and signal strength (RSSI)
- Stores data in SQLite database (`fablab_presence.db` by default)
- Anonymizes MAC addresses for privacy
- Provides reporting capabilities (list devices, stats, CSV export)
- Runs as a background service using Systemd
- Includes comprehensive quality checks and tests

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/fablab-visitor-logger.git # Replace with your repo URL
    cd fablab-visitor-logger
    ```

2.  **Install system dependencies:**
    ```bash
    sudo apt-get update
    sudo apt-get install libglib2.0-dev bluez python3-pip python3-venv
    ```

3.  **Set up a Python virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

4.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If you plan to run development checks, install dev dependencies:* `pip install -r requirements-dev.txt`

5.  **Grant Bluetooth permissions to Python:**
    *This step is required for the scanning functionality.*
    ```bash
    sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python))
    # If using a virtualenv:
    # sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f .venv/bin/python)
    ```
    *Verify capabilities:* `getcap $(readlink -f $(which python))` or `getcap $(readlink -f .venv/bin/python)`

6.  **Set up as a systemd service (Recommended for production):**
    ```bash
    sudo cp deployment/fablab-logger.service /etc/systemd/system/
    # Optional: Edit the service file to adjust paths if needed (e.g., WorkingDirectory, ExecStart)
    # sudo nano /etc/systemd/system/fablab-logger.service
    sudo systemctl enable fablab-logger
    sudo systemctl start fablab-logger
    # Check status: sudo systemctl status fablab-logger
    # View logs: sudo journalctl -u fablab-logger -f
    ```

## Usage

The application is run via the `main.py` script using Python's `-m` module execution.

### Running the Scanner

To start continuous scanning and logging:

```bash
# If running directly (requires permissions granted via setcap)
python -m fablab_visitor_logger.main scan

# If setcap didn't work or you prefer sudo (ensure virtualenv python is used if applicable)
# sudo $(which python) -m fablab_visitor_logger.main scan
# sudo .venv/bin/python -m fablab_visitor_logger.main scan
```

*   The scanner will run indefinitely until stopped (e.g., Ctrl+C or via systemd).
*   Logs are typically written to `presence_tracker.log` (configurable).
*   Data is stored in `fablab_presence.db` (configurable).

### Reporting Commands

Reporting commands access the database and **should generally be run without `sudo`**.

*   **List Devices:**
    ```bash
    # List all devices ever seen
    python -m fablab_visitor_logger.main report list-devices

    # List only devices considered currently active/present
    python -m fablab_visitor_logger.main report list-devices --active
    ```

*   **Show Statistics:**
    ```bash
    python -m fablab_visitor_logger.main report stats
    ```

*   **Export Data to CSV:**
    ```bash
    python -m fablab_visitor_logger.main report export-csv --output visitors.csv
    ```

### Viewing Logged Data Directly

You can query the SQLite database directly:

```bash
sqlite3 fablab_presence.db "SELECT * FROM presence_logs LIMIT 10;"
sqlite3 fablab_presence.db "SELECT * FROM device_info;"

# Export to CSV using sqlite3
sqlite3 -header -csv fablab_presence.db "SELECT * FROM presence_logs;" > presence_logs.csv
```

## Configuration

Key parameters can be adjusted in `fablab_visitor_logger/config.py`:

- `SCAN_INTERVAL`: Time between BLE scans (seconds).
- `SCAN_DURATION`: Duration of each BLE scan (seconds).
- `PRESENCE_TIMEOUT`: Time after which a device is considered absent (seconds).
- `DEPARTURE_THRESHOLD`: Time after which an absent device is considered departed (seconds).
- `RSSI_THRESHOLD`: Minimum signal strength (dBm) to consider a device.
- `DATABASE_PATH`: Path to the SQLite database file.
- `LOG_FILE`: Path to the application log file.
- `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`).
- `DATA_RETENTION_DAYS`: How long to keep raw presence logs.

## Quality Checks & Testing

This project uses several tools to maintain code quality. Development dependencies are required (`pip install -r requirements-dev.txt`).

### Makefile Commands

Common checks are available via `make`:

```bash
make check      # Run all checks (lint, typecheck, security, tests)
make lint       # Run flake8, black, isort
make format     # Run black and isort to format code
make typecheck  # Run mypy static type checking
make security   # Run bandit security scanning
make test       # Run pytest with coverage
make coverage   # Generate coverage report
make clean      # Remove temporary files
```

### Pre-commit Hooks

It's recommended to install pre-commit hooks to run checks automatically before each commit:

```bash
pip install pre-commit
pre-commit install
```

### Running Tests Manually

Tests are run using `pytest`:

```bash
# Run all tests (excluding those requiring BLE hardware)
pytest -m "not ble_required"

# Run all tests including hardware tests (requires BLE interface and permissions)
# sudo pytest -m "ble_required"

# Run tests with coverage report
pytest --cov=fablab_visitor_logger --cov-report=term-missing -m "not ble_required"

# Run a specific test file
pytest tests/test_scanner.py -m "not ble_required"
```

## Project Structure

```
fablab_visitor_logger/
├── __init__.py
├── ble_wrapper.py      # Wrapper for BLE operations (if needed)
├── config.py           # Configuration settings
├── database.py         # SQLite database interactions
├── main.py             # Main application entry point & CLI parsing
├── reporting.py        # Reporting functions
├── scanner.py          # Core BLE scanning and presence tracking logic
└── vendor.py           # MAC address vendor lookup
deployment/
├── fablab-logger.service # Systemd service file
tests/
├── features/           # BDD tests (if any)
├── steps/              # BDD step definitions (if any)
└── test_*.py           # Pytest unit/integration tests
.gitignore
Makefile
README.md               # This file
DEVELOPMENT.md          # Developer documentation
requirements.txt        # Main dependencies
requirements-dev.txt    # Development/testing dependencies
pyproject.toml          # Build system configuration (setuptools)
pytest.ini              # Pytest configuration
mypy.ini                # MyPy configuration
.flake8                 # Flake8 configuration
.pre-commit-config.yaml # Pre-commit hook configuration
```

## Contributing

Contributions are welcome! Please refer to the [DEVELOPMENT.md](DEVELOPMENT.md) file for detailed information on the system architecture, development guidelines, implementation plans, and testing strategies.
