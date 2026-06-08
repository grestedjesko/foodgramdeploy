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
        
        # Check if foodgram namespace exists with data
        if kubectl get namespace foodgram &>/dev/null; then
            warn "Namespace foodgram уже существует!"
            echo "Для чистой установки нужно удалить старые данные:"
            echo "  ./setup-vault.sh reset"
            echo ""
            echo "Или продолжить без очистки (нажмите Enter):"
            read -r
        fi
        
        # Install Vault
        log "Шаг 1/4: Устанавливаю Vault"
        
        # Скачиваем chart локально (обход проблем с TLS)
        if [ ! -d "vault" ]; then
            log "Скачиваю Vault chart..."
            curl -kL https://helm.releases.hashicorp.com/vault-0.31.0.tgz -o vault-0.31.0.tgz
            tar -xzf vault-0.31.0.tgz
            rm vault-0.31.0.tgz
        fi
        
        kubectl create namespace vault 2>/dev/null || true
        helm install vault ./vault \
            --namespace vault \
            --values vault-values.yaml
        
        # Ждем, пока pod создастся
        log "Ожидаю создания pod'а vault-0..."
        for i in {1..30}; do
            if kubectl get pod vault-0 -n vault >/dev/null 2>&1; then
                break
            fi
            sleep 2
        done
        
        # Ждем, пока pod запустится (Running), а не станет Ready (это произойдет после init)
        log "Ожидаю запуска контейнера..."
        kubectl wait --for=jsonpath='{.status.phase}'=Running pod/vault-0 -n vault --timeout=120s
        sleep 5
        ok "Vault установлен и запущен"
        
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
        
        log "Включаю KV secrets engine..."
        vault secrets enable -path=secret kv-v2 2>/dev/null || log "KV уже включен"
        
        log "Включаю kubernetes auth..."
        vault auth enable kubernetes 2>/dev/null || log "Kubernetes auth уже включен"
        
        log "Настраиваю kubernetes auth..."
        kubectl exec -n vault vault-0 -- sh -c \
            "VAULT_TOKEN=$VAULT_TOKEN vault write auth/kubernetes/config kubernetes_host=\"https://\$KUBERNETES_PORT_443_TCP_ADDR:443\""
        
        log "Создаю policy для foodgram..."
        kubectl exec -n vault vault-0 -- sh -c "cat > /tmp/policy.hcl << 'EOF'
