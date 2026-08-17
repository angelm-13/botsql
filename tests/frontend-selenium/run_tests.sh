#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
python3 -m black --check .
python3 -m isort --check-only .
python3 -m flake8 .
python3 -m pycodestyle .
python3 -m pytest -m "smoke or e2e" --html=reports/selenium.html --self-contained-html
