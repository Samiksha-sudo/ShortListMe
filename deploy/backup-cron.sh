#!/bin/sh
# Daily backup of the SQLite DB and uploaded CVs from the running api container to /root/backups.
# Install:  (crontab -l; echo "15 3 * * * sh /root/ShortListMe/deploy/backup-cron.sh") | crontab -
set -eu
DEST=/root/backups; mkdir -p "$DEST"
STAMP=$(date +%Y%m%d-%H%M%S)
cd "$(dirname "$0")/.."
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec -T api \
  python -c "import sqlite3;s=sqlite3.connect('/data/shortlistme.db');d=sqlite3.connect('/data/backup.db');s.backup(d);d.close()"
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec -T api tar -C /data -cf - backup.db storage > "$DEST/shortlistme-$STAMP.tar"
ls -1t "$DEST"/shortlistme-*.tar | tail -n +15 | xargs -r rm --
echo "backup written: $DEST/shortlistme-$STAMP.tar"
