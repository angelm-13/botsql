#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
pydocstyle app --convention=numpy || true
