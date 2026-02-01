import argparse
import asyncio
from typing import Optional

from bleak import BleakClient

DEFAULT_WRITE = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
DEFAULT_NOTIFY = "cba20003-224d-11e6-9fb8-0002a5d5c51b"


def _hex_to_bytes(s: str) -> bytes:
    s = s.strip().replace(" ", "").replace("0x", "")
    if len(s) % 2 != 0:
        raise ValueError("hex payload must have even length")
    return bytes.fromhex(s)


async def probe(
    address: str,
    payload_hex: str,
    *,
    write_uuid: str,
    notify_uuid: str,
    timeout: float,
) -> None:
    payload = _hex_to_bytes(payload_hex)

    def on_notify(_: int, data: bytearray) -> None:
        print(f"notify: {data.hex()} (len={len(data)})")

    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        await client.start_notify(notify_uuid, on_notify)
        await client.write_gatt_char(write_uuid, payload, response=False)
        try:
            await asyncio.sleep(timeout)
        finally:
            await client.stop_notify(notify_uuid)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a write and listen for notifications.")
    parser.add_argument("address", help="BLE address/UUID shown by scan")
    parser.add_argument("payload", help="Hex payload to write, e.g. A1B203")
    parser.add_argument("--write", default=DEFAULT_WRITE, help="Write characteristic UUID")
    parser.add_argument("--notify", default=DEFAULT_NOTIFY, help="Notify characteristic UUID")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to listen for notifications")
    args = parser.parse_args()

    asyncio.run(
        probe(
            args.address,
            args.payload,
            write_uuid=args.write,
            notify_uuid=args.notify,
            timeout=args.timeout,
        )
    )


if __name__ == "__main__":
    main()
