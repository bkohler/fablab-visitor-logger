# FabLab Visitor Logger - Developer Documentation

This document provides technical details, design decisions, development guidelines, and future plans for the FabLab Visitor Logger project. For user-facing information like installation and basic usage, please refer to [README.md](README.md).

## 1. System Overview & Architecture

The system is designed to monitor the presence of individuals in a FabLab environment by detecting Bluetooth Low Energy (BLE) devices. It logs device appearances, attempts to identify vendors, anonymizes MAC addresses, and stores presence information in an SQLite database. Reporting tools allow querying this data.

### High-Level Architecture

```mermaid
graph TD
    A[BLE Scanner (scanner.py)] -->|Detects devices| B[Presence Tracker (scanner.py)]
    B -->|Logs presence & device info| C[Database (database.py)]
    C -->|Provides data| D[Reporting Module (reporting.py)]
    D -->|Generates Reports/Stats| E[CLI Output (main.py)]
    F[Configuration (config.py)] --> A
    F --> B
    F --> C
    F --> D
```

### Core Components

-   **`scanner.py`**: Contains `BLEScanner` for raw device discovery and `PresenceTracker` for managing device status (present, absent, departed) based on scan results and timeouts.
-   **`database.py`**: Manages the SQLite database (`presence_logs`, `device_info` tables), including initialization, data logging (presence, device details), anonymization, and data cleanup.
-   **`reporting.py`**: Provides functions to query the database and generate reports (list devices, statistics, CSV export).
-   **`main.py`**: Handles command-line argument parsing (`argparse`) and orchestrates the application flow (running the scanner or executing report commands).
-   **`config.py`**: Centralizes configuration parameters (scan intervals, timeouts, database paths, logging settings).
-   **`vendor.py`**: Utility for looking up device vendors based on MAC address OUI.

## 2. Technology Stack

-   **Language**: Python 3.9+
-   **BLE Scanning**: `bleak` library (asynchronous)
-   **Database**: SQLite3 (via Python's `sqlite3` module)
-   **CLI**: Python's `argparse`
-   **Concurrency**: `asyncio` (used by `bleak`)
-   **Testing**: `pytest`, `pytest-cov`, `pytest-asyncio`, `mock`
-   **Linting/Formatting**: `flake8`, `black`, `isort`
-   **Type Checking**: `mypy`
-   **Security Scanning**: `bandit`
-   **Deployment**: Systemd (optional)

## 3. Project Structure

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
README.md               # User documentation
DEVELOPMENT.md          # This file
requirements.txt        # Main dependencies
requirements-dev.txt    # Development/testing dependencies
pyproject.toml          # Build system configuration (setuptools)
pytest.ini              # Pytest configuration
mypy.ini                # MyPy configuration
.flake8                 # Flake8 configuration
.pre-commit-config.yaml # Pre-commit hook configuration
```

## 4. Data Schema

### Current Schema (`database.py`)

```sql
-- Stores basic device tracking info
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY, -- Original MAC Address
    anonymous_id TEXT UNIQUE,   -- Hashed MAC Address
    first_seen DATETIME,
    last_seen DATETIME,
    status TEXT CHECK(status IN ('present', 'absent', 'departed')) -- Managed by PresenceTracker
);

-- Logs individual presence events
CREATE TABLE presence_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,             -- Original MAC Address
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT,                -- e.g., 'detected', 'absent', 'departed'
    rssi INTEGER,
    FOREIGN KEY(device_id) REFERENCES devices(device_id)
);

-- Stores detailed device information when available
CREATE TABLE device_info (
    device_id TEXT PRIMARY KEY, -- Original MAC Address
    device_name TEXT,
    device_type TEXT,           -- e.g., 'phone', 'laptop' (future enhancement)
    vendor_name TEXT,
    model_number TEXT,
    first_detected DATETIME,
    last_detected DATETIME,
    FOREIGN KEY(device_id) REFERENCES devices(device_id)
);
```

### Planned Schema Enhancements (`device_tracking_enhancement_plan.md`)

```sql
-- Potential future table for aggregated stats
CREATE TABLE occupancy_aggregates (
    date DATE,
    hour INTEGER,
    present_count INTEGER,
    PRIMARY KEY(date, hour)
);

