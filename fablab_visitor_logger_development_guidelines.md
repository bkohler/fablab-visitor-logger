# FabLab Visitor Logger - Development Guidelines (Updated)

## 1. Command-Line Interface Development
- **CLI Command Structure**
  ```mermaid
  graph TD
    A[main.py] --> B[Scan Mode]
    A --> C[Report Mode]
    C --> D[list-devices]
    C --> E[stats]
    C --> F[export-csv]
  ```
- **Required Commands**
  - `scan`: Start continuous scanning (default)
  - `report list-devices`: Show all detected devices
  - `report stats`: Show visit statistics
  - `report export-csv`: Export data to CSV

## 2. Test-Driven Development
- **100% Test Coverage**
  - Unit tests for all CLI commands
  - Mock testing for BLE interactions
  - Database operation verification
- **CLI Test Cases**
  - Command parsing validation
  - Output format verification
  - Error handling tests

## 3. Security Practices
- **Input Validation**
  - Sanitize all CLI inputs
  - Validate file paths for exports
- **Database Security**
  - Maintain parameterized queries
  - Secure default permissions

## 4. Development Standards
- **Python Requirements**
  - Python 3.9+ compatibility
  - PEP 8 compliance
  - Type hints for all functions
- **Documentation**
  - Help text for all CLI commands
  - Man page generation
  - Usage examples in README

## 5. Deployment Guidelines
- **Systemd Service**
  - Log rotation configuration
  - Resource limits
  - Secure runtime user
- **Installation**
  - Dependency installation
  - Database initialization
  - Permission setup
