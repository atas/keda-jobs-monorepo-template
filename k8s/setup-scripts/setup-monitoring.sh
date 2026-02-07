#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> Setting up monitoring..."

echo "  - Updating NATS with exporter sidecar..."
kubectl apply -f "$K8S_DIR/nats/nats.yaml"
kubectl rollout status statefulset/nats -n nats --timeout=120s

echo "  - Applying ServiceMonitors..."
kubectl apply -f "$K8S_DIR/monitoring/servicemonitors.yaml"

echo "  - Applying Grafana dashboards..."
kubectl apply -f "$K8S_DIR/monitoring/dashboards/"

echo "==> Monitoring setup complete!"