-- Potential future table for vendor-specific stats
CREATE TABLE vendor_stats (
    date DATE,
    vendor_name TEXT,
    device_count INTEGER,
    avg_presence_minutes INTEGER,
    PRIMARY KEY(date, vendor_name)
);
```

## 5. Configuration

Key parameters are defined in `fablab_visitor_logger/config.py`. See [README.md](README.md#configuration) for a list of user-configurable parameters.

### Internal Configuration Parameters (`fablab_presence_tracking_specs.md`)

| Parameter           | Default | Description                                  | Module        |
| ------------------- | ------- | -------------------------------------------- | ------------- |
| `PING_TIMEOUT`        | 3       | Missed pings before device marked 'absent' | `scanner.py`  |
| `DEPARTURE_THRESHOLD` | 5       | 'Absent' pings before device marked 'departed' | `scanner.py`  |
| `ANONYMIZE_SALT`    | (random)| Salt used for hashing MAC addresses        | `database.py` |

## 6. Development Guidelines

### Coding Standards

-   **Python Version**: 3.9+
-   **Style**: PEP 8 compliant, enforced by `flake8`.
-   **Formatting**: `black` with line length 88, `isort` for imports (black profile). Run `make format`.
-   **Type Hints**: Required for all function signatures, checked by `mypy`.
-   **Docstrings**: Google style for all public modules, classes, and functions.
-   **Naming**: `snake_case` for variables/functions, `CamelCase` for classes.
-   **Error Handling**: Use specific exception types. Catch exceptions appropriately and log errors. Avoid broad `except Exception:`.
-   **Logging**: Use the standard `logging` module configured in `config.py`. Add contextual information where helpful.

### Test-Driven Development (TDD) / Behavior-Driven Development (BDD)

-   **Coverage**: Aim for high test coverage (>90%). Check with `make coverage`.
-   **Unit Tests**: Test individual functions and classes in isolation. Use `mock` extensively, especially for hardware (BLE) and database interactions.
-   **Integration Tests**: Test interactions between components (e.g., scanner -> database).
-   **Fixtures**: Prefer `pytest` fixtures for setting up test preconditions.
-   **Markers**: Mark tests requiring specific hardware (e.g., BLE) with `@pytest.mark.ble_required`. These are skipped by default in `make test`.
-   **BDD (Optional)**: Use Gherkin (`.feature` files) and `pytest-bdd` for describing high-level features if desired (see `tdd_improvement_plan.md` for examples).

### Security Practices

-   **Input Validation**: Sanitize inputs, especially for file paths (e.g., CSV export) or data used in database queries.
-   **Database Security**:
    -   Always use parameterized queries (`?` placeholders) to prevent SQL injection.
    -   Ensure the database file has appropriate permissions.
-   **BLE Permissions**: Scanning requires specific capabilities (`cap_net_raw`, `cap_net_admin`). Avoid running the entire application as root if possible. Use `setcap` as described in the README.
-   **Dependencies**: Keep dependencies updated. Use `safety check` (via `make security` or pre-commit) to check for known vulnerabilities.
-   **Secrets**: Do not commit secrets (API keys, salts if made configurable) directly into the repository. Use environment variables or a secure configuration method if needed.

### Git Workflow & Commits

-   Use feature branches for new work.
-   Write clear and concise commit messages (e.g., `feat: add csv export functionality`, `fix: resolve database connection leak`, `refactor(scanner): simplify device processing logic`).
-   Run `pre-commit` hooks before committing (run `pre-commit install` once).
-   Ensure all checks pass (`make check`) before pushing.

## 7. Implementation Plans & History

*(This section summarizes past and present plans derived from various planning documents)*

### Initial Implementation Phases (`fablab_visitor_logger_design.md`, `fablab_visitor_logger_implementation_plan.md`)

1.  **Core Scanning Module**: Basic BLE discovery, MAC/RSSI collection.
2.  **Data Storage Layer**: SQLite setup, data insertion, basic maintenance.
3.  **Main Application**: Configuration, main loop, shutdown handling.
4.  **Reporting Interface**: CLI commands (`list-devices`, `stats`, `export-csv`).
5.  **Deployment**: Systemd service, documentation.

### Quality Improvement Plan (`improvement_implementation_plan.md`, `tdd_improvement_plan.md`)

*   **Focus**: Code quality, testing, GitHub workflow optimization.
*   **Phase 1 (Completed/In Progress)**:
    *   Fix duplicate code in `BLEScanner`.
    *   Add comprehensive type annotations.
    *   Unify vendor information (create `vendor.py`).
*   **Phase 2 (Planned)**:
    *   Enhance error handling (retries, recovery).
    *   Improve database connection management (context managers).
    *   Expand test coverage (error scenarios, edge cases).
*   **Phase 3 (Planned)**:
    *   Optimize GitHub Actions (caching, parallel tests).
    *   Integrate quality checks directly into `pytest` run (`pytest.ini`).

### Device Tracking Enhancement Plan (`device_tracking_enhancement_plan.md`)

*   **Objective**: Capture more detailed device info (type, name, model), enhance vendor stats.
*   **Steps**:
    *   Update scanner to extract more advertisement data.
    *   Implement TDD for new parsing/storage logic.
    *   Add new reporting functions (`get_vendor_stats`, `get_device_type_trends`).
    *   Update database schema (see Section 4).

## 8. Testing Strategy

-   **Framework**: `pytest`
-   **Coverage**: Measured using `pytest-cov`. Report via `make coverage`.
-   **Structure**: Tests are located in the `tests/` directory, mirroring the main application structure (e.g., `tests/test_scanner.py`).
-   **Mocking**: The `unittest.mock` library (via `pytest-mock`) is used extensively to isolate components and simulate hardware/external interactions.
-   **Asynchronous Code**: `pytest-asyncio` is used for testing `async`/`await` code (relevant for `bleak`).
-   **Hardware Tests**: Tests requiring a physical BLE adapter are marked with `@pytest.mark.ble_required` and are skipped by default. Run them explicitly with `pytest -m "ble_required"`.
-   **CI**: Tests (excluding hardware tests) are run automatically via GitHub Actions on pushes/pull requests (see `.github/workflows/tests.yml`).

### Key Test Commands

See [README.md](README.md#quality-checks--testing) for common `make` and `pytest` commands.

### Example Test (`tdd_improvement_plan.md`)

```python
# tests/test_scanner.py (Illustrative Example)
def test_scan_returns_devices(mocker):
    """Test scan returns list of devices with expected fields"""
    # Mock the bleak Scanner
    mock_scanner_cls = mocker.patch('bleak.BleakScanner')
    mock_scanner_instance = mock_scanner_cls.return_value
    mock_device = mocker.MagicMock()
    mock_device.address = "AA:BB:CC:DD:EE:FF"
    mock_device.rssi = -50
    mock_device.metadata = {'manufacturer_data': {}} # Example metadata
    # Simulate scan results
    async def mock_scan(*args, **kwargs):
        return [mock_device]
    mock_scanner_instance.discover = mock_scan # Assuming discover is the method

    scanner = BLEScanner() # Assuming BLEScanner uses BleakScanner internally
    # Need to run async scan appropriately
    import asyncio
    devices = asyncio.run(scanner.scan(duration=0.1)) # Example async call

    assert len(devices) == 1
    assert devices[0]["mac_address"] == "AA:BB:CC:DD:EE:FF"
    assert devices[0]["rssi"] == -50
