# Assignment 6 — Verification Log (Commands + Observations)

This file documents the exact checks performed for **Assignment 6** in this workspace, including the commands used and what happened.

> Note: Runtime checks (starting containers, calling HTTP endpoints, observing Prometheus/Grafana) require a running Docker daemon. In this environment the Docker daemon was **not running**, so runtime verification is recorded as **blocked** with the exact error output.

## 0) Environment / Preconditions

### Docker daemon status (BLOCKED)

Command:
```bash
FRONTEND_PORT=8080 PROMETHEUS_PORT=9090 GRAFANA_PORT=3000 ALERTMANAGER_PORT=9093 \
docker compose --profile capacity up -d --build
```

Result (error observed):
```text
unable to get image 'grafana/grafana:11.2.2': failed to connect to the docker API at unix:///Users/user/.docker/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /Users/user/.docker/run/docker.sock: connect: no such file or directory
```

Additional confirmation:
```bash
docker version
```
```text
Client:
 Version:           29.3.1
 API version:       1.54
 Go version:        go1.25.8
 Git commit:        c2be9cc
 Built:             Wed Mar 25 16:12:49 2026
 OS/Arch:           darwin/arm64
 Context:           desktop-linux
failed to connect to the docker API at unix:///Users/user/.docker/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /Users/user/.docker/run/docker.sock: connect: no such file or directory
```

Action to unblock (run locally):
- Start **Docker Desktop** (or `colima start`) and retry the command above.

## 1) Requirement: Automated deployment (Compose + Terraform integration)

### 1.1 Validate Compose configuration (OK)

Command:
```bash
docker compose config >/dev/null
```

Result:
- Exit code `0` (Compose file parses and renders successfully).

### 1.2 Validate capacity profile services exist (OK)

Command:
```bash
docker compose --profile capacity config | rg -n "cadvisor|postgres-exporter"
```

Result (observed):
```text
56:  cadvisor:
226:  postgres-exporter:
```

### 1.3 Terraform bootstrap automation present (OK — static)

Files used for automated provisioning on the VM:
- `main.tf` sets `user_data = file("${path.module}/infra/cloud-init/user_data.sh")`
- `infra/cloud-init/user_data.sh` installs Docker Engine + Compose plugin and enables Docker at boot

## 2) Requirement: Health checks + self-healing (restart + healthchecks)

### 2.1 Static verification in Compose (OK)

Command:
```bash
sed -n '1,220p' docker-compose.yml
```

Result (observed):
- Services use `restart: unless-stopped`.
- Services have `healthcheck:` definitions (DB: `pg_isready`, services: `/ready`, frontend/monitoring: HTTP checks).

### 2.2 Runtime verification (BLOCKED — requires Docker daemon)

Commands to run after Docker is started:
```bash
FRONTEND_PORT=8080 docker compose --profile capacity up -d --build
docker compose ps
```

Expected evidence:
- Containers show `healthy` after initial warmup (screenshots: `docker compose ps`).

## 3) Requirement: Monitoring-based alerting (Prometheus rules)

### 3.1 Static verification of alert rules file (OK)

Command:
```bash
sed -n '1,220p' infra/prometheus/alerts.yml
```

Result (observed):
- Includes downtime alerts (`*ServiceDown`, `PrometheusTargetMissing`).
- Includes error-rate alerts (`ServiceHigh5xx`, `OrderServiceHigh5xx`).
- Includes capacity alerts using cAdvisor metrics (CPU/memory/restarts).

### 3.2 Runtime verification (BLOCKED — requires Docker daemon)

Commands to run after Docker is started:
```bash
FRONTEND_PORT=8080 docker compose --profile capacity up -d --build
curl -sS http://localhost:9090/targets | head
curl -sS http://localhost:9093/ | head
```

Expected evidence:
- Prometheus Targets page shows all jobs UP (screenshot).
- Alertmanager UI shows configured receivers and active alerts (screenshot).

## 4) Requirement: Log-based troubleshooting automation

### 4.1 Script syntax check (OK)

Command:
```bash
sh -n scripts/inspect_logs.sh
```

Result:
- No syntax errors.

### 4.2 Runtime usage (requires Docker daemon)

Command:
```bash
scripts/inspect_logs.sh order-service
```

Expected evidence:
- Output shows last logs + highlighted suspicious patterns for the chosen service.

## 5) Requirement: Configuration validation (pre-deploy checks)

### 5.1 Run env preflight (OK)

Command:
```bash
python3 scripts/validate_env.py
```

Result (observed):
```text
Environment preflight OK.
```

## 6) Requirement: Load simulation + capacity analysis

### 6.1 Load test script syntax (OK — static)

Command:
```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile scripts/load_test_orders.py
```

Result:
- Compiled successfully.

### 6.2 Runtime load test (BLOCKED — requires running stack)

Commands to run after Docker is started:
```bash
FRONTEND_PORT=8080 docker compose --profile capacity up -d --build
python3 scripts/load_test_orders.py --base-url http://localhost:8080 --concurrency 20 --duration 60
```

Expected evidence:
- Terminal output includes `rps`, `err_rate`, `p95 latency` (screenshot).

### 6.3 Capacity snapshot script (OK — syntax only)

Command:
```bash
sh -n scripts/capacity_snapshot.sh
```

Result:
- No syntax errors.

Runtime command (requires Prometheus running):
```bash
PROM_URL=http://localhost:9090 scripts/capacity_snapshot.sh
```

Expected evidence:
- Snapshot prints `order_cpu_cores`, `order_mem_bytes`, `order_rps`, `order_5xx_rps`, `order_restarts_10m` (screenshot).

## 7) Requirement: Scaling strategies + resilience (recovery)

### 7.1 Horizontal scaling (runtime — requires Docker daemon)

Commands:
```bash
docker compose up -d --scale order-service=2
docker compose ps
```

Expected evidence:
- Two `order-service` replicas running (screenshot).

### 7.2 Recovery after failure (runtime — requires Docker daemon)

One simple self-healing demo:
```bash
docker compose kill order-service
docker compose ps
docker compose logs --tail=200 order-service
```

Expected evidence:
- Container restarts automatically due to `restart: unless-stopped` and returns to `healthy` (screenshot(s)).

