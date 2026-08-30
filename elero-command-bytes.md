# Elero command bytes

Why this gateway runs a patched `elero_packet.h`, and what the bytes mean.

## Two variants

Elero motors do not all read the same command bytes the same way. The component
ships one set of constants, and they are the wrong ones for these blinds.

| Byte | Roller-shutter reading (upstream default) | Raffstore / venetian reading (these motors) |
|------|------------------------------------------|---------------------------------------------|
| 0x00 | check — request status, no movement | same |
| 0x10 | stop | stop |
| 0x20 | **up / open** | **tilt step open** (short up) |
| 0x21 | — | **full travel up** (long up) |
| 0x24 | tilt position | **restore saved tilt / ventilation position** |
| 0x40 | **down / close** | **tilt step closed** (short down) |
| 0x41 | — | **full down, no tilt** |
| 0x44 | intermediate position | **full down + restore tilt** |

The difference is press length. On an Elero hand transmitter a short press steps
the slats and a long press starts a full travel. A roller shutter has no slats,
so a short press just starts the motor — which is why 0x20/0x40 work as "up" and
"down" for everyone else, and why the distinction never had to be modelled.

## What this installation needs

Confirmed against all seven blinds. With upstream defaults, "up" and "down" from
Home Assistant only nudge the slats one step; the blind never travels.

```
UP            0x21    full travel up
DOWN          0x44    full down + restore tilt
TILT_UP       0x20    step slats open
TILT_DOWN     0x40    step slats closed
VENTILATION   0x24    restore saved tilt position
DOWN_NO_TILT  0x41    full down without restoring tilt
STOP          0x10
CHECK         0x00
```

## Sources

- Elero's own transmitter-stick documentation, which lists the extended byte set.
- [andyboeh/esphome-elero#4](https://github.com/andyboeh/esphome-elero/issues/4)
  — the same variant reported in May 2024, still open.
- Verified here by sniffing the physical remote with the gateway's RF packet
  view and matching each button to the byte it sends.

## Why it is not upstream

`packet::command` is a set of global `constexpr` values in
`components/elero/elero_packet.h`. Changing them changes behaviour for **every**
device on **every** hub, so a fork that hard-codes this variant would break
roller shutters for everyone else. A hub with a mix of both kinds cannot be made
to work at all.

The upstream fix is per-device configurable command bytes:
[manuschillerdev/esphome-elero#63](https://github.com/manuschillerdev/esphome-elero/issues/63).
`NvsDeviceConfig` is a fixed 64-byte record, so it needs either a one-byte
variant selector in the existing `rf_reserved` field, or five explicit bytes
carved out of the reserve — a maintainer's call, because either way the web UI
and the backup format change with it.

andyboeh's original component did expose the bytes per cover in YAML
(`command_up`, `command_down`, `command_stop`, `command_check`, `command_tilt`).
This fork replaced the YAML cover platform with NVS-managed devices and the
capability did not come along.

## Where the patch lives

`local/schlotterer-variant` in
[deyanp/esphome-elero](https://github.com/deyanp/esphome-elero), and
[`patches/`](patches/) here. It touches `elero_packet.h`, and follows the rename
through `elero_strings.cpp`, `cover_sm.cpp` and the unit tests.
