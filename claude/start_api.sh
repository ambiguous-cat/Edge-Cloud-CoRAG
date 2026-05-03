#!/usr/bin/env bash
set -euo pipefail

APP_NAME="rag-api"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8005}"
WORKERS="${WORKERS:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PID_FILE="${PID_FILE:-$SCRIPT_DIR/$APP_NAME.pid}"
LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/$APP_NAME.log}"
MCP_DIR="${MCP_DIR:-$SCRIPT_DIR/Arxiv-Paper-MCP}"
MCP_ENTRY="${MCP_ENTRY:-$MCP_DIR/build/index.js}"
MCP_SOURCE="${MCP_SOURCE:-$MCP_DIR/src/index.ts}"

cd "$SCRIPT_DIR"
mkdir -p "$LOG_DIR"

ensure_python_deps() {
  if ! "$PYTHON_BIN" -c "import uvicorn, fastapi" >/dev/null 2>&1; then
    echo "Installing Python dependencies into system/user Python from requirements.txt"
    "$PYTHON_BIN" -m pip install -r "$SCRIPT_DIR/requirements.txt"
  fi
}

ensure_mcp_build() {
  if [[ -d "$MCP_DIR" && ( ! -f "$MCP_ENTRY" || "$MCP_SOURCE" -nt "$MCP_ENTRY" ) ]]; then
    echo "Building Arxiv-Paper-MCP"
    (cd "$MCP_DIR" && npm install && npm run build)
  fi
}

is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1
}

start_foreground() {
  ensure_python_deps
  ensure_mcp_build
  exec "$PYTHON_BIN" -m uvicorn api_server:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS"
}

start_daemon() {
  if is_running; then
    echo "$APP_NAME is already running, pid=$(cat "$PID_FILE")"
    return 0
  fi

  ensure_python_deps
  ensure_mcp_build
  echo "Starting $APP_NAME on $HOST:$PORT"
  nohup "$PYTHON_BIN" -m uvicorn api_server:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    >> "$LOG_FILE" 2>&1 &

  echo $! > "$PID_FILE"
  sleep 1

  if is_running; then
    echo "$APP_NAME started, pid=$(cat "$PID_FILE")"
    echo "Logs: $LOG_FILE"
  else
    echo "Failed to start $APP_NAME. Check logs: $LOG_FILE" >&2
    rm -f "$PID_FILE"
    return 1
  fi
}

stop_daemon() {
  if ! is_running; then
    echo "$APP_NAME is not running"
    rm -f "$PID_FILE"
    return 0
  fi

  pid="$(cat "$PID_FILE")"
  echo "Stopping $APP_NAME, pid=$pid"
  kill "$pid"

  for _ in {1..20}; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      rm -f "$PID_FILE"
      echo "$APP_NAME stopped"
      return 0
    fi
    sleep 0.5
  done

  echo "Force stopping $APP_NAME, pid=$pid"
  kill -9 "$pid" >/dev/null 2>&1 || true
  rm -f "$PID_FILE"
}

status_daemon() {
  if is_running; then
    echo "$APP_NAME is running, pid=$(cat "$PID_FILE"), url=http://$HOST:$PORT"
  else
    echo "$APP_NAME is not running"
    return 1
  fi
}

case "${1:-start}" in
  start)
    start_daemon
    ;;
  foreground)
    start_foreground
    ;;
  stop)
    stop_daemon
    ;;
  restart)
    stop_daemon
    start_daemon
    ;;
  status)
    status_daemon
    ;;
  logs)
    touch "$LOG_FILE"
    tail -f "$LOG_FILE"
    ;;
  *)
    echo "Usage: $0 {start|foreground|stop|restart|status|logs}"
    exit 2
    ;;
esac