path \"secret/data/foodgram/*\" { capabilities = [\"read\", \"list\"] }
path \"secret/data/rabbitmq/*\" { capabilities = [\"read\", \"list\"] }
path \"secret/data/redis/*\" { capabilities = [\"read\", \"list\"] }
EOF
VAULT_TOKEN=$VAULT_TOKEN vault policy write foodgram /tmp/policy.hcl"
        
        log "Создаю роль foodgram..."
        vault write auth/kubernetes/role/foodgram \
            bound_service_account_names=default \
            bound_service_account_namespaces=foodgram \
            policies=foodgram ttl=24h
        
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
        
        # Скачиваем ESO chart локально
        if [ ! -d "external-secrets" ]; then
            log "Скачиваю External Secrets chart..."
            helm repo add external-secrets https://charts.external-secrets.io --force-update
            helm repo update
            helm pull external-secrets/external-secrets --version 0.12.1 --untar
        fi
        
        helm install external-secrets ./external-secrets \
            -n external-secrets-system --create-namespace \
            --set installCRDs=true
        
        log "Ожидаю готовности External Secrets Operator..."
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=external-secrets-webhook \
            -n external-secrets-system --timeout=120s
        sleep 5
        
        kill $PF_PID 2>/dev/null || true
        
        echo ""
        ok "Готово! Проверяю конфигурацию..."
        echo ""
        
        # Проверка конфигурации
        log "Проверка Vault:"
        kubectl exec -n vault vault-0 -- sh -c "VAULT_TOKEN=$VAULT_TOKEN vault read auth/kubernetes/config" >/dev/null && ok "✓ Kubernetes auth настроен" || warn "✗ Ошибка kubernetes auth"
        kubectl exec -n vault vault-0 -- sh -c "VAULT_TOKEN=$VAULT_TOKEN vault policy read foodgram" >/dev/null && ok "✓ Policy создана" || warn "✗ Ошибка policy"
        kubectl exec -n vault vault-0 -- sh -c "VAULT_TOKEN=$VAULT_TOKEN vault read auth/kubernetes/role/foodgram" >/dev/null && ok "✓ Роль создана" || warn "✗ Ошибка роли"
        kubectl exec -n vault vault-0 -- sh -c "VAULT_TOKEN=$VAULT_TOKEN vault kv get secret/redis/auth" >/dev/null && ok "✓ Секреты сохранены" || warn "✗ Ошибка секретов"
        
        echo ""
        warn "Следующие шаги:"
        echo "  1. В values.yaml: externalSecrets.enabled: true"
        echo "  2. Деплой: helm upgrade --install foodgram . -n foodgram --set externalSecrets.enabled=true"
        echo ""
        echo "Пароли (см. в Vault):"
        echo "  Redis:      redis_pass_789"
        echo "  RabbitMQ:   rabbitmq_pass_123"  
        echo "  PostgreSQL: change_me"
        echo ""
        echo "Ключи сохранены в: $KEYS_FILE"
        ;;
    
    reset)
        warn "ВНИМАНИЕ: Это удалит ВСЁ (Vault + Foodgram)!"
        echo "Будут удалены:"
        echo "  - Vault + External Secrets"
        echo "  - Helm релиз foodgram"
        echo "  - Namespace foodgram (со всеми PVC)"
        echo ""
        echo "Продолжить? (yes/no)"
        read -r confirm
        if [ "$confirm" != "yes" ]; then
            echo "Отменено"
            exit 0
        fi
        
        warn "Удаляю всё..."
        
        # Удаляем Foodgram
        log "Удаляю Foodgram..."
        helm uninstall foodgram -n foodgram 2>/dev/null || true
        kubectl delete namespace foodgram --timeout=60s 2>/dev/null || true
        
        # Удаляем Vault и External Secrets
        log "Удаляю Vault..."
        helm uninstall vault -n vault 2>/dev/null || true
        helm uninstall external-secrets -n external-secrets-system 2>/dev/null || true
        kubectl delete namespace vault --timeout=60s 2>/dev/null || true
        kubectl delete namespace external-secrets-system --timeout=60s 2>/dev/null || true
        kubectl delete pvc -n vault --all 2>/dev/null || true
        
        # Очищаем локальные файлы
        rm -f $KEYS_FILE
        rm -rf vault external-secrets *.tgz 2>/dev/null || true
        
        ok "Всё очищено! Можно делать чистую установку."
        ;;
    
    *)
        cat <<EOF
Foodgram Vault Setup

Команды:
  ./setup-vault.sh setup  - Установить Vault + External Secrets
  ./setup-vault.sh reset  - Удалить ВСЁ (Vault + Foodgram) для чистой установки

Использование:
  1. ./setup-vault.sh setup
  2. В values.yaml: externalSecrets.enabled: true
  3. helm upgrade --install foodgram . -n foodgram

Чистая установка с нуля:
  1. ./setup-vault.sh reset  # Удалить всё
  2. ./setup-vault.sh setup  # Установить Vault
  3. eval \$(minikube docker-env)
  4. docker build -t foodgram-backend:latest ../backend
  5. docker build -t foodgram-frontend:latest ../frontend
  6. helm upgrade --install foodgram . -n foodgram --create-namespace \\
       --set backend.image.pullPolicy=Never \\
       --set frontend.image.pullPolicy=Never --wait --timeout 10m

Ключи: vault-keys.json (не коммитить!)

EOF
        ;;
esac