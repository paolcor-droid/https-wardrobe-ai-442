#!/usr/bin/env bash
# Verify a development MongoDB backup by restoring into an isolated temporary database.
# Never writes to or drops the live LUMIÈRE database.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVE="${1:-}"
[[ -f "$ARCHIVE" && "$ARCHIVE" == *.archive.gz ]] || { echo 'Usage: bash scripts/verify-lumiere-backup.sh /absolute/path/to/archive.gz' >&2; exit 2; }
ARCHIVE="$(realpath "$ARCHIVE")"
[[ -f "$ARCHIVE.sha256" ]] || { echo 'Missing checksum; refusing restoration test' >&2; exit 1; }
(cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256")
gzip -t "$ARCHIVE"
[[ -f "$ROOT/backend/.env" ]] || { echo 'Missing backend/.env' >&2; exit 1; }
LIVE_DB="$(python - "$ROOT/backend/.env" <<'PY'
import re,sys
from dotenv import dotenv_values
from urllib.parse import urlsplit
conf=dotenv_values(sys.argv[1])
url=urlsplit(conf.get('MONGO_URL') or '')
name=conf.get('DB_NAME') or ''
if url.scheme != 'mongodb' or url.hostname not in ('localhost','127.0.0.1') or url.port != 27017 or not re.fullmatch('[A-Za-z0-9_-]{1,64}',name):
    raise SystemExit('Unsafe database configuration; abort')
print(name)
PY
)"
CONTAINER=lumiere-dev-mongo
[[ "$(docker inspect --format '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" == true ]] || { echo 'Existing MongoDB not running' >&2; exit 1; }
docker exec "$CONTAINER" mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' | grep -qx '1'
TMP_DB="lumiere_restorecheck_$(date -u +%Y%m%d%H%M%S)_$RANDOM"
[[ "$TMP_DB" != "$LIVE_DB" ]] || exit 1
cleanup() {
  if [[ "${RESTORE_TEST_KEEP:-0}" != 1 ]]; then
    docker exec "$CONTAINER" mongosh --quiet --eval "db.getSiblingDB('$TMP_DB').dropDatabase()" >/dev/null || echo 'WARNING: could not clean temporary test database' >&2
  fi
}
trap cleanup EXIT
echo "Restoring archive into temporary database $TMP_DB, NOT $LIVE_DB."
docker exec -i "$CONTAINER" mongorestore --quiet --gzip --archive --nsFrom="$LIVE_DB.*" --nsTo="$TMP_DB.*" --stopOnError < "$ARCHIVE"
docker exec "$CONTAINER" mongosh --quiet --eval "const d=db.getSiblingDB('$TMP_DB'); const names=d.getCollectionNames(); const totals=names.map(n=>({collection:n,count:d.getCollection(n).countDocuments({})})); print(JSON.stringify({collections:names.length,documents:totals.reduce((a,b)=>a+b.count,0)})); if (!names.length) quit(2);"
echo 'Restore test succeeded. Temporary database will be removed by the cleanup handler.'
