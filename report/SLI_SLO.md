# SLI / SLO (Endterm)

Measured via Prometheus metrics exposed by each microservice (`GET /metrics`).

## SLI/SLO Table (what to show in Grafana)

| SLI | SLO target | Typical for flower shop web app | Risk | Metric | PromQL |
|---|---:|---|---|---|---|
| Availability | **≥ 99.9%** | Usually **≥ 99.9%** (≈ 8h 45m downtime/year vs ≈ 3.5 days/year for 99.0%) | **99.0% is low** for modern web apps; users notice frequent “cannot load flowers” | success / total | `sum(rate(http_requests_total{status=~"2..|3.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| Latency (`POST /orders`) | **p95 ≤ 300 ms** | 300 ms acceptable (incl. payment simulation) | 200 ms is aggressive: payment + DB writes + notifications can exceed this | histogram buckets | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{service="order-service",method="POST",path="/orders"}[5m])))` |
| Error rate | **≤ 0.5% 5xx** | ≤ 0.5% typical | 1% is borderline (e.g., occasional dependency timeouts) | 5xx / total | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |

## Notes for this repo (label mapping)

This project’s metrics use these labels:
- Counter: `http_requests_total{service, method, path, status}`
- Histogram: `http_request_duration_seconds_bucket{service, method, path, le}`

So in Grafana, filter endpoints by `service="order-service"`, `method="POST"`, `path="/orders"` (not `endpoint=`).

## Optional: per-service availability

Availability for `order-service` only:
`sum(rate(http_requests_total{service="order-service",status=~"2..|3.."}[5m])) / sum(rate(http_requests_total{service="order-service"}[5m]))`
