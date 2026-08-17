#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
bandit -q -r app -x "*/tests/*"
