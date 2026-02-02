import argparse
import asyncio
import time

from bleak import BleakScanner

try:
    import TheengsDecoder  # type: ignore
except Exception:
    TheengsDecoder = None


def _uuid16_from_uuid(uuid: str) -> str:
    u = uuid.lower()
    if u.startswith("0000") and u.endswith("-0000-1000-8000-00805f9b34fb"):
        return u[4:8]
    return u.replace("-", "")


def _hex(b: bytes) -> str:
    return b.hex()


def _make_manufacturer_hex(manufacturer_data: dict[int, bytes]):
    if not manufacturer_data:
        return None
    for company_id in (0x0969, 0x0059):
        if company_id in manufacturer_data:
            data = manufacturer_data[company_id]
            return company_id.to_bytes(2, "little").hex() + _hex(data)
    company_id, data = next(iter(manufacturer_data.items()))
    return company_id.to_bytes(2, "little").hex() + _hex(data)


def _make_service_data(adv):
    if not adv.service_data:
        return None, None
    for uuid, data in adv.service_data.items():
        if _uuid16_from_uuid(uuid) == "fd3d":
            return _hex(data), "fd3d"
    uuid, data = next(iter(adv.service_data.items()))
    return _hex(data), _uuid16_from_uuid(uuid)


def _decode_with_theengs(payload: dict):
    if TheengsDecoder is None:
        return None
    decoded = TheengsDecoder.decodeBLE(__import__("json").dumps(payload))
    if not decoded:
        return None
    try:
        return __import__("json").loads(decoded)
    except Exception:
        return None


async def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor RSSI for a SwitchBot device by MAC.")
    parser.add_argument("mac", help="Target MAC (e.g., E8:77:0C:00:20:7B)")
    parser.add_argument("--interval", type=float, default=0.0, help="Min seconds between prints")
    args = parser.parse_args()

    target = args.mac.lower()
    last_print = 0.0

    def cb(device, adv):
        nonlocal last_print

        manufacturer_hex = _make_manufacturer_hex(adv.manufacturer_data)
        service_hex, service_uuid = _make_service_data(adv)

        payload = {
            "name": device.name or "",
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

        decoded = _decode_with_theengs(payload)
        if not decoded:
            return
        if decoded.get("mac", "").lower() != target:
            return

        now = time.time()
        if args.interval and (now - last_print) < args.interval:
            return
        last_print = now
        print(f"{time.strftime('%H:%M:%S')} RSSI={decoded.get('rssi')} dBm tempc={decoded.get('tempc')} hum={decoded.get('hum')}")

    scanner = BleakScanner(cb)
    await scanner.start()
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await scanner.stop()


if __name__ == "__main__":
    asyncio.run(main())
