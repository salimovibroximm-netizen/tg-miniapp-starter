#!/bin/sh
# Daily backup: a consistent copy of the SQLite database (gzipped, KEEP_DAYS kept)
# and ONE mirror of the photos (only new files are copied, so it stays cheap).
# Also warns in the log when the disk is getting full.
set -u
cd "$(dirname "$0")/.." || exit 1
. ./server/paths.conf

DEST="$DATA_ROOT/backups"
LOG="$DATA_ROOT/log/backup.log"
DB="$DATA_ROOT/data/app.db"
mkdir -p "$DEST/media"
STAMP=$(date +%Y-%m-%d)

if [ -f "$DB" ]; then
  # sqlite's backup API copies a live database safely, unlike cp
  "$VENV/bin/python" - "$DB" "$DEST/app-$STAMP.db" <<'PY'
import sqlite3, sys
src, dst = sqlite3.connect(sys.argv[1]), sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close(); src.close()
PY
  gzip -f "$DEST/app-$STAMP.db"
fi
[ -d "$DATA_ROOT/data/media" ] && cp -ru "$DATA_ROOT/data/media/." "$DEST/media/"
find "$DEST" -maxdepth 1 -name 'app-*.db.gz' -mtime +"$KEEP_DAYS" -delete

USED=$(df -P "$DATA_ROOT" | awk 'NR==2 {gsub("%", "", $5); print $5}')
echo "$(date '+%F %T') backup done, disk ${USED}%" >> "$LOG"
[ "${USED:-0}" -ge 85 ] && echo "$(date '+%F %T') WARNING: disk ${USED}% full" >> "$LOG"
exit 0
