#!/usr/bin/env python3
"""Dump the Elero gateway's device registry.

The gateway sends its whole NVS registry as a `config` event the moment a
WebSocket client connects, so no command is needed and nothing is written.

Produces three files:

  registry-<date>.json  the raw config event, every field the firmware exposes
  restore-<date>.json   a ConfigSnapshot ready for the web UI's Restore button
  registry-<date>.md    a table to paste into devices.md

Usage:
    pip install websockets
    ./dump-registry.py [host]        # default: elero-c6-test.local

Note on completeness: the `config` event does not carry the five per-device RF
framing bytes that NvsDeviceConfig stores (hop, payload_1, payload_2, msg_type,
type2). They are emitted in the *backup* snapshot, which needs firmware newer
than v0.10.1. Until then this script fills in the Elero defaults, which is
correct for any device created or edited through the web UI: the UI's
upsert_device payload omits all five, and the firmware defaults every omitted
field. Confirmed on the wire — see README.
"""

import asyncio
import json
import sys
from datetime import date

import websockets

# Elero defaults, from packet::defaults / packet::msg_type in elero_packet.h.
RF_DEFAULTS = {
    "hop": "0x0a",
    "payload_1": "0x00",
    "payload_2": "0x04",
    "msg_type": "0x6a",
    "type2": "0x00",
}

SNAPSHOT_VERSION = 2


async def fetch(host: str) -> dict:
    uri = f"ws://{host}/elero/ws"
    async with websockets.connect(uri, max_size=None, open_timeout=15) as ws:
        async with asyncio.timeout(30):
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("event") == "config":
                    return msg["data"]


def to_snapshot(cfg: dict) -> dict:
    devices = []
    for b in cfg.get("blinds", []):
        devices.append({
            "device_type": "cover",
            "dst_address": b["address"],
            "src_address": b["remote"],
            "name": b["name"],
            "channel": b["channel"],
            "enabled": b["enabled"],
            "supports_tilt": b["supports_tilt"],
            "open_duration_ms": b["open_ms"],
            "close_duration_ms": b["close_ms"],
            "ha_device_class": 0,          # 0 = shutter
            **RF_DEFAULTS,
        })
    for lt in cfg.get("lights", []):
        devices.append({
            "device_type": "light",
            "dst_address": lt["address"],
            "src_address": lt["remote"],
            "name": lt["name"],
            "channel": lt["channel"],
            "enabled": lt["enabled"],
            "dim_duration_ms": lt.get("dim_ms", 0),
            **RF_DEFAULTS,
        })
    for r in cfg.get("remotes", []):
        devices.append({
            "device_type": "remote",
            "dst_address": r["address"],
            "name": r["name"],
            "enabled": True,
        })
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "exported_at": 0,
        "exporter": {"device": cfg["hub"]["device"], "version": "dump-registry.py"},
        "hub": {},
        "groups": cfg.get("groups", []),
        "devices": devices,
    }


def to_markdown(cfg: dict) -> str:
    out = []
    hub, radio = cfg["hub"], cfg["radio"]
    freq = radio["freq"]
    out.append(f"Hub `{hub['device']}` — mode {hub['mode']}, reports version "
               f"{hub['version']}, CRUD {'on' if hub['crud'] else 'off'}.  \n"
               f"Radio {radio['chipset']}, RX sensitivity {radio['rx_sensitivity']} dBm, "
               f"freq2 `{freq['freq2']}` / freq1 `{freq['freq1']}` / freq0 `{freq['freq0']}`.\n")

    out.append("| Name | Address | Ch | Remote (src) | Open | Close | Tilt | Enabled | Class |")
    out.append("|------|---------|----|--------------|-----:|------:|------|---------|-------|")
    for b in sorted(cfg.get("blinds", []), key=lambda x: x["name"]):
        out.append(
            f"| {b['name']} | `{b['address']}` | {b['channel']} | `{b['remote']}` | "
            f"{b['open_ms'] / 1000:g} s | {b['close_ms'] / 1000:g} s | "
            f"{'yes' if b['supports_tilt'] else 'no'} | "
            f"{'yes' if b['enabled'] else 'no'} | {b.get('device_class', '')} |")

    out.append("\nLast observed state (not configuration — it changes):\n")
    out.append("| Name | Position | HA state | Motion | Tilted | RSSI | Problem |")
    out.append("|------|---------:|----------|--------|--------|-----:|---------|")
    for b in sorted(cfg.get("blinds", []), key=lambda x: x["name"]):
        out.append(
            f"| {b['name']} | {b['position'] * 100:.0f} % | {b['ha_state']} | {b['state']} | "
            f"{'yes' if b['tilted'] else 'no'} | {b['rssi']:g} dBm | {b['problem_type']} |")

    if cfg.get("remotes"):
        out.append("\n| Remote | Address |")
        out.append("|--------|---------|")
        for r in cfg["remotes"]:
            out.append(f"| {r['name']} | `{r['address']}` |")

    rf = ", ".join(f"`{k}` {v}" for k, v in RF_DEFAULTS.items())
    out.append(f"\nRF framing bytes, identical for every device: {rf}.")
    return "\n".join(out) + "\n"


def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "elero-c6-test.local"
    cfg = asyncio.run(fetch(host))
    stamp = date.today().isoformat()

    for name, data in (
        (f"registry-{stamp}.json", cfg),
        (f"restore-{stamp}.json", to_snapshot(cfg)),
    ):
        with open(name, "w") as fh:
            json.dump(data, fh, indent=2)
        print(f"wrote {name}")

    md = to_markdown(cfg)
    with open(f"registry-{stamp}.md", "w") as fh:
        fh.write(md)
    print(f"wrote registry-{stamp}.md\n")
    print(md)


if __name__ == "__main__":
    main()
