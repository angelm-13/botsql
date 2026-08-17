#!/bin/bash
set -e
cd "$(dirname "$0")"
export TESTING=1
export JWT_SECRET="${JWT_SECRET:-test-secret}"
export JWT_SS="${JWT_SS:-test-secret}"
pytest -q
