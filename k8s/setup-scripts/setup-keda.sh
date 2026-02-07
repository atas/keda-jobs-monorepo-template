#!/usr/bin/env bash
set -euo pipefail

echo "==> Adding KEDA Helm repo..."
helm repo add kedacore https://kedacore.github.io/charts
helm repo update

echo "==> Installing KEDA via Helm..."
helm upgrade --install keda kedacore/keda --namespace keda --create-namespace

echo "==> Waiting for KEDA to be ready..."
kubectl wait --for=condition=Available deployment/keda-operator -n keda --timeout=120s
kubectl wait --for=condition=Available deployment/keda-operator-metrics-apiserver -n keda --timeout=120s
kubectl wait --for=condition=Available deployment/keda-admission-webhooks -n keda --timeout=120s

echo "==> KEDA setup complete!"
