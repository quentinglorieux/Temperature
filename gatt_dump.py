import argparse
import asyncio
from typing import Optional

from bleak import BleakClient


async def dump_gatt(address: str, *, read: bool) -> None:
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        if hasattr(client, "get_services"):
            services = await client.get_services()
        else:
            services = client.services
        for service in services:
            print(f"\n[Service] {service.uuid} ({service.description})")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  [Char] {char.uuid} ({char.description}) props={props}")
                if read and ("read" in char.properties):
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        print(f"    value: {value.hex()} (len={len(value)})")
                    except Exception as exc:
                        print(f"    read failed: {exc}")
            # Bleak 2.x does not expose service descriptors consistently.


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump GATT services/characteristics.")
    parser.add_argument("address", help="BLE address/UUID shown by scan")
    parser.add_argument("--read", action="store_true", help="Attempt to read readable chars/descriptors")
    args = parser.parse_args()

    asyncio.run(dump_gatt(args.address, read=args.read))


if __name__ == "__main__":
    main()
