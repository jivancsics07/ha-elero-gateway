# Device registry

The firmware currently flashed (**v0.10.1** plus local patches) has **no
backup/restore** — `export_config` was added upstream after v0.10.1 was tagged.
A wiped NVS means walking to every blind and re-running discovery. That has
already happened once, after a serial factory flash.

So this is the paper copy. Regenerate it with
[`dump-registry.py`](dump-registry.py) whenever anything changes.

## Getting a dump

```bash
pip install websockets
./dump-registry.py                     # or: ./dump-registry.py 192.168.8.109
```

The gateway pushes its entire registry as a `config` event the moment a
WebSocket client connects, so nothing is commanded and nothing is written. The
script produces three files in [`registry/`](registry/):

| File | What it is |
|------|------------|
| `registry-<date>.json` | the raw event — every field the firmware exposes |
| `restore-<date>.json` | a `ConfigSnapshot` ready for the web UI's Restore button |
| `registry-<date>.md` | the table below, regenerated |

Latest: [`registry/registry-2026-08-30.json`](registry/registry-2026-08-30.json),
[`registry/restore-2026-08-30.json`](registry/restore-2026-08-30.json).

## What a dump does and does not contain

`NvsDeviceConfig` stores 5 RF framing bytes that the live `config` event **does
not send back**: `hop`, `payload_1`, `payload_2`, `msg_type`, `type2`. They only
appear in the backup snapshot, which needs firmware newer than v0.10.1.

They are knowable anyway, and they are the Elero defaults for every device here:

| Field | Value | |
|-------|-------|---|
| `hop` | `0x0a` | `packet::defaults::HOP` |
| `payload_1` | `0x00` | `packet::defaults::PAYLOAD_1` |
| `payload_2` | `0x04` | `packet::defaults::PAYLOAD_2` |
| `msg_type` | `0x6a` | `packet::msg_type::COMMAND` |
| `type2` | `0x00` | `packet::defaults::TYPE2` |

Two independent reasons:

1. **The web UI cannot set them to anything else.** `sendUpsertDevice()` omits
   all five from the `upsert_device` payload, and the firmware defaults every
   omitted field. So every save through the Manage tab pins them to the
   defaults, whatever they were before.
2. **Observed on the wire.** A `check` (status request, no movement) sent to R3
   produced `1d 03 6a 00 1a 01 03 31 41 73 …` — `msg_type` `0x6a`, `type2`
   `0x00`, `payload_1` `0x00`, `payload_2` `0x04`. The `0x1a` in the hop
   position is a *repeat* of the frame by another motor; the Elero mesh
   increments the high nibble on each hop. Gateway-originated frames carry
   `0x0a`.

`dump-registry.py` writes these defaults into `restore-<date>.json`, so the
restore file is complete even though the dump it came from is not.

## Blinds

Seven Schlotterer-badged Elero Raffstore (venetian) blinds, all learned in
against the same physical remote `0x314173` — which is therefore the source
address the gateway transmits from.

| Name | Address | Ch | Remote (src) | Open | Close | Tilt | Enabled | Class |
|------|---------|----|--------------|-----:|------:|------|---------|-------|
| R1 | `0xb8770c` | 17 | `0x314173` | 38 s | 37 s | yes | yes | shutter |
| R2 | `0xac770c` | 2 | `0x314173` | 61 s | 60 s | yes | yes | shutter |
| R3 | `0x86520c` | 3 | `0x314173` | 61 s | 60 s | yes | yes | shutter |
| R4 | `0xae770c` | 4 | `0x314173` | 61 s | 60 s | yes | yes | shutter |
| R5 | `0xb3770c` | 5 | `0x314173` | 61 s | 60 s | yes | yes | shutter |
| R6 | `0xb2770c` | 6 | `0x314173` | 61 s | 60 s | yes | yes | shutter |
| R7 | `0xaa770c` | 7 | `0x314173` | 39 s | 38 s | yes | yes | shutter |

Travel durations are measured, not guessed — they drive position tracking. R1
and R7 are the short blinds.

Working notes called these Raff1…Raff7; NVS stores R1…R7. Addresses and channels
match the notes exactly.

Signal, from a dump on 2026-08-30 (state, not configuration — it changes):

| Name | RSSI | | Name | RSSI |
|------|-----:|---|------|-----:|
| R1 | −77 dBm | | R5 | −64 dBm |
| R2 | −74 dBm | | R6 | −73.5 dBm |
| R3 | −68.5 dBm | | R7 | −68 dBm |
| R4 | −68 dBm | | | |

Against a −104 dBm receiver, from one central position.

## Remotes — read this before trusting a dump

**Auto-discovered remotes are not persisted.** `device_registry.cpp` is explicit:

```cpp
// Don't persist — auto-discovered remotes are ephemeral until user saves.
```

They live in RAM and vanish on reboot unless explicitly saved. `updated_at: 0`
in a dump means exactly that: never written to NVS.

This bit harder than it should have: the gateway was rebooting **every 15
minutes** because `testc6.yaml` had a bare `api:` block and nothing ever
connects to the native API in MQTT mode (see
[README](README.md#3-install)). Every discovered remote was therefore thrown away
within the quarter hour. With the `api:` block removed, a discovered remote
survives until the next real restart — but still save it if you want to keep
it.

| Address | In dumps | Note |
|-----------|----------|------|
| `0x314173` | always | the remote all 7 blinds are paired to. Reappears every boot because every blind's status reply names it. |
| `0x163e0b` | intermittently | seen 2026-08-30, gone after a restart. Never saved, so it only shows up while it is being heard. |

Two dumps of the same gateway will therefore disagree about remotes and agree
about blinds. That is the firmware behaving as designed, not data loss.

## Seen but not registered

From working notes and RF sniffing; not in the registry at all:

| Address | Note |
|-----------|------|
| `0x61d20c` | noted as the Schlotterer remote |
| `0xc4522b` | seen on channel 17 from the Schlotterer remote |
| `0xcbbb2f` | seen on channel 2 from the Schlotterer remote |

## Radio

| | |
|---|---|
| Chipset | CC1101 |
| Frequency | `freq2 0x21` / `freq1 0x71` / `freq0 0x7a` → 869.525 MHz (the default — do not override) |
| RX sensitivity | −104 dBm |

## Restoring the registry

**1. Restore from a snapshot.** Once the gateway runs firmware newer than
v0.10.1: Hub panel → **Backup & Restore** → *Restore from backup*, and feed it
[`registry/restore-2026-08-30.json`](registry/restore-2026-08-30.json). That file
is generated by `dump-registry.py` and is already complete, including the RF
bytes. Regenerate it before you need it.

`snapshot_version` must be `2` and match `SNAPSHOT_VERSION` in
`components/elero_web/elero_web_server.cpp`, or the import is rejected with
"Unsupported snapshot_version".

**2. Rediscover.** The Manage tab can only edit devices discovery has already
surfaced — there is no "add device" form. This means standing at each blind and
pressing a button on the physical remote until the gateway hears the frame, then
setting the name, channel and durations by hand from the table above.
