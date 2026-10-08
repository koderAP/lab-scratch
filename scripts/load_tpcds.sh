#!/usr/bin/env bash
# Generate TPC-DS with DuckDB and load into PostgreSQL.
# Usage: scripts/load_tpcds.sh <scale_factor>
# Example: scripts/load_tpcds.sh 1
set -euo pipefail

SF="${1:?scale factor required, e.g. 1 or 10}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_NAME="${COL868_DB:-col868}"
SCHEMA="tpcds_sf$(echo "$SF" | tr -d '.')"
EXPORT_DIR="$ROOT/data/${SCHEMA}"

mkdir -p "$ROOT/data"
rm -rf "$EXPORT_DIR"

echo "==> DuckDB dsdgen sf=${SF} -> ${EXPORT_DIR}"
duckdb -c "INSTALL tpcds; LOAD tpcds; CALL dsdgen(sf=${SF}); EXPORT DATABASE '${EXPORT_DIR}' (FORMAT CSV, DELIMITER '|');"

echo "==> Rewriting COPY to \\\\copy for client-side load"
sed 's/^COPY /\\copy /' "$EXPORT_DIR/load.sql" > "$EXPORT_DIR/load-psql.sql"

echo "==> Creating schema ${SCHEMA} in database ${DB_NAME}"
psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS ${SCHEMA} CASCADE; CREATE SCHEMA ${SCHEMA};"
# DuckDB schema/load SQL is unqualified; search_path + cwd for \copy paths.
(
  cd "$EXPORT_DIR"
  PGOPTIONS="--search-path=${SCHEMA}" psql -d "$DB_NAME" -v ON_ERROR_STOP=1 \
    -f schema.sql \
    -f load-psql.sql
)

echo "==> ANALYZE ${SCHEMA}"
PGOPTIONS="--search-path=${SCHEMA}" psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "ANALYZE;"

psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
WHERE schemaname = '${SCHEMA}'
ORDER BY n_live_tup DESC
LIMIT 15;
"

echo "==> Loaded ${SCHEMA}. Optional: rm -rf ${EXPORT_DIR} to reclaim CSV disk."
