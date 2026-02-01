import argparse
import asyncio
from typing import Optional

from bleak import BleakClient

WRITE_UUID = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
NOTIFY_UUID = "cba20003-224d-11e6-9fb8-0002a5d5c51b"


def _build_read_value_req() -> bytes:
    # 0x57 magic, command 0x0F (extend), payload 0x31 (read value)
    return bytes([0x57, 0x0F, 0x31])


def _parse_value_resp(data: bytes) -> Optional[dict]:
    if not data or data[0] != 0x01:
        return None
    if len(data) < 4:
        return None
    frac = data[1] & 0x0F
    temp_sign = 1 if (data[2] & 0x80) else -1
    temp_int = data[2] & 0x7F
    temp_c = temp_sign * (temp_int + frac / 10.0)
    hum = data[3] & 0x7F
    return {"tempc": temp_c, "hum": hum}


async def read_value(address: str, timeout: float) -> Optional[dict]:
    result: Optional[dict] = None
    done = asyncio.Event()

    def on_notify(_: int, data: bytearray) -> None:
        nonlocal result
        parsed = _parse_value_resp(bytes(data))
        if parsed:
            result = parsed
            done.set()

    async with BleakClient(address) as client:
        await client.start_notify(NOTIFY_UUID, on_notify)
        await client.write_gatt_char(WRITE_UUID, _build_read_value_req(), response=False)
        try:
            await asyncio.wait_for(done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            await client.stop_notify(NOTIFY_UUID)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Read temp/humidity via GATT (extend cmd 0x31).")
    parser.add_argument("address", help="BLE address/UUID shown by scan")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for response")
    args = parser.parse_args()

    data = asyncio.run(read_value(args.address, timeout=args.timeout))
    if data is None:
        print("No response (device may not support 0x31 or is asleep).")
        return
    print(data)


if __name__ == "__main__":
    main()
