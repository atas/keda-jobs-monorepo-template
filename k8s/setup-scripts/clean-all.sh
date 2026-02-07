#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$K8S_DIR")"

echo "========================================="
echo "  keda-jobs - Full Infrastructure Teardown"
echo "========================================="
echo ""

echo "==> Removing monitoring..."
kubectl delete -f "$K8S_DIR/monitoring/dashboards/" --ignore-not-found
kubectl delete -f "$K8S_DIR/monitoring/servicemonitors.yaml" --ignore-not-found

echo "==> Removing services and scaled objects..."
kubectl delete -f "$ROOT_DIR/jobs/image-download/service.yaml" --ignore-not-found
kubectl delete -f "$ROOT_DIR/jobs/image-resize/service.yaml" --ignore-not-found

echo "==> Removing kustomize manifests..."
kubectl delete -k "$K8S_DIR/kustomize/overlays/prod" --ignore-not-found

echo "==> Removing KEDA..."
helm uninstall keda --namespace keda --ignore-not-found 2>/dev/null || true
kubectl delete namespace keda --ignore-not-found

echo "==> Removing NATS..."
kubectl delete -f "$K8S_DIR/nats/nats.yaml" --ignore-not-found
kubectl delete -f "$K8S_DIR/nats/namespace.yaml" --ignore-not-found

echo ""
echo "========================================="
echo "  Cleanup complete!"
echo "========================================="
