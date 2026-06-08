#!/bin/bash
# Install metrics-server and enable Locust for load testing

set -e

echo "=== Setting up metrics-server ==="

# Enable metrics-server addon in minikube (simplest approach)
if command -v minikube &>/dev/null; then
    minikube addons enable metrics-server
    echo "metrics-server addon enabled in minikube"
else
    # For plain k8s clusters, deploy metrics-server from official manifest
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    # Patch for non-TLS environments (minikube / kubeadm without cert rotation)
    kubectl patch deployment metrics-server -n kube-system \
        --type='json' \
        -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' \
        2>/dev/null || true
fi

echo "Waiting for metrics-server to be ready..."
kubectl rollout status deployment/metrics-server -n kube-system --timeout=90s

echo ""
echo "=== Current resource usage (after ~60s metrics become available) ==="
echo "Run these commands to inspect usage:"
echo "  kubectl top nodes"
echo "  kubectl top pods -n foodgram"
echo ""

echo "=== Deploying Locust load testing tool ==="

if ! minikube status | grep -q "host: Running" 2>/dev/null; then
    echo "minikube is not running, skipping docker-env setup"
else
    eval "$(minikube -p minikube docker-env)"
fi

MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "")
if [ -z "$MINIKUBE_IP" ]; then
    echo "WARNING: Could not get minikube IP. Set TARGET_HOST manually."
    TARGET_HOST="http://foodgram-backend:8000"
else
    TARGET_HOST="http://${MINIKUBE_IP}"
fi

echo "Target host for locust: ${TARGET_HOST}"

helm upgrade --install foodgram . \
    --namespace foodgram \
    -f values.yaml \
    --set locust.enabled=true \
    --set "locust.target.host=${TARGET_HOST}" \
    --set locust.config.users=50 \
    --set locust.config.spawnRate=5 \
    --set locust.config.runTime=5m \
    --reuse-values \
    --wait \
    --timeout 3m

echo ""
echo "=== Locust deployed. Open the web UI: ==="
echo "  kubectl port-forward -n foodgram svc/foodgram-locust 8089:8089"
echo "  Then open http://localhost:8089"
echo ""
echo "=== Stress test settings ==="
echo "  Number of users : 50"
echo "  Spawn rate      : 5 users/sec"
echo "  Duration        : 5 minutes"
echo ""
echo "Acceptance criteria:"
echo "  - No request failures (error rate = 0%)"
echo "  - Average response time < 5000 ms"
echo "  - 95th percentile < 7000 ms"
