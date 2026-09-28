# Patches

## `elero-local-changes-v0.10.1.diff`

The verbatim `git diff` recovered from `/config/esphome/elero-src` on the Home
Assistant box on 2026-08-30, against upstream tag **v0.10.1**. These edits were
made by hand on the box and had never been version-controlled. This is the
source of truth for everything that follows.

It is also committed as `local/recovered-v0.10.1` in
[deyanp/esphome-elero](https://github.com/deyanp/esphome-elero/tree/local/recovered-v0.10.1),
so the unsplit state is recoverable from git alone.

## Which upstream PR supersedes which hunk

Retire the fork one row at a time: when a PR merges, that hunk can be dropped
from the local branch on the next rebase.

| Hunk | Goes upstream as | Status |
|------|------------------|--------|
| `elero_web/elero_web_server.h`, `.cpp` — `logger::LogListener` → `add_log_callback` | [#58](https://github.com/manuschillerdev/esphome-elero/pull/58) | open |
| `device_registry.h`, `device_registry.cpp` — `command_cover_tilt(dev, open)` | [#62](https://github.com/manuschillerdev/esphome-elero/pull/62) | open |
| `elero_mqtt/mqtt_adapter.cpp` — read the tilt payload instead of dropping it | [#62](https://github.com/manuschillerdev/esphome-elero/pull/62) | open |
| `cover_sm.cpp` — `TILT_UP`/`TILT_DOWN` branches | **not needed upstream** — upstream's `TILT_UP` aliases `UP`, so `on_command` already routes 0x20/0x40 correctly. Needed locally only because the remap below breaks that identity. | stays local |
| `elero_packet.h` — command byte remap | **never.** Tracked as [#63](https://github.com/manuschillerdev/esphome-elero/issues/63) (per-device command bytes). See [`../elero-command-bytes.md`](../elero-command-bytes.md). | stays local |
| `elero_strings.cpp` — `TILT`→`TILT_UP`, `INTERMEDIATE`→`DOWN_NO_TILT` | **never** — follow-on of the remap above. | stays local |

## Fixes that are not in the recovered diff

Found while splitting the work, and carried on the same fork branch:

| Change | Upstream PR |
|--------|-------------|
| `ELERO_VERSION` chased a release that does not exist (0.9.0), so the prebuilt UI header 404s and the build dies hundreds of steps later | [#57](https://github.com/manuschillerdev/esphome-elero/pull/57) |
| ESP32-C6 compile target, CI matrix entry, device docs, ESPHome version bump | [#60](https://github.com/manuschillerdev/esphome-elero/pull/60) |
| CC1101 health line logged at `ESP_LOGW` every 5 s in normal operation | [#61](https://github.com/manuschillerdev/esphome-elero/pull/61) |
| Packet-copy button used `navigator.clipboard`, which is undefined over plain HTTP | [#64](https://github.com/manuschillerdev/esphome-elero/pull/64) |

## Open upstream issues that affect this gateway

- [#59](https://github.com/manuschillerdev/esphome-elero/issues/59) —
  `elero_nvs` does not compile on ESPHome ≥ 2026.x. This gateway uses
  `elero_mqtt`, which is unaffected. Do not enable `elero_nvs:`.
- [#63](https://github.com/manuschillerdev/esphome-elero/issues/63) — no
  per-device command bytes. The reason the remap above cannot go upstream.

## Applying the diff by hand

Only needed if starting from upstream v0.10.1 rather than from the fork branch.
The normal rebuild path pulls `local/schlotterer-variant` via `github://`,
which already contains all of this — see the [rebuild procedure](../README.md#rebuilding-from-scratch).

```bash
git clone https://github.com/manuschillerdev/esphome-elero
cd esphome-elero
git checkout v0.10.1
git apply /path/to/elero-local-changes-v0.10.1.diff
```
