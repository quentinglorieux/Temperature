import json

from scan_switchbot import read_sensor

MAC = "EA:06:06:3B:35:B7"
TIMEOUT = 20


def main() -> None:
    data = read_sensor(MAC, timeout=TIMEOUT)
    if data is None:
        print(json.dumps({"error": "timeout", "mac": MAC}))
        return
    print(json.dumps(data))


if __name__ == "__main__":
    main()
