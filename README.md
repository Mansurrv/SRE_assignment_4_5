# Endterm — Comprehensive SRE Implementation (Microservices)

This repository contains a distributed microservices system (6+ services) with:
- **Docker Compose** (local) + **Docker Swarm** stack (`swarm/`)
- **Kubernetes (kustomize + HPA)** manifests (`k8s/`)
- **Terraform (AWS EC2)** provisioning (`main.tf`, `variables.tf`, `outputs.tf`)
- **Ansible** automation playbooks (`ansible/`)
- **Observability**: Prometheus + Grafana + Alertmanager (`infra/`)
- **Incident simulation** + **postmortem** (`docker-compose.incident.yml`, `report/POSTMORTEM.md`)
- **SLI/SLO** definition (`report/SLI_SLO.md`)

## Services (6+)

- `services/auth` — registration/login, issues JWT
- `services/user` — user profile API
- `services/product` — product catalog
- `services/order` — order creation/listing; calls Product/User/Payment/Notification
- `services/payment` — payment simulation + DB persistence
- `services/notification` — notification simulation

Supporting components:
- Frontend + API gateway: Nginx (`frontend/`, `infra/nginx/nginx.conf`)
- Database: PostgreSQL
- Monitoring: Prometheus + Grafana + Alertmanager

## Run (Docker Compose)

```bash
cp .env.example .env
docker compose up -d --build
```

Open:
- UI: `http://localhost:8080`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (admin/admin)
- Alertmanager: `http://localhost:9093`

Health:
- Auth: `http://localhost:8001/health`
- User: `http://localhost:8002/health`
- Product: `http://localhost:8003/health`
- Order: `http://localhost:8004/health`
- Payment: `http://localhost:8005/health`
- Notification: `http://localhost:8006/health`

## Monitoring & Alerts

- Prometheus scrape config: `infra/prometheus/prometheus.yml`
- Alert rules: `infra/prometheus/alerts.yml`
- Grafana provisioning + dashboard: `infra/grafana/`

Each service exposes:
- `GET /metrics`
- `GET /health` (liveness)
- `GET /ready` (readiness)

Optional capacity targets:
- `cadvisor` and `postgres-exporter` appear as Prometheus targets only when started:
```bash
docker compose --profile capacity up -d --build
```

If `cadvisor` fails with `Bind for 0.0.0.0:8081 failed: port is already allocated`, change the host port:
- Set `CADVISOR_PORT=8082` in `.env`, then re-run the command above.

## Incident Simulation (Assignment 4)

Simulated incident: break `order-service` dependency URL to generate 5xx.

```bash
docker compose -f docker-compose.yml -f docker-compose.incident.yml up -d --build
```

Recovery (revert incident override + restart):
```bash
docker compose up -d --build order-service
```

Postmortem template + example: `report/POSTMORTEM.md`.

## Terraform (Assignment 5)

AWS EC2 provisioning:
- `main.tf`, `variables.tf`, `outputs.tf`
- cloud-init bootstrap: `infra/cloud-init/user_data.sh`

## Ansible Automation (Assignment 6 + Endterm)

Docs: `ansible/README.md`
- Docker Compose deploy: `ansible/playbooks/docker-compose.yml`
- Docker Swarm deploy: `ansible/playbooks/swarm.yml`
- Kubernetes (k3s) install: `ansible/playbooks/k3s.yml`
- Kubernetes deploy: `ansible/playbooks/deploy-k8s.yml`

## Docker Swarm

Docs: `swarm/README.md`  
Stack: `swarm/docker-stack.yml`

## Kubernetes

Docs: `k8s/README.md`  
Manifests: `k8s/` (apply with `kubectl apply -k k8s`)  
Autoscaling: `k8s/hpa.yaml` (requires metrics-server)

---

# What to include in the Endterm Report (PDF)

Your submission requires **ONLY PDF + Git link**. This repo already contains a report you can export:
- Main report: `report/ENDTERM_REPORT.md`
- SLI/SLO: `report/SLI_SLO.md`
- Postmortem: `report/POSTMORTEM.md`
- PDF export notes: `report/EXPORT_TO_PDF.md`

Use the following checklist/structure (copy into your PDF if you write from scratch):

## 1) Title
- Exact title of the project (as in assignment)
- Student name, group, date, timezone

