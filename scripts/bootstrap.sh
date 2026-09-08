#!/usr/bin/env bash
# First-run install for lg-thinq-grok-bot (venv-safe; PEP 668 friendly).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip
pip install -e .
echo
echo "OK. Use: $ROOT/.venv/bin/thinq-specialty"
echo "Next: thinq-specialty login   (read the login-loop note it prints)"
