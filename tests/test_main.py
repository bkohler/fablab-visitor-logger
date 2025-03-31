"""Tests for the main application module."""

import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fablab_visitor_logger.main import PresenceMonitoringApp

# Using pytest structure instead of unittest.TestCase for consistency
# and better integration with pytest-asyncio


@pytest.fixture
def mock_dependencies():
    """Fixture to provide mocks for app dependencies."""
    with patch("fablab_visitor_logger.main.BLEScanner") as mock_scanner, patch(
        "fablab_visitor_logger.main.Database"
    ) as mock_db, patch(
        "fablab_visitor_logger.main.PresenceTracker"
    ) as mock_tracker, patch(
        "fablab_visitor_logger.main.Config"
    ) as mock_config:
        # Configure mock instances
        mock_scanner_instance = MagicMock()
        mock_scanner.return_value = mock_scanner_instance

        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance

        # Configure the mock class to return the desired instance when called
        mock_tracker_instance = AsyncMock()
        # Set up the update_presence method to return a value when awaited
        mock_tracker_instance.update_presence.return_value = 3
        mock_tracker.return_value = mock_tracker_instance

        # Set a default scan interval for tests
        mock_config.SCAN_INTERVAL = 30

        yield {
            "scanner": mock_scanner,
            "db": mock_db,
            "tracker": mock_tracker,  # Yield the mock class object
            "scanner_instance": mock_scanner_instance,
            "db_instance": mock_db_instance,
            # Yield the configured mock instance
            "tracker_instance": mock_tracker_instance,
            "config": mock_config,
        }


def test_signal_handling(mock_dependencies):
    """Test application handles signals properly by setting running flag."""
    app = PresenceMonitoringApp()
    # Ensure running is initially True or set it for the test context if needed
    app.running = True
    app._handle_signal(signal.SIGINT, None)
    assert app.running is False


@pytest.mark.asyncio
@patch("asyncio.sleep")
async def test_run_loop_single_iteration(mock_asyncio_sleep, mock_dependencies):
    """Test main application async loop executes one iteration correctly."""
    # Get the pre-configured mock instances from the fixture
    mock_scanner_instance = mock_dependencies["scanner_instance"]
    mock_db_instance = mock_dependencies["db_instance"]
    mock_tracker_instance = mock_dependencies["tracker_instance"]

    # Inject mocks into app instance
    app = PresenceMonitoringApp(
        scanner=mock_scanner_instance,
        db=mock_db_instance,
        tracker=mock_tracker_instance,
    )

    # Modify sleep mock to stop the loop after the first call
    async def sleep_and_stop(*args, **kwargs):
        print("[DEBUG] test_run_loop_single_iteration: sleep_and_stop called")  # DEBUG
        app._shutdown_event.set()  # Signal shutdown when sleep is called
        return None

    mock_asyncio_sleep.side_effect = sleep_and_stop

    # Run the loop - it should exit after one iteration due to the sleep mock
    print("[DEBUG] test_run_loop_single_iteration: Before await app.run()")  # DEBUG
    await app.run()
    print("[DEBUG] test_run_loop_single_iteration: After await app.run()")  # DEBUG

    # Verify key interactions
    mock_tracker_instance.update_presence.assert_awaited_once()
    mock_db_instance.cleanup_old_data.assert_called_once()
    # Cannot easily verify exact sleep duration without time mock,
    # but assert_awaited confirms sleep logic was reached
    mock_asyncio_sleep.assert_awaited()  # Ensure sleep was called to stop loop


@pytest.mark.asyncio
@patch("asyncio.sleep")
async def test_run_loop_error_handling(mock_asyncio_sleep, mock_dependencies):
    """Test application handles errors during tracker update gracefully."""
    # Get the pre-configured mock instances from the fixture
    mock_scanner_instance = mock_dependencies["scanner_instance"]
    mock_db_instance = mock_dependencies["db_instance"]

    # Create a new tracker mock with error behavior
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_presence.side_effect = Exception("Scan error")

    # Inject mocks into app instance
    app = PresenceMonitoringApp(
        scanner=mock_scanner_instance,
        db=mock_db_instance,
        tracker=mock_tracker_instance,
    )

    # Modify sleep mock to stop the loop after the error handling sleep
    async def sleep_and_stop_after_error(*args, **kwargs):
        print(
            "[DEBUG] test_run_loop_error_handling: sleep_and_stop_after_error called"
        )  # DEBUG
        app._shutdown_event.set()
        return None

    mock_asyncio_sleep.side_effect = sleep_and_stop_after_error

    # Run the loop - it should hit the error, log, sleep, then exit
    print("[DEBUG] test_run_loop_error_handling: Before await app.run()")  # DEBUG
    await app.run()
    print("[DEBUG] test_run_loop_error_handling: After await app.run()")  # DEBUG

    # Verify error was handled by checking the sleep call in the except block
    mock_tracker_instance.update_presence.assert_awaited_once()
    mock_asyncio_sleep.assert_awaited_with(5)


