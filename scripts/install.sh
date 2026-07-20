#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE:?Set IMAGE, for example registry.example.com/security/visionone-bank-demo}"
TAG="${TAG:-1.0.0}"
NAMESPACE="${NAMESPACE:-visionone-demo}"
RELEASE="${RELEASE:-visionone-bank-demo}"
VALUES_FILE="${VALUES_FILE:-helm/visionone-bank-demo/values-trend-id.example.yaml}"

helm upgrade --install "$RELEASE" ./helm/visionone-bank-demo \
  --namespace "$NAMESPACE" \
  --create-namespace \
  -f "$VALUES_FILE" \
  --set image.repository="$IMAGE" \
  --set image.tag="$TAG"

kubectl -n "$NAMESPACE" rollout status "deployment/$RELEASE" --timeout=180s
