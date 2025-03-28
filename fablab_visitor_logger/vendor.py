"""Centralized vendor identification module with caching."""

from functools import lru_cache
from typing import Dict

VENDOR_MAP: Dict[str, str] = {
    "A4C138": "Apple",
    "4C0B3E": "Google",
    "D4F057": "Samsung",
    "B827EB": "Raspberry Pi",
    "F0F8F2": "Xiaomi",
    "001CBF": "Apple",
    "001D4F": "Samsung",
    "0022F4": "Intel",
}


@lru_cache(maxsize=128)
def get_vendor(mac: str) -> str:
    """Get vendor name from MAC address with caching.

    Args:
        mac: MAC address in format 'AA:BB:CC:DD:EE:FF'

    Returns:
        Vendor name or 'Unknown' if not found
    """
    try:
        # First 3 bytes of MAC are OUI (Organizationally Unique Identifier)
        oui = mac[:8].upper().replace(":", "")[:6]
        return VENDOR_MAP.get(oui, "Unknown")
    except (AttributeError, IndexError):
        return "Unknown"
