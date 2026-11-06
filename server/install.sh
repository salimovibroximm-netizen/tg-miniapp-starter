#!/bin/sh
# One-time setup: creates the data folders and the virtualenv, installs packages.
# Safe to run again after updating requirements.txt.
set -eu
cd "$(dirname "$0")/.."
APP_DIR=$(pwd)
[ -f server/paths.conf ] || { echo "copy server/paths.conf.example to server/paths.conf first"; exit 1; }
. "$APP_DIR/server/paths.conf"
[ -f .env ] || { echo "copy .env.example to .env and fill it in first"; exit 1; }

mkdir -p "$DATA_ROOT/data" "$DATA_ROOT/log" "$DATA_ROOT/backups" "$DATA_ROOT/cache/pip" "$DATA_ROOT/cache/tmp"
chmod 600 .env

"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), sys.version' \
  || { echo "need Python 3.11+, set PYTHON in server/paths.conf"; exit 1; }

[ -x "$VENV/bin/python" ] || "$PYTHON" -m venv "$VENV"
# pip's cache and temp files go to the data disk too, not to the small home quota
export PIP_CACHE_DIR="$DATA_ROOT/cache/pip" TMPDIR="$DATA_ROOT/cache/tmp"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r requirements.txt

grep -q '^DATA_DIR=' .env || echo "DATA_DIR=$DATA_ROOT/data" >> .env
chmod +x server/*.sh
echo
echo "Done. Next:"
echo "  sh server/manage.sh start"
echo "  curl -s http://127.0.0.1:$PORT/health"
echo "then set up the web proxy (server/htaccess.example) and cron (server/crontab.example)."
