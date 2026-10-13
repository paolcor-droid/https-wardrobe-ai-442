#!/usr/bin/env bash
# Dedicated disposable MongoDB for Samsung private staging. No existing DB touched.
set -Eeuo pipefail
expected="solid-space-waffle-g4v4jwv7wr7gh9r7v"
if [[ "${CODESPACE_NAME:-}" != "$expected" ]]; then
  echo "BLOCKED: run only in the specifically verified disposable staging Codespace." >&2; exit 2
fi
if [[ "$(git branch --show-current)" != "lumiere-recommendations-v2" ]]; then
  echo "BLOCKED: unexpected branch." >&2; exit 2
fi
container="lumiere-android-staging-mongo"
volume="lumiere-android-staging-disposable-db"
if docker inspect "$container" >/dev/null 2>&1; then
  echo "Existing staging container detected. No changes made."
  docker inspect -f 'Name={{.Name}} Running={{.State.Running}}' "$container"
  exit 0
fi
if docker volume inspect "$volume" >/dev/null 2>&1; then
  echo "BLOCKED: staging volume already exists but container is missing; refusing to attach automatically." >&2
  exit 2
fi
if (echo >/dev/tcp/127.0.0.1/27019) >/dev/null 2>&1; then
  echo "BLOCKED: port 27019 is occupied." >&2; exit 2
fi
docker run -d --name "$container" --restart unless-stopped \
  --publish 127.0.0.1:27019:27017 \
  --mount "type=volume,source=$volume,target=/data/db" \
  mongo:7 --bind_ip_all >/dev/null
for i in {1..35}; do
  if docker exec "$container" mongosh --quiet --eval 'db.adminCommand({ping:1}).ok' 2>/dev/null | grep -qx 1; then
    echo "PASS: isolated staging MongoDB is healthy on loopback only (127.0.0.1:27019)"
    echo "Container: $container ; volume: $volume"
    echo "Use MONGO_URL=mongodb://127.0.0.1:27019 and DB_NAME=lumiere_android_staging_disposable"
    exit 0
  fi
  sleep 1
done
echo "MongoDB was created but did not pass health check. Inspect its logs before proceeding." >&2
exit 1
