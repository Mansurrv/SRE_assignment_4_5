# Incident Response Simulation and Infrastructure as Code Implementation

Дата: **заполните**  
Автор: **заполните**  
Часовой пояс: **например Asia/Almaty**  

## 1) Title

Design and Deployment of a Containerized Microservices System with Terraform-Based Infrastructure Provisioning and Incident Response Simulation

## 2) Objectives

Цель проекта — объединить практики IaC и SRE: развернуть контейнеризированную микросервисную систему, добавить наблюдаемость (metrics/dashboards/alerts), затем смоделировать инцидент и оформить postmortem.

## 3) System Requirements

### 3.1 Functional Requirements
- Web UI для взаимодействия с системой
- Регистрация/логин и авторизация (RBAC customer/florist)
- Просмотр продуктов и создание заказов
- Межсервисное взаимодействие по HTTP
- Метрики `/metrics` для мониторинга
- Детекция ошибок через dashboards/alerts

### 3.2 Non-Functional Requirements
- Изоляция компонентов через микросервисы
- Воспроизводимость деплоя (Terraform + Docker Compose)
- Наблюдаемость (Prometheus + Grafana)
- Устойчивость (healthchecks, быстрый rollback конфигов)

## 4) Technology Stack

- Backend: Python / FastAPI
- Frontend: HTML/JS, раздача через Nginx
- Database: PostgreSQL
- Containerization: Docker
- Orchestration: Docker Compose
- Monitoring: Prometheus + Grafana
- Alerting: Prometheus rules + Alertmanager
- IaC: Terraform (AWS EC2)

## 5) System Architecture

### 5.1 Components
- Frontend: Nginx (`frontend`)
- Auth Service: `services/auth`
- User Service: `services/user`
- Product Service: `services/product`
- Order Service: `services/order`
- Postgres: `postgres`
- Prometheus: `prometheus`
- Grafana: `grafana`
- Alertmanager: `alertmanager`

### 5.2 Ports (укажите фактические)
- Web UI: `8080`
- Auth/User/Product/Order: `8001/8002/8003/8004`
- Grafana: `3000` (или `3001`, если порт был занят)
- Prometheus: `9090` (или `9091`, если порт был занят)
- Alertmanager: `9093` (или `9094`, если порт был занят)

## 6) Infrastructure as Code (Assignment 5)

### 6.1 Objective
Provision VM + firewall rules using Terraform in a reproducible manner.

### 6.2 Terraform configuration

#### `main.tf`
```hcl
<PASTE main.tf HERE>
```

#### `variables.tf`
```hcl
<PASTE variables.tf HERE>
```

#### `outputs.tf`
```hcl
<PASTE outputs.tf HERE>
```

### 6.3 Evidence (screenshots)
- `report/screenshots/terraform-init.png` (optional)
- `report/screenshots/terraform-apply.png` (mandatory: shows `instance_id` and `public_ip`)

## 7) Containerized Deployment

### 7.1 Dockerfiles + Compose
- Dockerfiles: `services/*/Dockerfile`
- Compose: `docker-compose.yml`

### 7.2 Evidence (screenshots)
- `report/screenshots/docker-ps.png` (mandatory: running containers)
- `report/screenshots/web-ui.png` (mandatory: working UI in browser)

## 8) Monitoring and Observability

### 8.1 Prometheus
- Scrape config: `infra/prometheus/prometheus.yml`
- Alert rules: `infra/prometheus/alerts.yml`

### 8.2 Grafana
- Datasource provisioning: `infra/grafana/provisioning/datasources/datasource.yml`
- Dashboard provisioning: `infra/grafana/provisioning/dashboards/dashboards.yml`
- Dashboard JSON: `infra/grafana/dashboards/sre-dashboard.json`

### 8.3 Evidence (screenshots)
- `report/screenshots/prometheus-targets.png` (mandatory: targets UP)
- `report/screenshots/grafana-dashboard-normal.png` (optional: normal state)

## 9) Alerting

### 9.1 Alertmanager
- Config: `infra/alertmanager/alertmanager.yml`
- UI: `http://localhost:<ALERTMANAGER_PORT>`

### 9.2 Evidence (screenshots)
- `report/screenshots/alertmanager-firing.png` (mandatory: alert firing during incident)

## 10) Incident Response Simulation (Assignment 4)

### 10.1 Objective
Simulate a realistic failure and demonstrate detect → analyze → mitigate → restore.

### 10.2 Incident Scenario
Misconfiguration in Order Service (wrong dependency host/URL), leading to 5xx on `POST /orders`.

### 10.3 Severity
- Severity: **High** (или Critical — по вашему выбору)

### 10.4 Timeline (укажите ваш часовой пояс)
- 07:30 — инцидент начался (ошибка конфигурации `order-service`, `POST /orders` начал отдавать 5xx).
- 07:33 — обнаружено в Grafana (рост `Order Service 5xx`, падение успешных `POST /orders 2xx`).
- 07:45 — исправлено (конфиг откатан, `order-service` перезапущен, 5xx пошли вниз).

