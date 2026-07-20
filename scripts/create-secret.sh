#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-visionone-demo}"
SECRET_NAME="${2:-visionone-bank-demo-secrets}"

read -rsp "Trend Vision One AI Guard API key: " TMV1_API_KEY; echo
read -rsp "File Security SDK API key (Enter to reuse AI Guard key): " FILE_SECURITY_API_KEY; echo
read -rsp "Optional external LLM API key: " LLM_API_KEY; echo
read -rsp "AI Scanner target bearer token (Enter to auto-generate): " AI_SCANNER_TARGET_TOKEN; echo

FILE_SECURITY_API_KEY="${FILE_SECURITY_API_KEY:-$TMV1_API_KEY}"
AI_SCANNER_TARGET_TOKEN="${AI_SCANNER_TARGET_TOKEN:-$(openssl rand -hex 32)}"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NAMESPACE" create secret generic "$SECRET_NAME" \
  --from-literal=TMV1_API_KEY="$TMV1_API_KEY" \
  --from-literal=FILE_SECURITY_API_KEY="$FILE_SECURITY_API_KEY" \
  --from-literal=LLM_API_KEY="$LLM_API_KEY" \
  --from-literal=AI_SCANNER_TARGET_TOKEN="$AI_SCANNER_TARGET_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

printf 'Secret %s/%s created or updated.\n' "$NAMESPACE" "$SECRET_NAME"
printf 'AI Scanner target token: %s\n' "$AI_SCANNER_TARGET_TOKEN"
