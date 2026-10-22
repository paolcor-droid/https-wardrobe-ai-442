#!/usr/bin/env bash
# Archive LUMIÈRE local private photographs without changing or deleting originals.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/backend/.lumiere-private-images"
DEST="${LUMIERE_BACKUP_DIR:-$ROOT/.lumiere-backups}"
if [[ ! -d "$SOURCE" ]]; then
  echo 'Local private photograph directory absent; no local photo archive created.' >&2
  echo 'Check LUMIERE_PHOTO_STORAGE (S3/Supabase need provider-specific backups).' >&2
  exit 2
fi
[[ "$DEST" = /* ]] || { echo 'Backup directory must be absolute' >&2; exit 1; }
umask 077
mkdir -p "$DEST"
chmod 700 "$DEST"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$DEST/lumiere-private-photos-$STAMP.tar.gz"
TMP="$(mktemp "$DEST/.photos-XXXXXXXX")"
trap 'rm -f "$TMP"' EXIT
# Never follow symlinks (including symlinks to outside the private image directory).
if find "$SOURCE" -type l -print -quit | grep -q .; then
  echo 'Symlink found inside private photo storage; refusing archive' >&2; exit 1
fi
tar -C "$ROOT/backend" -czf "$TMP" .lumiere-private-images
gzip -t "$TMP"
[[ ! -e "$TARGET" ]] || { echo 'Archive already exists' >&2; exit 1; }
mv "$TMP" "$TARGET"
sha256sum "$TARGET" > "$TARGET.sha256"
chmod 600 "$TARGET" "$TARGET.sha256"
trap - EXIT
echo "Local private-photo backup: $TARGET"
echo 'Includes sensitive personal images. Keep encrypted, offsite and never commit it.'
