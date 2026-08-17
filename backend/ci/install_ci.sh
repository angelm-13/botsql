#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install --upgrade pip setuptools wheel
if [ -f requirements-ci.txt ]; then
  python -m pip install -r requirements-ci.txt
elif [ -f requirements.txt ]; then
  python -m pip install -r requirements.txt
  python -m pip install coverage flake8 pycodestyle pydocstyle isort black bandit pip-audit pytest pytest-cov
else
  python -m pip install coverage flake8 pycodestyle pydocstyle isort black bandit pip-audit pytest pytest-cov
fi
python -m pip check
