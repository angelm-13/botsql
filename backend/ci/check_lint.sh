#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
flake8 app tests --count --show-source --statistics
