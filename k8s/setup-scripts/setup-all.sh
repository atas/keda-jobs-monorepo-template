#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "  keda-jobs - Full Infrastructure Setup"
echo "========================================="
echo ""

"$SCRIPT_DIR/setup-nats.sh"
echo ""

"$SCRIPT_DIR/../../jobs/nats-streams-config.sh"
echo ""

"$SCRIPT_DIR/setup-keda.sh"
echo ""

"$SCRIPT_DIR/setup-app.sh"
echo ""

"$SCRIPT_DIR/setup-monitoring.sh"
echo ""

echo "========================================="
echo "  All setup complete!"
echo "========================================="
