#!/bin/bash
set -e

echo "Deploying Foodgram..."

if ! minikube status | grep -q "host: Running"; then
    echo "Starting minikube..."
    minikube start
    sleep 5
fi

kubectl create namespace foodgram 2>/dev/null || true

echo "Switching to minikube docker..."
eval $(minikube -p minikube docker-env)

echo "Building backend..."
docker build -t foodgram-backend:latest ../backend

echo "Building frontend..."
timeout 30 docker build -t foodgram-frontend:latest ../frontend 2>/dev/null || echo "Frontend build skipped"

echo "Setting up Vault..."
kubectl port-forward -n vault svc/vault 8200:8200 >/dev/null 2>&1 &
VAULT_PF_PID=$!
trap "kill $VAULT_PF_PID 2>/dev/null || true" EXIT
sleep 3

export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN=$(jq -r '.root_token' vault-keys.json)
export PATH="$HOME/bin:$PATH"

echo "Resolving secrets..."
vals eval -f secrets.yaml > /tmp/resolved-secrets.yaml

kubectl delete job foodgram-backend-migrate -n foodgram --ignore-not-found=true

echo "Deploying with Helm..."
helm upgrade --install foodgram . \
    --namespace foodgram \
    -f values.yaml \
    -f /tmp/resolved-secrets.yaml \
    --set backend.image.pullPolicy=Never \
    --set frontend.image.pullPolicy=Never \
    --set rabbitmq.enabled=true \
    --set redis.enabled=true \
    --set backend.redis.enabled=true \
    --set backend.rabbitmq.enabled=true \
    --set backend.consumer.enabled=true \
    --wait \
    --timeout 5m

rm -f /tmp/resolved-secrets.yaml

echo ""
echo "Deployment complete"
echo ""
kubectl get pods -n foodgram
echo ""
kubectl get deploy -n foodgram

echo ""
if kubectl get deploy -n foodgram | grep -q consumer; then
    echo "Consumer deployment found"
    kubectl get pods -n foodgram | grep consumer || echo "Consumer pods starting"
else
    echo "WARNING: Consumer deployment not found"
fi

echo ""
echo "Commands:"
echo "  kubectl logs -n foodgram -l app.kubernetes.io/component=backend --tail=50"
echo "  kubectl logs -n foodgram -l app.kubernetes.io/component=consumer --all-containers --tail=50"
echo "  minikube service -n ingress-nginx ingress-nginx-controller"