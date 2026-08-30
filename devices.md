# Device registry

The firmware currently flashed on this gateway (**v0.10.1** plus local patches)
has **no backup/restore** — `export_config` was added upstream after v0.10.1 was
tagged. So there is no way to get this table off the device except by reading
it, and a wiped NVS means walking to every blind and re-running discovery. That
has already happened once, after a serial factory flash.

This file is the paper copy. Keep it current.

**Read from the live gateway on 2026-08-30** — the `config` event that
`/elero/ws` sends on connect carries the full NVS registry:

```bash
# needs `pip install websockets`
python3 - <<'EOF'
import asyncio, json, websockets
async def main():
    async with websockets.connect("ws://elero-c6-test.local/elero/ws") as ws:
        while True:
            d = json.loads(await ws.recv())
            if d.get("event") == "config":
                print(json.dumps(d["data"], indent=2)); return
asyncio.run(main())
EOF
```

## Blinds

Seven Schlotterer-badged Elero Raffstore (venetian) blinds. All are learned in
against the same physical remote, `0x314173`, which is therefore the source
address the gateway transmits from.

| Name | Address | Ch | Remote (src) | Open | Close | Tilt | HA class |
|------|-----------|----|--------------|------:|------:|------|----------|
| R1 | `0xb8770c` | 17 | `0x314173` | 38 s | 37 s | yes | shutter |
| R2 | `0xac770c` |  2 | `0x314173` | 61 s | 60 s | yes | shutter |
| R3 | `0x86520c` |  3 | `0x314173` | 61 s | 60 s | yes | shutter |
| R4 | `0xae770c` |  4 | `0x314173` | 61 s | 60 s | yes | shutter |
| R5 | `0xb3770c` |  5 | `0x314173` | 61 s | 60 s | yes | shutter |
| R6 | `0xb2770c` |  6 | `0x314173` | 61 s | 60 s | yes | shutter |
| R7 | `0xaa770c` |  7 | `0x314173` | 39 s | 38 s | yes | shutter |

Travel durations are measured, not guessed — they drive position tracking. R1
and R7 are the short blinds.

Working notes called these Raff1…Raff7; the names stored in NVS are R1…R7. The
addresses and channels match the notes exactly.

## Remotes

| Name | Address | Note |
|------|-----------|------|
| Remote 0x314173 | `0x314173` | the Elero remote all 7 blinds are paired to |
| Remote 0x163e0b | `0x163e0b` | discovered and stored, not yet identified |

## Seen but not registered

From the working notes and RF sniffing; **not** in the gateway's NVS. Recorded so
they are not later mistaken for devices that went missing:

| Address | Note |
|-----------|------|
| `0x61d20c` | noted as the Schlotterer remote; not present in NVS |
| `0xc4522b` | seen on channel 17 from the Schlotterer remote |
| `0xcbbb2f` | seen on channel 2 from the Schlotterer remote |

## Radio

| | |
|---|---|
| Chipset | CC1101 |
| Frequency | `freq2 0x21` / `freq1 0x71` / `freq0 0x7a` → 869.525 MHz (the default — do not override) |
| RX sensitivity | −104 dBm |
| Observed RSSI | −63 dBm (nearest blind) to −91 dBm (furthest) |

## Restoring the registry

In order of preference.

**1. Restore from a JSON backup.** Only available once the gateway runs firmware
newer than v0.10.1 — Hub panel → **Backup & Restore** → *Restore from backup*.
The [rebuild procedure](README.md#rebuilding-from-scratch) flashes from
`local/schlotterer-variant`, which is based on upstream `dev` and does have it.
**Take a backup as soon as that firmware is running.**

**2. Feed a hand-written snapshot to the same Restore button.** The importer
accepts any valid `ConfigSnapshot`, so the table above can be typed into one
file rather than clicked in seven times:

```json
{
  "snapshot_version": 2,
  "exported_at": 0,
  "exporter": { "device": "elero-c6-test", "version": "manual" },
  "hub": {},
  "groups": [],
  "devices": [
    { "device_type": "cover", "dst_address": "0xb8770c", "src_address": "0x314173",
      "name": "R1", "channel": 17, "enabled": true, "supports_tilt": true,
      "open_duration_ms": 38000, "close_duration_ms": 37000 },
    { "device_type": "cover", "dst_address": "0xac770c", "src_address": "0x314173",
      "name": "R2", "channel": 2, "enabled": true, "supports_tilt": true,
      "open_duration_ms": 61000, "close_duration_ms": 60000 }
  ]
}
```

Repeat the object for R3–R7 with the addresses, channels and durations above.
The remaining RF bytes (`hop`, `payload_1`, `payload_2`, `msg_type`, `type2`)
can be omitted — the importer fills in the Elero defaults `0x0a`, `0x00`,
`0x04`, `0x6a`, `0x00`, which is what these blinds use.

`snapshot_version` must be `2` and must match `SNAPSHOT_VERSION` in
`components/elero_web/elero_web_server.cpp`, or the import is rejected with
"Unsupported snapshot_version".

**3. Rediscover.** The Manage tab can only edit devices discovery has already
surfaced — there is no "add device" form. So this means standing at each blind
and pressing a button on the physical remote until the gateway sees the frame,
then correcting the name, channel and durations by hand.
