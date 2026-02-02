import argparse
import asyncio
import time

from bleak import BleakClient, BleakScanner


def _fmt(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


async def monitor(address: str, interval: float) -> None:
    # Try connected RSSI if backend supports it; otherwise fall back to adv RSSI.
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")

        if hasattr(client, "get_rssi"):
            while True:
                rssi = await client.get_rssi()  # type: ignore[attr-defined]
                print(f"{_fmt(time.time())} RSSI={rssi} dBm")
                await asyncio.sleep(interval)
        else:
            print("Connected RSSI not supported by this Bleak version; falling back to adv RSSI.")
            last_print = 0.0

            def cb(device, adv):
                nonlocal last_print
                if device.address != address:
                    return
                now = time.time()
                if (now - last_print) < interval:
                    return
                last_print = now
                print(f"{_fmt(now)} RSSI={adv.rssi} dBm")

            scanner = BleakScanner(cb)
            await scanner.start()
            try:
                while True:
                    await asyncio.sleep(1)
            finally:
                await scanner.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor RSSI via connection if possible.")
    parser.add_argument("address", help="BLE address/UUID shown by scan")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between reads")
    args = parser.parse_args()

    asyncio.run(monitor(args.address, args.interval))


if __name__ == "__main__":
    main()
