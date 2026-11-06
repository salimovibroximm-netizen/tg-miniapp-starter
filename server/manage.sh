#!/bin/sh
# start | stop | restart | status | log
#
# Works on shared hosting without systemd or root. The running process is found
# by scanning /proc for its exact command line, not only by a PID file: a stale
# PID file (after a server reboot, for example) would otherwise make the
# watchdog start a second copy every few minutes ("address already in use").
set -u
cd "$(dirname "$0")/.." || exit 1
APP_DIR=$(pwd)
. "$APP_DIR/server/paths.conf"

PID_FILE="$DATA_ROOT/app.pid"
LOG="$DATA_ROOT/log/app.log"
mkdir -p "$DATA_ROOT/log"

find_pid() {
  for d in /proc/[0-9]*; do
    cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null) || continue
    case "$cmd" in
      *"uvicorn app.main:app"*"--port $PORT "*) echo "${d#/proc/}"; return 0 ;;
    esac
  done
  return 1
}

start() {
  if pid=$(find_pid); then
    echo "$pid" > "$PID_FILE"
    echo "already running (pid $pid, port $PORT)"
    return 0
  fi
  # copy+truncate keeps the log small without breaking the open file handle
  if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 5000000 ]; then
    cp "$LOG" "$LOG.1" && : > "$LOG"
  fi
  TMPDIR="$DATA_ROOT/cache/tmp" nohup "$VENV/bin/python" -m uvicorn app.main:app \
    --host 127.0.0.1 --port "$PORT" --proxy-headers --forwarded-allow-ips='*' >> "$LOG" 2>&1 &
  sleep 3
  if pid=$(find_pid); then
    echo "$pid" > "$PID_FILE"
    echo "started (pid $pid, port $PORT)"
  else
    rm -f "$PID_FILE"
    echo "FAILED to start - last log lines:"
    tail -n 20 "$LOG"
    return 1
  fi
}

stop() {
  if pid=$(find_pid); then
    kill "$pid"
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      find_pid > /dev/null || break
      sleep 1
    done
    find_pid > /dev/null && kill -9 "$pid"
    echo "stopped"
  else
    echo "not running"
  fi
  rm -f "$PID_FILE"
}

case "${1:-status}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) if pid=$(find_pid); then echo "running (pid $pid, port $PORT)"; else echo "not running"; exit 1; fi ;;
  log) tail -n "${2:-50}" "$LOG" ;;
  *) echo "usage: $0 start|stop|restart|status|log [lines]"; exit 2 ;;
esac
