# Home Assistant Channel Buttons (Xumo + IR)

Xumo channel/app navigation is most reliable through IR commands.  
This document shows a practical pattern for one-tap channel buttons on iPad.

## 1) Prerequisites

1. An IR integration in Home Assistant (Broadlink, ESPHome IR, or Infrared proxy).  
2. Learned commands for digits `0-9`, `ok`, `home`, arrows, back.  
3. One IR emitter/entity per Xumo (recommended), or carefully isolated emitters.

## 2) Data model

Use [`config/channels.example.yaml`](../config/channels.example.yaml) as your source of truth:

- Program → Encoder
- Encoder → HA IR entity
- Named channels (label + number)

## 3) Script pattern

Example HA script that sends channel digits to one Xumo IR entity:

```yaml
script:
  xumo_tune_espn_program_a:
    alias: "Program A → ESPN"
    sequence:
      - service: remote.send_command
        target:
          entity_id: remote.xumo_01_ir
        data:
          command: ["2", "0", "6", "ok"]
```

For channels with one-digit numbers, just use `["4", "ok"]`.

## 4) Dashboard pattern

- Top row: Preset 1 / Preset 2 / Preset 3
- Channel row: ESPN / TNT / FOX / CBS
- Program selector: A / B / C / D (for Preset 2) or A..I (for Preset 3)

This keeps operations simple:
1) Select preset  
2) Pick program tile  
3) Tap channel

## 5) Guide information options

If you want guide context (what's on now/next), use an XMLTV/EPG integration in HA and display:

- Current program per favorite channel
- Upcoming program
- Search card for program titles

Treat unofficial Spectrum API scripts as optional and non-critical.
