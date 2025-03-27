import argparse
import csv
import sys
from typing import Any, Dict, List

from fablab_visitor_logger.database import Database


class Reporter:
    def __init__(self):
        self.db = Database()

    def list_devices(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all detected devices with their status"""
        with self.db.conn:
            cursor = self.db.conn.cursor()
            query = "SELECT device_id, anonymous_id, status FROM devices"
            if active_only:
                query += " WHERE status IN ('present', 'absent')"
            cursor.execute(query)
            return [
                dict(zip(["device_id", "anonymous_id", "status"], row))
                for row in cursor.fetchall()
            ]

    def get_stats(self) -> Dict[str, Any]:
        """Get visitor statistics"""
        stats = {}
        with self.db.conn:
            cursor = self.db.conn.cursor()

            # Total unique devices
            cursor.execute("SELECT COUNT(DISTINCT device_id) FROM devices")
            stats["total_devices"] = cursor.fetchone()[0]

            # Currently present devices
            cursor.execute(
                "SELECT COUNT(*) FROM devices WHERE status = 'present'"
            )
            stats["present_devices"] = cursor.fetchone()[0]

            # Visits in last 24 hours
            cursor.execute(
                """
                SELECT COUNT(*) FROM presence_logs
                WHERE timestamp > datetime('now', '-1 day')
            """
            )
            stats["recent_visits"] = cursor.fetchone()[0]

        return stats

    def export_csv(self, output_path: str) -> None:
        """Export all presence logs to CSV"""
        if not output_path.endswith(".csv"):
            raise ValueError("Output path must end with .csv")

        data = []
        with self.db.conn:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT device_id, timestamp, status, rssi
                FROM presence_logs
                ORDER BY timestamp DESC
            """
            )
            data = cursor.fetchall()

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["device_id", "timestamp", "status", "rssi"])
            writer.writerows(data)


def main():
    parser = argparse.ArgumentParser(
        description="FabLab Visitor Logger Reporting Interface",
        prog="fablab-report",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List devices command
    list_parser = subparsers.add_parser(
        "list-devices", help="List all detected devices"
    )
    list_parser.add_argument(
        "--active", action="store_true", help="Show only active devices"
    )

    # Stats command
    stats_parser = subparsers.add_parser(  # noqa: F841
        "stats", help="Show visitor statistics"
    )

    # Export command
    export_parser = subparsers.add_parser(
        "export-csv", help="Export data to CSV"
    )
    export_parser.add_argument("output_path", help="Path to output CSV file")

    args = parser.parse_args()
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
            reporter.export_csv(args.output_path)
            print(f"Data exported to {args.output_path}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
