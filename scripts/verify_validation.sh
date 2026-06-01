#!/usr/bin/env bash
#
# Verify that every final target passes the MAPLE v0.1.0 validator suite.
#
# Reproduces the manuscript claim that no final SubmodelTarget or
# CalibrationTarget retains an unresolved validator failure. The result is
# pinned to MAPLE v0.1.0 (commit 7f1faa4); later versions have a different
# schema and would report spurious failures. This wrapper puts MAPLE v0.1.0 on
# the path, then runs scripts/verify_validation.py.
#
# MAPLE v0.1.0 is sourced, in order, from:
#   1. $MAPLE_SRC, if set (a maple 'src' dir checked out at 7f1faa4); else
#   2. a shallow clone of the public repo at the pinned commit, cached in
#      .maple-v0.1.0/ (gitignored). Override the URL with $MAPLE_REPO_URL.
#
# Usage: ./scripts/verify_validation.sh [-v]

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN=7f1faa4
MAPLE_REPO_URL="${MAPLE_REPO_URL:-https://github.com/popellab/maple.git}"
SRC="${MAPLE_SRC:-}"

if [ -z "$SRC" ]; then
  CACHE="$REPO/.maple-v0.1.0"
  if [ ! -d "$CACHE/src/maple" ]; then
    rm -rf "$CACHE"
    echo "Fetching MAPLE @ ${PIN} from ${MAPLE_REPO_URL} ..."
    git clone --quiet --filter=blob:none "$MAPLE_REPO_URL" "$CACHE"
    git -C "$CACHE" checkout --quiet "$PIN"
  fi
  SRC="$CACHE/src"
fi

if [ ! -d "$SRC/maple" ]; then
  echo "Error: no maple package found at ${SRC}." >&2
  echo "Set MAPLE_SRC to a MAPLE v0.1.0 (commit ${PIN}) 'src' dir, or ensure" >&2
  echo "${MAPLE_REPO_URL} is reachable so it can be cloned at ${PIN}." >&2
  exit 1
fi

PY="${PYTHON:-$REPO/.venv/bin/python}"
[ -x "$PY" ] || PY=python3

PYTHONPATH="$SRC${PYTHONPATH:+:$PYTHONPATH}" "$PY" "$REPO/scripts/verify_validation.py" "$@"
