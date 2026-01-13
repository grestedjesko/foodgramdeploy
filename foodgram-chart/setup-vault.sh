#!/bin/bash
set -e

VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_ADDR
KEYS_FILE="vault-keys.json"

log() { echo "$1"; }
ok() { echo "$1"; }
warn() { echo "$1"; }

case "$1" in
    setup)
        log "Устанавливаю Vault + External Secrets..."
        echo ""
        
        # Install Vault
        log "Шаг 1/4: Устанавливаю Vault"
        helm repo add hashicorp https://helm.releases.hashicorp.com 2>/dev/null || true
        helm repo add external-secrets https://charts.external-secrets.io 2>/dev/null || true
        helm repo update >/dev/null 2>&1
        
        kubectl create namespace vault 2>/dev/null || true
        helm install vault hashicorp/vault \
            --namespace vault \
            --values vault-values.yaml 2>/dev/null || true
        
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=vault -n vault --timeout=120s
        ok "Vault установлен"
        
        # Port-forward
        log "Шаг 2/4: Запускаю port-forward"
        kubectl port-forward -n vault svc/vault 8200:8200 >/dev/null 2>&1 &
        PF_PID=$!
        sleep 3
        
        # Init & Unseal
        log "Шаг 3/4: Инициализирую и настраиваю Vault"
        vault operator init -key-shares=1 -key-threshold=1 -format=json > $KEYS_FILE 2>/dev/null
        UNSEAL_KEY=$(jq -r '.unseal_keys_b64[0]' $KEYS_FILE)
        vault operator unseal "$UNSEAL_KEY" >/dev/null 2>&1
        
        export VAULT_TOKEN=$(jq -r '.root_token' $KEYS_FILE)
        
        vault secrets enable -path=secret kv-v2 2>/dev/null || true
        vault auth enable kubernetes 2>/dev/null || true
        kubectl exec -n vault vault-0 -- sh -c \
            "vault write auth/kubernetes/config kubernetes_host=\"https://\$KUBERNETES_PORT_443_TCP_ADDR:443\"" 2>/dev/null || true
        
        kubectl exec -n vault vault-0 -- sh -c 'cat > /tmp/policy.hcl << "EOF"
path "secret/data/foodgram/*" { capabilities = ["read", "list"] }
path "secret/data/rabbitmq/*" { capabilities = ["read", "list"] }
path "secret/data/redis/*" { capabilities = ["read", "list"] }
EOF
vault policy write foodgram /tmp/policy.hcl' 2>/dev/null || true
        
        vault write auth/kubernetes/role/foodgram \
            bound_service_account_names=default \
            bound_service_account_namespaces=foodgram \
            policies=foodgram ttl=24h 2>/dev/null || true
        
        # Store secrets
        vault kv put secret/foodgram/postgres \
            password="change_me" database="foodgram" username="foodgram_user" >/dev/null 2>&1
        vault kv put secret/foodgram/django \
            secret_key="django-insecure-change-me" debug="False" allowed_hosts="*" >/dev/null 2>&1
        vault kv put secret/rabbitmq/auth \
            username="foodgram_user" password="rabbitmq_pass_123" erlang_cookie="erlang_cookie_456" >/dev/null 2>&1
        vault kv put secret/redis/auth \
            password="redis_pass_789" >/dev/null 2>&1
        
        ok "Vault настроен с секретами"
        
        # Install ESO
        log "Шаг 4/4: Устанавливаю External Secrets Operator"
        helm install external-secrets external-secrets/external-secrets \
            -n external-secrets-system --create-namespace \
            --set installCRDs=true 2>/dev/null || true
        
        kill $PF_PID 2>/dev/null || true
        
        echo ""
        ok "Готово!"
        echo ""
        warn "Следующие шаги:"
        echo "  1. В values.yaml: externalSecrets.enabled: true"
        echo "  2. Деплой: helm upgrade --install foodgram . -n foodgram"
        echo ""
        echo "Ключи сохранены в: $KEYS_FILE"
        ;;
    
    reset)
        warn "Удаляю все..."
        helm uninstall vault -n vault 2>/dev/null || true
        helm uninstall external-secrets -n external-secrets-system 2>/dev/null || true
        kubectl delete namespace vault 2>/dev/null || true
        kubectl delete namespace external-secrets-system 2>/dev/null || true
        kubectl delete pvc -n vault --all 2>/dev/null || true
        rm -f $KEYS_FILE
        ok "Очищено"
        ;;
    
    *)
        cat <<EOF
Foodgram Vault Setup

Команды:
  ./setup-vault.sh setup  - Установить все (Vault + External Secrets)
  ./setup-vault.sh reset  - Удалить все и начать заново

Использование:
  1. ./setup-vault.sh setup
  2. В values.yaml: externalSecrets.enabled: true
  3. helm upgrade --install foodgram . -n foodgram

Ключи: vault-keys.json (не коммитить!)

EOF
        ;;
esac