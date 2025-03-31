from behave import given, then, when

from fablab_visitor_logger.database import Database


@given('a BLE device is detected with vendor "{vendor}"')
def step_given_ble_device_detected(context, vendor):
    context.db = Database()
    context.device_info = {
        "device_name": "Test Device",
        "vendor_name": vendor,
        "manufacturer_data": {0xFFFF: b"test"},
    }


@given("a device exists in the database")
def step_given_device_exists(context):
    context.db = Database()
    # Create test device
    context.db.log_device_info(
        "AA:BB:CC:DD:EE:FF", {"device_name": "Old Device", "vendor_name": "Old Vendor"}
    )


@when("the device info is logged")
def step_when_device_info_logged(context):
    context.db.log_device_info("AA:BB:CC:DD:EE:FF", context.device_info)


@when('new vendor info "{vendor}" is provided')
def step_when_new_vendor_provided(context, vendor):
    context.db.log_device_info("AA:BB:CC:DD:EE:FF", {"vendor_name": vendor})


@then('the database should update to vendor "{vendor}"')
def step_then_database_updates_vendor(context, vendor):
    # Verify database contains the updated vendor name
    with context.db.conn:
        cursor = context.db.conn.cursor()
        cursor.execute(
            "SELECT vendor_name FROM device_info WHERE device_id=?",
            ("AA:BB:CC:DD:EE:FF",),
        )
        result = cursor.fetchone()
        assert result[0] == vendor


@then('the database should store "{vendor}" as vendor_name')
def step_then_database_stores_vendor(context, vendor):
    # Verify database contains the vendor name
    with context.db.conn:
        cursor = context.db.conn.cursor()
        cursor.execute(
            "SELECT vendor_name FROM device_info WHERE device_id=?",
            ("AA:BB:CC:DD:EE:FF",),
        )
        result = cursor.fetchone()
        assert result[0] == vendor
