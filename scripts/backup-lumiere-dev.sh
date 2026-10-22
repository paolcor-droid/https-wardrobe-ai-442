#!/usr/bin/env bash
# Back up the existing LUMIÈRE development MongoDB without editing the source database.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER=lumiere-dev-mongo
BACKUP_DIR="${LUMIERE_BACKUP_DIR:-$ROOT/.lumiere-backups}"
[[ "$BACKUP_DIR" = /* ]] || { echo "Backup location must be absolute" >&2; exit 1; }
command -v docker >/dev/null || { echo "Docker is unavailable" >&2; exit 1; }
docker inspect "$CONTAINER" >/dev/null 2>&1 || { echo "Existing MongoDB container unavailable" >&2; exit 1; }
[[ "$(docker inspect --format '{{.State.Running}}' "$CONTAINER")" = true ]] || { echo "MongoDB must be running" >&2; exit 1; }
[[ -f "$ROOT/backend/.env" ]] || { echo "Missing backend/.env" >&2; exit 1; }
DB_NAME="$(python - "$ROOT/backend/.env" <<'PY'
import sys,re
from pathlib import Path
from dotenv import dotenv_values
from urllib.parse import urlsplit
conf=dotenv_values(Path(sys.argv[1]))
url=urlsplit(conf.get('MONGO_URL') or '')
db=conf.get('DB_NAME') or ''
if url.scheme!='mongodb' or url.hostname not in ('localhost','127.0.0.1') or url.port != 27017 or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',db):
    raise SystemExit('Unsafe database configuration; backup refused')
print(db)
PY
)"
umask 077
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
now="$(date -u +%Y%m%dT%H%M%SZ)"
target="$BACKUP_DIR/lumiere-$now.archive.gz"
temp="$(mktemp "$BACKUP_DIR/.backup-XXXXXXXX")"
trap 'rm -f "$temp"' EXIT
echo "Backing up configured database to a private, Git-ignored directory."
docker exec "$CONTAINER" mongodump --quiet --db "$DB_NAME" --archive --gzip > "$temp"
[[ -s "$temp" ]] || { echo "Backup empty; refused" >&2; exit 1; }
# Verify stream integrity before publishing the backup; do not restore into the live DB.
gzip -t "$temp" || { echo "Backup gzip stream failed integrity check" >&2; exit 1; }
[[ ! -e "$target" ]] || { echo "Backup target already exists; refusing overwrite" >&2; exit 1; }
mv "$temp" "$target"
sha256sum "$target" > "$target.sha256"
chmod 600 "$target" "$target.sha256"
trap - EXIT
echo "Backup created: $target"
echo "This archive contains private customer records: keep it encrypted offsite and never commit or publicly share it."
echo "Retention is manual; old backups are not automatically removed."
