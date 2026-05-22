#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 backups/ai_trader_YYYYMMDD_HHMMSS.sql.gz" >&2
  exit 1
fi

DUMP_FILE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${DATABASE_URL:-}" ]]; then
  echo "Restoring into $DATABASE_URL from $DUMP_FILE"
  gunzip -c "$DUMP_FILE" | psql "$DATABASE_URL"
  echo "Restore complete."
  exit 0
fi

if docker compose -f "$ROOT_DIR/docker-compose.yml" ps postgres >/dev/null 2>&1; then
  echo "Restoring Docker postgres from $DUMP_FILE"
  gunzip -c "$DUMP_FILE" | docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
    psql -U ai_trader ai_trader
  echo "Restore complete."
  exit 0
fi

echo "Set DATABASE_URL or run docker compose with postgres service." >&2
exit 1
