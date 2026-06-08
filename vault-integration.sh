#!/bin/bash
# vault-integration.sh
# Vault integration for foodgram CI/CD:
#   - Authenticates to Vault via Kubernetes SA token (in-cluster) or token env var
#   - Reads secrets and exports them as env vars for Helm/werf
#   - Stores the GHCR docker token in Vault so the cluster can pull images
#   - Creates the ghcr-credentials imagePullSecret in the foodgram namespace
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://vault.vault.svc.cluster.local:8200}"
VAULT_AUTH_PATH="${VAULT_AUTH_PATH:-auth/kubernetes/login}"
VAULT_ROLE="${VAULT_ROLE:-foodgram}"
NAMESPACE="${NAMESPACE:-foodgram}"
SA_TOKEN_FILE="/var/run/secrets/kubernetes.io/serviceaccount/token"

log()  { echo "[vault] $*"; }
err()  { echo "[vault] ERROR: $*" >&2; exit 1; }

# ─── authenticate ─────────────────────────────────────────────────────────────

vault_login() {
  if [ -n "${VAULT_TOKEN:-}" ]; then
    log "Using VAULT_TOKEN from environment"
    export VAULT_TOKEN
    return
  fi

  if [ -f "$SA_TOKEN_FILE" ]; then
    log "Authenticating via Kubernetes service account token"
    local sa_token
    sa_token=$(cat "$SA_TOKEN_FILE")
    local response
    response=$(curl -sf \
      --request POST \
      --data "{\"jwt\": \"${sa_token}\", \"role\": \"${VAULT_ROLE}\"}" \
      "${VAULT_ADDR}/v1/${VAULT_AUTH_PATH}")
    VAULT_TOKEN=$(echo "$response" | grep -o '"client_token":"[^"]*"' | cut -d'"' -f4)
    export VAULT_TOKEN
    log "Vault login successful"
  else
    err "No VAULT_TOKEN and no SA token found at ${SA_TOKEN_FILE}"
  fi
}

# ─── read a kv-v2 secret field ────────────────────────────────────────────────

vault_read() {
  local path="$1"
  local field="$2"
  curl -sf \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    "${VAULT_ADDR}/v1/secret/data/${path}" \
    | grep -o "\"${field}\":\"[^\"]*\"" \
    | cut -d'"' -f4
}

# ─── write a kv-v2 secret ─────────────────────────────────────────────────────

vault_write() {
  local path="$1"
  local payload="$2"   # JSON: {"key":"val",...}
  curl -sf \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    --request POST \
    --data "{\"data\": ${payload}}" \
    "${VAULT_ADDR}/v1/secret/data/${path}" > /dev/null
}

# ─── store docker (GHCR) credentials in Vault ─────────────────────────────────

store_docker_token() {
  local registry="${1:-ghcr.io}"
  local username="${2:-}"
  local token="${3:-}"

  if [ -z "$username" ] || [ -z "$token" ]; then
    log "DOCKER_USERNAME / DOCKER_TOKEN not provided — skipping docker token storage"
    return
  fi

  log "Storing docker credentials for ${registry} in Vault..."
  # Store as base64-encoded .dockerconfigjson so ESO can sync it directly
  local auth
  auth=$(echo -n "${username}:${token}" | base64 -w0)
  local dockerconfig
  dockerconfig=$(printf '{"auths":{"%s":{"auth":"%s"}}}' "$registry" "$auth" | base64 -w0)

  vault_write "foodgram/docker" \
    "{\"registry\": \"${registry}\", \"username\": \"${username}\", \"token\": \"${token}\", \"dockerconfigjson\": \"${dockerconfig}\"}"

  log "Docker credentials stored at secret/data/foodgram/docker"
}

# ─── create imagePullSecret from Vault data ───────────────────────────────────

create_pull_secret() {
  local registry="${1:-ghcr.io}"
  local username="${2:-}"
  local token="${3:-}"

  if [ -z "$username" ] || [ -z "$token" ]; then
    log "Reading docker credentials from Vault..."
    username=$(vault_read "foodgram/docker" "username")
    token=$(vault_read "foodgram/docker" "token")
    registry=$(vault_read "foodgram/docker" "registry")
  fi

  if [ -z "$username" ] || [ -z "$token" ]; then
    log "No docker credentials found — skipping imagePullSecret creation"
    return
  fi

  log "Creating ghcr-credentials imagePullSecret in namespace ${NAMESPACE}..."
  kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
  kubectl create secret docker-registry ghcr-credentials \
    --namespace "${NAMESPACE}" \
    --docker-server="${registry}" \
    --docker-username="${username}" \
    --docker-password="${token}" \
    --dry-run=client -o yaml | kubectl apply -f -
  log "imagePullSecret ghcr-credentials created/updated"
}

