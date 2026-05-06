# Этап 1 — микросервисы (FastAPI + Nginx + Postgres)

Состав:
- `services/auth` — Auth Service (логин/пароль → JWT)
- `services/user` — User Service (профиль)
- `services/product` — Product Service (товары из PostgreSQL)
- `services/order` — Order Service (создание заказов; ходит по HTTP в Product/User)
- `frontend` — простая HTML/JS страница, раздается Nginx
- `infra/postgres/init.sql` — схема + сиды товаров
- `infra/nginx/nginx.conf` — reverse proxy `/api/*` → сервисы

## Запуск

Требования: Docker + Docker Compose.

Локальный запуск (рекомендуемый порт фронтенда — `8080`, чтобы не занимать привилегированный порт `80`):

```bash
FRONTEND_PORT=8080 docker compose up -d --build
```

Открыть:
- Frontend: `http://localhost:8080`
- Auth: `http://localhost:8001/health`
- User: `http://localhost:8002/health`
- Product: `http://localhost:8003/health`
- Order: `http://localhost:8004/health`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (логин/пароль: `admin` / `admin`)

Если у вас уже запущено, лучше пересобрать после правок:

```bash
FRONTEND_PORT=8080 docker compose up -d --build --force-recreate
```

## Демо-логины

- `admin@example.com` / `admin`
- `user@example.com` / `user`

## Примечания по ошибкам

- Если Nginx падал с `host not found in upstream ...`, это было из-за старта `frontend` раньше сервисов. В `docker-compose.yml` добавлены `healthcheck` и `depends_on: condition: service_healthy`, чтобы Nginx стартовал только после готовности сервисов.
- Если Auth Service падал внутри `passlib`/`bcrypt` с `ValueError: password cannot be longer than 72 bytes`, это известимая несовместимость `passlib==1.7.4` с `bcrypt` v5. В `services/auth/requirements.txt` зафиксирован `bcrypt==4.3.0`.

## Как общаются сервисы

- Браузер → Nginx:
  - `/api/auth/*` → `auth-service`
  - `/api/users/*` → `user-service`
  - `/api/products/*` → `product-service`
  - `/api/orders/*` → `order-service`
- `order-service` → (HTTP):
  - `product-service` для проверки товара и цены
  - `user-service` для проверки пользователя

## Мониторинг (Prometheus + Grafana)

Сервисы отдают метрики по `GET /metrics`:
- `auth-service`: `http://localhost:8001/metrics`
- `user-service`: `http://localhost:8002/metrics`
- `product-service`: `http://localhost:8003/metrics`
- `order-service`: `http://localhost:8004/metrics`

Prometheus конфиг: `infra/prometheus/prometheus.yml`.
Grafana datasource provisioning: `infra/grafana/provisioning/datasources/datasource.yml`.
Alerting rules: `infra/prometheus/alerts.yml` (через Alertmanager).

Если порты `9090` или `3000` заняты локально, можно поднять на других портах:

```bash
PROMETHEUS_PORT=9091 GRAFANA_PORT=3001 ALERTMANAGER_PORT=9094 docker compose up -d prometheus grafana alertmanager
```

Alertmanager UI:
- `http://localhost:9093` (или ваш `ALERTMANAGER_PORT`)

Проверка алертов:
- Во время инцидента (когда `POST /orders` дает 5xx) алерт `OrderServiceHigh5xx` должен стать **Firing** в Alertmanager.

## Этап 6 — Automation + Capacity Planning (Assignment 6)

### Automation (SRE)
- Readiness endpoint: каждый сервис имеет `GET /ready` (DB + зависимости), а Docker healthchecks используют `/ready`.
- Self-healing: для всех контейнеров включен `restart: unless-stopped`.
- Terraform VM bootstrap: в `main.tf` добавлен `user_data` для установки Docker + Compose (`infra/cloud-init/user_data.sh`).
- Config validation (pre-deploy): проверка `.env` перед деплоем:

```bash
python scripts/validate_env.py
```

- Log troubleshooting: быстрый поиск паттернов в логах:

```bash
scripts/inspect_logs.sh order-service
```

