# Assignment 6 — Automation in Site Reliability Engineering and Capacity Planning

Дата: **заполните**  
Автор: **заполните**  
Часовой пояс: **например Asia/Almaty**  

## 1. Title
Automation and Capacity Planning in a Containerized Microservices System Following Incident Response and Infrastructure Provisioning

## 2. Objectives
Цель — расширить микросервисную систему из Assignment 4 (incident response) и Assignment 5 (Terraform IaC), добавив автоматизацию (health/self-healing/валидации/алерты) и выполнить capacity planning анализ на основе метрик под нагрузкой.

Конкретные цели:
1) Implement automation workflows (reliability + ops efficiency)  
2) Introduce monitoring-based alerting  
3) Perform capacity analysis under load  
4) Propose scaling strategies for increased demand  
5) Improve resilience with proactive SRE practices  

## 3. System Context
Система — Dockerized microservices architecture:
1) Frontend: Nginx (`frontend`)  
2) Backend services:
   - Authentication Service (`auth-service`)
   - User Service (`user-service`)
   - Product Service (`product-service`)
   - Order Service (`order-service`)
3) PostgreSQL (`postgres`)  
4) Monitoring stack:
   - Prometheus (`prometheus`)
   - Grafana (`grafana`)
   - Alertmanager (`alertmanager`)
5) Infrastructure provisioned using Terraform (AWS EC2)  

Контекст инцидента (Assignment 4): `order-service` мог возвращать 5xx из-за misconfiguration, поэтому добавлены readiness/валидации/алерты и сценарии масштабирования.

## 3.1 AWS/Terraform Deployment (Commands Used)
Ниже приведён реальный end-to-end флоу деплоя на **AWS EC2** через Terraform (Assignment 5) + запуск системы (Assignment 6).

### 3.1.1 Terraform apply (локально)
```bash
terraform init
terraform validate
terraform plan
terraform apply -auto-approve
```

Получить IP/ID инстанса:
```bash
terraform output public_ip
terraform output instance_id
```

Скриншоты:
- `report/screenshots/a6-terraform-apply.png` (вывод `terraform apply` с outputs)

### 3.1.2 Подключение по SSH (локально)
```bash
ssh -i <PATH_TO_PRIVATE_KEY> ubuntu@<PUBLIC_IP>
```

Скриншоты:
- `report/screenshots/a6-ssh-to-vm.png` (успешный SSH login)

### 3.1.3 Bootstrap на VM (через Terraform user_data)
VM автоматически устанавливает Docker + Compose через `user_data`:
- `main.tf` → `user_data = file("${path.module}/infra/cloud-init/user_data.sh")`
- `infra/cloud-init/user_data.sh`

Проверка на VM:
```bash
docker --version
docker compose version
```

Скриншоты:
- `report/screenshots/a6-docker-version.png` (docker/compose версии на VM)

### 3.1.4 Загрузка проекта на VM и запуск
Вариант A (через `scp`, без git):
```bash
scp -i <PATH_TO_PRIVATE_KEY> -r . ubuntu@<PUBLIC_IP>:~/sre-assignment
ssh -i <PATH_TO_PRIVATE_KEY> ubuntu@<PUBLIC_IP>
cd ~/sre-assignment
```

Запуск (capacity профиль для cAdvisor + postgres-exporter):
```bash
FRONTEND_PORT=80 PROMETHEUS_PORT=9090 GRAFANA_PORT=3000 ALERTMANAGER_PORT=9093 \
docker compose --profile capacity up -d --build
docker compose ps
```

Скриншоты:
- `report/screenshots/a6-compose-ps-on-vm.png` (`docker compose ps` на VM)

### 3.1.5 Проверка доступности UI и monitoring (из браузера)
Открыть в браузере (замените `<PUBLIC_IP>`):
- Frontend: `http://<PUBLIC_IP>/`
- Grafana: `http://<PUBLIC_IP>:3000` (admin/admin)
- Prometheus: `http://<PUBLIC_IP>:9090`
- Alertmanager: `http://<PUBLIC_IP>:9093`

Скриншоты:
- `report/screenshots/a6-grafana-ui.png`
- `report/screenshots/a6-prometheus-ui.png`
- `report/screenshots/a6-alertmanager-ui.png`

## 4. Automation in SRE

