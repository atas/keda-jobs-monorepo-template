name: CI/CD

on:
    workflow_dispatch: # Manual trigger from UI
    push:
        branches: [main]
        paths:
            - "jobs/**"
            - "shared-py/**"
            - ".github/workflows/ci.yml"
    pull_request:
        branches: [main]
        paths:
            - "jobs/**"
            - "shared-py/**"
            - ".github/workflows/ci.yml"

env:
    REGISTRY: ghcr.io
    IMAGE_PREFIX: ${{ github.repository_owner }}/keda-jobs

jobs:
    # Detect which jobs have changed
    changed_dirs:
        runs-on: ubuntu-latest
        permissions:
            contents: read
            pull-requests: read
        outputs:
            dirs: ${{ steps.changed_dirs.outputs.dirs }}
        steps:
            - uses: actions/checkout@v4

            - uses: atas/actions/changed-dirs@main
              id: changed_dirs
              with:
                  path: jobs
                  trigger_all: shared-py

    # Test shared package
    test_shared:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v4
            - uses: actions/setup-python@v5
              with:
                  python-version: "3.12"
            - uses: astral-sh/setup-uv@v5
            - run: uv pip install --system ./shared-py[test]
            - run: pytest shared-py/tests/ -v

    # Build and push changed job images
    build:
        needs: [changed_dirs, test_shared]
        if: ${{ needs.changed_dirs.outputs.dirs != '[]' }}
        runs-on: ubuntu-latest
        strategy:
            matrix:
                dir: ${{ fromJson(needs.changed_dirs.outputs.dirs) }}
        permissions:
            contents: read
            packages: write

        steps:
            - uses: actions/checkout@v4

            - name: Set up Docker Buildx
              uses: docker/setup-buildx-action@v3

            - name: Log in to Container Registry
              uses: docker/login-action@v3
              with:
                  registry: ${{ env.REGISTRY }}
                  username: ${{ github.actor }}
                  password: ${{ secrets.GITHUB_TOKEN }}

            - name: Extract metadata
              id: meta
              uses: docker/metadata-action@v5
              with:
                  images: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.dir }}
                  tags: |
                      type=sha,prefix=
                      type=raw,value=latest,enable={{is_default_branch}}
                      type=ref,event=pr

            - name: Run tests
              uses: docker/build-push-action@v5
              with:
                  context: .
                  file: ./jobs/${{ matrix.dir }}/Dockerfile
                  target: test
                  push: false
                  cache-from: type=gha
                  cache-to: type=gha,mode=max

            - name: Build and push
              uses: docker/build-push-action@v5
              with:
                  context: .
                  file: ./jobs/${{ matrix.dir }}/Dockerfile
                  target: production
                  push: ${{ github.ref == 'refs/heads/main' }}
                  tags: ${{ steps.meta.outputs.tags }}
                  labels: ${{ steps.meta.outputs.labels }}
                  cache-from: type=gha
                  cache-to: type=gha,mode=max

    # Deploy to Kubernetes (only on main branch)
    deploy:
        needs: [changed_dirs, build]
        if: github.ref == 'refs/heads/main' && needs.changed_dirs.outputs.dirs != '[]'
        runs-on: ubuntu-latest
        strategy:
            matrix:
                dir: ${{ fromJson(needs.changed_dirs.outputs.dirs) }}

        steps:
            - uses: actions/checkout@v4

            - name: Get short SHA
              id: sha
              run: echo "short=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

            - name: Update image tag in manifest
              run: |
                  sed -i "s|image: ghcr.io/atas/keda-jobs-${{ matrix.dir }}:.*|image: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.dir }}:${{ steps.sha.outputs.short }}|" \
                    jobs/${{ matrix.dir }}/service.yaml

            - name: Deploy service
              run: |
                  kubectl --server=${{ secrets.K8S_SERVER }} --token=${{ secrets.K8S_TOKEN }} --insecure-skip-tls-verify \
                    apply --validate=false -f jobs/${{ matrix.dir }}/service.yaml

            - name: Wait for rollout
              run: |
                  kubectl --server=${{ secrets.K8S_SERVER }} --token=${{ secrets.K8S_TOKEN }} --insecure-skip-tls-verify \
                    rollout status deployment/${{ matrix.dir }} -n keda-jobs-prod --timeout=120s
