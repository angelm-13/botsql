#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python ci/link_checker.py --root .
if [ "${CHECK_REMOTE_LINKS:-0}" = "1" ]; then python ci/link_checker.py --root . --remote; fi
