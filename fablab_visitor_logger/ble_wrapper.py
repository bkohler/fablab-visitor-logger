#!/usr/bin/env python3
import sys

from scanner import BLEScanner


def main():
    try:
        scanner = BLEScanner()
        devices = scanner.scan(5)  # 5 second scan
        print(f"Found {len(devices)} BLE devices")
        return 0
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
