# AGENTS.md

This project uses small Python tools to scan and decode SwitchBot BLE advertisements.

Guidelines for agents:
- Prefer updating existing scripts rather than adding new entry points.
- Keep dependencies minimal; use `bleak` for BLE and optional `TheengsDecoder` for decoding.
- Avoid OS-specific hacks unless required; note macOS CoreBluetooth behavior when relevant.
- When adding CLI options, use `argparse` and keep defaults sensible.
- Keep output human-readable; add a `--json` flag only if requested.
- Use the project venv at `.venv` when running or installing Python packages.
- Document any new usage in the script’s `--help` output.
