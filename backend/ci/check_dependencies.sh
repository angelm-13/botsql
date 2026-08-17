#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip check
if [ -f requirements.txt ]; then pip-audit -r requirements.txt || true; else pip-audit || true; fi
