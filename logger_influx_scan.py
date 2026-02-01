import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from influxdb_client import InfluxDBClient, Point, WriteOptions

from scan_switchbot import _decode_with_theengs, _looks_like_switchbot, _make_manufacturer_hex, _make_service_data
from bleak import BleakScanner


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def scan_once(duration: float) -> Dict[str, dict]:
    latest: Dict[str, dict] = {}

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
        mac = decoded.get("mac")
        if not mac:
            return
        if "tempc" not in decoded or "hum" not in decoded:
            return
        latest[mac] = decoded

    scanner = BleakScanner(cb)
    await scanner.start()
    await asyncio.sleep(duration)
    await scanner.stop()
    return latest


def _load_name_map(path: str) -> Dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {k.lower(): v for k, v in data.items()}


async def run(
    scan_duration: float,
    interval: float,
    url: str,
    token: str,
    org: str,
    bucket: str,
    name_map: Dict[str, str],
) -> None:
    with InfluxDBClient(url=url, token=token, org=org) as client:
        write_api = client.write_api(write_options=WriteOptions(batch_size=1))
        while True:
            samples = await scan_once(scan_duration)
            if samples:
                print(f"[{_now().isoformat()}] found {len(samples)} sensor(s)")
            else:
                print(f"[{_now().isoformat()}] no sensors found")
            for mac, data in samples.items():
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
                print(f"[{_now().isoformat()}] wrote {mac}")
            await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan all SwitchBot meters and log to InfluxDB.")
    parser.add_argument("--scan", type=float, default=10.0, help="Seconds per BLE scan")
    parser.add_argument("--interval", type=float, default=30.0, help="Seconds between scans")
    parser.add_argument("--names", default="sensors.json", help="MAC->name JSON map file")
    parser.add_argument("--url", default="http://localhost:8086", help="InfluxDB URL")
    parser.add_argument("--token", required=True, help="InfluxDB token")
    parser.add_argument("--org", default="temperature", help="InfluxDB org")
    parser.add_argument("--bucket", default="switchbot", help="InfluxDB bucket")
    args = parser.parse_args()

    name_map = _load_name_map(args.names)
    asyncio.run(run(args.scan, args.interval, args.url, args.token, args.org, args.bucket, name_map))


if __name__ == "__main__":
    main()
