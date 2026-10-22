#!/usr/bin/env bash
# Deploy avaccess-automator to the gaps Raspberry Pi (Docker + host networking).
#
# Run from a machine that can SSH to the Pi (default: pi@gaps).
# First install:  ./scripts/deploy_gaps_pi.sh --init
# Later updates:  ./scripts/deploy_gaps_pi.sh
#
# Matches docs/HA_LIVE.md §2 "Docker Compose on an AV-LAN host".
# Does not overwrite site YAML, inventory.json, or custom_tv_sets.json on update.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_USER="${DEPLOY_USER:-pi}"
REMOTE_HOST="${DEPLOY_HOST:-gaps}"
REMOTE_DIR_SET=0
REMOTE_DIR="${DEPLOY_DIR:-}"
if [[ -n "$REMOTE_DIR" ]]; then
  REMOTE_DIR_SET=1
fi
GIT_REMOTE="${DEPLOY_GIT_REMOTE:-https://github.com/integrid-int/avaccess-automator.git}"
GIT_REF="${DEPLOY_GIT_REF:-main}"
COMPOSE_FILE="homeassistant/docker-compose.host.yml"
MODE="update"
METHOD="${DEPLOY_METHOD:-git}"
DRY_RUN=0
RESTART_HA=1
SKIP_PULL=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Deploy this repo to the gaps Raspberry Pi over SSH and run Home Assistant
with host networking (required for Live UDP).

Options:
  --init              First-time install (clone/rsync, seed YAML examples, start HA)
  --update            Pull/sync and restart (default)
  --host NAME         SSH host (default: gaps, or \$DEPLOY_HOST)
  --user NAME         SSH user (default: pi, or \$DEPLOY_USER)
  --dir PATH          Remote clone path (default: /home/<user>/avaccess-automator)
  --ref REF           Git branch/tag to deploy (default: main; git method only)
  --rsync             Sync this local checkout over SSH (best for private repos)
  --git               git clone/pull on the Pi (default; needs Pi GitHub access)
  --no-restart        Update files but do not recreate the container
  --skip-pull         Do not git pull / rsync; only restart compose
  --dry-run           Print remote commands without running them
  -h, --help          Show this help

Environment:
  DEPLOY_HOST, DEPLOY_USER, DEPLOY_DIR, DEPLOY_GIT_REMOTE, DEPLOY_GIT_REF, DEPLOY_METHOD
  Put Host gaps in ~/.ssh/config (IdentityFile, User) if needed.
  For a private repo without credentials on the Pi, use --rsync (or
  DEPLOY_GIT_REMOTE=git@github.com:integrid-int/avaccess-automator.git).

Examples:
  ./scripts/deploy_gaps_pi.sh --init --rsync
  ./scripts/deploy_gaps_pi.sh --host gaps.local --user ryan
  DEPLOY_HOST=192.168.10.5 ./scripts/deploy_gaps_pi.sh --rsync
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --init) MODE="init"; shift ;;
    --update) MODE="update"; shift ;;
    --host) REMOTE_HOST="$2"; shift 2 ;;
    --user) REMOTE_USER="$2"; shift 2 ;;
    --dir) REMOTE_DIR="$2"; REMOTE_DIR_SET=1; shift 2 ;;
    --ref) GIT_REF="$2"; shift 2 ;;
    --rsync) METHOD="rsync"; shift ;;
    --git) METHOD="git"; shift ;;
    --no-restart) RESTART_HA=0; shift ;;
    --skip-pull) SKIP_PULL=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$REMOTE_DIR_SET" -eq 0 ]]; then
  REMOTE_DIR="/home/${REMOTE_USER}/avaccess-automator"
fi
SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"

remote_bash() {
  local script="$1"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "+ ssh ${SSH_TARGET} bash -s <<'REMOTE_EOF'"
    printf '%s\n' "$script"
    echo "REMOTE_EOF"
    return 0
  fi
  # Pipe the script so local heredoc expansion cannot rewrite remote $vars.
  printf '%s\n' "$script" | ssh -o BatchMode=yes -o ConnectTimeout=15 "$SSH_TARGET" bash -s
}

echo "Deploy target: ${SSH_TARGET}:${REMOTE_DIR} (mode=${MODE}, method=${METHOD}, ref=${GIT_REF})"
cd "$ROOT_DIR"

if [[ "$METHOD" != "git" && "$METHOD" != "rsync" ]]; then
  echo "Invalid method: ${METHOD} (use --git or --rsync)" >&2
  exit 2
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  if ! ssh -o BatchMode=yes -o ConnectTimeout=15 "$SSH_TARGET" 'echo ok' >/dev/null; then
    echo "Cannot SSH to ${SSH_TARGET} (BatchMode). Check keys / Host ${REMOTE_HOST} in ~/.ssh/config." >&2
    exit 1
  fi
