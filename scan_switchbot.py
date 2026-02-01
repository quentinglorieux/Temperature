import argparse
import asyncio
import json
from typing import Optional

from bleak import BleakScanner

try:
    import TheengsDecoder  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    TheengsDecoder = None


def _uuid16_from_uuid(uuid: str) -> str:
    u = uuid.lower()
    if u.startswith("0000") and u.endswith("-0000-1000-8000-00805f9b34fb"):
        return u[4:8]
    return u.replace("-", "")


def _hex(b: bytes) -> str:
    return b.hex()


def _make_manufacturer_hex(manufacturer_data: dict[int, bytes]) -> Optional[str]:
    if not manufacturer_data:
        return None
    # Prefer SwitchBot company IDs; fall back to the first entry.
    for company_id in (0x0969, 0x0059):
        if company_id in manufacturer_data:
            data = manufacturer_data[company_id]
            return company_id.to_bytes(2, "little").hex() + _hex(data)
    company_id, data = next(iter(manufacturer_data.items()))
    return company_id.to_bytes(2, "little").hex() + _hex(data)


def _make_service_data(adv) -> tuple[Optional[str], Optional[str]]:
    if not adv.service_data:
        return None, None
    # Prefer SwitchBot fd3d service data if present.
    for uuid, data in adv.service_data.items():
        if _uuid16_from_uuid(uuid) == "fd3d":
            return _hex(data), "fd3d"
    uuid, data = next(iter(adv.service_data.items()))
    return _hex(data), _uuid16_from_uuid(uuid)


def _looks_like_switchbot(name: str, adv) -> bool:
    if "switchbot" in name.lower():
        return True
    if adv.manufacturer_data:
        if 0x0969 in adv.manufacturer_data or 0x0059 in adv.manufacturer_data:
            return True
    if adv.service_data:
        return any(_uuid16_from_uuid(u) == "fd3d" for u in adv.service_data.keys())
    return False


def _decode_with_theengs(payload: dict) -> Optional[dict]:
    if TheengsDecoder is None:
        return None
    decoded = TheengsDecoder.decodeBLE(json.dumps(payload))
    if not decoded:
        return None
    try:
        return json.loads(decoded)
    except json.JSONDecodeError:
        return None


async def read_sensor_async(mac: str, timeout: int = 15) -> Optional[dict]:
    """Scan until we see the target MAC in decoded payloads, or timeout."""
    found: Optional[dict] = None
    done = asyncio.Event()

    def cb(device, adv):
        nonlocal found
        if found is not None:
            return

        name = device.name or ""
        if not _looks_like_switchbot(name, adv):
            return

        manufacturer_hex = _make_manufacturer_hex(adv.manufacturer_data)
        service_hex, service_uuid = _make_service_data(adv)

        payload = {
            "name": name,
            "id": device.address,
        }
        if adv.rssi is not None:
            payload["rssi"] = adv.rssi
        if manufacturer_hex:
            payload["manufacturerdata"] = manufacturer_hex
        if service_hex:
            payload["servicedata"] = service_hex
        if service_uuid:
            payload["servicedatauuid"] = service_uuid

        decoded = _decode_with_theengs(payload) or payload
        if decoded.get("mac", "").lower() == mac.lower():
            found = decoded
            done.set()

    scanner = BleakScanner(cb)
    await scanner.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    await scanner.stop()
    return found


def read_sensor(mac: str, timeout: int = 15) -> Optional[dict]:
    """Blocking helper to read a single sensor packet by MAC."""
    return asyncio.run(read_sensor_async(mac, timeout))


async def main():
    parser = argparse.ArgumentParser(description="Scan and decode SwitchBot BLE advertisements.")
    parser.add_argument("--timeout", type=int, default=15, help="Scan duration in seconds.")
    parser.add_argument("--address", type=str, default="", help="Filter by BLE MAC address.")
    parser.add_argument("--name", type=str, default="", help="Filter by device name substring.")
    args = parser.parse_args()

    def cb(device, adv):
        name = device.name or ""
        if args.address and device.address.lower() != args.address.lower():
            return
        if args.name and args.name.lower() not in name.lower():
            return
        if not _looks_like_switchbot(name, adv):
            return

        manufacturer_hex = _make_manufacturer_hex(adv.manufacturer_data)
        service_hex, service_uuid = _make_service_data(adv)

        rssi = getattr(adv, "rssi", None)
        payload = {
            "name": name,
            "id": device.address,
        }
        if rssi is not None:
            payload["rssi"] = rssi
        if manufacturer_hex:
            payload["manufacturerdata"] = manufacturer_hex
        if service_hex:
            payload["servicedata"] = service_hex
        if service_uuid:
            payload["servicedatauuid"] = service_uuid

        decoded = _decode_with_theengs(payload)

        print("----")
        print("Name:", name)
        print("Address:", device.address)
        print("RSSI:", rssi)
        print("Manufacturer:", manufacturer_hex)
        print("Service:", service_hex, service_uuid)
        if decoded:
            print("Decoded:", decoded)
        else:
            print("Decoded: (none) - install TheengsDecoder to decode")

    scanner = BleakScanner(cb)
    await scanner.start()
    await asyncio.sleep(args.timeout)
    await scanner.stop()


if __name__ == "__main__":
    asyncio.run(main())
