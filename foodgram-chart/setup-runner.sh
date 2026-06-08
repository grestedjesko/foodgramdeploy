#!/bin/bash
set -e

NAMESPACE="actions-runner-system"
REPO="${GITHUB_REPO:-grestedjesko/foodgramdeploy}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { echo "$1"; }
warn() { echo "WARNING: $1"; }

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  setup    Install ARC, register runner, create GHCR pull secret
  status   Show runner and controller status
  remove   Uninstall runner and ARC controller

Environment variables:
  GITHUB_TOKEN   GitHub PAT with repo scope (required for setup)
  GITHUB_REPO    Repository for runner (default: grestedjesko/foodgramdeploy)
  GHCR_USER      GitHub username for image pull secret (optional)
  GHCR_TOKEN     Token for ghcr.io pull secret (optional, defaults to GITHUB_TOKEN)

Before setup:
  1. Start minikube: minikube start
  2. Create PAT: GitHub -> Settings -> Developer settings -> Personal access tokens
     Scopes: repo, read:packages, write:packages
  3. In repo settings enable Actions with read/write permissions
EOF
}

ensure_minikube() {
  if ! minikube status 2>/dev/null | grep -q "host: Running"; then
    log "Starting minikube..."
    minikube start
  fi
}

install_cert_manager() {
  if kubectl get crd certificates.cert-manager.io >/dev/null 2>&1; then
    log "cert-manager already installed"
    return
  fi

  log "Installing cert-manager (required by actions-runner-controller)..."
  helm repo add jetstack https://charts.jetstack.io 2>/dev/null || true
  helm repo update jetstack

  helm upgrade --install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --create-namespace \
    --version v1.16.2 \
    --set crds.enabled=true \
    --wait \
    --timeout 5m

  log "Waiting for cert-manager webhook..."
  kubectl wait --for=condition=Available deployment/cert-manager-webhook \
    -n cert-manager --timeout=3m
}

install_arc() {
  if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "GITHUB_TOKEN is required"
    echo "Example: GITHUB_TOKEN=ghp_xxx $0 setup"
    exit 1
  fi

  helm repo add actions-runner-controller \
    https://actions-runner-controller.github.io/actions-runner-controller 2>/dev/null || true
  helm repo update

  kubectl create namespace "${NAMESPACE}" 2>/dev/null || true

  helm upgrade --install arc \
    actions-runner-controller/actions-runner-controller \
    --namespace "${NAMESPACE}" \
    --set authSecret.create=true \
    --set authSecret.github_token="${GITHUB_TOKEN}" \
    --wait \
    --timeout 5m
}

apply_runner_manifests() {
  kubectl apply -f "${SCRIPT_DIR}/actions-runner/rbac.yaml"

  sed "s|repository: grestedjesko/foodgramdeploy|repository: ${REPO}|" \
    "${SCRIPT_DIR}/actions-runner/runner-deployment.yaml" | kubectl apply -f -
}

create_ghcr_secret() {
  local user="${GHCR_USER:-}"
  local token="${GHCR_TOKEN:-${GITHUB_TOKEN:-}}"

  if [ -z "${token}" ]; then
    warn "GHCR_TOKEN not set, skipping image pull secret"
    return
  fi

  if [ -z "${user}" ]; then
    warn "GHCR_USER not set, skipping image pull secret"
    warn "Create it manually:"
    warn "  kubectl create secret docker-registry ghcr-credentials -n foodgram \\"
    warn "    --docker-server=ghcr.io --docker-username=YOUR_USER --docker-password=YOUR_TOKEN"
    return
  fi

  kubectl create namespace foodgram 2>/dev/null || true
  kubectl delete secret ghcr-credentials -n foodgram --ignore-not-found=true
  kubectl create secret docker-registry ghcr-credentials \
    --namespace foodgram \
    --docker-server=ghcr.io \
    --docker-username="${user}" \
    --docker-password="${token}"
  ok "Created ghcr-credentials secret in foodgram namespace"
}

ok() { echo "$1"; }

case "${1:-}" in
  setup)
    log "Setting up GitHub Actions self-hosted runner..."
    ensure_minikube
    install_cert_manager
    install_arc
    apply_runner_manifests
    create_ghcr_secret
    echo ""
    ok "Runner setup complete"
    echo ""
    echo "Check status:"
    echo "  $0 status"
    echo ""
    echo "In GitHub: Settings -> Actions -> Runners"
    echo "Push to main with conventional commit, e.g.:"
    echo "  git commit -m 'feat: add CI/CD pipeline'"
    ;;

  status)
    kubectl get pods -n "${NAMESPACE}" || true
    echo ""
    kubectl get runners -n "${NAMESPACE}" 2>/dev/null || true
    ;;

  remove)
    kubectl delete -f "${SCRIPT_DIR}/actions-runner/runner-deployment.yaml" --ignore-not-found=true
    kubectl delete -f "${SCRIPT_DIR}/actions-runner/rbac.yaml" --ignore-not-found=true
    helm uninstall arc -n "${NAMESPACE}" 2>/dev/null || true
    kubectl delete namespace "${NAMESPACE}" --ignore-not-found=true
    ok "Runner removed (cert-manager left installed — shared cluster component)"
    ;;

  *)
    usage
    exit 1
    ;;
esac