### Capacity planning
Для CPU/Memory метрик включите профиль `capacity` (cAdvisor + postgres-exporter):

```bash
FRONTEND_PORT=8080 docker compose --profile capacity up -d --build
```

Нагрузочное тестирование (создание заказов, concurrency/duration настраиваются):

```bash
python scripts/load_test_orders.py --base-url http://localhost:8080 --concurrency 20 --duration 60
```

Снимок метрик для отчета (берется из Prometheus instant query):

```bash
PROM_URL=http://localhost:9090 scripts/capacity_snapshot.sh
```

Простейшая горизонтальная масштабируемость (Docker Compose):

```bash
docker compose up -d --scale order-service=2
```

## Assignment 6 — Report (README)

### 1. Title
Automation and Capacity Planning in a Containerized Microservices System Following Incident Response and Infrastructure Provisioning

### 2. Objectives
The objective of this assignment is to extend the previously developed microservices-based system by incorporating automation mechanisms and performing capacity planning analysis in alignment with Site Reliability Engineering (SRE) principles.

The assignment builds upon:
1. Assignment 4: Incident Response and Postmortem Analysis
2. Assignment 5: Infrastructure as Code using Terraform

The specific goals are:
1. To implement automation workflows that improve system reliability and operational efficiency
2. To introduce monitoring-based alerting mechanisms
3. To perform capacity analysis based on system load and metrics
4. To propose scaling strategies for handling increased demand
5. To enhance system resilience through proactive engineering practices

### 3. System Context
The system under consideration is a Dockerized microservices architecture consisting of:
1. Frontend (Nginx-based)
2. Backend services:
   - Authentication Service
   - Product Service
   - Order Service
3. PostgreSQL database
4. Monitoring stack:
   - Prometheus
   - Grafana
5. Infrastructure provisioned using Terraform

Following the incident identified in Assignment 4 (Order Service failure due to misconfiguration), the system requires improved automation and scalability mechanisms.

### 4. Automation in SRE

#### 4.1 Objective
To reduce manual intervention and improve system reliability by automating deployment, monitoring, and recovery processes.

#### 4.2 Implemented Automation Mechanisms

1. Automated Deployment
   1. Use of Docker Compose for consistent multi-container deployment
   2. Integration with Terraform-provisioned infrastructure
   3. Standardized environment configuration via `.env` files

2. Health Checks and Self-Healing  
Each microservice includes:
1. HTTP health endpoints (e.g., `/health`)
2. Docker health checks to verify service availability (uses `/ready`)
3. Automatic container restart policies: `restart: unless-stopped`

3. Monitoring-Based Alerting
1. Prometheus collects system and service metrics
2. Alert conditions include:
   - High CPU usage
   - Service downtime
   - Increased error rates
3. Alerts are configured using Prometheus alert rules (`infra/prometheus/alerts.yml`) and delivered via Alertmanager

4. Log-Based Troubleshooting Automation
1. Centralized logging via container logs
2. Automated log inspection using predefined patterns:
   - Database connection failures
   - Service restart loops
3. Enables faster root cause identification (helper script: `scripts/inspect_logs.sh`)

5. Configuration Validation
To prevent incidents similar to Assignment 4:
1. Validation of environment variables before deployment
2. Use of template-based configuration files (`.env.example`)
3. Pre-deployment checks to ensure correctness of:
   - Database connection strings
   - Service endpoints

### 5. Capacity Planning

#### 5.1 Objective
To analyze system resource usage and determine strategies for handling increased load while maintaining performance and reliability.

#### 5.2 Metrics Collection
The following metrics are collected via Prometheus:
1. CPU usage
2. Memory utilization
3. Request rate (RPS)
4. Error rate
5. Container restart frequency

#### 5.3 Load Simulation
System load is simulated using:
1. Concurrent user requests
2. Repeated API calls to backend services
3. CPU stress testing

This allows observation of system behavior under stress conditions.

#### 5.4 Observations
Under increased load:
1. CPU usage rises significantly in the Order Service
2. Response time increases
3. Error rates may increase if resources are insufficient
4. Database becomes a potential bottleneck

#### 5.5 Capacity Analysis
The system capacity is evaluated based on:
1. Maximum sustainable request rate
2. Resource consumption per service
3. Failure thresholds

