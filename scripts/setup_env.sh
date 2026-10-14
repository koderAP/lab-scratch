#!/usr/bin/env bash
# Create database col868, install extensions, point postgresql.conf at the project settings.
# Laptop (Homebrew PG 14): uses config/postgresql-tpcds.conf
# Server: set COL868_PG_CONF to config/postgresql-server.conf (edit the numbers first)
#         and PG_CONF to the cluster's postgresql.conf if it is not auto-detected.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_NAME="${COL868_DB:-col868}"
SETTINGS="${COL868_PG_CONF:-$ROOT/config/postgresql-tpcds.conf}"

echo "==> DuckDB"
command -v duckdb >/dev/null
duckdb --version

echo "==> PostgreSQL"
command -v psql >/dev/null
psql --version
pg_isready

detect_pg_conf() {
  if [[ -n "${PG_CONF:-}" && -f "$PG_CONF" ]]; then
    echo "$PG_CONF"
    return
  fi
  local c
  for c in \
    /opt/homebrew/var/postgresql@14/postgresql.conf \
    /etc/postgresql/14/main/postgresql.conf \
    /etc/postgresql/15/main/postgresql.conf \
    /etc/postgresql/16/main/postgresql.conf \
    /var/lib/pgsql/14/data/postgresql.conf \
    /var/lib/pgsql/data/postgresql.conf
  do
    if [[ -f "$c" ]]; then
      echo "$c"
      return
    fi
  done
  echo "Set PG_CONF to the cluster postgresql.conf" >&2
  exit 1
}

PG_CONF="$(detect_pg_conf)"
INCLUDE_LINE="include_if_exists '${SETTINGS}'"
echo "==> postgresql.conf: $PG_CONF"
echo "==> settings file:   $SETTINGS"

if ! grep -Fq "$INCLUDE_LINE" "$PG_CONF"; then
  echo "==> Adding include (needs write permission on $PG_CONF)"
  printf '\n# COL868 TPC-DS settings\n%s\n' "$INCLUDE_LINE" >> "$PG_CONF"
else
  echo "==> include already present"
fi

restart_pg() {
  if command -v brew >/dev/null 2>&1 && brew services list 2>/dev/null | grep -q postgresql@14; then
    echo "==> Restarting Homebrew postgresql@14"
    brew services restart postgresql@14
    return
  fi
  if command -v systemctl >/dev/null 2>&1; then
    echo "==> Restart Postgres so shared_buffers and autovacuum=off take effect:"
    echo "    sudo systemctl restart postgresql"
    echo "    (or postgresql@14-main, depending on the unit name)"
    return
  fi
  echo "==> Restart the Postgres cluster, then rerun this script to finish extensions."
}

restart_pg

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
SHOW autovacuum;
SHOW effective_io_concurrency;
SQL

mkdir -p "$ROOT/data" "$ROOT/results" "$ROOT/workloads"
echo "==> Ready. Data dir: $ROOT/data  database: ${DB_NAME}"
echo "==> Confirm autovacuum is off and shared_buffers matches the machine before loading TPC-DS."
