#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/homeassistant/docker-compose.yml"
CONFIG_DIR="$ROOT_DIR/homeassistant/config"
CONTAINER_NAME="ha_panel_test"
if [[ -z "${PYTHON_BIN:-}" && -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "No Python interpreter found (checked python3 and python)." >&2
    exit 1
  fi
fi

echo "Running static panel validator..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/validate_panels.py" --config-dir "$CONFIG_DIR"

if command -v docker >/dev/null 2>&1; then
  echo "Starting Home Assistant test container..."
  docker compose -f "$COMPOSE_FILE" up -d

  echo "Waiting for container process..."
  for _ in {1..30}; do
    if docker ps --format "{{.Names}}" | rg "^${CONTAINER_NAME}$" >/dev/null; then
      break
    fi
    sleep 1
  done

  echo "Checking Home Assistant configuration in container..."
  docker exec "$CONTAINER_NAME" python -m homeassistant --script check_config --config /config
else
  echo "Docker not found, using local Home Assistant check_config fallback..."
  "$PYTHON_BIN" -m homeassistant --script check_config --config "$CONFIG_DIR"
fi

echo "Panel validation completed successfully."
