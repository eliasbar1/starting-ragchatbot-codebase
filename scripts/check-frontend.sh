#!/usr/bin/env bash
# Run frontend code quality checks.
# Usage: ./scripts/check-frontend.sh [--fix]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FIX=false
if [[ "${1:-}" == "--fix" ]]; then
  FIX=true
fi

echo "==> Frontend quality checks"

if $FIX; then
  echo "    Formatting with Prettier (--fix mode)..."
  npx prettier --write frontend/
  echo "    Done. All files formatted."
else
  echo "    Checking formatting with Prettier..."
  if npx prettier --check frontend/; then
    echo "    All files are correctly formatted."
  else
    echo ""
    echo "    Run './scripts/check-frontend.sh --fix' to auto-format."
    exit 1
  fi
fi
