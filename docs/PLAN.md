# AVAccess 4KIP200 Preset Control Plan

**Inventory:** 10× encoders (TX / 4KIP200E) · 35× receivers (RX / 4KIP200D)  
**Sources:** Xumo Stream Boxes feeding encoders  
**UI target:** iPad (single pane for matrix presets + source control)  
**API source:** [API Command Guide V1.0.3](https://support.avaccess.com/wp-content/uploads/2025/12/API-Command-Guide-_-HDIP100-4KIP200-Series-V1.0.3.pdf)

---

## 1. Goals

| Preset | Behavior |
|--------|----------|
| **Preset 1 — ALL** | Encoder 1 → all 35 TVs |
| **Preset 2 — 4 Programs** | 4 encoders split as evenly as possible across 35 TVs |
| **Preset 3 — 9 Programs** | 9 encoders split across all 35 TVs |

**Secondary:** Control Xumo source boxes from the same iPad UI.

**Constraint noted:** Not married to Home Assistant — pick the simplest reliable stack.

---

## 2. How the hardware actually switches

AVAccess devices speak:

| Protocol | Port | Use |
|----------|------|-----|
| **UDP discovery** | 3335 → / 3336 ← | Find TX/RX hostnames + IPs |
| **Telnet** | **24** (not 23) | Per-device config (`root`, prompt `/ #`) |
| **UDP broadcast** | **5010** | Switch many RXs to one TX **at once** |
| **HTTP** | 80 | TX preview MJPEG (`/stream`), firmware, overlays |

### Per-RX source assign (Telnet)

```text
gbconfig --source-select=<TX_MAC_WITHOUT_COLONS>
e e_reconnect
```

Example: TX hostname `IPE935-341B22822FEF` → MAC `341B22822FEF`.

### Bulk simultaneous switch (recommended for presets)

UDP to `255.255.255.255:5010` (or subnet broadcast):

```text
msg_b_reconnect <TX_HOSTNAME>:<session>:<rx_count> <RX1_HOSTNAME> <RX2_HOSTNAME> ...
```

Example (2 RXs → one TX):

```text
msg_b_reconnect IPE935-341B22822FEA:1:2 IPD935-341B228007BD IPD935-341B2282302C
```

For presets with multiple source groups, send **one UDP message per encoder group** (4 messages for Preset 2, 9 for Preset 3). Increment `session` each time.

### Bonus: TV power via RX CEC

```text
sinkpower on
sinkpower off
```

Useful for “room on / room off” from the same UI.

---

## 3. Recommended control architecture

```text
┌─────────────┐     HTTPS/LAN      ┌──────────────────────┐
│  iPad UI    │ ─────────────────► │  Control brain       │
│ (browser /  │                    │  (HA / Node-RED /    │
│  HA app /   │                    │   small Python API)  │
│  Companion) │                    └──────────┬───────────┘
└─────────────┘                               │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
           UDP :5010 bulk             Telnet :24 (status,        IR blaster(s)
           source presets             CEC power, alias)          → Xumo boxes
                    │
                    ▼
        ┌──────────────────────────┐
        │ Gigabit switch (LAN)     │
        │ 10× TX  +  35× RX        │
        └──────────────────────────┘
```

### Platform choice (ranked)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **A. Home Assistant + shell scripts / pyscript** | Great iPad UI (HA Companion), scenes, dashboards, IR integrations (Broadlink/ESPHome), TV CEC helpers | No native AVAccess integration — you write scripts | **Best default** if you already want one iPad “remote” for AV + lights/etc. |
| **B. BitFocus Companion** | Built for button grids / Stream Deck / iPad; TCP/UDP/Telnet native; instant preset buttons | Weaker for Xumo unless IR module added; less “smart home” | **Best if UI is only AV presets** |
| **C. Node-RED** | Excellent for UDP/Telnet flows; dashboard on iPad | Another stack to host | Good middle ground |
| **D. Vendor VDirector app** | Already supports matrix + **presets** + source preview | May not control Xumo; less customizable branding | **Use for commissioning / backup**, not primary if you need Xumo on same UI |
| **E. Tiny custom Python API + web UI** | Full control, simple deploy (Docker) | You own maintenance | Good if HA feels heavy |

**Recommendation:**  
- **Primary:** Home Assistant **or** Companion for the iPad button surface.  
- **Engine:** a small Python/shell module that owns device inventory + preset UDP sends (reusable from HA `shell_command`, Companion, or Node-RED).  
- Keep **VDirector** installed as a technician fallback.

---

## 4. Preset math (35 TVs)

Assign encoders by **stable hostname/MAC**, not DHCP IP.

### Preset 1 — ALL

| Encoder | RX count | RXs |
|---------|----------|-----|
| ENC-01  | 35       | RX-01 … RX-35 |

One UDP `msg_b_reconnect` with all 35 RX hostnames.

### Preset 2 — 4 programs (even split)

35 ÷ 4 = **8 remainder 3** → three groups get 9, one gets 8:

| Program | Encoder | TVs | Suggested RX IDs |
|---------|---------|-----|------------------|
| A | ENC-01 | 9 | 1–9 |
| B | ENC-02 | 9 | 10–18 |
| C | ENC-03 | 9 | 19–27 |
| D | ENC-04 | 8 | 28–35 |

*(Adjust mapping to physical room layout — e.g. by wall / zone — once TVs are labeled.)*

### Preset 3 — 9 programs

35 ÷ 9 = **3 remainder 8** → eight groups get 4, one gets 3:

| Program | Encoder | TVs | Suggested RX IDs |
|---------|---------|-----|------------------|
| 1 | ENC-01 | 4 | 1–4 |
| 2 | ENC-02 | 4 | 5–8 |
| 3 | ENC-03 | 4 | 9–12 |
| 4 | ENC-04 | 4 | 13–16 |
| 5 | ENC-05 | 4 | 17–20 |
| 6 | ENC-06 | 4 | 21–24 |
| 7 | ENC-07 | 4 | 25–28 |
| 8 | ENC-08 | 4 | 29–32 |
| 9 | ENC-09 | 3 | 33–35 |

ENC-10 held in reserve / spare / special event source.

> **Important:** Split is logical (which TV shows which program), not a single multiview tile. Each RX shows **one** full-screen encoder. (4KIP200M multiview is a different product; your RXs are standard decoders.)

---

## 5. Inventory & network prerequisites

Before automation:

1. **Same L2/L3 network** for control host, all TX, all RX (Gigabit switch; broadcast must work — do not block UDP broadcasts on ports 3335/3336/5010).
2. Prefer **DHCP reservations or static IPs** for all 45 devices + control host.
3. Set friendly aliases via Telnet:
   ```text
   gbparam s alias ENC-01-Lobby
   gbparam s alias RX-12-Bar-Left
   ```
4. Build a CSV/YAML inventory:

```yaml
encoders:
  - id: ENC-01
    hostname: IPE935-XXXXXXXXXXXX
    mac: XXXXXXXXXXXX
    ip: 192.168.10.11
    source: "Xumo-01"
receivers:
  - id: RX-01
    hostname: IPD935-YYYYYYYYYYYY
    mac: YYYYYYYYYYYY
    ip: 192.168.10.101
    zone: "Wall-A"
```

5. Document which Xumo → which encoder HDMI.

Optional discovery helper: UDP probe port 3335 and listen 3336 (per API §6).

---

## 6. Home Assistant design (if chosen)

### Entities / actions

- `script.av_preset_1_all`
- `script.av_preset_2_four`
- `script.av_preset_3_nine`
- `script.av_tvs_on` / `script.av_tvs_off` (loop `sinkpower` on RXs)
- Optional: per-zone scripts later

### Implementation sketch

```yaml
# configuration.yaml (concept)
shell_command:
  av_preset_1: python3 /config/avaccess/apply_preset.py --preset 1
  av_preset_2: python3 /config/avaccess/apply_preset.py --preset 2
  av_preset_3: python3 /config/avaccess/apply_preset.py --preset 3

script:
  av_preset_1_all:
    alias: "AV Preset 1 — ALL"
    sequence:
      - service: shell_command.av_preset_1
```

`apply_preset.py` responsibilities:

1. Load inventory YAML  
2. Resolve preset → `{ tx_hostname: [rx_hostnames...] }`  
3. Send one UDP `:5010` message per TX group  
4. Log success / failures  
5. Optionally verify with Telnet `gbconfig --show --source-select` on a sample of RXs  

### iPad UI

- HA Companion app dashboard: 3 large buttons + TV power  
- Or Browser Mod / Fully Kiosk for kiosk mode  
- Optional: Encoder preview cards via `http://<tx_ip>/stream` (MJPEG; load carefully — max 4 streams per TX)

---

## 7. Xumo control from the same iPad

Xumo Stream Box has **no documented open IP control API** for channel/app navigation. Practical options:

| Method | Capability | Fit |
|--------|------------|-----|
| **IR blaster** (Broadlink RM4, ESPHome IR, Global Cache) | Power, Home, arrows, OK, numbers, app shortcuts if learned | **Recommended** for real remote replacement |
| **HDMI-CEC** | Limited (power / input); unreliable for channel/app | Secondary only |
| **Keep physical remotes / Xumo app** | Full control | Fallback |
| **RS-232 pass-through via AVAccess** | Only if a device in chain exposes serial control — Xumo does **not** | Not applicable |

### Practical HA + Xumo pattern

1. One IR emitter covering the rack of Xumos **or** one emitter per box if IR isolation needed.  
2. Learn codes from the Xumo remotes into Broadlink/ESPHome.  
3. HA dashboard:  
   - Preset buttons (matrix)  
   - Per-program “Xumo remote” mini-panels (Power, Home, Up/Down/Left/Right, OK, Back)  
4. Label panels to match Preset 2/3 programs (Program A remote → Xumo on ENC-01, etc.).

**Scope tip:** You probably do **not** need to control all 10 Xumos live on every dashboard page — only the encoders used by the **active preset** (1, 4, or 9).

---

## 8. Implementation phases

### Phase 0 — Commission (½–1 day)
- Label every TX/RX physically  
- Capture hostname/MAC/IP inventory  
- Confirm VDirector can route Encoder 1 → all TVs  
- Confirm Gigabit switch allows required broadcasts  

### Phase 1 — Preset engine (1 day)
- Inventory YAML  
- Python `apply_preset.py` with Presets 1–3  
- CLI test from a laptop on the AV LAN  

### Phase 2 — iPad surface (½–1 day)
- Wire engine into HA scripts **or** Companion buttons  
- Large 3-button dashboard  

### Phase 3 — Xumo (1–2 days)
- Mount IR emitters  
- Learn essential codes  
- Add remote widgets to same dashboard  

### Phase 4 — Polish
- TV power on/off  
- Optional “which source is on which TV” status page  
- Fail-safe: “recall last preset”  

---

## 9. Risks & decisions to lock early

1. **Physical TV layout** for Presets 2 & 3 (even numeric split vs. zone-based split).  
2. **Which 4 / which 9 encoders** are the “programs” (and what ENC-10 is for).  
3. **Control host location** — must sit on AV network (or routed with broadcast forwarding — avoid that; prefer same subnet).  
4. **Xumo depth of control** — navigation only vs. deep links / channel favorites.  
5. **Audio** — each RX follows its video TX by default; confirm if separate audio matrix is needed (API supports `--asource-select` if required).  

---

## 10. Suggested next step

Build a minimal **inventory + Preset 1 UDP proof** on the AV LAN:

```bash
# Conceptual proof (replace hostnames)
echo -n 'msg_b_reconnect IPE935-<ENC1_MAC>:1:35 IPD935-<RX1> ... IPD935-<RX35>' \
  | socat - UDP-DATAGRAM:255.255.255.255:5010,broadcast
```

Once Preset 1 works, encode Presets 2 & 3 as config — no more protocol uncertainty.

---

## Appendix A — Useful Telnet cheatsheet

| Action | Commands |
|--------|----------|
| Login | `telnet <ip> 24` → user `root` |
| Alias | `gbparam s alias NAME` / `gbparam g alias` |
| Set source | `gbconfig --source-select=MAC` then `e e_reconnect` |
| Show source | `gbconfig --show --source-select` |
| TV on/off | `sinkpower on` / `sinkpower off` |
| Firmware | `cat /etc/version` |
| Reboot | `reboot` |

## Appendix B — Why not only VDirector?

VDirector already does presets and previews and is ideal for install/commissioning. A HA/Companion layer is justified when you need:

- Same iPad to also drive **Xumo IR**  
- Bigger branded buttons / kiosk  
- Schedules (“Preset 2 at 4pm game day”)  
- Integration with room lighting / audio  

Use both: VDirector for tech, HA/Companion for operators.
