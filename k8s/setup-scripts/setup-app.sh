#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$K8S_DIR")"

echo "==> Applying kustomize manifests..."
kubectl apply -k "$K8S_DIR/kustomize/overlays/prod"

# Setup secrets (R2) if .env exists
if [ -f "$K8S_DIR/.env" ]; then
  "$SCRIPT_DIR/setup-secrets.sh"
else
  echo "WARNING: k8s/.env not found, skipping secrets. Copy .env.template to .env"
fi

echo "==> Setting up Deployments and ScaledObjects..."
kubectl apply -f "$ROOT_DIR/jobs/image-download/service.yaml"
kubectl apply -f "$ROOT_DIR/jobs/image-resize/service.yaml"

echo "==> App setup complete!"