@pytest.mark.asyncio
@patch("fablab_visitor_logger.main.PresenceMonitoringApp")
@patch("fablab_visitor_logger.main.parse_args")
@patch("asyncio.run")  # To check if asyncio.run is called
async def test_main_scan_mode(mock_asyncio_run, mock_parse_args, mock_app_class):
    """Test main() function correctly initiates scan mode."""
    # Setup mocks
    mock_args = MagicMock()
    mock_args.mode = "scan"
    mock_parse_args.return_value = mock_args

    # Create a mock instance for the app using MagicMock
    mock_app_instance = MagicMock(spec=PresenceMonitoringApp)
    # Explicitly make its 'run' method an AsyncMock
    mock_app_instance.run = AsyncMock()
    mock_app_class.return_value = mock_app_instance

    # Run main
    # Need to import main inside the test or ensure it's available
    from fablab_visitor_logger.main import main

    print("[DEBUG] test_main_scan_mode: Before main()")  # DEBUG
    main()
    print("[DEBUG] test_main_scan_mode: After main()")  # DEBUG

    # Verify
    mock_parse_args.assert_called_once()
    mock_app_class.assert_called_once()  # App was instantiated
    # Check that asyncio.run was called with the app's run method
    # Avoid comparing coroutine objects directly
    # Check that app.run() was called (which returns a coroutine)
    mock_app_instance.run.assert_called_once()

    # Check that asyncio.run was called once with the coroutine returned by app.run()
    mock_asyncio_run.assert_called_once()
    call_args, _ = mock_asyncio_run.call_args
    import asyncio

    assert asyncio.iscoroutine(call_args[0])  # Verify it received a coroutine


# --- Report Mode Tests (remain synchronous) ---


@patch("fablab_visitor_logger.main.sys")
@patch("fablab_visitor_logger.main.parse_args")
@patch("fablab_visitor_logger.main.Reporter")  # Patch where Reporter is used in main()
def test_report_mode_list(mock_reporter, mock_parse_args, mock_sys, capsys):
    """Test report mode CLI functionality for list-devices."""
    # Setup mocks
    mock_args = MagicMock()
    mock_args.mode = "report"
    mock_args.command = "list-devices"
    mock_args.active = False
    mock_parse_args.return_value = mock_args

    mock_reporter_instance = MagicMock()
    mock_reporter.return_value = mock_reporter_instance
    mock_reporter_instance.list_devices.return_value = [
        {
            "device_id": "test1",
            "status": "present",
            "device_name": "Dev1",
            "vendor_name": "VendorA",
            "device_type": "TypeX",
        },
    ]

    # Run test
    from fablab_visitor_logger.main import main

    main()

    # Verify
    mock_reporter_instance.list_devices.assert_called_once_with(False)
    captured = capsys.readouterr()
    assert (
        "ID: test1 | Status: present | Name: Dev1 | Vendor: VendorA | Type: TypeX"
        in captured.out
    )


# Remove mock_sys from parameters and patch decorator
@patch("fablab_visitor_logger.main.parse_args")
@patch("fablab_visitor_logger.main.Reporter")  # Patch where Reporter is used in main()
def test_report_mode_error(mock_reporter, mock_parse_args):
    """Test report mode error handling when reporter fails."""
    # Setup mocks
    mock_args = MagicMock()
    mock_args.mode = "report"
    mock_args.command = "stats"  # Example command
    mock_parse_args.return_value = mock_args

    mock_reporter_instance = MagicMock()
    mock_reporter.return_value = mock_reporter_instance
    mock_reporter_instance.get_stats.side_effect = ValueError(
        "Test DB error"
    )  # Simulate error

    # Run test and assert SystemExit(1) is raised
    from fablab_visitor_logger.main import main

    with pytest.raises(SystemExit) as excinfo:
        main()

    # Verify the exit code was 1
    assert excinfo.value.code == 1
    # Verify stderr write still happened (optional but good)
    # Removed check as sys is not mocked
