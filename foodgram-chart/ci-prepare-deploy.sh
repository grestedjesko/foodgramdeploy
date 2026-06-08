#!/bin/bash
set -e

log() { echo "$1"; }

unseal_vault() {
  if ! kubectl get pod vault-0 -n vault &>/dev/null; then
    log "Vault pod not found, skipping unseal"
    return
  fi

  if kubectl exec -n vault vault-0 -- vault status -format=json 2>/dev/null | grep -q '"sealed":false'; then
    log "Vault already unsealed"
    return
  fi

  if [ -z "${VAULT_UNSEAL_KEY:-}" ]; then
    echo "ERROR: Vault is sealed. Set GitHub secret VAULT_UNSEAL_KEY or run: ./setup-vault.sh unseal"
    exit 1
  fi

  log "Unsealing Vault..."
  kubectl exec -n vault vault-0 -- vault operator unseal "${VAULT_UNSEAL_KEY}"
  sleep 3
}

restart_external_secrets() {
  if ! kubectl get namespace external-secrets-system &>/dev/null; then
    return
  fi

  log "Restarting External Secrets Operator..."
  kubectl rollout restart deployment -n external-secrets-system \
    -l app.kubernetes.io/name=external-secrets 2>/dev/null || true
  kubectl rollout status deployment -n external-secrets-system \
    -l app.kubernetes.io/name=external-secrets --timeout=3m 2>/dev/null || true
  sleep 10
}

wait_for_secretstore() {
  if ! kubectl get secretstore vault-backend -n foodgram &>/dev/null; then
    return
  fi

  log "Waiting for SecretStore vault-backend..."
  for _ in $(seq 1 36); do
    READY=$(kubectl get secretstore vault-backend -n foodgram \
      -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
    if [ "$READY" = "True" ]; then
      log "SecretStore is ready"
      return
    fi
    sleep 5
  done

  echo "ERROR: SecretStore vault-backend is not ready"
  kubectl describe secretstore vault-backend -n foodgram | tail -20
  exit 1
}

wait_for_externalsecrets() {
  if ! kubectl get externalsecret -n foodgram &>/dev/null; then
    return
  fi

  log "Waiting for ExternalSecrets in foodgram..."
  for _ in $(seq 1 36); do
    NOT_READY=$(kubectl get externalsecret -n foodgram \
      -o jsonpath='{range .items[*]}{.status.conditions[?(@.type=="Ready")].status}{" "}{end}' \
      2>/dev/null | grep -c False || true)
    if [ "${NOT_READY:-1}" -eq 0 ]; then
      log "ExternalSecrets synced"
      return
    fi
    sleep 5
  done

  kubectl get externalsecret -n foodgram
  echo "ERROR: ExternalSecrets not synced"
  exit 1
}

unseal_vault
restart_external_secrets
wait_for_secretstore
wait_for_externalsecrets
