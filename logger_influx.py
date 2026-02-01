import argparse
import asyncio
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient, Point, WriteOptions

from read_meter_gatt import read_value


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def run(address: str, interval: float, timeout: float, url: str, token: str, org: str, bucket: str) -> None:
    with InfluxDBClient(url=url, token=token, org=org) as client:
        write_api = client.write_api(write_options=WriteOptions(batch_size=1))
        while True:
            data = await read_value(address, timeout=timeout)
            if data:
                print(f"[{_now().isoformat()}] read: tempc={data['tempc']} hum={data['hum']}")
                point = (
                    Point("switchbot_meter")
                    .tag("address", address)
                    .field("tempc", float(data["tempc"]))
                    .field("hum", int(data["hum"]))
                    .time(_now())
                )
                write_api.write(bucket=bucket, org=org, record=point)
                print(f"[{_now().isoformat()}] wrote point to {bucket}")
            else:
                print(f"[{_now().isoformat()}] no response")
            await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Log SwitchBot meter readings to InfluxDB.")
    parser.add_argument("address", help="BLE address/UUID shown by scan")
    parser.add_argument("--interval", type=float, default=60.0, help="Seconds between reads")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for response")
    parser.add_argument("--url", default="http://localhost:8086", help="InfluxDB URL")
    parser.add_argument("--token", required=True, help="InfluxDB token")
    parser.add_argument("--org", default="temperature", help="InfluxDB org")
    parser.add_argument("--bucket", default="switchbot", help="InfluxDB bucket")
    args = parser.parse_args()

    asyncio.run(run(args.address, args.interval, args.timeout, args.url, args.token, args.org, args.bucket))


if __name__ == "__main__":
    main()