# ─── export secrets as env vars for Helm / werf ───────────────────────────────

export_secrets() {
  log "Reading secrets from Vault..."

  POSTGRES_PASSWORD=$(vault_read "foodgram/postgres" "password")
  DJANGO_SECRET_KEY=$(vault_read "foodgram/django" "secret_key")
  DEBUG=$(vault_read "foodgram/django" "debug")
  ALLOWED_HOSTS=$(vault_read "foodgram/django" "allowed_hosts")
  REDIS_PASSWORD=$(vault_read "redis/auth" "password")
  RABBITMQ_USERNAME=$(vault_read "rabbitmq/auth" "username")
  RABBITMQ_PASSWORD=$(vault_read "rabbitmq/auth" "password")
  RABBITMQ_ERLANG_COOKIE=$(vault_read "rabbitmq/auth" "erlang_cookie")

  export POSTGRES_PASSWORD DJANGO_SECRET_KEY DEBUG ALLOWED_HOSTS
  export REDIS_PASSWORD RABBITMQ_USERNAME RABBITMQ_PASSWORD RABBITMQ_ERLANG_COOKIE

  log "Secrets exported as environment variables"
}

# ─── main ─────────────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
Usage: $0 <command> [options]

Commands:
  login                        Authenticate to Vault and verify
  export                       Export all secrets as env vars (source this file)
  store-docker <user> <token>  Write GHCR credentials to Vault
  pull-secret [user] [token]   Create ghcr-credentials imagePullSecret in k8s
  all <user> <token>           Full flow: login + store-docker + pull-secret + export

Environment:
  VAULT_ADDR        Vault address (default: http://vault.vault.svc.cluster.local:8200)
  VAULT_TOKEN       Root/pipeline token (skips k8s auth if set)
  VAULT_ROLE        Kubernetes auth role (default: foodgram)
  NAMESPACE         Target k8s namespace (default: foodgram)

Examples:
  # In CI pipeline (GitHub Actions runner has VAULT_TOKEN secret):
  source <(./vault-integration.sh export)

  # Store GHCR PAT in Vault once:
  VAULT_TOKEN=\$ROOT_TOKEN ./vault-integration.sh store-docker \$GITHUB_ACTOR \$GITHUB_TOKEN

  # Full deploy prep:
  ./vault-integration.sh all \$GITHUB_ACTOR \$GITHUB_TOKEN
EOF
}

case "${1:-help}" in
  login)
    vault_login
    log "Vault address: ${VAULT_ADDR}"
    curl -sf -H "X-Vault-Token: ${VAULT_TOKEN}" "${VAULT_ADDR}/v1/sys/health" | grep -q '"initialized":true' \
      && log "Vault is healthy and unsealed" || err "Vault health check failed"
    ;;

  export)
    vault_login
    export_secrets
    # Print as shell exports so callers can: source <(./vault-integration.sh export)
    echo "export POSTGRES_PASSWORD='${POSTGRES_PASSWORD}'"
    echo "export DJANGO_SECRET_KEY='${DJANGO_SECRET_KEY}'"
    echo "export DEBUG='${DEBUG}'"
    echo "export ALLOWED_HOSTS='${ALLOWED_HOSTS}'"
    echo "export REDIS_PASSWORD='${REDIS_PASSWORD}'"
    echo "export RABBITMQ_USERNAME='${RABBITMQ_USERNAME}'"
    echo "export RABBITMQ_PASSWORD='${RABBITMQ_PASSWORD}'"
    echo "export RABBITMQ_ERLANG_COOKIE='${RABBITMQ_ERLANG_COOKIE}'"
    ;;

  store-docker)
    vault_login
    store_docker_token "ghcr.io" "${2:-}" "${3:-}"
    ;;

  pull-secret)
    vault_login
    create_pull_secret "ghcr.io" "${2:-}" "${3:-}"
    ;;

  all)
    vault_login
    store_docker_token "ghcr.io" "${2:-}" "${3:-}"
    create_pull_secret "ghcr.io" "${2:-}" "${3:-}"
    export_secrets
    log "Done. Secrets available as env vars."
    ;;

  *)
    usage
    ;;
esac