### 10.5 Detection (what you saw)
- Grafana dashboard: рост 5xx / падение 2xx по `POST /orders`

### 10.6 Analysis (what you checked)
- Логи контейнера: `docker compose logs --tail=200 order-service`

### 10.7 Mitigation (what you changed)
- Откат конфигурации и перезапуск сервиса: `docker compose up -d --build order-service`

### 10.8 Resolution confirmation
- Снова `200` на `POST /orders`
- Снижение 5xx на графиках

### 10.9 Evidence (screenshots)
- `report/screenshots/grafana-incident.png` (mandatory: 5xx > 0 и 2xx ~ 0)
- `report/screenshots/order-service-logs.png` (mandatory: log error during incident)
- `report/screenshots/grafana-after-fix.png` (optional: 5xx drop after fix)

## 11) Postmortem Analysis

### 11.1 Lessons learned
- Конфиги сервисов должны валидироваться до деплоя (CI/линт).
- Нужно иметь alerts на 5xx и на недоступность targets.
- Для зависимостей нужен readiness endpoint (`/ready`) и fallback/timeout handling.

### 11.2 Action items
| Item | Owner | Priority | Due date |
|---|---|---|---|
| Add config validation for `*_SERVICE_URL` | You | High | <date> |
| Add readiness checks (`/ready`) | You | Medium | <date> |
| Add alert routing to email/slack (optional) | You | Low | <date> |

## 12) Conclusion

Коротко опишите, что было сделано: IaC (Terraform), деплой Docker Compose, observability (Prometheus/Grafana), alerting (Alertmanager), инцидент + response + postmortem.

## 13) Automation and Capacity Planning (Assignment 6)

### 13.1 Automation mechanisms implemented
Система запускается воспроизводимо через `docker-compose.yml` + `.env`, VM поднимается Terraform и автоматически ставит Docker/Compose через `user_data`, сервисы имеют `/health` (liveness) и `/ready` (readiness), контейнеры самовосстанавливаются через `restart: unless-stopped`, а перед деплоем выполняются проверки конфигурации и быстрый анализ логов.

Скриншоты:
- `report/screenshots/compose-up-healthy.png` (containers healthy in `docker compose ps`)
- `report/screenshots/ready-endpoints.png` (curl `/ready` for all services OR browser tab with /health checks)

### 13.2 Monitoring-based alerting
Prometheus собирает метрики сервисов и контейнеров и по правилам в `infra/prometheus/alerts.yml` формирует алерты (downtime/5xx/CPU/memory/restarts), которые видны в Alertmanager.

Скриншоты:
- `report/screenshots/prometheus-targets-up.png` (Prometheus → Status → Targets: all UP)
- `report/screenshots/alertmanager-active.png` (Alertmanager UI with active/firing alerts or ready state)

### 13.3 Load simulation
Нагрузка генерируется скриптом `scripts/load_test_orders.py`, который параллельно создаёт заказы и печатает RPS/latency/error rate.

Скриншоты:
- `report/screenshots/load-test-terminal.png` (terminal output of the load test command)

### 13.4 Capacity analysis (template)
Во время нагрузки метрики CPU/Memory/RPS/5xx/restarts фиксируются в Grafana/Prometheus, после чего делается вывод о предельной пропускной способности и узком месте (обычно `order-service` и/или PostgreSQL).

Данные (заполнить по результатам):
- Max sustainable RPS: **<value>**
- p95 latency under load: **<value>**
- Bottleneck: **<Order Service / DB / network>**

Скриншоты:
- `report/screenshots/grafana-under-load.png` (Grafana dashboard under load)
- `report/screenshots/capacity-snapshot.png` (terminal output of `scripts/capacity_snapshot.sh` OR Prometheus query results)

### 13.5 Scaling strategy (proposal)
Для роста нагрузки предлагается горизонтально масштабировать `order-service` (несколько реплик), вертикально увеличить ресурсы VM через Terraform (instance type), а также оптимизировать БД (пулы соединений/индексы/настройки) при выявлении bottleneck.

Скриншоты:
- `report/screenshots/scale-order-service.png` (output of `docker compose up -d --scale order-service=2` + `docker compose ps`)

### 13.6 Evidence (screenshots)
Минимально для сдачи:
- `report/screenshots/grafana-under-load.png` (mandatory)
- `report/screenshots/recovery-after-failure.png` (mandatory: контейнер восстановился после restart)

Дополнительно (по желанию/если требуется преподавателем):
- `report/screenshots/prometheus-alerts.png`
- `report/screenshots/alertmanager-firing.png`

## PDF export

Откройте `report/REPORT.md` и сделайте **Print → Save as PDF**.
