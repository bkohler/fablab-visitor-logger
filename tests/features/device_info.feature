Feature: Device Information Tracking
  As a system administrator
  I want to track detailed device information
  So I can analyze visitor patterns

  Scenario: Recording device vendor information
    Given a BLE device is detected with vendor "Apple"
    When the device info is logged
    Then the database should store "Apple" as vendor_name

  Scenario: Updating existing device info
    Given a device exists in the database
    When new vendor info "Samsung" is provided
    Then the database should update to vendor "Samsung"