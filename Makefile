.PHONY: build push deploy-local logs help

# Default job to operate on
JOB ?= image-download

# Registry settings
REGISTRY ?= ghcr.io/atas
TAG ?= latest

# Build a job image (for linux/amd64 - compatible with most k8s clusters)
build:
	docker build --platform linux/amd64 -t $(REGISTRY)/keda-jobs-$(JOB):$(TAG) -f ./jobs/$(JOB)/Dockerfile .

# Push a job image
push:
	docker push $(REGISTRY)/keda-jobs-$(JOB):$(TAG)

# Build and push
build-push: build push

# Build all jobs
build-all:
	$(MAKE) build JOB=image-download
	$(MAKE) build JOB=image-resize

# Push all jobs
push-all:
	$(MAKE) push JOB=image-download
	$(MAKE) push JOB=image-resize

# Restart deployment with latest image
deploy-local:
	kubectl rollout restart deployment/$(JOB) -n keda-jobs-prod

# Watch logs for a job
logs:
	kubectl logs -l app=$(JOB) -n keda-jobs-prod -f --tail=100

# Watch logs for all jobs
logs-all:
	kubectl logs -l app -n keda-jobs-prod -f --tail=100

# Help
help:
	@echo "keda-jobs - Event-driven job execution platform"
	@echo ""
	@echo "Usage: make [target] [JOB=image-download|image-resize]"
	@echo ""
	@echo "Build targets:"
	@echo "  build          Build Docker image for JOB (default: image-download)"
	@echo "  push           Push Docker image for JOB"
	@echo "  build-push     Build and push image for JOB"
	@echo "  build-all      Build all job images"
	@echo "  push-all       Push all job images"
	@echo ""
	@echo "Deploy targets:"
	@echo "  deploy-local   Restart deployment to pick up latest image"
	@echo ""
	@echo "Debug targets:"
	@echo "  logs           Watch logs for JOB"
	@echo "  logs-all       Watch logs for all jobs"
	@echo ""
	@echo "Examples:"
	@echo "  make build JOB=image-download"
	@echo "  make push JOB=image-resize TAG=v1.0.0"
	@echo "  make logs JOB=image-download"
