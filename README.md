# Elero blind gateway — ESP32-C6 + CC1101 for Home Assistant

Everything needed to rebuild a working **Elero 868 MHz blind gateway** from
scratch on a fresh Home Assistant install: the wiring, the ESPHome config, the
device registry, and the local component patches these motors need.

| | |
|---|---|
| Blinds | 7 × Schlotterer-badged Elero Raffstore (venetian), 868 MHz |
| Board | ESP32-C6-DevKitC-1 (ESP32-C6-WROOM-1) |
| Radio | CC1101 868 MHz module, SPI |
| Framework | ESP-IDF 5.5.5 (no Arduino core exists for the C6) |
| ESPHome | 2026.8.1 |
| Component | [manuschillerdev/esphome-elero](https://github.com/manuschillerdev/esphome-elero), patched fork pulled via `github://` — see [patches/](patches/) |
| Mode | `elero_mqtt` — MQTT discovery into Home Assistant |
| Image | RAM 37.0 % (167 106 / 452 112 B), flash 61.7 % (1 131 752 / 1 835 008 B) |

Home Assistant sees seven cover entities with position and tilt, both tilt
directions working.

### What the whole job looks like

1. Wire the CC1101 to the C6 — [hardware](#hardware)
2. Add the secrets in the ESPHome Builder — [step 1](#1-add-the-secrets)
3. Add a device and paste in `testc6.yaml` — [step 2](#2-add-the-device)
4. Install once over USB, then only ever wirelessly — [step 3](#3-install)
5. Check the radio is receiving — [verifying](#verifying)
6. Restore the seven blinds — [devices.md](devices.md#restoring-the-registry)
7. Dump the registry and keep it — [`dump-registry.py`](dump-registry.py)

Budget an evening, most of it the first ESP-IDF build.

## Why this repository exists

Three things about this installation are not reproducible from upstream alone.

**The motors use different command bytes.** These are Raffstore (venetian)
motors on Elero's extended byte set, where `0x20`/`0x40` are slat steps and full
travel is `0x21`/`0x44`. Upstream's constants are the slat-step bytes, so out of
the box "up" and "down" only nudge the slats — the blind never travels. The fix
is a patch to a global constant, which cannot go upstream because it would break
roller shutters for everyone else. Full table and reasoning in
[elero-command-bytes.md](elero-command-bytes.md).

**The device registry lives only in NVS.** The firmware currently flashed
(v0.10.1) has no backup/restore at all, and the web UI has no "add device" form.
A serial flash erases NVS — which has already happened once — and the only
recovery was to walk to each of the seven blinds and re-run discovery. The
registry is written down in [devices.md](devices.md).

**The local edits were never in git.** They lived in a working tree on the HA
box. They are now recovered, committed, and split into upstream PRs —
[patches/](patches/).

## Hardware

| CC1101 | ESP32-C6 | Function |
|--------|----------|----------|
| VCC | 3V3 | Power — **3.3 V only** |
| GND | GND | Ground |
| SCK | GPIO18 | SPI clock |
| MOSI | GPIO23 | SPI data out |
| MISO | GPIO19 | SPI data in |
| CSN | **GPIO6** | SPI chip select |
| GDO0 | **GPIO3** | Interrupt |

GDO2 is unused.

> **Do not put chip select on GPIO5.** GPIO5 is a strapping pin on the ESP32-C6
> (JTAG signal source select), and the generic ESP32 wiring in the component's
> docs uses it. Copying that pin onto a C6 can leave the board unable to boot.
> Pins to avoid on the C6: **4, 5** (strapping), **8, 9** (boot mode, GPIO9 is
> the BOOT button), **15** (ROM message printing), **12, 13** (USB Serial/JTAG),
> **24–30** (flash/PSRAM).

> **The CC1101 is a 3.3 V part.** Never connect it to 5 V.

### Radio

The **default** frequency preset works with these motors. Do not override it.

| Preset | freq2 | freq1 | freq0 | Carrier |
|---|---|---|---|---|
| **Standard (default, in use)** | `0x21` | `0x71` | `0x7a` | 869.525 MHz |
| Alternative | `0x21` | `0x71` | `0xc0` | 869.553 MHz |

Measured RSSI runs from −63 dBm on the nearest blind to −91 dBm on the furthest,
against a −104 dBm receiver — comfortable margin from a single central position.

## Rebuilding from scratch

Installed like any other ESPHome device, from the **ESPHome Builder** add-on in
Home Assistant. No SSH, no git on the HA box: `testc6.yaml` pulls the patched
component straight from GitHub.

### 1. Add the secrets

In the ESPHome Builder, click **Secrets** (top right) and add the keys from
[`secrets.yaml.example`](secrets.yaml.example) with the real values.

### 2. Add the device

**+ New device → Continue → Skip** (or any name — the YAML is replaced next),
then **Edit** the new device and replace its entire content with
[`testc6.yaml`](testc6.yaml). Save. Keep `name: elero-c6-test`: it is the
hostname, the OTA target and the MQTT topic prefix.

The component comes from
[`deyanp/esphome-elero`](https://github.com/deyanp/esphome-elero/tree/local/schlotterer-variant),
branch `local/schlotterer-variant` — upstream `dev` plus every fix listed in
[patches/](patches/), plus the command byte remap. The YAML pins a commit of
that branch, so a rebase of the branch never changes the firmware unnoticed. To
pick up a newer state, replace the hash in `external_components:` with the
branch's new head and reinstall.

> **Do not add an `api:` block.** ESPHome reboots the device every 15 minutes
> when no native-API client connects (`reboot_timeout`, default `15min`), and in
> MQTT mode nothing ever does. Measured on this gateway before the fix: three
> consecutive boots 14 min 53 s and 14 min 56 s apart. `wifi:` and `mqtt:` keep
> their own 15-minute `reboot_timeout`, so removing `api:` costs no watchdog.
> `testc6.yaml` here has no `api:` block; if you want one present but idle, use
> `api:` with `reboot_timeout: 0s`.
>
> Applied to the live gateway on 2026-08-31. Uptime passed 28 minutes — two
> reboot windows — where it had never previously exceeded 15. Dropping the
> component also saved a little image: flash 60.6 % → **59.9 %**, RAM
> **35.7 %** (unchanged).
>
> Without `api:` the device never shows up under *Settings → Devices → ESPHome*
> and HA does not offer to adopt it. That is expected: the covers arrive through
> the MQTT integration instead.

### 3. Install

Click **Install** on the device card.

- **First time, blank board:** *Plug into this computer* — the browser flashes
  the C6 over USB (Chrome/Edge). Or *Manual download* and flash the factory
  image with [web.esphome.io](https://web.esphome.io).
- **Every time after that:** *Wirelessly* (OTA).

The first build compiles ESP-IDF and takes a long time; later builds are quick.

> **Never do a serial *factory* flash on a working gateway.** It erases NVS and
> takes all seven blinds with it. OTA does not. This is why `testc6.yaml`
> carries an `ota:` block — keep it. On a gateway that is already running, only
> ever choose *Wirelessly*.

<details>
<summary>Alternative: build against a local checkout</summary>

For working on the component itself. On the HA box (Terminal & SSH add-on):

```bash
cd /config/esphome
git clone https://github.com/deyanp/esphome-elero elero-src
git -C elero-src checkout local/schlotterer-variant
```

and in `testc6.yaml` swap the `external_components:` source for:

```yaml
external_components:
  - source:
      type: local
      path: elero-src/components
```

Then build with the ESPHome Builder as above, or `esphome run testc6.yaml` from
the command line.

</details>

### 4. Restore the blinds

See [devices.md](devices.md#restoring-the-registry).

## Verifying

With `logger: level: DEBUG`:

- The CC1101 reports `MARCSTATE=0x0d` (RX) after setup.
- Received frames log with `crc_ok: true`.
- The web UI is at `http://elero-c6-test.local/` (it redirects to `/elero`).
- Home Assistant picks up seven covers through MQTT discovery.

Read the live registry straight off the device without the UI:

```bash
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

### Dump the registry

`./dump-registry.py` writes the full device registry to [`registry/`](registry/),
including a `restore-<date>.json` that the web UI's Restore button accepts. It
reads the `config` event the gateway pushes on connect — no command is sent and
nothing is written, so it is safe to run any time. Do it after every change.

That file is the difference between a five-minute recovery and an afternoon of
walking around the house. Note that restoring it needs firmware newer than
v0.10.1; see [devices.md](devices.md#restoring-the-registry).

## Known limitations

- **Do not enable `elero_nvs:`.** It does not compile on ESPHome ≥ 2026.x
  ([#59](https://github.com/manuschillerdev/esphome-elero/issues/59)). This
  gateway uses `elero_mqtt`, which is unaffected.
- **The live `config` event omits 5 per-device RF bytes** (`hop`, `payload_1`,
  `payload_2`, `msg_type`, `type2`), and the web UI's `upsert_device` omits them
  too — so every save through the Manage tab resets them to defaults. Harmless
  here because these blinds use the defaults, but it means the UI cannot express
  a non-default value. See [devices.md](devices.md#what-a-dump-does-and-does-not-contain).
- **Auto-discovered remotes are not persisted** and disappear on reboot until
  explicitly saved. Two dumps will disagree about remotes.
- **The hub reports its version as 0.9.0.** A stale constant, fixed by
  [#57](https://github.com/manuschillerdev/esphome-elero/pull/57). Cosmetic, but
  it is also why builds used to fail on a 404 for the prebuilt UI header.
- **`uint32_t` log lines are garbled on the C6.** `uint32_t` is
  `long unsigned int` on RISC-V, so `%u`/`%x` format specifiers do not match.
  Cosmetic — log output only, not RF behaviour.

## Credits

- [manuschillerdev/esphome-elero](https://github.com/manuschillerdev/esphome-elero)
  — the component this runs on
- [andyboeh/esphome-elero](https://github.com/andyboeh/esphome-elero) — the
  original Elero component, and
  [issue #4](https://github.com/andyboeh/esphome-elero/issues/4), which
  documents the venetian command byte variant

## Licence

Documentation and configuration here are CC BY 4.0. The patch in
[patches/](patches/) is a derivative of esphome-elero and carries its terms.

Not affiliated with or endorsed by Elero or Schlotterer. Use at your own risk.