The Order Service is identified as the most resource-intensive component.

#### 5.6 Scaling Strategies

1. Horizontal Scaling
   1. Deploy multiple instances of services (especially Order Service)
   2. Use load balancing to distribute requests

2. Vertical Scaling
   1. Increase CPU and memory allocation for containers
   2. Upgrade VM resources via Terraform

3. Database Optimization
   1. Connection pooling
   2. Query optimization
   3. Resource allocation tuning

#### 5.7 Auto-Scaling Considerations
Although not fully implemented, the following strategies are proposed:
1. Metric-based scaling using CPU thresholds
2. Integration with orchestration platforms (e.g., Kubernetes)
3. Automated scaling policies

### 6. Improvements Based on Previous Assignments
Following Assignment 4 (Incident) and Assignment 5 (IaC), the system has been improved by:
1. Introducing automated configuration validation
2. Implementing monitoring and alerting mechanisms
3. Enhancing deployment consistency through Terraform
4. Reducing recovery time via automation
5. Increasing system resilience through proactive planning

### 7. Deliverables
The submission includes:
1. Updated Source Code
   - Services with health checks and improved configuration
2. Docker Configuration
   - Enhanced `docker-compose.yml` with restart policies
3. Monitoring Configuration
   - Prometheus alert rules (if implemented)
4. Terraform Configuration
   - Updated infrastructure definitions (if scaling applied)
5. Documentation
   - Description of automation mechanisms
   - Capacity planning analysis
6. Supporting Evidence
   - Screenshots of:
     - Grafana dashboards
     - System under load
     - Service recovery after failure

### 7.1 Supporting Evidence (how to produce)

Required screenshots folder: `report/screenshots/`

1) Start the stack with capacity metrics (cAdvisor + postgres-exporter):

```bash
FRONTEND_PORT=8080 docker compose --profile capacity up -d --build
```

2) Verify targets are UP (Prometheus and Grafana):
- Prometheus: `http://localhost:9090/targets`
- Grafana: `http://localhost:3000` (admin/admin)

3) Run load test and save the terminal output (copy into your report as evidence):

```bash
python scripts/load_test_orders.py --base-url http://localhost:8080 --concurrency 20 --duration 60
```

4) Take screenshots (minimum for Assignment 6):
- `report/screenshots/grafana-under-load.png` (Grafana dashboard panels showing CPU/Memory/RPS/Error rate under load)
- `report/screenshots/recovery-after-failure.png` (proof of self-healing after a failure; e.g., Grafana alert fired + container restarted)

Optional screenshots (recommended):
- `report/screenshots/prometheus-alerts.png` (Prometheus “Alerts” page)
- `report/screenshots/docker-ps-under-load.png` (terminal: `docker compose ps` while load test runs)

Self-healing demonstration (for the recovery screenshot):

```bash
docker compose kill -s SIGKILL order-service
docker compose ps
```

You should see `order-service` come back due to `restart: unless-stopped` and/or see restart-related alerting (when `capacity` profile is enabled).

### 7.2 Capacity Analysis (fill with your measured results)

After running the load test, fill in (paste your real numbers):
- Max sustainable throughput (RPS): `<value>`
- Error rate (5xx): `<value>`
- Latency p95 (s): `<value>`
- Order Service peak CPU (cores): `<value>`
- Order Service peak memory (MB): `<value>`
- Primary bottleneck observed: `<order-service | postgres | network | other>`
- Scaling strategy chosen: `<horizontal | vertical | both>` and why

### 8. Evaluation Criteria
The assignment is evaluated based on:
1. Effectiveness of automation implementation
2. Quality of monitoring and alerting mechanisms
3. Depth of capacity planning analysis
4. Integration with previous assignments
5. Clarity of documentation and explanation
6. Demonstration of system scalability and resilience

## Этап 4 — Симуляция инцидента (Assignment 4)

Поломка (ломаем зависимость Order Service от Product Service — сервис остается живым, но `POST /orders` начнет отдавать 5xx):

```bash
docker compose -f docker-compose.yml -f docker-compose.incident.yml up -d --build order-service
```

