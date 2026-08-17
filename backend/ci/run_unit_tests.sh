#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export TESTING="${TESTING:-1}"
coverage run -m unittest discover -s tests -p "test_*.py" -v
coverage xml -o coverage.xml
coverage report --show-missing
