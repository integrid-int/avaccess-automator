# AVAccess Automator

Plan and tooling to drive **10× 4KIP200 encoders + 35× receivers** with iPad-friendly presets (and optional Xumo IR control).

## Docs

- **[docs/PLAN.md](docs/PLAN.md)** — architecture, preset math, Home Assistant vs alternatives, Xumo strategy

## Quick start (after inventory is filled)

```bash
cp config/inventory.example.yaml config/inventory.yaml
# edit hostnames / MACs / preset RX lists

python3 -m pip install pyyaml
python3 scripts/apply_preset.py --inventory config/inventory.yaml --preset 1_all --dry-run
python3 scripts/apply_preset.py --inventory config/inventory.yaml --preset 1_all
```

Presets are applied with AVAccess UDP bulk reconnect (`255.255.255.255:5010`).
