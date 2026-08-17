#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m compileall -q app tests
python -c "import importlib; [importlib.import_module(m) for m in ['app','app.models','app.services']]; print('import checks ok')"
