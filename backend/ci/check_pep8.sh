#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
pycodestyle app tests