Примечание: если у вас установлен `docker-compose` (v1), используйте:

```bash
docker-compose -f docker-compose.yml -f docker-compose.incident.yml up -d --build order-service
```

Генерация трафика (создать заказ, чтобы появились 500-е):
1) Зайдите на `http://localhost:8080`, залогиньтесь customer-пользователем.
2) Нажмите **Create Order** несколько раз.

Детекция:
- Grafana: `http://localhost:3000` (admin/admin), dashboard **SRE / SRE Assignment**
  - график **Order Service 5xx** должен вырасти
  - **Orders created (2xx)** упасть к нулю

Реагирование:
1) Логи: `docker compose logs --tail=200 order-service`
2) Исправить конфиг: вернуть нормальный `DATABASE_URL`:

```bash
docker compose up -d --build order-service
```

Должно стать `healthy`, а 5xx в Grafana уйдут вниз.

## Этап 2 — Terraform (Assignment 5)

В корне репозитория добавлены Terraform-файлы для AWS EC2: `main.tf`, `variables.tf`, `outputs.tf`.

Что создается:
- 1 VM (EC2) в дефолтной VPC/подсети
- Security Group с открытыми портами `22`, `80`, `3000`, `9090`

Запуск:

```bash
terraform init
terraform plan -var="ssh_public_key_path=$HOME/.ssh/id_ed25519.pub" # или id_rsa.pub
terraform apply -var="ssh_public_key_path=$HOME/.ssh/id_ed25519.pub" # или id_rsa.pub
```

После `terraform apply` в output появится `public_ip` — IP адрес сервера.

Дальше зайдите в браузере:
- Frontend: `http://<public_ip>/`
- Grafana: `http://<public_ip>:3000`
- Prometheus: `http://<public_ip>:9090`

### Полный набор команд (Terraform → деплой на EC2)

Ниже — команды, которые использовались, чтобы:
1) создать VM в AWS через Terraform,
2) подключиться по SSH,
3) задеплоить проект через Docker Compose,
4) открыть сайт по `public_ip`.

#### 1) Terraform (на вашем компьютере)

Перейдите в папку проекта:

```bash
cd /path/to/SRE_assignment_4_5
```

Инициализация:

```bash
terraform init
```

План (проверка изменений перед применением):

```bash
terraform plan -var="ssh_public_key_path=$HOME/.ssh/id_ed25519.pub"
```

Применение (создание инфраструктуры):

```bash
terraform apply -var="ssh_public_key_path=$HOME/.ssh/id_ed25519.pub"
```

Получить IP созданной VM:

```bash
terraform output -raw public_ip
```

#### 2) Подключение к VM по SSH (на вашем компьютере)

Подключение (подставьте IP из `terraform output -raw public_ip`):

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<public_ip>
```

#### 3) Копирование проекта на VM (если кода на VM ещё нет)

Скопировать папку проекта на VM:

```bash
scp -i ~/.ssh/id_ed25519 -r "/path/to/SRE_assignment_4_5" ubuntu@<public_ip>:~/
```

#### 4) Установка Docker и запуск Compose (уже на VM, Ubuntu 22.04)

Проверить, что порт `80` свободен (если занят — фронтенд не сможет слушать `80`):

```bash
sudo ss -lntp | grep ':80' || echo "port 80 free"
```

Установить Docker и Docker Compose:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl enable --now docker
```

Запустить проект (в папке проекта):

```bash
cd ~/SRE_assignment_4_5
sudo docker-compose up -d --build
```

Проверка на самой VM, что Nginx отвечает на `80`:

```bash
curl -I http://localhost/
```

#### 5) Открыть сервисы в браузере (с вашего компьютера)

- Frontend: `http://<public_ip>/`
- Grafana: `http://<public_ip>:3000` (логин/пароль: `admin` / `admin`)
- Prometheus: `http://<public_ip>:9090`

### Частые ошибки

- Не вводите команды с угловыми скобками: `ssh ubuntu@<public_ip>` — это пример. Нужно без `< >`, например `ssh ubuntu@34.227.225.202`.
- `apt-get` работает на Ubuntu (EC2). На macOS команды `apt-get ...` не существует.
