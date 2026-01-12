#!/bin/bash
set -e

kubectl create namespace foodgram 2>/dev/null || true

# Setup Vault connection
kubectl port-forward -n vault svc/vault 8200:8200 >/dev/null 2>&1 &
VAULT_PF_PID=$!
trap "kill $VAULT_PF_PID 2>/dev/null || true" EXIT
sleep 2

export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN=$(jq -r '.root_token' foodgram-chart/vault-keys.json)
export PATH="$HOME/bin:$PATH"

# Get secrets from Vault
vals eval -f foodgram-chart/secrets.yaml > /tmp/resolved-secrets.yaml

# Build images
echo "Building images..."
docker build -t foodgram-backend:latest ./backend
docker build -t foodgram-frontend:latest ./frontend

# Load to minikube
echo "Loading images to minikube..."
minikube image load foodgram-backend:latest
minikube image load foodgram-frontend:latest

# Deploy
echo "Deploying..."
helm upgrade --install foodgram ./foodgram-chart \
    --namespace foodgram \
    -f foodgram-chart/values.yaml \
    -f /tmp/resolved-secrets.yaml \
    --set backend.image.pullPolicy=Never \
    --set frontend.image.pullPolicy=Never \
    --wait \
    --timeout 5m

rm -f /tmp/resolved-secrets.yaml

echo ""
echo "Done. Check status:"
echo "  kubectl get pods -n foodgram"
echo ""
echo "Access app:"
echo "  minikube service -n ingress-nginx ingress-nginx-controller"