## 2) Abstract
- 8–12 lines describing: microservices, multi-orchestration (Swarm + K8s), monitoring, IaC, automation, incident + postmortem, capacity planning

## 3) Objectives
- List the 9 objectives from the assignment (6+ services, Swarm, K8s, Terraform, Ansible, SLIs/SLOs, monitoring+alerting, incident, postmortem, automation+capacity planning)

## 4) System Overview
- Short description of the application/business flow
- **List all 6+ microservices** and what each one does
- Supporting components (Nginx frontend/gateway, Postgres, Prometheus, Grafana, Alertmanager)
- Architecture diagram (optional) + component communication (who calls whom)

## 5) Multi-Orchestration

### 5.1 Docker Swarm
- Why Swarm is used (simple clustering/replicas/fast deploy)
- Commands used:
  - `docker swarm init`
  - `docker stack deploy -c swarm/docker-stack.yml app`
- Evidence screenshots (see “Evidence” section)

### 5.2 Kubernetes
- Why K8s is used (declarative, self-healing, auto-scaling)
- Resources used: Deployments, Services, ConfigMaps, HPA
- Apply command: `kubectl apply -k k8s`

## 6) Infrastructure Provisioning (Terraform)
- Provider + resources created (EC2, SG, key pair, networking)
- How you ran it: `terraform init/plan/apply`
- Show outputs (public_ip, instance_id)

## 7) Configuration Management (Ansible)
- What is automated (Docker/Compose install, Swarm init/join + deploy, k3s install + deploy)
- Inventory explanation (hosts/groups)
- Commands you ran (ansible-playbook)

## 8) SLIs & SLOs
Include (and define how you measure them):
- Availability / success rate
- Latency (p95)
- Error rate (5xx %)
- Request rate (RPS)

Targets (as required):
- Availability **≥ 99%**
- Latency **≤ 200ms** (choose critical endpoint, e.g., `POST /orders`)
- Error rate **≤ 1%**

Reference: `report/SLI_SLO.md`.

## 9) Monitoring & Observability
- Prometheus scrape targets (all services UP)
- Grafana dashboard(s): what panels you used (RPS, error rate, latency)
- Alert rules (at least: service down, high 5xx; ideally CPU/memory/restarts if collected)

## 10) Incident Simulation + Response
Must include:
- Incident scenario (what broke and why)
- Impact (what users could not do)
- Detection (alert/dashboards)
- Investigation (logs/metrics you checked)
- Mitigation & recovery (what you changed, restart/rollback)
- Confirmation (metrics back to normal)

Reference: `report/POSTMORTEM.md`.

## 11) Postmortem
- Timeline (with **exact times + timezone**)
- Root cause
- Contributing factors
- Lessons learned
- Action items table (owner, priority, due date)

## 12) Automation & Capacity Planning
Automation:
- health checks + restart policies
- pre-deploy config validation (`scripts/validate_env.py`)
- automated deployment (Compose/Ansible)

Capacity planning:
- load test command you ran (`scripts/load_test_orders.py`)
- what became bottleneck (order/payment/db)
- scaling strategy (horizontal replicas, vertical resources, DB tuning)
- screenshots/metrics proving your conclusions

## 13) Results & Conclusion
- Bullet list summarizing what you achieved + why it meets the objectives

## 14) Deliverables (Git link)
Include link and list the repo artifacts:
- `services/` (6+ services)
- `docker-compose.yml`
- `swarm/docker-stack.yml`
- `k8s/`
- `main.tf`, `variables.tf`, `outputs.tf`, `infra/cloud-init/user_data.sh`
- `ansible/`
- `infra/` (prom/grafana/alertmanager configs)
- `report/*`

---

# Evidence (Screenshots) — recommended set

Save screenshots into `report/screenshots/` and reference them in the PDF:
- Terraform: `terraform apply` output (public IP + instance ID)
- Docker Compose: `docker compose ps` showing **healthy** containers
- UI: browser screenshot of the working frontend
- Prometheus: Status → Targets (all service targets **UP**)
- Grafana: dashboard in normal state
- Alertmanager: alert firing during incident
- Incident: Grafana panel with 5xx spike + logs (`docker compose logs order-service`)
- After fix: Grafana panel showing recovery
- Swarm: `docker stack services app` output
- Kubernetes: `kubectl get pods -n sre-app` + `kubectl get hpa -n sre-app` (if HPA enabled)
