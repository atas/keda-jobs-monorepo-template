#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if it exists
if [ -f "$K8S_DIR/.env" ]; then
  set -a
  source "$K8S_DIR/.env"
  set +a
fi

# Create R2 secret if R2 vars are set
if [ -n "${R2_ACCOUNT_ID:-}" ] && [ -n "${R2_ACCESS_KEY_ID:-}" ] && [ -n "${R2_SECRET_ACCESS_KEY:-}" ]; then
  echo "==> Creating R2 secret..."
  envsubst < "$K8S_DIR/manual/prod/r2-secret.yaml.tpl" | kubectl apply -f -
else
  echo "ERROR: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY must be set in k8s/.env"
  exit 1
fi

echo "==> Secrets created!"
