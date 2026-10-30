"""Debug support for hoerfrau, a simulated drive (github.com/DennyWeinberg/hoerfrau-ble).

The simulator runs on a Mac, and macOS can't advertise manufacturer data - so
it shows up with only a local name, HFSIM + the last 4 serial digits, and
serves the advertisement a real drive would send from a debug characteristic
instead. Everything here keys on that name prefix: a real drive never takes
these paths.
"""

from __future__ import annotations

import json
import logging

from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from hoermoles_ble import AdvertisementInfo
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)

SIMULATOR_NAME_PREFIX = "HFSIM"
# Read + notify, JSON: {"company_id": 1972, "packets": ["<short hex>", "<long hex>"], "serial_no": ...}
DEBUG_ADVERTISEMENT_CHAR = "686f6572-6672-6175-0002-000000000000"


def is_simulator(service_info: BluetoothServiceInfoBleak) -> bool:
    return (service_info.name or "").startswith(SIMULATOR_NAME_PREFIX)


async def async_read_advertisement(ble_device: BLEDevice, rssi: int) -> AdvertisementInfo:
    """The advertisement the simulated drive would send, read over GATT."""
    client = await establish_connection(BleakClientWithServiceCache, ble_device, SIMULATOR_NAME_PREFIX, max_attempts=2)
    try:
        raw = await client.read_gatt_char(DEBUG_ADVERTISEMENT_CHAR)
    finally:
        await client.disconnect()
    packets = [bytes.fromhex(packet) for packet in json.loads(raw)["packets"]]
    _LOGGER.debug("Simulator %s advertises %s", ble_device.address, [p.hex() for p in packets])
    return AdvertisementInfo.from_scan(ble_device.address, rssi, packets)
