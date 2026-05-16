# Kubernetes deployment (manifests)

Manifests are in `k8s/` and use the namespace `sre-app`.

## Images

Kubernetes needs images available to the cluster nodes. Options:
1) Push to a registry (recommended) and update image names in `k8s/deployments/*.yaml`
2) For local clusters:
   - kind: `kind load docker-image sre/auth-service:latest ...`
   - minikube: `minikube image load sre/auth-service:latest ...`

Build locally:
```bash
docker build -t sre/auth-service:latest services/auth
docker build -t sre/user-service:latest services/user
docker build -t sre/product-service:latest services/product
docker build -t sre/order-service:latest services/order
docker build -t sre/payment-service:latest services/payment
docker build -t sre/notification-service:latest services/notification
```

## Apply

```bash
kubectl apply -k k8s
```

## Access (NodePort)

- Frontend: `http://<node-ip>:30080`
- Prometheus: `http://<node-ip>:30090`
- Alertmanager: `http://<node-ip>:30093`
- Grafana: `http://<node-ip>:30300` (`admin`/`admin`)

## Autoscaling

`k8s/hpa/` includes HPAs for `order-service` and `payment-service` (requires metrics-server).

