#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export TESTING="${TESTING:-1}"
export JWT_SECRET="${JWT_SECRET:-test-secret}"
export JWT_SS="${JWT_SS:-test-secret}"
export MFA_ISSUER="${MFA_ISSUER:-TYAKXA CI}"
bash ci/check_format.sh
bash ci/check_lint.sh
bash ci/check_pep8.sh
bash ci/check_docstyle.sh
bash ci/check_imports.sh
bash ci/check_security.sh
bash ci/check_dependencies.sh
bash ci/check_links.sh
bash ci/run_unit_tests.sh
