#!/bin/sh
# Daily SQLite backup. Run from a Render cron job or any scheduler with access to /data.
# Usage: DB=/data/shortlistme.db DEST=/data/backups KEEP=14 ./backup.sh   (then copy DEST off-site)
set -eu
DB="${DB:-/data/shortlistme.db}"
DEST="${DEST:-/data/backups}"
KEEP="${KEEP:-14}"
mkdir -p "$DEST"
OUT="$DEST/shortlistme-$(date +%Y%m%d-%H%M%S).db"
python - "$DB" "$OUT" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
PY
ls -1t "$DEST"/shortlistme-*.db | tail -n +$((KEEP + 1)) | xargs -r rm --
echo "backup written: $OUT"
