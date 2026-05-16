# Docker Swarm deployment

This repository includes a Swarm stack file for the same microservices system. Swarm does **not** build images from source during `docker stack deploy`, so build/tag the images first.

## 1) Build images (on the Swarm manager)

```bash
docker build -t sre/auth-service:latest services/auth
docker build -t sre/user-service:latest services/user
docker build -t sre/product-service:latest services/product
docker build -t sre/order-service:latest services/order
docker build -t sre/payment-service:latest services/payment
docker build -t sre/notification-service:latest services/notification
```

If you have multiple nodes, push these images to a registry and change the image names in `swarm/docker-stack.yml`.

## 2) Init Swarm and deploy

```bash
docker swarm init
docker stack deploy -c swarm/docker-stack.yml app
```

## 3) Verify

```bash
docker stack services app
docker stack ps app
```

Access:
- UI: `http://<manager-ip>:8080`
- Prometheus: `http://<manager-ip>:9090`
- Grafana: `http://<manager-ip>:3000` (`admin`/`admin`)

