#!/usr/bin/env bash
set -euo pipefail
SCHEMA="${1:?schema e.g. tpcds_sf1}"
DB="${COL868_DB:-col868}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PGOPTIONS="--search-path=${SCHEMA}" psql -d "$DB" -v ON_ERROR_STOP=1 -f "$ROOT/sql/tpcds_pks.sql"
PGOPTIONS="--search-path=${SCHEMA}" psql -d "$DB" -v ON_ERROR_STOP=1 -c "ANALYZE;"
echo "PKs applied on ${SCHEMA}"
