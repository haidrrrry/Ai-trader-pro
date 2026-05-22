#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [[ -n "${DATABASE_URL:-}" ]]; then
  OUT="$BACKUP_DIR/ai_trader_${TIMESTAMP}.sql.gz"
  echo "Backing up PostgreSQL to $OUT"
  pg_dump "$DATABASE_URL" | gzip > "$OUT"
  echo "Done: $OUT"
  exit 0
fi

if docker compose -f "$ROOT_DIR/docker-compose.yml" ps postgres >/dev/null 2>&1; then
  OUT="$BACKUP_DIR/ai_trader_${TIMESTAMP}.sql.gz"
  echo "Backing up Docker postgres to $OUT"
  docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
    pg_dump -U ai_trader ai_trader | gzip > "$OUT"
  echo "Done: $OUT"
  exit 0
fi

echo "Set DATABASE_URL or run docker compose with postgres service." >&2
exit 1
