# Minikube Deployment Runbook

## Prerequisites

- Docker Desktop is running.
- Install `minikube`, `helm`, and `kubectl`.
- The local `.env` contains runtime values and a reachable `MLFLOW_TRACKING_URI`, PostgreSQL host, and MinIO endpoint for the cluster. Do not commit `.env`.

## Start Cluster

```powershell
minikube start --driver=docker
minikube addons enable ingress
```

## Deploy

Build images, load them into Minikube, create the namespace-scoped runtime secret, and deploy the API plus a one-off pipeline Job:

```powershell
.\scripts\minikube-deploy.ps1
```

The chart creates a ServiceAccount without an API token, ConfigMap, Secret references, API Deployment/Service/Ingress, and pipeline Job. Secrets remain a namespace object created from `.env`, never a chart value.

## Access API

```powershell
minikube tunnel
```

Add `flightops.local` to the local hosts file pointing at the Minikube tunnel address, then call `http://flightops.local/health/ready`.

## Rollout and Rollback

Deploy a different immutable image tag with Helm, then verify rollout:

```powershell
helm upgrade flightops .\deploy\helm\flightops --namespace flightops --set image.tag=<sha>
kubectl rollout status deployment/flightops --namespace flightops
```

Rollback to the previous Helm release:

```powershell
helm rollback flightops 1 --namespace flightops
kubectl rollout status deployment/flightops --namespace flightops
```

## Observability

For Minikube, use managed Prometheus/Grafana/Alertmanager equivalents or install them with a separate observability chart. The API exposes `/metrics`; configure the selected Prometheus instance to scrape the FlightOps Service.
