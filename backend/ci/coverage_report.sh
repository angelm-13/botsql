#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f coverage.xml ]; then coverage report --show-missing; else echo "coverage.xml not found"; fi
