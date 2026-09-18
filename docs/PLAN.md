# AVAccess 4KIP200 Preset Control Plan

**Inventory:** 10× encoders (TX / 4KIP200E) · 35× receivers (RX / 4KIP200D)  
**Sources:** DirecTV H25 receivers feeding encoders (SHEF IP control, no IR)  
**UI target:** iPad (single pane for matrix presets + source control)  
**API source:** [API Command Guide V1.0.3](https://support.avaccess.com/wp-content/uploads/2025/12/API-Command-Guide-_-HDIP100-4KIP200-Series-V1.0.3.pdf)

---

## 1. Goals

| Preset | Behavior |
|--------|----------|
| **Preset 1 — ALL** | Encoder 1 → all 35 TVs |
| **Preset 2 — 4 Programs** | 4 encoders split as evenly as possible across 35 TVs |
| **Preset 3 — 9 Programs** | 9 encoders split across all 35 TVs |

**Secondary:** Control DirecTV H25 source boxes from the same iPad UI (SHEF HTTP :8080).

**Constraint noted:** Not married to Home Assistant — pick the simplest reliable stack.

### Locked decisions (current)

1. **TV split strategy:** numeric for now; move to zone mapping later via file profile.  
2. **ENC-10:** spare/extra for now (not used in Presets 2/3).  
3. **Preset 2 encoder set:** ENC-01..ENC-04.  
4. **Preset 3 encoder set:** ENC-01..ENC-09.

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
           UDP :5010 bulk             Telnet :24 (status,        HTTP :8080 SHEF
           source presets             CEC power, alias)          → DirecTV H25
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
| **A. Home Assistant + shell scripts / pyscript** | Great iPad UI (HA Companion), scenes, dashboards, DirecTV integration, TV CEC helpers | No native AVAccess integration — you write scripts | **Best default** if you already want one iPad “remote” for AV + lights/etc. |
| **B. BitFocus Companion** | Built for button grids / Stream Deck / iPad; TCP/UDP/Telnet native; instant preset buttons | Weaker for H25 now-playing / EPG unless HTTP module added; less “smart home” | **Best if UI is only AV presets** |
| **C. Node-RED** | Excellent for UDP/Telnet flows; dashboard on iPad | Another stack to host | Good middle ground |
| **D. Vendor VDirector app** | Already supports matrix + **presets** + source preview | Does not control DirecTV H25; less customizable branding | **Use for commissioning / backup**, not primary if you need H25 on same UI |
| **E. Tiny custom Python API + web UI** | Full control, simple deploy (Docker) | You own maintenance | Good if HA feels heavy |

**Recommendation:**  
- **Primary:** Home Assistant **or** Companion for the iPad button surface.  
- **Engine:** a small Python/shell module that owns device inventory + preset UDP sends (reusable from HA `shell_command`, Companion, or Node-RED).  
- Keep **VDirector** installed as a technician fallback.

### Home Assistant vs Companion (pluses / minuses)

| Platform | Pluses | Minuses |
|----------|--------|---------|
| **Home Assistant** | Strong iPad dashboarding; automations/schedules; easy add-ons (DirecTV, notifications, EPG cards); future integration beyond AV | More setup and maintenance; no native AVAccess integration so scripts are required |
| **BitFocus Companion** | Very fast AV button workflow; native feel for preset panels; simple operator UX | Less strong for “TV guide + search + automations”; H25 control depends on added HTTP workflow |

**Short take:**  
- If you want **channel search + guide overlays + future automation**, pick **Home Assistant**.  
- If you want **fastest operator preset panel only**, pick **Companion**.

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
    source: "H25-01"
receivers:
  - id: RX-01
    hostname: IPD935-YYYYYYYYYYYY
    mac: YYYYYYYYYYYY
    ip: 192.168.10.101
    zone: "Wall-A"
```

5. Document which H25 → which encoder HDMI.

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

## 7. DirecTV H25 control from the same iPad

Each H25 is controlled over **SHEF HTTP :8080** (`/tv/tune`, `/tv/getTuned`, `/remote/processKey`). There is **no IR** on the live path.

| Method | Capability | Fit |
|--------|------------|-----|
| **SHEF IP** (`scripts/directv_shef.py`) | Tune, now-playing, remote keys | **Live path** |
| **HA DirecTV integration** | `media_player` now-playing cards | Optional overlay on Matrix |
| **HDMI-CEC** | Limited (power / input) | Secondary only |

### Practical HA + H25 pattern

1. Enable External Access + Current Program on every H25.  
2. Map `ENC-01`…`ENC-10` → `H25-01`…`H25-10` in `config/directv.yaml`.  
3. HA dashboard:  
   - Preset buttons (matrix)  
   - Channel buttons that SHEF-tune the selected program’s H25  
4. Label panels to match Preset 2/3 programs (Program A → H25 on ENC-01, etc.).

**Scope tip:** You probably do **not** need to control all 10 H25s live on every dashboard page — only the encoders used by the **active preset** (1, 4, or 9).

### Channel picking (practical)

1. Define favorite channels in config (e.g., ESPN=206, TNT=245).  
2. HA button runs `directv_shef.py tune --encoder ENC-01 --channel 206`.  
3. Optional “Program A/B/C” channel buttons per active encoder page.

This gives one-tap channel changes from iPad over IP.

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

### Phase 3 — DirecTV H25 (1 day)
- Enable SHEF External Access on each box  
- Fill `config/directv.yaml` IPs  
- Probe/tune from the same dashboard  

### Phase 4 — Polish
- TV power on/off  
- Optional “which source is on which TV” status page  
- Fail-safe: “recall last preset”  

---

## 9. Risks & decisions to lock early

1. **Physical TV layout** for Presets 2 & 3 (even numeric split vs. zone-based split).  
2. **Which 4 / which 9 encoders** are the “programs” (and what ENC-10 is for).  
3. **Control host location** — must sit on AV network (or routed with broadcast forwarding — avoid that; prefer same subnet).  
4. **H25 depth of control** — SHEF tune + now-playing vs. full future guide (use XMLTV for that).  
5. **Audio** — each RX follows its video TX by default; confirm if separate audio matrix is needed (API supports `--asource-select` if required).  

---

## 10. Guide data (“bonus guide info”)

SHEF gives **current program** on a live H25 (`/tv/getTuned`). For now/next listings, use XMLTV.

| Option | Reliability | Notes |
|--------|-------------|-------|
| **A. XMLTV/EPG builder** (`build_guide_epg.py`) | High | Best supported way to show now/next guide cards and search in HA |
| **B. SHEF getTuned / HA DirecTV media_player** | High | Now-playing on each live box, not a future dump |
| **C. Manual favorites list only (no guide feed)** | Very High | Simplest: channel buttons without dynamic program data |

**Recommended path:**  
1) Start with **manual favorite channels** for dependable one-tap switching.  
2) Add **EPG/XMLTV** for on-screen guide/search cards on iPad.  
3) Use SHEF `getTuned` (and optional HA DirecTV entities) for live Now Playing.

---

## 11. Suggested next step

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

- Same iPad to also drive **DirecTV H25 SHEF**  
- Bigger branded buttons / kiosk  
- Schedules (“Preset 2 at 4pm game day”)  
- Integration with room lighting / audio  

Use both: VDirector for tech, HA/Companion for operators.
