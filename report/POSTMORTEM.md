# Postmortem: Order Creation Failures (Simulated)

Date: **May 15, 2026**  
Timezone: **Asia/Almaty**  
Services impacted: `order-service` (customer order creation)  
Detection: Prometheus alert + Grafana dashboard

## Summary

A configuration change introduced an invalid upstream dependency URL in `order-service` (Product Service endpoint). As a result, `POST /orders` began returning 5xx responses. Monitoring detected the elevated 5xx rate and the team restored service by reverting the configuration and restarting the service.

## Impact

- User-visible: customers could not create orders
- API impact: increased `5xx` from `order-service` on `POST /orders`
- Duration: **~12 minutes** (example timeline below)

## Root Cause

Misconfigured `PRODUCT_SERVICE_URL` in `order-service`, pointing to a non-existent host, which caused dependency requests to fail and the endpoint to return errors.

This is reproducible using:
```bash
docker compose -f docker-compose.yml -f docker-compose.incident.yml up -d --build
```

## Timeline (example)

- 18:05 — config deployed (invalid `PRODUCT_SERVICE_URL`)
- 18:06 — `POST /orders` errors observed in Grafana
- 18:07 — alert `OrderServiceHigh5xx` firing in Alertmanager
- 18:12 — logs reviewed (`scripts/inspect_logs.sh order-service`)
- 18:17 — config reverted and service restarted
- 18:18 — metrics returned to normal (5xx down, 2xx up)

## Detection

- Alert: `OrderServiceHigh5xx` (Prometheus → Alertmanager)
- Dashboard: `infra/grafana/dashboards/sre-dashboard.json`

## Resolution

Reverted `PRODUCT_SERVICE_URL` and rebuilt/restarted the service:
```bash
docker compose up -d --build order-service
```

## What went well

- Alerting detected errors quickly
- Logs clearly showed dependency failures
- Restart/self-healing reduced recovery time

## What went wrong

- Config regression was not validated pre-deploy
- No automated smoke test for order creation after deploy

## Action items

| Item | Owner | Priority | Due date |
|---|---|---|---|
| Pre-deploy env validation in CI (`scripts/validate_env.py`) | Team | High | May 22, 2026 |
| Add smoke test for `POST /orders` in deployment pipeline | Team | High | May 22, 2026 |
| Add dashboard panels for dependency health | Team | Medium | May 29, 2026 |
| Route alerts to chat/email (optional) | Team | Low | Jun 5, 2026 |

