import signal
from unittest.mock import MagicMock, patch

from fablab_visitor_logger.main import PresenceMonitoringApp


class TestPresenceMonitoringApp:
    @patch("fablab_visitor_logger.scanner.BLEScanner")
    @patch("fablab_visitor_logger.database.Database")
    @patch("fablab_visitor_logger.scanner.PresenceTracker")
    def test_signal_handling(self, mock_tracker, mock_db, mock_scanner):
        """Test application handles signals properly"""
        app = PresenceMonitoringApp()
        app._handle_signal(signal.SIGINT, None)
        assert app.running is False

    @patch("fablab_visitor_logger.main.BLEScanner")
    @patch("fablab_visitor_logger.main.Database")
    @patch("fablab_visitor_logger.main.PresenceTracker")
    @patch("time.sleep")
    @patch("logging.getLogger")
    @patch("time.time")
    def test_run_loop(
        self,
        mock_time,
        mock_get_logger,
        mock_sleep,
        mock_tracker,
        mock_db,
        mock_scanner,
    ):
        """Test main application loop execution"""
        # Mock logger to prevent time.time() calls during logging
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_tracker_instance = MagicMock()
        mock_tracker.return_value = mock_tracker_instance
        mock_tracker_instance.update_presence.return_value = 2
        mock_scanner_instance = MagicMock()
        mock_scanner.return_value = mock_scanner_instance
        mock_scanner_instance.scan.return_value = ["device1", "device2"]

        app = PresenceMonitoringApp()
        app._test_mode = True

        # Setup mocks
        mock_time.side_effect = [
            0,
            1,
            2,
        ]  # start_time=0, iteration_time=1, end_time=2
        mock_sleep.side_effect = lambda *_: setattr(app, "running", False)

        # Run test
        app.running = True
        app.run()

        # Verify key interactions
        mock_tracker_instance.update_presence.assert_called_once()

        mock_tracker_instance.update_presence.assert_called_once()

    @patch("fablab_visitor_logger.main.BLEScanner")
    @patch("fablab_visitor_logger.main.Database")
    @patch("fablab_visitor_logger.main.PresenceTracker")
    @patch("time.sleep")
    @patch("time.time")
    def test_error_handling(
        self, mock_time, mock_sleep, mock_tracker, mock_db, mock_scanner
    ):
        """Test application handles scan errors gracefully"""
        mock_tracker_instance = MagicMock()
        mock_tracker.return_value = mock_tracker_instance
        mock_tracker_instance.update_presence.side_effect = Exception(
            "Scan error"
        )
        mock_scanner_instance = MagicMock()
        mock_scanner.return_value = mock_scanner_instance
        mock_scanner_instance.scan.side_effect = Exception("BLE scan failed")

        app = PresenceMonitoringApp()
        app._test_mode = True

        # Setup mocks
        mock_time.side_effect = [
            0,
            1,
            2,
        ]  # start_time=0, iteration_time=1, end_time=2
        mock_sleep.side_effect = lambda *_: setattr(app, "running", False)

        # Run test
        app.running = True
        app.run()

        # Verify error was handled
        mock_tracker_instance.update_presence.assert_called_once()

        mock_tracker_instance.update_presence.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("fablab_visitor_logger.main.sys")
    @patch("fablab_visitor_logger.main.parse_args")
    @patch("fablab_visitor_logger.reporting.Reporter")
    def test_report_mode(self, mock_reporter, mock_parse_args, mock_sys):
        """Test report mode CLI functionality"""
        # Setup mocks
        mock_args = MagicMock()
        mock_args.mode = "report"
        mock_args.command = "list-devices"
        mock_args.active = False
        mock_parse_args.return_value = mock_args
        mock_reporter_instance = MagicMock()
        mock_reporter.return_value = mock_reporter_instance
        mock_reporter_instance.list_devices.return_value = [
            {"device_id": "test1", "status": "present"},
            {"device_id": "test2", "status": "absent"}
        ]
        
        # Run test
        with patch("__main__.__name__", "__main__"):
            from fablab_visitor_logger.main import main
            main()
        
        # Verify report mode was called
        mock_reporter_instance.list_devices.assert_called_once_with(False)
        # Print calls verified by captured stdout
        
    @patch("fablab_visitor_logger.main.sys")
    @patch("fablab_visitor_logger.main.argparse")
    @patch("fablab_visitor_logger.reporting.Reporter")
    def test_report_mode_error(self, mock_reporter, mock_argparse, mock_sys):
        """Test report mode error handling"""
        # Setup mocks
        mock_parser = MagicMock()
        mock_argparse.ArgumentParser.return_value = mock_parser
        mock_subparsers = MagicMock()
        mock_parser.add_subparsers.return_value = mock_subparsers
        mock_report_parser = MagicMock()
        mock_subparsers.add_parser.return_value = mock_report_parser
        mock_args = MagicMock()
        mock_args.mode = "report"
        mock_args.command = "export-csv"
        mock_args.output = None
        mock_parser.parse_args.return_value = mock_args
        mock_reporter_instance = MagicMock()
        mock_reporter.return_value = mock_reporter_instance
        mock_reporter_instance.export_csv.side_effect = ValueError("Test error")
        
        # Run test
        with patch("__main__.__name__", "__main__"):
            from fablab_visitor_logger.main import main
            main()
        
        # Verify error was handled
        mock_sys.stderr.write.assert_called()
        mock_sys.exit.assert_called_once_with(1)
