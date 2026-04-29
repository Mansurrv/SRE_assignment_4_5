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

```bash
docker compose up --build
```

Если у вас уже запущено, лучше пересобрать после правок:

```bash
docker compose up -d --build --force-recreate
```

Открыть:
- Frontend: `http://localhost:8080`
- Auth: `http://localhost:8001/health`
- User: `http://localhost:8002/health`
- Product: `http://localhost:8003/health`
- Order: `http://localhost:8004/health`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (логин/пароль: `admin` / `admin`)

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

## Этап 4 — Симуляция инцидента (Assignment 4)

Поломка (ломаем зависимость Order Service от Product Service — сервис остается живым, но `POST /orders` начнет отдавать 5xx):

```bash
docker compose -f docker-compose.yml -f docker-compose.incident.yml up -d --build order-service
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
terraform apply -var="ssh_public_key_path=$HOME/.ssh/id_rsa.pub"
```

После `terraform apply` в output появится `public_ip` — IP адрес сервера.
