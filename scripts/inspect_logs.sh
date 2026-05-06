#!/usr/bin/env sh
set -eu

SERVICE="${1:-}"
TAIL="${TAIL:-200}"

if [ -z "$SERVICE" ]; then
  echo "Usage: scripts/inspect_logs.sh <service>" >&2
  exit 2
fi

echo "== docker compose logs --tail=$TAIL $SERVICE"
docker compose logs --tail="$TAIL" "$SERVICE" || true

echo
echo "== suspicious patterns (best-effort)"
PATTERN="traceback|exception|error|connection refused|could not connect|timeout|restart|healthcheck|jwt|database_url"
if command -v rg >/dev/null 2>&1; then
  docker compose logs --tail="$TAIL" "$SERVICE" 2>/dev/null | rg -n -i "$PATTERN" || true
else
  docker compose logs --tail="$TAIL" "$SERVICE" 2>/dev/null | grep -Eni "$PATTERN" || true
fi
