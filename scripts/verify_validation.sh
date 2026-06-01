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
#   2. a sibling ../maple git checkout, via 'git archive 7f1faa4' into
#      .maple-v0.1.0/ (cached, gitignored). Non-destructive: reads the commit
#      from the object store, leaving the working tree untouched.
#
# Usage: ./scripts/verify_validation.sh [-v]

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN=7f1faa4
SRC="${MAPLE_SRC:-}"

if [ -z "$SRC" ]; then
  CACHE="$REPO/.maple-v0.1.0"
  if [ ! -d "$CACHE/src/maple" ]; then
    if git -C "$REPO/../maple" cat-file -e "${PIN}^{commit}" 2>/dev/null; then
      mkdir -p "$CACHE"
      git -C "$REPO/../maple" archive "$PIN" | tar -x -C "$CACHE"
      echo "Extracted MAPLE @ ${PIN} into ${CACHE}"
    else
      echo "Error: cannot find MAPLE commit ${PIN}." >&2
      echo "Clone github.com/popellab/maple next to this repo, or set MAPLE_SRC to a" >&2
      echo "maple 'src' directory checked out at ${PIN}." >&2
      exit 1
    fi
  fi
  SRC="$CACHE/src"
fi

PY="${PYTHON:-$REPO/.venv/bin/python}"
[ -x "$PY" ] || PY=python3

PYTHONPATH="$SRC${PYTHONPATH:+:$PYTHONPATH}" "$PY" "$REPO/scripts/verify_validation.py" "$@"