### 4.1 Objective
Снизить ручные операции и ускорить detect→recover, автоматизировав деплой, проверки готовности, мониторинг/алерты и быстрый troubleshooting.

### 4.2 Implemented Automation Mechanisms

#### 4.2.1 Automated Deployment
Реализация:
- Docker Compose для консистентного multi-container deployment: `docker-compose.yml`
- Terraform provisioning + bootstrap: `main.tf` использует `user_data` из `infra/cloud-init/user_data.sh` (установка Docker + Compose на VM)
- Стандартизированные конфиги через `.env` (пример: `.env.example`)

Доказательства (скриншоты):
- `report/screenshots/a6-terraform-apply.png` (Terraform apply + outputs)
- `report/screenshots/a6-docker-version.png` (Docker/Compose versions on VM)
- `report/screenshots/a6-compose-ps-on-vm.png` (`docker compose ps` on VM)

#### 4.2.2 Health Checks and Self-Healing
Реализация:
- Каждый сервис имеет HTTP endpoints:
  - `GET /health` (liveness)
  - `GET /ready` (readiness: БД + зависимости)
- Docker healthchecks проверяют готовность через `/ready` (и готовность monitoring компонентов).
- Restart policy включен: `restart: unless-stopped` (self-healing через automatic restart).

Доказательства (скриншоты):
- `report/screenshots/a6-ready-endpoints.png` (curl `/ready` на VM для сервисов)
- `report/screenshots/a6-compose-healthy.png` (`docker compose ps` показывает `healthy` на VM)

#### 4.2.3 Monitoring-Based Alerting
Реализация:
- Prometheus scrape + rules:
  - config: `infra/prometheus/prometheus.yml`
  - alert rules: `infra/prometheus/alerts.yml`
- Alert conditions (примерно):
  - Service downtime: `*ServiceDown` / `OrderServiceDown`
  - Increased error rates: `ServiceHigh5xx`, `OrderServiceHigh5xx`
  - High CPU/Memory/Restarts (requires cAdvisor profile): `AnyServiceHighCPU`, `AnyServiceHighMemory`, `AnyServiceRestartLoop`, а также order-specific capacity alerts
- Alert delivery: Alertmanager (`infra/alertmanager/alertmanager.yml`) и UI.

Доказательства (скриншоты):
- `report/screenshots/a6-prometheus-targets.png` (Prometheus → Targets: UP)
- `report/screenshots/a6-alertmanager-ui.png` (Alertmanager UI: alerts visible / firing)

#### 4.2.4 Log-Based Troubleshooting Automation
Реализация:
- Centralized logging через `docker compose logs` (container logs).
- Автоматизированная инспекция паттернов: `scripts/inspect_logs.sh <service>` (ошибки БД, restart loops, timeouts, etc.).

Доказательства (скриншоты):
- `report/screenshots/a6-inspect-logs.png` (пример запуска `scripts/inspect_logs.sh order-service`)

#### 4.2.5 Configuration Validation
Реализация:
- Pre-deploy env validation: `scripts/validate_env.py` (проверка обязательных env vars + sanity checks URL/DB URL).
- Template-based configuration: `.env.example`.
- Цель: предотвратить misconfiguration как в Assignment 4 (например, неверные `*_SERVICE_URL`).

Доказательства (скриншоты):
- `report/screenshots/a6-validate-env.png` (успешный запуск `python3 scripts/validate_env.py` или пример ошибки при неверном env)

## 5. Capacity Planning

### 5.1 Objective
Определить поведение системы под нагрузкой (CPU/memory/RPS/errors/restarts), оценить пределы и предложить стратегии масштабирования.

### 5.2 Metrics Collection
Метрики через Prometheus:
1) CPU usage (cAdvisor)  
2) Memory utilization (cAdvisor)  
3) Request rate (RPS) (`http_requests_total`)  
4) Error rate (5xx rate)  
5) Container restart frequency (cAdvisor `container_start_time_seconds` changes)  

Примечание: для container-level CPU/memory/restarts включить профиль `capacity` (cAdvisor + postgres-exporter):
- `docker compose --profile capacity up -d --build`

### 5.3 Load Simulation
Реализация:
- Concurrent user requests + repeated API calls: `scripts/load_test_orders.py`
- (Опционально) CPU stress testing: через увеличение concurrency/duration или внешний stress-tool (если разрешено преподавателем).

