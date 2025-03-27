import argparse
import logging
import signal
import sys
import time

from fablab_visitor_logger.config import Config
from fablab_visitor_logger.database import Database
from fablab_visitor_logger.scanner import BLEScanner, PresenceTracker


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="FabLab Visitor Logger")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Scan mode (default behavior)
    scan_parser = subparsers.add_parser("scan", help="Run continuous scanning")

    # Report mode
    report_parser = subparsers.add_parser("report", help="Reporting commands")
    report_parser.add_argument(
        "command",
        choices=["list-devices", "stats", "export-csv"],
        help="Reporting command to execute",
    )
    report_parser.add_argument(
        "--output", help="Output file path for export-csv"
    )
    report_parser.add_argument(
        "--active",
        action="store_true",
        help="Show only active devices for list-devices",
    )
    
    return parser.parse_args()


class PresenceMonitoringApp:
    def __init__(self):
        Config.setup_logging()
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.scanner = BLEScanner()
        self.db = Database()
        self.tracker = PresenceTracker(self.scanner, self.db)

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def run(self):
        self.running = True
        self.logger.info("Starting FabLab Presence Monitoring System")

        try:
            iteration = 0
            while self.running:
                iteration += 1
                self.logger.debug(f"Starting iteration {iteration}")
                start_time = time.time()

                try:
                    device_count = self.tracker.update_presence()
                    self.logger.info(
                        f"Scan complete, detected {device_count} devices"
                    )
                    self.db.cleanup_old_data()
                except Exception as e:
                    self.logger.error(f"Error during scan: {str(e)}")
                    # Break on error if we're in test mode
                    if hasattr(self, "_test_mode"):
                        self.running = False
                        break

                # Double-check running flag before sleep
                if not self.running:
                    self.logger.debug("Loop stopping due to running=False")
                    break

                # Sleep for remaining interval time
                elapsed = time.time() - start_time
                if elapsed < Config.SCAN_INTERVAL:
                    sleep_time = Config.SCAN_INTERVAL - elapsed
                    self.logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                else:
                    self.logger.debug(
                        "Scan took longer than interval, skipping sleep"
                    )

        except Exception as e:
            self.logger.critical(f"Fatal error: {str(e)}")
            raise
        finally:
            self.running = False
            self.logger.info("FabLab Presence Monitoring System stopped")


def main():
    """Main entry point for CLI"""
    args = parse_args()

    if args.mode == "scan":
        app = PresenceMonitoringApp()
        app.run()
    elif args.mode == "report":
        from fablab_visitor_logger.reporting import Reporter

        reporter = Reporter()

        try:
            if args.command == "list-devices":
                devices = reporter.list_devices(args.active)
                for device in devices:
                    print(f"{device['device_id']} ({device['status']})")
            elif args.command == "stats":
                stats = reporter.get_stats()
                print(f"Total unique devices: {stats['total_devices']}")
                print(f"Currently present: {stats['present_devices']}")
                print(f"Visits in last 24h: {stats['recent_visits']}")
            elif args.command == "export-csv":
                if not args.output:
                    raise ValueError("Output path required for export-csv")
                reporter.export_csv(args.output)
                print(f"Data exported to {args.output}")
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
