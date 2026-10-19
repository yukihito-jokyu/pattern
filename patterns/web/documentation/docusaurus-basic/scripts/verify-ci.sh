#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cleanup() {
  result=$?
  trap - EXIT
  if [ -n "${CI_ARTIFACTS_DIR:-}" ] && [ -d test-results ]; then
    mkdir -p "$CI_ARTIFACTS_DIR"
    cp -R test-results "$CI_ARTIFACTS_DIR/" || { if [ "$result" -eq 0 ]; then result=1; fi; }
  fi
  exit "$result"
}
trap cleanup EXIT
npm ci
npm run setup -- check
npm run typecheck
npm run build
npx playwright install --with-deps chromium
npm test
