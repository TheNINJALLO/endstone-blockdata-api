#!/usr/bin/env bash
set -Eeuo pipefail
python3 scripts/build_exact.py --bds "${1:-1.26.40}" --platform "${2:-linux-x64}"
