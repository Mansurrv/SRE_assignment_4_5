# End Term Project — Comprehensive SRE Implementation

Title: **End-to-End Implementation of SRE Practices in a Multi-Orchestrated Microservices Infrastructure Using Docker Swarm, Kubernetes, Terraform, and Ansible**

Date: **May 16, 2026**  
Timezone: **Asia/Almaty**

## 1) Abstract

This project demonstrates a full SRE lifecycle on a distributed microservices system: containerization, multi-orchestration (Docker Swarm + Kubernetes), monitoring and alerting (Prometheus + Grafana + Alertmanager), infrastructure provisioning (Terraform), configuration management and deployment automation (Ansible), incident simulation with postmortem, and capacity planning concepts.

## 2) Objectives

1. Deploy a distributed microservices architecture (**6+ services**)
2. Implement multi-orchestration using **Docker Swarm** and **Kubernetes (k3s)**
3. Provision infrastructure using **Terraform**
4. Automate configuration and deployments using **Ansible**
5. Define **SLIs and SLOs**
6. Implement monitoring and alerting systems
7. Simulate and resolve a production incident
8. Conduct postmortem analysis
9. Provide automation and capacity planning strategies

## 3) System Overview

### Microservices (6+)

1. `auth-service` — registration/login, JWT issuance
2. `user-service` — user profile retrieval/update
3. `product-service` — product catalog
4. `order-service` — order creation/listing; calls Product/User/Payment/Notification
5. `payment-service` — payment simulation + DB persistence
6. `notification-service` — notification simulation (best-effort)

Supporting components:
- Frontend: Nginx static UI + reverse proxy
- Database: PostgreSQL
- Monitoring: Prometheus + Grafana
- Alerting: Alertmanager

## 4) Architecture

User → Frontend (Nginx) → `/api/...` → microservices → PostgreSQL  
Observability: services → Prometheus → Grafana, alerts → Alertmanager

## 5) Multi-orchestration

### 5.1 Docker Swarm

- Stack file: `swarm/docker-stack.yml`
- Deploy:
  - `docker swarm init`
  - `docker stack deploy -c swarm/docker-stack.yml app`

### 5.2 Kubernetes

- Manifests: `k8s/` (kustomize)
- Deploy:
  - `kubectl apply -k k8s`
- Autoscaling:
  - `k8s/hpa.yaml` (requires metrics-server)

## 6) Infrastructure provisioning (Terraform)

- AWS EC2 provisioning: `main.tf`, `variables.tf`, `outputs.tf`
- VM bootstrap via cloud-init: `infra/cloud-init/user_data.sh`

## 7) Configuration management & automation (Ansible)

Playbooks:
- `ansible/playbooks/docker-compose.yml` — install Docker/Compose and deploy
- `ansible/playbooks/swarm.yml` — Swarm init/join + stack deploy
- `ansible/playbooks/k3s.yml` — install k3s server/agents
- `ansible/playbooks/deploy-k8s.yml` — apply Kubernetes manifests

## 8) SLIs & SLOs

Documented in: `report/SLI_SLO.md`.

## 9) Monitoring & alerting

- Prometheus config: `infra/prometheus/prometheus.yml`
- Alert rules: `infra/prometheus/alerts.yml`
- Grafana dashboard: `infra/grafana/dashboards/sre-dashboard.json`
- Alertmanager config: `infra/alertmanager/alertmanager.yml`

### 9.1 Verification (Assignment 3)

1) Confirm services expose metrics (`/metrics`) and are running:
```bash
docker compose ps
```

2) Confirm Prometheus is ready:
```bash
curl -fsS http://localhost:9090/-/ready
```

3) Confirm Alertmanager is ready:
```bash
curl -fsS http://localhost:9093/-/ready
```

4) Confirm Prometheus scrapes all services:
- Open Prometheus UI: `http://localhost:9090`
- Go to: **Status → Targets**
- Expected (app services): `auth-service`, `user-service`, `product-service`, `order-service`, `payment-service`, `notification-service` are **UP**
- Note: `cadvisor` and `postgres` targets are **optional** and become UP only when the capacity profile is enabled:
```bash
docker compose --profile capacity up -d
```
- If `cadvisor` port `8081` is already used on the host, set `CADVISOR_PORT=8082` in `.env` and run the command again.

5) Confirm alert rules are loaded:
- Prometheus UI → **Status → Rules**
- Expected: alerts from `infra/prometheus/alerts.yml` are visible (e.g., `OrderServiceHigh5xx`, `ServiceHigh5xx`, `PrometheusTargetMissing`)

6) Confirm Alertmanager UI is reachable:
- Open Alertmanager UI: `http://localhost:9093`

### 9.2 Evidence (screenshots)

Save screenshots into `report/screenshots/` and reference them in the PDF:
- `report/screenshots/compose-ps-healthy.png` — `docker compose ps` output (all healthy)
- `report/screenshots/prometheus-targets-up.png` — Prometheus **Status → Targets** (all service targets UP)
- `report/screenshots/prometheus-rules-loaded.png` — Prometheus **Status → Rules** (alerts loaded)
- `report/screenshots/alertmanager-ready.png` — Alertmanager UI reachable

## 10) Incident simulation

Scenario: `order-service` misconfigured dependency endpoint, causing `POST /orders` failures.

Reproduce:
```bash
docker compose -f docker-compose.yml -f docker-compose.incident.yml up -d --build
```

Postmortem: `report/POSTMORTEM.md`.

### 10.1 Verification steps (generate 5xx + alert)

1) Create a customer user and get a token:
```bash
EMAIL="student_$(date +%s)@example.com"
TOKEN=$(curl -fsS -X POST http://localhost:8001/register -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"pass123\",\"full_name\":\"Student\",\"role\":\"customer\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

2) Trigger the failing endpoint (should return 5xx/502 during the incident):
```bash
curl -i -X POST http://localhost:8004/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$EMAIL\",\"items\":[{\"product_id\":1,\"quantity\":1}]}"
```

3) Confirm alert fires:
- Grafana dashboard: `http://localhost:3000` → error/5xx panels for `order-service`
- Alertmanager UI: `http://localhost:9093` → `OrderServiceHigh5xx` is **Firing/Active**

4) Fix (revert incident override):
```bash
docker compose up -d --build order-service
```

5) Confirm recovery:
- `POST /orders` returns `200`
- Alertmanager returns to “no active alerts” after ~1–2 minutes

## 11) Capacity planning (summary)

Approach:
- Generate load with `scripts/load_test_orders.py`
- Observe CPU/memory/RPS/error rate in Prometheus/Grafana
- Scale horizontally (replicas) for stateless services (`order-service`, `payment-service`)

## 12) Deliverables (Git)

- Microservices source code: `services/*`
- Docker Compose stack: `docker-compose.yml`
- Swarm stack: `swarm/docker-stack.yml`
- Kubernetes manifests: `k8s/`
- Terraform: `main.tf`, `variables.tf`, `outputs.tf`, `infra/cloud-init/user_data.sh`
- Ansible: `ansible/`
- SLOs + incident report: `report/SLI_SLO.md`, `report/POSTMORTEM.md`, `report/ENDTERM_REPORT.md`
