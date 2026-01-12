#!/bin/bash
set -e

VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_ADDR

case "$1" in
    reset)
        helm uninstall vault -n vault 2>/dev/null || true
        kubectl delete pvc -n vault --all 2>/dev/null || true
        kubectl delete namespace vault 2>/dev/null || true
        rm -f foodgram-chart/vault-keys.json
        echo "Cleaned. Run: ./setup-vault.sh install"
        ;;
    
    install)
        helm repo add hashicorp https://helm.releases.hashicorp.com 2>/dev/null || true
        helm repo update
        kubectl create namespace vault
        
        helm install vault hashicorp/vault \
            --namespace vault \
            --values foodgram-chart/vault-values.yaml
        
        echo ""
        echo "Installed. Start port-forward in another terminal:"
        echo "  kubectl port-forward -n vault svc/vault 8200:8200"
        echo ""
        echo "Then run: ./setup-vault.sh init"
        ;;
    
    init)
        vault operator init -key-shares=1 -key-threshold=1 -format=json > foodgram-chart/vault-keys.json
        
        ROOT_TOKEN=$(jq -r '.root_token' foodgram-chart/vault-keys.json)
        echo "Root token: $ROOT_TOKEN"
        echo ""
        echo "Keys saved to foodgram-chart/vault-keys.json"
        echo "Run: ./setup-vault.sh unseal"
        ;;
    
    unseal)
        UNSEAL_KEY=$(jq -r '.unseal_keys_b64[0]' foodgram-chart/vault-keys.json)
        vault operator unseal "$UNSEAL_KEY"
        echo "Run: ./setup-vault.sh setup"
        ;;
    
    setup)
        export VAULT_TOKEN=$(jq -r '.root_token' foodgram-chart/vault-keys.json)
        
        vault secrets enable -path=secret kv-v2 2>/dev/null || true
        
        # Setup Kubernetes auth
        vault auth enable kubernetes 2>/dev/null || true
        kubectl exec -n vault vault-0 -- sh -c \
            "vault write auth/kubernetes/config kubernetes_host=\"https://\$KUBERNETES_PORT_443_TCP_ADDR:443\"" 2>/dev/null || true
        
        # Create policy
        kubectl exec -n vault vault-0 -- sh -c 'cat > /tmp/policy.hcl << EOF
path "secret/data/foodgram/*" {
  capabilities = ["read", "list"]
}
EOF
vault policy write foodgram /tmp/policy.hcl' 2>/dev/null || true
        
        # Create role
        vault write auth/kubernetes/role/foodgram \
            bound_service_account_names=default \
            bound_service_account_namespaces=foodgram \
            policies=foodgram \
            ttl=24h 2>/dev/null || true
        
        # Store secrets
        vault kv put secret/foodgram/postgres \
            password="change_me" \
            database="foodgram" \
            username="foodgram_user"
        
        vault kv put secret/foodgram/django \
            secret_key="django-insecure-my-secret-key-123" \
            debug="False" \
            allowed_hosts="*"
        
        echo "Done. Vault is ready."
        ;;
    
    status)
        vault status
        ;;
    
    *)
        cat <<EOF
Usage: ./setup-vault.sh [command]

Commands:
  reset     - Remove everything
  install   - Install Vault
  init      - Initialize Vault
  unseal    - Unseal Vault
  setup     - Configure secrets
  status    - Check status

Example:
  ./setup-vault.sh install
  kubectl port-forward -n vault svc/vault 8200:8200  # in another terminal
  ./setup-vault.sh init
  ./setup-vault.sh unseal
  ./setup-vault.sh setup

EOF
        ;;
esac
