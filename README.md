# keda-jobs

Event-driven job execution platform using NATS JetStream for messaging and KEDA for autoscaling. Jobs scale 0→N based on consumer lag and pull messages directly from JetStream.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│  nats namespace                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  NATS JetStream (StatefulSet)                                     │ │
│  │  - Stream: keda-jobs-events                                       │ │
│  │  - Subjects: image-download, image-downloaded                     │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                    (Jobs pull messages directly)
                                    │
┌────────────────────────────────────────────────────────────────────────┐
│  keda-jobs-prod namespace                                              │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  KEDA ScaledObjects                                              │  │
│  │  - Watches consumer lag via NATS monitoring endpoint             │  │
│  │  - Scales Deployments 0→N based on pending messages              │  │
│  └──────────────────────┬──────────────────────────────────────────┘  │
│                         │                                              │
│           ┌─────────────┴──────────────┐                               │
│           ▼                            ▼                               │
│   ┌────────────────┐          ┌────────────────┐                       │
│   │ image-download │          │ image-resize   │                       │
│   │ consumer       │          │ consumer       │                       │
│   │ filter:        │          │ filter:        │                       │
│   │ image-download │          │ image-downloaded│                      │
│   └───────┬────────┘          └───────┬────────┘                       │
│           ▼                           ▼                                │
│   ┌────────────────┐          ┌────────────────┐                       │
│   │ image-download │          │ image-resize   │                       │
│   │ (Deployment)   │          │ (Deployment)   │                       │
│   └───────┬────────┘          └────────────────┘                       │
│           │                                                            │
│           │ publishes image-downloaded                                 │
│           └──────────► NATS ──► image-resize consumer ──► image-resize │
└────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Kubernetes cluster
- `kubectl` configured to access your cluster
- Docker (for building images)
- `nats` CLI (for testing)
- `make`

## Quick Start

### 1. Setup Infrastructure

```bash
# Setup everything: NATS, KEDA, namespace, and NATS streams/consumers
./k8s/setup-scripts/setup-all.sh
```

### 2. Configure Secrets

```bash
# Copy and edit the env template
cp k8s/.env.template k8s/.env
# Edit k8s/.env with your R2 credentials
```

### 3. Build and Deploy Jobs

```bash
# Build all images
make build-all

# Push to registry
make push-all

# Deploy services
kubectl apply -f jobs/image-download/service.yaml
kubectl apply -f jobs/image-resize/service.yaml
```

### 4. Test the Event Flow

```bash
# Send an image-download event via NATS CLI
nats -s localhost:4222 pub image-download '{"url":"https://picsum.photos/2000/1000"}'

# Watch logs
kubectl logs -l app=image-download -n keda-jobs-prod -f
kubectl logs -l app=image-resize -n keda-jobs-prod -f
```

Expected flow:
1. `image-download` message received by image-download job
2. image-download downloads image, uploads to R2 `images/`, publishes `image-downloaded`
3. image-resize receives `image-downloaded`, resizes to max 200px, uploads to R2 `images_resized/`

## Repository Structure

```
keda-jobs/
├── .github/
│   └── workflows/
│       └── ci.yml                  # Build & deploy changed jobs
├── k8s/
│   ├── kustomize/
│   │   ├── base/                   # Shared manifests (namespace, rbac)
│   │   └── overlays/prod/          # Production overlay
│   ├── setup-scripts/              # Setup/teardown shell scripts
│   ├── manual/prod/
│   │   └── r2-secret.yaml.tpl      # R2 secret template (envsubst)
│   ├── nats/                       # NATS StatefulSet + JetStream
│   ├── monitoring/                 # ServiceMonitors, Grafana dashboards
│   └── Makefile                    # Utility targets
├── jobs/
│   ├── nats-streams-config.sh      # NATS stream/consumer setup
│   ├── image-download/             # Downloads images, uploads to R2
│   └── image-resize/               # Resizes images to max 200px
├── shared-py/                      # Shared Python package
├── Makefile
└── README.md
```

## Adding New Jobs

See `CLAUDE.md` for detailed instructions and templates.

## CI/CD

The GitHub Actions workflow automatically:
- Detects which jobs have changed (via `atas/actions/changed-dirs`)
- Runs shared-py tests
- Builds and pushes Docker images to GHCR
- Deploys to Kubernetes on main branch merges

## Dead Letter Queue

Messages that fail all retry attempts (15 deliveries with linear backoff over ~3 days) are published to the `dead-letter` subject in the `keda-jobs-events` stream and acked so they don't block the consumer.

```bash
# View dead-letter messages
nats -s localhost:4222 stream view keda-jobs-events --subject dead-letter

# Check how many dead-letter messages exist
nats -s localhost:4222 stream info keda-jobs-events --subjects

# Replay a dead-letter message (re-publish to original subject)
nats -s localhost:4222 stream get keda-jobs-events --subject dead-letter --seq <seq_number> | jq -r '.data' | nats -s localhost:4222 pub <original-subject>
```

Each dead-letter message contains:
```json
{
  "subject": "image-download",
  "data": { "url": "https://..." },
  "num_delivered": 15
}
```

## Troubleshooting

```bash
# Check component status
cd k8s && make status

# Check NATS
kubectl logs -n nats nats-0

# List JetStream streams
nats -s localhost:4222 stream ls

# Check consumer lag
nats -s localhost:4222 consumer info keda-jobs-events image-download-consumer

# Check job logs
kubectl logs -l app=image-download -n keda-jobs-prod
kubectl logs -l app=image-resize -n keda-jobs-prod

# Check KEDA operator
kubectl logs -n keda -l app=keda-operator

# Check scaled objects
kubectl get scaledobjects -n keda-jobs-prod
```
