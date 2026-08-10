#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/homeassistant/docker-compose.yml"
CONFIG_DIR="$ROOT_DIR/homeassistant/config"
CONTAINER_NAME="ha_panel_test"

echo "Running static panel validator..."
python "$ROOT_DIR/scripts/validate_panels.py" --config-dir "$CONFIG_DIR"

echo "Starting Home Assistant test container..."
docker compose -f "$COMPOSE_FILE" up -d

echo "Waiting for container process..."
for _ in {1..30}; do
  if docker ps --format "{{.Names}}" | rg "^${CONTAINER_NAME}$" >/dev/null; then
    break
  fi
  sleep 1
done

echo "Checking Home Assistant configuration..."
docker exec "$CONTAINER_NAME" python -m homeassistant --script check_config --config /config

echo "Panel validation completed successfully."
