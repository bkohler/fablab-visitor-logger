# FabLab Visitor Logger - Implementation Plan

## Project Structure
```
fablab_visitor_logger/
├── scanner.py          # Core BLE scanning logic
├── database.py         # SQLite database interactions
├── reporting.py        # CLI reporting functions
├── main.py             # Main application entry point
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
└── deployment/         # Deployment files
    ├── fablab-logger.service
    └── install.sh
```

## Phase 1: Core Scanning Module
1. Create `requirements.txt` with `bluepy`/`bleak`
2. Implement `BLEScanner` class with scan() method
3. Add error handling for BLE interface

## Phase 2: Data Storage Layer
1. Create database connection function
2. Implement table creation on startup
3. Add data insertion with duplicate prevention
4. Create data retrieval functions for reporting

## Phase 3: Main Application
1. Define configuration constants
2. Implement main scanning loop
3. Add graceful shutdown handling

## Phase 4: Reporting Interface
1. Set up CLI argument parsing
2. Implement reporting functions:
   - List unique devices
   - Show statistics
   - Export to CSV

## Phase 5: Deployment
1. Create systemd service file
2. (Optional) Write installation script
3. Document setup and usage
