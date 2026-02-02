import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from influxdb_client import InfluxDBClient, Point, WriteOptions
from bleak import BleakScanner

from scan_switchbot import _decode_with_theengs, _looks_like_switchbot, _make_manufacturer_hex, _make_service_data


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_name_map(path: str) -> Dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {k.lower(): v for k, v in data.items()}


def _mac_from_manufacturer_hex(manufacturer_hex: Optional[str]) -> Optional[str]:
    if not manufacturer_hex:
        return None
    # Manufacturer hex includes 2-byte company ID + 6-byte MAC at the start.
    if len(manufacturer_hex) < 16:
        return None
    mac_hex = manufacturer_hex[4:16]
    return ":".join(mac_hex[i : i + 2].upper() for i in range(0, 12, 2))


async def run(
    interval: float,
    stale_after: float,
    url: str,
    token: str,
    org: str,
    bucket: str,
    name_map: Dict[str, str],
) -> None:
    latest: Dict[str, Tuple[dict, float]] = {}

    def cb(device, adv):
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

        decoded = _decode_with_theengs(payload)
        if not decoded:
            return
        mac = decoded.get("mac") or _mac_from_manufacturer_hex(manufacturer_hex)
        if not mac:
            return
        if "tempc" not in decoded or "hum" not in decoded:
            return
        latest[mac] = (decoded, time.time())

    with InfluxDBClient(url=url, token=token, org=org) as client:
        write_api = client.write_api(write_options=WriteOptions(batch_size=1))
        scanner = BleakScanner(cb)
        await scanner.start()
        while True:
            now = time.time()
            active = {m: d for m, (d, ts) in latest.items() if (now - ts) <= stale_after}
            if active:
                print(f"[{_now().isoformat()}] active {len(active)} sensor(s)", flush=True)
            else:
                print(f"[{_now().isoformat()}] no sensors found", flush=True)
            for mac, data in active.items():
                name = name_map.get(mac.lower(), "")
                point = (
                    Point("switchbot_meter")
                    .tag("mac", mac)
                    .tag("name", name)
                    .field("tempc", float(data["tempc"]))
                    .field("hum", int(data["hum"]))
                    .time(_now())
                )
                if "batt" in data:
                    point.field("batt", int(data["batt"]))
                write_api.write(bucket=bucket, org=org, record=point)
                print(
                    f"[{_now().isoformat()}] wrote {mac} tempc={data['tempc']} hum={data['hum']}",
                    flush=True,
                )
            await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan all SwitchBot meters and log to InfluxDB.")
    parser.add_argument("--interval", type=float, default=30.0, help="Seconds between writes")
    parser.add_argument("--stale", type=float, default=120.0, help="Seconds to keep last seen sensor active")
    parser.add_argument("--names", default="sensors.json", help="MAC->name JSON map file")
    parser.add_argument("--url", default="http://localhost:8086", help="InfluxDB URL")
    parser.add_argument("--token", required=True, help="InfluxDB token")
    parser.add_argument("--org", default="temperature", help="InfluxDB org")
    parser.add_argument("--bucket", default="switchbot", help="InfluxDB bucket")
    args = parser.parse_args()

    name_map = _load_name_map(args.names)
    asyncio.run(run(args.interval, args.stale, args.url, args.token, args.org, args.bucket, name_map))


if __name__ == "__main__":
    main()
