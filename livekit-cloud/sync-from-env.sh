#!/usr/bin/env bash
# Pull livekit.toml from LiveKit Cloud using credentials from the environment.
# Use the same variable names as your DigitalOcean App Platform env (or export them locally).
#
# Required:
#   LIVEKIT_URL
#   LIVEKIT_API_KEY
#   LIVEKIT_API_SECRET
#   LIVEKIT_CLOUD_AGENT_ID   (or LIVEKIT_AGENT_ID)
#
# Optional:
#   LK_VERSION   (default: v2.16.2)
#
# Usage (from repo root):
#   export LIVEKIT_URL=... LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... LIVEKIT_CLOUD_AGENT_ID=...
#   bash livekit-cloud/sync-from-env.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${LIVEKIT_URL:?missing LIVEKIT_URL}"
: "${LIVEKIT_API_KEY:?missing LIVEKIT_API_KEY}"
: "${LIVEKIT_API_SECRET:?missing LIVEKIT_API_SECRET}"

AGENT_ID="${LIVEKIT_CLOUD_AGENT_ID:-${LIVEKIT_AGENT_ID:-}}"
if [[ -z "$AGENT_ID" ]]; then
  echo "Set LIVEKIT_CLOUD_AGENT_ID (or LIVEKIT_AGENT_ID)" >&2
  exit 1
fi

LK_VERSION="${LK_VERSION:-v2.16.2}"
VER="${LK_VERSION#v}"

OS="linux"
ARCH="amd64"
case "$(uname -s)" in
  Darwin) OS="darwin" ;;
  Linux) OS="linux" ;;
esac
case "$(uname -m)" in
  arm64|aarch64) ARCH="arm64" ;;
  x86_64|amd64) ARCH="amd64" ;;
esac

INSTALL_DIR="${ROOT}/.livekit-cli"
mkdir -p "$INSTALL_DIR"
LK_BIN="$INSTALL_DIR/lk-${LK_VERSION}-${OS}-${ARCH}"
ASSET="lk_${VER}_${OS}_${ARCH}.tar.gz"
URL="https://github.com/livekit/livekit-cli/releases/download/${LK_VERSION}/${ASSET}"

if [[ ! -x "$LK_BIN" ]]; then
  echo "Installing LiveKit CLI ${LK_VERSION} (${OS}-${ARCH})..."
  curl -sSL -o "$INSTALL_DIR/cli.tgz" "$URL"
  tar -xzf "$INSTALL_DIR/cli.tgz" -C "$INSTALL_DIR"
  mv "$INSTALL_DIR/lk" "$LK_BIN"
  chmod +x "$LK_BIN"
  rm -f "$INSTALL_DIR/cli.tgz"
fi

export HOME="${ROOT}/.lk-home"
rm -rf "$HOME"
mkdir -p "$HOME"

"$LK_BIN" project add do-sync \
  --url "$LIVEKIT_URL" \
  --api-key "$LIVEKIT_API_KEY" \
  --api-secret "$LIVEKIT_API_SECRET" \
  --default

mkdir -p livekit-cloud
cd livekit-cloud
"$LK_BIN" agent config --id "$AGENT_ID"

echo "Wrote $(pwd)/livekit.toml"
