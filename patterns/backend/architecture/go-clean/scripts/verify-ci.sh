#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-pattern-go-clean-ci}"
export DB_PORT="${DB_PORT:-15432}"
export DATABASE_URL="${DATABASE_URL:-postgres://app:app@127.0.0.1:15432/app?sslmode=disable}"
export APP_ADDR="${APP_ADDR:-127.0.0.1:18080}"
export API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:18080}"
api_pid=''
database_started=false
log_file=$(mktemp)
cleanup() {
  result=$?
  trap - EXIT
  if [ -n "$api_pid" ]; then kill "$api_pid" 2>/dev/null || true; wait "$api_pid" 2>/dev/null || true; fi
  if [ "$database_started" = true ]; then
    docker compose down -v || { if [ "$result" -eq 0 ]; then result=1; fi; }
  fi
  cat "$log_file"
  rm -f "$log_file"
  exit "$result"
}
trap cleanup EXIT

go mod download
make tools
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-setup.txt
.venv/bin/python scripts/setup.py check
.venv/bin/python scripts/setup_test.py
make check
make test
make check-deps
database_started=true
make db-up
make migrate-up
make build
bin/api > "$log_file" 2>&1 &
api_pid=$!
make smoke
make migrate-down
make migrate-up
