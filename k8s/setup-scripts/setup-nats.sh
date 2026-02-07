#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> Setting up NATS..."
kubectl apply -f "$K8S_DIR/nats/namespace.yaml"
kubectl apply -f "$K8S_DIR/nats/nats.yaml"

echo "==> Waiting for NATS to be ready..."
kubectl wait --for=condition=Ready pod -l app=nats -n nats --timeout=120s

echo "==> NATS setup complete!"
