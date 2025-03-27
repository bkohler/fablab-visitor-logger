import pytest
import signal
from unittest.mock import patch, MagicMock
from main import PresenceMonitoringApp

class TestPresenceMonitoringApp:
    @patch('main.BLEScanner')
    @patch('main.Database')
    @patch('main.PresenceTracker')
    def test_signal_handling(self, mock_tracker, mock_db, mock_scanner):
        """Test application handles signals properly"""
        app = PresenceMonitoringApp()
        app._handle_signal(signal.SIGINT, None)
        assert app.running is False

    @patch('main.BLEScanner')
    @patch('main.Database')
    @patch('main.PresenceTracker')
    @patch('time.sleep')
    @patch('main.logging.getLogger')
    def test_run_loop(self, mock_get_logger, mock_sleep, mock_tracker, mock_db, mock_scanner):
        """Test main application loop execution"""
        # Mock logger to prevent time.time() calls during logging
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        mock_tracker_instance = MagicMock()
        mock_tracker.return_value = mock_tracker_instance
        mock_tracker_instance.update_presence.return_value = 2
        
        app = PresenceMonitoringApp()
        app._test_mode = True
        
        # Mock time.time() with increasing values
        time_values = [0, 1]  # start_time=0, elapsed=1
    
        # Mock sleep to stop after one iteration
        def sleep_side_effect(*args):
            app.running = False
    
        mock_sleep.side_effect = sleep_side_effect
    
        with patch('time.time', side_effect=time_values):
            app.running = True
            app.run()
    
        mock_tracker_instance.update_presence.assert_called_once()

    @patch('main.BLEScanner')
    @patch('main.Database')
    @patch('main.PresenceTracker')
    @patch('time.sleep')
    def test_error_handling(self, mock_sleep, mock_tracker, mock_db, mock_scanner):
        """Test application handles scan errors gracefully"""
        mock_tracker_instance = MagicMock()
        mock_tracker.return_value = mock_tracker_instance
        mock_tracker_instance.update_presence.side_effect = Exception("Scan error")
        
        app = PresenceMonitoringApp()
        app._test_mode = True
        app.running = False  # Stop immediately
        
        app.run()
        
        mock_tracker_instance.update_presence.assert_called_once()
        mock_sleep.assert_not_called()