#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
black --check app tests
isort --check-only app tests