fi

rsync_to_pi() {
  local excludes=(
    --exclude '.git/'
    --exclude '.venv/'
    --exclude '__pycache__/'
    --exclude '.pytest_cache/'
    --exclude 'homeassistant/config/.storage/'
    --exclude 'homeassistant/config/home-assistant_v2.db*'
    --exclude 'homeassistant/config/home-assistant.log*'
    --exclude 'homeassistant/config/.HA_VERSION'
    --exclude 'homeassistant/config/blueprints/'
    --exclude 'homeassistant/config/deps/'
    --exclude 'config/directv.yaml'
    --exclude 'homeassistant/config/www/avaccess/custom_tv_sets.json'
  )
  # On updates, keep site inventory/channel YAML and the Live gate JSON.
  if [[ "$MODE" == "update" ]]; then
    excludes+=(
      --exclude 'config/inventory.yaml'
      --exclude 'config/channels.yaml'
      --exclude 'config/schedule_sync.yaml'
      --exclude 'config/guide_epg.yaml'
      --exclude 'homeassistant/config/www/avaccess/inventory.json'
    )
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "+ rsync -az --delete ${excludes[*]} ${ROOT_DIR}/ ${SSH_TARGET}:${REMOTE_DIR}/"
    return 0
  fi
  ssh -o BatchMode=yes "$SSH_TARGET" "mkdir -p $(printf '%q' "$REMOTE_DIR")"
  rsync -az --delete "${excludes[@]}" \
    -e "ssh -o BatchMode=yes -o ConnectTimeout=15" \
    "${ROOT_DIR}/" "${SSH_TARGET}:${REMOTE_DIR}/"
}

# shellcheck disable=SC2016
ENSURE_DOCKER=$(cat <<'EOS'
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed on the Pi." >&2
  echo "Install Docker Engine for Raspberry Pi OS, then re-run --init:" >&2
  echo "  curl -fsSL https://get.docker.com | sudo sh" >&2
  echo "  sudo usermod -aG docker \"$USER\"" >&2
  echo "Then log out and back in so the docker group applies." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is missing." >&2
  exit 1
fi
EOS
)

# shellcheck disable=SC2016
SEED_SITE_YAML=$(cat <<'EOS'
seed_one() {
  local name="$1"
  local src="config/${name}.example.yaml"
  local dst="config/${name}.yaml"
  if [[ ! -f "$src" ]]; then
    return 0
  fi
  if [[ -L "$dst" ]] || [[ ! -e "$dst" ]]; then
    rm -f "$dst"
    cp --remove-destination "$src" "$dst"
    echo "Seeded $dst from example (edit before Live)."
  else
    echo "Keeping existing $dst"
  fi
}
seed_one inventory
seed_one channels
seed_one schedule_sync
seed_one guide_epg
if [[ ! -f config/directv.yaml ]]; then
  cp --remove-destination config/directv.example.yaml config/directv.yaml
  echo "Seeded config/directv.yaml (replace placeholder H25 IPs before Live)."
else
  echo "Keeping existing config/directv.yaml"
fi
EOS
)

# shellcheck disable=SC2016
MARK_PANEL_LIVE=$(cat <<'EOS'
cfg=homeassistant/config/configuration.yaml
if [[ -f "$cfg" ]] && grep -q "environment: test" "$cfg"; then
  sed -i.bak "s/environment: test/environment: live/" "$cfg"
  rm -f "${cfg}.bak"
  echo "Set panel_custom environment to live in configuration.yaml"
fi
EOS
)

post_sync_remote() {
  remote_bash "$(cat <<EOF
set -euo pipefail
${ENSURE_DOCKER}
cd "${REMOTE_DIR}"
${SEED_SITE_YAML}
${MARK_PANEL_LIVE}
python3 -m pip install --user pyyaml >/dev/null 2>&1 || true
EOF
)"
}

if [[ "$MODE" == "init" ]]; then
  if [[ "$METHOD" == "rsync" ]]; then
    rsync_to_pi
  else
    remote_bash "$(cat <<EOF
set -euo pipefail
${ENSURE_DOCKER}
mkdir -p "$(dirname "$REMOTE_DIR")"
if [[ ! -d "${REMOTE_DIR}/.git" ]]; then
  git clone --branch "${GIT_REF}" "${GIT_REMOTE}" "${REMOTE_DIR}"