```

## 9. Build, Lint, Test Commands

Refer to the [Makefile](Makefile) and the [README.md](README.md#quality-checks--testing) for the primary commands (`make check`, `make test`, `make lint`, etc.) and pre-commit hook setup.

## 10. Deployment

-   **Method**: Systemd service (see `deployment/fablab-logger.service`).
-   **Setup**: Described in [README.md](README.md#installation).
-   **Considerations**:
    -   Ensure the service runs as a non-root user if possible, after granting necessary capabilities via `setcap`.
    -   Configure paths correctly in the `.service` file (`WorkingDirectory`, `ExecStart`).
    -   Set up log rotation for the application log file (`presence_tracker.log`) and potentially the systemd journal.

## 11. Future Enhancements & Improvement Suggestions

*(Compiled from `improvement_suggestions.md`, `device_tracking_enhancement_plan.md`, `fablab_presence_tracking_specs.md`)*

### Code Quality / Refactoring

-   Implement robust error handling (retries, backoff) for scanner/DB operations.
-   Use context managers for database connections (`with Database() as db:`).
-   Consider database connection pooling for higher loads.
-   Centralize more configuration values in `config.py`.
-   Enhance logging with more structure/context.
-   Complete type annotation coverage.
-   Address any remaining test coverage gaps, especially error/edge cases.

### Feature Enhancements

-   **Device Identification**:
    -   Implement full OUI database lookup (replace/extend `vendor.py`).
    -   Parse more BLE advertisement data (device name, services, manufacturer data) to classify device types (phone, laptop, etc.).
    -   Store and report on detailed device info.
-   **Analytics & Reporting**:
    -   Implement RSSI-to-distance estimation.
    -   Develop advanced statistics (vendor distribution, device type trends, peak times).
    -   Create daily/hourly occupancy aggregates.
-   **Privacy**:
    -   Implement configurable data retention policies.
    -   Consider an opt-in/out mechanism.
-   **API/UI**:
    -   Develop a simple web interface/dashboard for real-time monitoring.
    -   Create a REST API for programmatic data access.

## 12. Specific Workflows

### Batch Refactoring Example (`batch_implementation_workflow.md`)

*This describes a past workflow for a specific refactoring task.*

-   **Task**: Refactor `BLEScanner` (consolidate code, add types, extract vendor logic).
-   **Verification**: Run specific tests (`test_scanner.py`, `test_database.py`) locally. Run `pre-commit run --all-files`.
-   **Commit**: Single atomic commit (`git commit -m "refactor(scanner): ..."`).
-   **CI**: Monitor GitHub Actions run (`gh run watch ...`).

*(End of DEVELOPMENT.md)*
