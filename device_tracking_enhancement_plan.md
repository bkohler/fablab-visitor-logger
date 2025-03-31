# Device Tracking Enhancement Plan

## Objective
Enhance the BLE device tracking system to:
1. Capture detailed device type (e.g., iPhone 14, MacBook Pro)
2. Store full vendor information
3. Implement statistics based on vendor/type

## Database Schema Changes

```sql
-- New device_info table
CREATE TABLE device_info (
    device_id TEXT PRIMARY KEY,
    device_name TEXT,
    device_type TEXT,
    vendor_name TEXT,
    model_number TEXT,
    first_detected DATETIME,
    last_detected DATETIME,
    FOREIGN KEY(device_id) REFERENCES devices(device_id)
);

-- Vendor statistics table
CREATE TABLE vendor_stats (
    date DATE,
    vendor_name TEXT,
    device_count INTEGER,
    avg_presence_minutes INTEGER,
    PRIMARY KEY(date, vendor_name)
);
```

## Implementation Steps

1. **Scanner Updates**:
   - Extract device name from advertisement data
   - Parse manufacturer data for vendor info
   - Classify devices using BLE service UUIDs

2. **TDD Approach**:
   - Write tests first for each component
   - 100% test coverage requirement
   - Linting (flake8) and security (bandit) checks

3. **Reporting System**:
   ```python
   def get_vendor_stats(start_date, end_date):
       """Return vendor distribution statistics"""
       pass

   def get_device_type_trends():
       """Return device type trends over time"""
       pass
   ```

4. **CI/CD Requirements**:
   - All tests must pass
   - 100% code coverage
   - No linting errors
   - No security vulnerabilities
