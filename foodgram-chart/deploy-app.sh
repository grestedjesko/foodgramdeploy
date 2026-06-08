#!/bin/bash
set -e

# --with-locust   also deploy Locust load testing pod
WITH_LOCUST=false
for arg in "$@"; do
    [ "$arg" = "--with-locust" ] && WITH_LOCUST=true
done

echo "Deploying Foodgram..."

if ! minikube status | grep -q "host: Running"; then
    echo "Starting minikube..."
    minikube start
    sleep 5
fi

echo "Enabling metrics-server..."
minikube addons enable metrics-server 2>/dev/null || true

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

MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "")
LOCUST_FLAGS=""
if [ "$WITH_LOCUST" = "true" ]; then
    TARGET_HOST="http://${MINIKUBE_IP:-foodgram-backend:8000}"
    LOCUST_FLAGS="--set locust.enabled=true --set locust.target.host=${TARGET_HOST}"
    echo "Locust will be deployed targeting: ${TARGET_HOST}"
fi

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
    ${LOCUST_FLAGS} \
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
echo ""
echo "Resource metrics (available ~60s after startup):"
echo "  kubectl top nodes"
echo "  kubectl top pods -n foodgram"
if [ "$WITH_LOCUST" = "true" ]; then
    echo ""
    echo "Locust UI:"
    echo "  kubectl port-forward -n foodgram svc/foodgram-locust 8089:8089"
    echo "  Open http://localhost:8089"
fi