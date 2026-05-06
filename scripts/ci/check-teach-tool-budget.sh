#!/usr/bin/env bash
# CI assertion: verify state-teach tool descriptions are within token budget.
# Exits 0 if all pass, non-zero on failure.
#
# Usage: bash scripts/ci/check-teach-tool-budget.sh
#
# Prerequisites:
#   - Run from the project root
#   - .venv/ must exist with state installed in dev mode

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Tool Budget Check: state-teach ==="
.venv/bin/python -m state_cli dev tool-budget --server state-teach
echo "=== PASS: All state-teach tools within budget ==="
