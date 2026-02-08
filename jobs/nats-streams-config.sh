#!/usr/bin/env bash
set -euo pipefail

NATS_URL="${NATS_URL:-nats://localhost:4222}"

echo "==> Setting up NATS JetStream streams and consumers..."

# Port-forward NATS if not already accessible
if ! nats -s "$NATS_URL" server ping --count=1 >/dev/null 2>&1; then
  echo "    Starting port-forward to NATS..."
  kubectl port-forward -n nats svc/nats 4222:4222 &
  PF_PID=$!
  trap "kill $PF_PID 2>/dev/null || true" EXIT
  sleep 2
fi

# Create stream (idempotent — will update if exists)
echo "==> Creating keda-jobs-events stream..."
nats -s "$NATS_URL" stream add keda-jobs-events \
  --subjects="image-download,image-downloaded,dead-letter" \
  --storage=file \
  --retention=work \
  --max-msgs=-1 \
  --max-bytes=-1 \
  --max-age=72h \
  --max-msg-size=-1 \
  --discard=old \
  --dupe-window=2m \
  --replicas=1 \
  --no-deny-delete \
  --no-deny-purge \
  --defaults \
  2>/dev/null || nats -s "$NATS_URL" stream update keda-jobs-events --force 2>/dev/null || true

# Create consumers (idempotent)
echo "==> Creating image-download-consumer..."
nats -s "$NATS_URL" consumer add keda-jobs-events image-download-consumer \
  --filter="image-download" \
  --ack=explicit \
  --deliver=all \
  --max-deliver=15 \
  --backoff=linear --backoff-min=1m --backoff-max=24h --backoff-steps=15 \
  --wait=600s \
  --replay=instant \
  --pull \
  --defaults \
  2>/dev/null || true

echo "==> Creating image-resize-consumer..."
nats -s "$NATS_URL" consumer add keda-jobs-events image-resize-consumer \
  --filter="image-downloaded" \
  --ack=explicit \
  --deliver=all \
  --max-deliver=15 \
  --backoff=linear --backoff-min=1m --backoff-max=24h --backoff-steps=15 \
  --wait=600s \
  --replay=instant \
  --pull \
  --defaults \
  2>/dev/null || true

echo "==> NATS streams and consumers setup complete!"
nats -s "$NATS_URL" stream ls
nats -s "$NATS_URL" consumer ls keda-jobs-events
