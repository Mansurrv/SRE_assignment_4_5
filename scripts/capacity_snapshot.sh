#!/usr/bin/env sh
set -eu

PROM_URL="${PROM_URL:-http://localhost:9090}"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 2
  fi
}

need curl
need jq

q() {
  name="$1"
  query="$2"
  value="$(curl -sS "$PROM_URL/api/v1/query" --data-urlencode "query=$query" | jq -r '.data.result[0].value[1] // "n/a"')"
  printf "%-28s %s\n" "$name" "$value"
}

echo "Prometheus: $PROM_URL"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

q "order_cpu_cores" 'sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service="order-service",image!=""}[2m]))'
q "order_mem_bytes" 'max(container_memory_working_set_bytes{container_label_com_docker_compose_service="order-service",image!=""})'
q "order_rps" 'sum(rate(http_requests_total{service="order-service"}[1m]))'
q "order_5xx_rps" 'sum(rate(http_requests_total{service="order-service",status=~"5.."}[1m]))'
q "order_restarts_10m" 'changes(container_start_time_seconds{container_label_com_docker_compose_service="order-service",image!=""}[10m])'

echo
echo "Tip: run with capacity profile enabled:"
echo "  FRONTEND_PORT=8080 docker compose --profile capacity up -d --build"
