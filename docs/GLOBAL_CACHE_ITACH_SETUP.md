# Global Caché iTach IP2IR-P Setup (x4)

This project now supports direct iTach TCP IR sending (no generic HA remote entity required).

## Hardware layout

- 4x **Global Caché iTach IP2IR-P**
- 10x stick-on IR emitters (plus 2 spare outputs)
- 1 emitter per Xumo box

Suggested addressing:
- `gc1`: `192.168.10.210`
- `gc2`: `192.168.10.211`
- `gc3`: `192.168.10.212`
- `gc4`: `192.168.10.213`

## Config files

1) Copy and edit:

```bash
cp /config/avaccess/config/itach.example.yaml /config/avaccess/config/itach.yaml
```

2) Ensure `channels.yaml` has:

```yaml
ir_transport: itach_tcp
itach_config_path: /config/avaccess/config/itach.yaml
```

3) Replace all `REPLACE_WITH_XUMO_CODE_*` in `itach.yaml` with learned `sendir` payloads.

## Quick dry-run test

```bash
python3 /config/avaccess/scripts/send_xumo_ir_itach.py \
  --itach-config /config/avaccess/config/itach.yaml \
  --encoder ENC-01 \
  --digits 206 \
  --suffix ok \
  --dry-run
```

## Live smoke test

```bash
python3 /config/avaccess/scripts/send_xumo_ir_itach.py \
  --itach-config /config/avaccess/config/itach.yaml \
  --encoder ENC-01 \
  --digits 206 \
  --suffix ok
```

If this works, regenerate HA package/dashboard:

```bash
python3 /config/avaccess/scripts/generate_ha_bundle.py \
  --inventory /config/avaccess/config/inventory.yaml \
  --channels /config/avaccess/config/channels.yaml \
  --out-package /config/packages/avaccess_matrix.yaml \
  --out-dashboard /config/dashboards/avaccess_matrix.yaml
```

## Notes

- iTach listens on TCP port `4998`.
- Keep emitters physically isolated to avoid cross-control.
- ENC-10 is mapped and available as spare by default.