else
  echo "Clone already exists at ${REMOTE_DIR}; fetching ${GIT_REF}"
  cd "${REMOTE_DIR}"
  git fetch --prune origin
  git checkout "${GIT_REF}"
  git pull --ff-only origin "${GIT_REF}" || git pull --ff-only
fi
EOF
)"
  fi
  post_sync_remote
  if [[ "$RESTART_HA" -eq 1 ]]; then
    remote_bash "$(cat <<EOF
set -euo pipefail
cd "${REMOTE_DIR}"
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans
echo "Home Assistant: http://${REMOTE_HOST}:8123  (Sports Routing → /panel-health)"
echo
echo "Next (on the Pi / docs/HA_LIVE.md):"
echo "  1. Edit config/inventory.yaml and config/directv.yaml (no REPLACE_ME / placeholder IPs)."
echo "  2. python3 scripts/avaccess/export_inventory_json.py --input config/inventory.yaml"
echo "  3. Generate Matrix package (section 4) when ready; leave Live commit off for Soft Launch."
EOF
)"
  fi
  echo "Init deploy finished."
  exit 0
fi

# --- update ---
if [[ "$SKIP_PULL" -eq 0 ]]; then
  if [[ "$METHOD" == "rsync" ]]; then
    remote_bash "$(cat <<EOF
set -euo pipefail
${ENSURE_DOCKER}
mkdir -p "${REMOTE_DIR}"
EOF
)"
    rsync_to_pi
    remote_bash "$(cat <<EOF
set -euo pipefail
cd "${REMOTE_DIR}"
${MARK_PANEL_LIVE}
echo "Rsync deploy from laptop complete."
EOF
)"
  else
    remote_bash "$(cat <<EOF
set -euo pipefail
${ENSURE_DOCKER}
if [[ ! -d "${REMOTE_DIR}/.git" ]]; then
  echo "No clone at ${REMOTE_DIR}. Re-run with --init (or use --rsync)." >&2
  exit 1
fi
cd "${REMOTE_DIR}"

BACKUP="/tmp/avaccess-deploy-backup-\$(date +%Y%m%d-%H%M%S)"
mkdir -p "\$BACKUP"
preserve() {
  local f="\$1"
  if [[ -e "\$f" && ! -L "\$f" ]]; then
    mkdir -p "\$BACKUP/\$(dirname "\$f")"
    cp -a "\$f" "\$BACKUP/\$f"
  fi
}
preserve config/inventory.yaml
preserve config/directv.yaml
preserve config/channels.yaml
preserve config/schedule_sync.yaml
preserve config/guide_epg.yaml
preserve homeassistant/config/www/avaccess/inventory.json
preserve homeassistant/config/www/avaccess/custom_tv_sets.json
preserve homeassistant/config/configuration.yaml
git rev-parse HEAD > "\$BACKUP/git-sha-before.txt"
echo "Backup: \$BACKUP"

git fetch --prune origin
git checkout "${GIT_REF}"
git pull --ff-only origin "${GIT_REF}" || git pull --ff-only

restore() {
  local f="\$1"
  if [[ -e "\$BACKUP/\$f" ]]; then
    mkdir -p "\$(dirname "\$f")"
    cp -a "\$BACKUP/\$f" "\$f"
    echo "Restored \$f"
  fi
}
restore config/inventory.yaml
restore config/directv.yaml
restore config/channels.yaml
restore config/schedule_sync.yaml
restore config/guide_epg.yaml
restore homeassistant/config/www/avaccess/inventory.json
restore homeassistant/config/www/avaccess/custom_tv_sets.json
if [[ -f "\$BACKUP/homeassistant/config/configuration.yaml" ]] \\
  && grep -q "environment: live" "\$BACKUP/homeassistant/config/configuration.yaml"; then
${MARK_PANEL_LIVE}
fi

echo "Deployed \$(git rev-parse --short HEAD)"
EOF
)"
  fi
else
  remote_bash "$(cat <<EOF
set -euo pipefail
${ENSURE_DOCKER}
EOF
)"
fi

if [[ "$RESTART_HA" -eq 1 ]]; then
  remote_bash "$(cat <<EOF
set -euo pipefail
cd "${REMOTE_DIR}"
if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Missing ${COMPOSE_FILE} on the Pi. Pull a revision that includes it, or re-run --init." >&2
  exit 1
fi
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans
echo "Home Assistant: http://${REMOTE_HOST}:8123  (Sports Routing → /panel-health)"
EOF
)"
fi

echo "Update deploy finished. Turn Live commit off before smoke-testing (docs/HA_LIVE.md §7)."
echo "If panel-health.js changed, bump ?v= in configuration.yaml, restart HA, force-quit Companion."
