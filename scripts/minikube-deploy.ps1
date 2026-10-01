[CmdletBinding()]
param(
    [string]$Namespace = "flightops",
    [string]$Release = "flightops"
)

$ErrorActionPreference = "Stop"

minikube status -p minikube

docker compose build api pipeline
minikube image load flightops/api:0.1.0
minikube image load flightops/pipeline:0.1.0

kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic flightops-runtime --namespace $Namespace `
    --from-env-file .env `
    --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install $Release .\deploy\helm\flightops `
    --namespace $Namespace `
    --set image.repository=flightops/api `
    --set image.tag=0.1.0 `
    --set pipeline.image.repository=flightops/pipeline `
    --set pipeline.image.tag=0.1.0

kubectl rollout status deployment/$Release --namespace $Namespace --timeout=180s
kubectl get ingress $Release --namespace $Namespace
