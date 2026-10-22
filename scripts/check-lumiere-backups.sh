#!/usr/bin/env bash
# Read-only health report for local LUMIÈRE backup files. No restores or deletion.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="${LUMIERE_BACKUP_DIR:-$ROOT/.lumiere-backups}"
[[ "$DIR" = /* ]] || { echo 'Backup directory must be absolute' >&2; exit 2; }
[[ -d "$DIR" ]] || { echo "No backup directory: $DIR"; exit 1; }
command -v sha256sum >/dev/null || exit 2
shopt -s nullglob
db=( "$DIR"/lumiere-*.archive.gz )
photos=( "$DIR"/lumiere-private-photos-*.tar.gz )
status=0
check() {
  local label="$1"; shift
  local files=( "$@" )
  if (("${#files[@]}" == 0)); then
    echo "$label: no backup files found"
    status=1
    return
  fi
  local newest=""
  local f
  for f in "${files[@]}"; do
    if [[ ! -f "$f.sha256" ]]; then
      echo "$label: UNVERIFIED (missing checksum): $(basename "$f")"
      status=1
      continue
    fi
    if (cd "$(dirname "$f")" && sha256sum -c --status "$(basename "$f").sha256"); then
      [[ "$f" > "$newest" ]] && newest="$f"
    else
      echo "$label: FAILED integrity: $(basename "$f")"
      status=1
    fi
  done
  if [[ -n "$newest" ]]; then
    echo "$label: latest checksum-verified archive: $(basename "$newest")"
  fi
}
check Database "${db[@]}"
check 'Local photographs' "${photos[@]}"
echo 'Checksums do NOT verify database restoration or offsite storage.'
echo 'Offsite encryption and independent restoration still require separate verification.'
exit "$status"
