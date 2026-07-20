#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-vulnerable}"
TARGET_BASE_URL="${TARGET_BASE_URL:-https://ai-bank.trend-id.top}"
TARGET_TOKEN="${TARGET_TOKEN:-}"
TMAS_REGION="${TMAS_REGION:-ap-southeast-1}"

case "$TARGET" in
  vulnerable|protected) ;;
  *) echo "Usage: $0 vulnerable|protected" >&2; exit 2 ;;
esac

ENDPOINT="${TARGET_BASE_URL%/}/api/ai/$TARGET/v1/chat/completions"

cat <<OUT
AI Scanner target preparation
-----------------------------
Target type: Model Endpoint (OpenAI-compliant)
Endpoint: $ENDPOINT
Model ID: visionone-bank-demo
Authentication: Bearer token${TARGET_TOKEN:+ (TARGET_TOKEN is set)}
Response shape: choices[0].message.content
TMAS command: tmas aiscan llm -i --region=$TMAS_REGION

Use the same objectives, techniques, modifiers, and saved scan configuration for
both vulnerable and protected endpoints so the before/after comparison is fair.
OUT

if [[ -n "$TARGET_TOKEN" ]]; then
  echo
  echo "Connectivity test:"
  curl -fsS "$ENDPOINT" \
    -H "Authorization: Bearer $TARGET_TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"model":"visionone-bank-demo","messages":[{"role":"user","content":"What is my balance?"}]}'
  echo
fi
