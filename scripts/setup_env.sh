#!/usr/bin/env bash
# Local development environment for COL868 sample-based index evaluation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PG_CONF="/opt/homebrew/var/postgresql@14/postgresql.conf"
INCLUDE_LINE="include_if_exists '${ROOT}/config/postgresql-tpcds.conf'"
DB_NAME="${COL868_DB:-col868}"

echo "==> DuckDB"
command -v duckdb >/dev/null
duckdb --version

echo "==> PostgreSQL 14"
pg_isready
psql --version

if ! grep -Fq "$INCLUDE_LINE" "$PG_CONF"; then
  echo "==> Adding include to $PG_CONF"
  printf '\n# COL868 TPC-DS iteration settings\n%s\n' "$INCLUDE_LINE" >> "$PG_CONF"
else
  echo "==> postgresql.conf already includes project settings"
fi

echo "==> Restarting postgresql@14 to load pg_stat_statements and buffers"
brew services restart postgresql@14

for i in $(seq 1 30); do
  if pg_isready -q; then
    break
  fi
  sleep 1
done
pg_isready

echo "==> Creating database ${DB_NAME} and extensions"
if ! psql -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  psql -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${DB_NAME};"
fi

psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS hypopg;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS tsm_system_rows;
CREATE EXTENSION IF NOT EXISTS tsm_system_time;
SELECT extname, extversion FROM pg_extension ORDER BY 1;
SHOW shared_buffers;
SHOW shared_preload_libraries;
SQL

mkdir -p "$ROOT/data" "$ROOT/results" "$ROOT/workloads"
echo "==> Ready. Data dir: $ROOT/data"
