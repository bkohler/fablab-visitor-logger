import argparse
import asyncio  # Import asyncio
import logging
import signal
import sys
import time  # Keep time for time.time()

from fablab_visitor_logger.config import Config
from fablab_visitor_logger.database import Database

# Import Reporter here for report mode handling
from fablab_visitor_logger.reporting import Reporter
from fablab_visitor_logger.scanner import BLEScanner, PresenceTracker


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="FabLab Visitor Logger")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Scan mode (default behavior)
    subparsers.add_parser("scan", help="Run continuous scanning")

    # Report mode
    report_parser = subparsers.add_parser("report", help="Reporting commands")
    report_subparsers = report_parser.add_subparsers(dest="command", required=True)

    # List devices command
    list_parser = report_subparsers.add_parser(
        "list-devices", help="List all detected devices"
    )
    list_parser.add_argument(
        "--active", action="store_true", help="Show only active devices"
    )

    # Stats command
    report_subparsers.add_parser("stats", help="Show visitor statistics")

    # Export command
    export_parser = report_subparsers.add_parser(
        "export-csv", help="Export data to CSV"
    )
    export_parser.add_argument("output_path", help="Path to output CSV file")

    return parser.parse_args()


class PresenceMonitoringApp:
    def __init__(self):
        Config.setup_logging()
        self.logger = logging.getLogger(__name__)
        self.running = False
        # Dependencies could be injected here in a future refactor
        self.scanner = BLEScanner()
        self.db = Database()
        self.tracker = PresenceTracker(self.scanner, self.db)
        self._shutdown_event = asyncio.Event()  # Use asyncio Event for shutdown

    def _handle_signal(self, signum, frame):
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        # Set the event to signal the run loop to stop
        self._shutdown_event.set()
        # Setting self.running = False might still be useful for immediate checks
        self.running = False

    # Make run method asynchronous
    async def run(self):
        # Setup signal handlers within the async context if possible,
        # or ensure they correctly interact with the asyncio event loop.
        # Using loop.add_signal_handler is generally preferred in async code.
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_signal, sig, None)

        self.running = True  # Initial state
        self.logger.info("Starting FabLab Presence Monitoring System (Async)")

        try:
            iteration = 0
            while not self._shutdown_event.is_set():  # Check asyncio event
                iteration += 1
                self.logger.debug(f"Starting async iteration {iteration}")
                start_time = time.time()

                try:
                    # Await the async presence update
                    print("[DEBUG] main.py: Before await self.tracker.update_presence()") # DEBUG
                    device_count = await self.tracker.update_presence()
                    print(f"[DEBUG] main.py: After await self.tracker.update_presence(), count={device_count}") # DEBUG
                    self.logger.info(
                        f"Async scan complete, detected {device_count} devices"
                    )
                    # Consider making cleanup async if it involves I/O,
                    # but for now assume it's quick enough or refactor later.
                    self.db.cleanup_old_data()
                except Exception as e:
                    # Log error but continue loop unless it's critical
                    self.logger.error(
                        f"Error during async presence update: {e}", exc_info=True
                    )
                    # Maybe add a short sleep after error before retrying
                    await asyncio.sleep(5)  # Sleep briefly after an error

                # Check shutdown event again before sleep
                if self._shutdown_event.is_set():
                    self.logger.debug("Shutdown event set, exiting loop.")
                    break

                # Sleep asynchronously for remaining interval time
                elapsed = time.time() - start_time
                sleep_time = Config.SCAN_INTERVAL - elapsed
                if sleep_time > 0:
                    self.logger.debug(
                        f"Sleeping asynchronously for {sleep_time:.2f} seconds"
                    )
                    # Simpler sleep - rely on the loop condition and signal handler
                    print(f"[DEBUG] main.py: Before await asyncio.sleep({sleep_time})") # DEBUG
                    await asyncio.sleep(sleep_time)
                    print(f"[DEBUG] main.py: After await asyncio.sleep({sleep_time})") # DEBUG
                else:
                    self.logger.warning(
                        f"Scan iteration took longer ({elapsed:.2f}s) than interval "
                        f"({Config.SCAN_INTERVAL}s), skipping sleep."
                    )

        except asyncio.CancelledError:
            self.logger.info("Run loop cancelled.")
        except Exception as e:
            self.logger.critical(f"Fatal error in async run loop: {e}", exc_info=True)
            # Potentially re-raise or handle differently
        finally:
            self.running = False  # Ensure flag is false on exit
            self.logger.info("FabLab Presence Monitoring System stopped")


def main():
    """Main entry point for CLI"""
    args = parse_args()

    if args.mode == "scan":
        app = PresenceMonitoringApp()
        try:
            # Run the async application using asyncio.run
            asyncio.run(app.run())
        except KeyboardInterrupt:
            # Handle Ctrl+C if asyncio.run doesn't catch it gracefully enough
            logging.getLogger(__name__).info(
                "Scan interrupted by user (KeyboardInterrupt)."
            )
        except Exception as e:
            logging.getLogger(__name__).critical(
                f"Unhandled exception during scan startup or shutdown: {e}",
                exc_info=True,
            )
            sys.exit(1)

    elif args.mode == "report":
        # Simplified report handling: Instantiate Reporter and call methods
        reporter = Reporter()
        try:
            if args.command == "list-devices":
                devices = reporter.list_devices(args.active)
                # Simple console output formatting
                if devices:
                    # Print header (optional)
                    # print("ID | Status | Name | Vendor | Type")
                    # print("-" * 50)
                    for device in devices:
                        output = [
                            f"ID: {device.get('device_id', 'N/A')}",
                            f"Status: {device.get('status', 'N/A')}",
                            f"Name: {device.get('device_name', 'Unknown')}",
                            f"Vendor: {device.get('vendor_name', 'Unknown')}",
                            f"Type: {device.get('device_type', 'Unknown')}",
                        ]
                        print(" | ".join(output))
                else:
                    print("No devices found.")
            elif args.command == "stats":
                stats = reporter.get_stats()
                print(f"Total unique devices: {stats.get('total_devices', 0)}")
                print(f"Currently present: {stats.get('present_devices', 0)}")
                print(f"Visits in last 24h: {stats.get('recent_visits', 0)}\n")

                print("Vendor Breakdown:")
                for vendor, count in stats.get("vendor_breakdown", {}).items():
                    print(f"  {vendor or 'Unknown'}: {count}")

                print("\nDevice Type Breakdown:")
                for dev_type, count in stats.get("type_breakdown", {}).items():
                    print(f"  {dev_type or 'Unknown'}: {count}")

            elif args.command == "export-csv":
                # output_path is now required by argparse for this command
                reporter.export_csv(args.output_path)
                print(f"Data exported to {args.output_path}")

        except Exception as e:
            print(f"Error during report generation: {str(e)}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
