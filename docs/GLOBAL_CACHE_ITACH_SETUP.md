# Global Caché iTach IP2IR-P (unused rollback leftover)

**Not on the live path.** Sources are DirecTV H25 boxes controlled over SHEF IP. There is no IR control in operator Home Assistant, Track B Live Send, or the generated Matrix bundle.

This file documents the old iTach TCP helper so the scripts are not a mystery if you find them in the repo:

- `config/itach.example.yaml`
- `scripts/send_xumo_ir_itach.py`
- `scripts/avaccess/ir_itach.py`
- `generate_ha_bundle.py` still accepts `ir_transport: itach_tcp` if you force it

Do **not** copy `itach.yaml` onto the site HA unless you are deliberately rebuilding an IR-only lab.

## Historical hardware layout (not commissioned)

- 4x **Global Caché iTach IP2IR-P**
- Stick-on IR emitters (one per former Xumo box)

Suggested addressing (lab only):
- `gc1`: `192.168.10.210`
- `gc2`: `192.168.10.211`
- `gc3`: `192.168.10.212`
- `gc4`: `192.168.10.213`

## If you ever force the unused IR generator

```bash
cp config/itach.example.yaml config/itach.yaml
```

```yaml
ir_transport: itach_tcp
itach_config_path: /config/avaccess/config/itach.yaml
```

Replace all `REPLACE_WITH_XUMO_CODE_*` in `itach.yaml` with learned `sendir` payloads, then regenerate the HA package. Live DirecTV SHEF is the supported tune path; prefer that.

```bash
python3 /config/avaccess/scripts/send_xumo_ir_itach.py \
  --itach-config /config/avaccess/config/itach.yaml \
  --encoder ENC-01 \
  --digits 206 \
  --suffix ok \
  --dry-run
```

## Notes

- iTach listens on TCP port `4998`.
- ENC-10 is mapped and available as spare by default.
