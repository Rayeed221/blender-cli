#!/usr/bin/env bash
# Install an official portable Blender build (checksum-verified) for headless use,
# and link the repo's blender-cli onto PATH.
#
# Usage: scripts/install-blender.sh [version]        (default: 5.2.0 LTS)
#   BLENDER_PREFIX=/opt            where the build is unpacked
#   BLENDER_SKIP_APT=1             skip installing runtime libraries
#
# Idempotent: re-running with an installed version only refreshes the links.
# Needs network access to download.blender.org.
set -euo pipefail

VERSION="${1:-${BLENDER_VERSION:-5.2.0}}"
PREFIX="${BLENDER_PREFIX:-/opt}"
SERIES="${VERSION%.*}"
NAME="blender-${VERSION}-linux-x64"
DEST="${PREFIX}/${NAME}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null && SUDO="sudo"

log() { printf '[install-blender] %s\n' "$*" >&2; }

# 1. Runtime libraries a headless Blender still links against.
if [ "${BLENDER_SKIP_APT:-0}" != "1" ] && command -v apt-get >/dev/null; then
  pkgs=(libxrender1 libxi6 libxkbcommon0 libsm6 libegl1 libgl1 libxxf86vm1 libxfixes3)
  missing=()
  for p in "${pkgs[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
  if [ "${#missing[@]}" -gt 0 ]; then
    log "installing runtime libraries: ${missing[*]}"
    $SUDO apt-get update -qq
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${missing[@]}"
  fi
fi

# 2. Download, verify and unpack the official build.
if [ -x "${DEST}/blender" ]; then
  log "Blender ${VERSION} already at ${DEST}"
else
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  base="https://download.blender.org/release/Blender${SERIES}"
  log "downloading ${NAME}.tar.xz"
  curl --fail --location --retry 3 -s "${base}/${NAME}.tar.xz" -o "${tmp}/${NAME}.tar.xz"
  curl --fail --location --retry 3 -s "${base}/blender-${VERSION}.sha256" -o "${tmp}/blender.sha256"
  (cd "$tmp" && sha256sum --check --ignore-missing --status blender.sha256) \
    || { log "checksum mismatch"; exit 1; }
  log "unpacking to ${PREFIX}"
  $SUDO mkdir -p "$PREFIX"
  $SUDO tar -xf "${tmp}/${NAME}.tar.xz" -C "$PREFIX"
fi

# 3. Put blender and blender-cli on PATH.
$SUDO ln -sfn "${DEST}/blender" /usr/local/bin/blender
$SUDO ln -sfn "${REPO_DIR}/blender-cli" /usr/local/bin/blender-cli

log "installed: $(blender --version 2>/dev/null | head -1)"
log "verify with: blender-cli doctor -H"
