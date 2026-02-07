.PHONY: help deploy-services status diff-prod port-forward-nats
.DEFAULT_GOAL := help

## help: Show this help message
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup/teardown scripts are in setup-scripts/. Run them directly:"
	@echo "  ./setup-scripts/setup-all.sh    Setup everything"
	@echo "  ./setup-scripts/clean-all.sh    Tear down everything"
	@echo ""
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'

## deploy-services: Deploy all job services
deploy-services:
	@echo "Deploying services..."
	kubectl apply -f ../jobs/image-download/service.yaml
	kubectl apply -f ../jobs/image-resize/service.yaml
	@echo "Services deployed!"

## status: Show status of all components
status:
	@echo "=== NATS ==="
	kubectl get pods -n nats
	@echo ""
	@echo "=== KEDA ==="
	kubectl get pods -n keda
	@echo ""
	@echo "=== Deployments ==="
	kubectl get deployments -n keda-jobs-prod
	@echo ""
	@echo "=== ScaledObjects ==="
	kubectl get scaledobjects -n keda-jobs-prod
	@echo ""
	@echo "=== Pods ==="
	kubectl get pods -n keda-jobs-prod

## diff-prod: Show diff before applying kustomize
diff-prod:
	kubectl diff -k kustomize/overlays/prod || true

## port-forward-nats: Port forward NATS to localhost:4222
port-forward-nats:
	kubectl port-forward -n nats svc/nats 4222:4222
