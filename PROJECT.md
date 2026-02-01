# Project Summary

Small Python tool for scanning and decoding SwitchBot Indoor/Outdoor Thermo‑Hygrometer BLE advertisements.

What it does:
- Scans BLE advertisements and filters SwitchBot devices
- Decodes temperature, humidity, and battery data via TheengsDecoder (optional)
- Prints raw manufacturer/service data for troubleshooting

How to run:
- Create/activate venv: `python3 -m venv .venv && . .venv/bin/activate`
- Install deps: `python -m pip install -r requirements.txt`
- Scan: `python scan_switchbot.py --timeout 15`
- Filter by MAC: `python scan_switchbot.py --address AA:BB:CC:DD:EE:FF`

InfluxDB + Grafana (Docker):
- Edit `.env` with your passwords/tokens
- Start services: `docker compose up -d`
- Grafana: http://localhost:3000 (credentials in `.env`)
- InfluxDB: http://localhost:8086

Logger (writes to InfluxDB):
- `python logger_influx.py <BLE_ADDRESS> --token <INFLUX_TOKEN>`
- For Raspberry Pi, use the systemd template: `switchbot-logger.service`

Dependencies:
- `bleak` (required)
- `TheengsDecoder` (optional, for decoding)

Notes:
- On macOS, BLE scanning uses CoreBluetooth and device addresses may appear as UUIDs.