Команда (пример):
```bash
python3 scripts/load_test_orders.py --base-url http://<PUBLIC_IP> --concurrency 20 --duration 60
```

Доказательства (скриншоты):
- `report/screenshots/a6-load-test.png` (вывод load test в терминале)

### 5.4 Observations
Наблюдения под нагрузкой (заполнить фактическими данными):
1) CPU usage увеличивается сильнее всего в `order-service` (обычно, из-за межсервисных запросов + записи в DB).  
2) Response time растет с ростом concurrency.  
3) Error rates (5xx) могут расти при нехватке ресурсов или timeouts.  
4) PostgreSQL может стать bottleneck (I/O, connections).  

Скриншоты:
- `report/screenshots/a6-grafana-under-load.png` (Grafana dashboard under load)

### 5.5 Capacity Analysis
Итоговые числа (заполнить):
- Max sustainable request rate (RPS): **<value>**
- p95 latency (seconds): **<value>**
- Error rate (5xx): **<value>**
- Failure threshold reached at: **<concurrency/RPS/CPU/mem>**
- Main bottleneck: **<order-service / postgres / network>**

Быстрый снимок ключевых метрик (instant queries):
```bash
PROM_URL=http://<PUBLIC_IP>:9090 scripts/capacity_snapshot.sh
```

Скриншоты:
- `report/screenshots/a6-capacity-snapshot.png` (вывод `scripts/capacity_snapshot.sh`)

### 5.6 Scaling Strategies
1) Horizontal Scaling:
   - Scale replicas for `order-service`: `docker compose up -d --scale order-service=2`
   - Load balancing: Nginx + Docker DNS (при наличии нескольких A records)
2) Vertical Scaling:
   - Увеличить CPU/RAM контейнеров / VM, например изменить `var.instance_type` в Terraform.
3) Database Optimization:
   - Connection pooling (PgBouncer) (optional)
   - Query optimization / indexes (если выявлено)
   - Resource tuning for Postgres (shared_buffers, max_connections, etc.) (optional)

Скриншоты:
- `report/screenshots/a6-scale-order-service.png` (`--scale order-service=2` + `docker compose ps`)

### 5.7 Auto-Scaling Considerations
Хотя auto-scaling не реализован полностью в Docker Compose, предлагается:
1) Metric-based scaling (CPU threshold)  
2) Migration path to Kubernetes (HPA/VPA)  
3) Automated scaling policies + SLO-based alerts  

## 6. Improvements Based on Previous Assignments
После Assignment 4 (incident) и Assignment 5 (IaC) добавлены улучшения:
1) Automated config validation (`scripts/validate_env.py`)  
2) Monitoring + alerting (Prometheus rules + Alertmanager)  
3) Consistent deployment via Terraform + Compose (включая VM bootstrap через `user_data`)  
4) Reduced recovery time via self-healing + readiness gating  
5) Resilience improvements via capacity planning + scaling strategy  

## 7. Deliverables (Checklist)
1) Updated source code:
   - Services: `/health`, `/ready`, `/metrics`
2) Docker configuration:
   - `docker-compose.yml` with restart policies + healthchecks
3) Monitoring configuration:
   - `infra/prometheus/prometheus.yml`
   - `infra/prometheus/alerts.yml`
   - `infra/alertmanager/alertmanager.yml`
4) Terraform configuration:
   - `main.tf` updated with `user_data` bootstrap
   - `infra/cloud-init/user_data.sh`
5) Documentation:
   - This file: `report/ASSIGNMENT_6_REPORT.md`
6) Supporting evidence screenshots:
   - Grafana dashboards
   - System under load
   - Service recovery after failure

## 8. Evaluation Criteria (How this report maps)
1) Automation effectiveness: Sections 4.2.1–4.2.5 + screenshots  
2) Alerting quality: Section 4.2.3 + Prometheus/Alertmanager screenshots  
3) Capacity planning depth: Section 5 (load test + metrics + filled values)  
4) Integration with previous assignments: Section 6  
5) Clarity: short implementation mapping + checklist  
6) Scalability/resilience: Section 5.6 + evidence of recovery + scaling screenshot  

## PDF export
Откройте `report/ASSIGNMENT_6_REPORT.md` и сделайте **Print → Save as PDF**.
