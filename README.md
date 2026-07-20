# VisionOne Bank Demo

> **Deployment mode:** This package is locked to Trend-hosted AI Guard, Trend-hosted AI Scanner, and the Trend-hosted File Security SDK service. It does not deploy an in-cluster AI Guard service or accept a custom AI Guard endpoint override.

A synthetic digital-banking application built for demonstrating **TrendAI Vision One AI Guard, AI Scanner, and File Security** on Kubernetes.

The application recreates the main demo journey of a modern banking portal without copying the source code or proprietary brand assets of the reference site. It contains fictional accounts and customers only.

## Demo capabilities

- Banking dashboard and C-3PO-style banking assistant.
- AI Guard pre-call inspection before the LLM and post-call inspection before the response reaches the user.
- Two OpenAI-compatible AI Scanner targets:
  - `/api/ai/vulnerable/v1/chat/completions`
  - `/api/ai/protected/v1/chat/completions`
- AI Scanner campaign visualization in the UI for presentation flow.
- File Security SDK upload scanning with clean/quarantine handling.
- Optional File Security Storage handoff to an S3 bucket already monitored by Vision One.
- Local demo fallback for AI Guard and EICAR detection when live credentials are not configured.
- Helm chart with Ingress, TLS, persistent storage, security context, probes, HPA, and optional NetworkPolicy.

## Repository layout

```text
app/                         FastAPI backend and static web UI
helm/visionone-bank-demo/    Kubernetes Helm chart
docs/                        Integration guide, architecture, and demo runbook
scripts/                     Installation, secret, scan, and smoke-test helpers
samples/                     Harmless sample files
tests/                       API tests
```

## Quick local demo

```bash
cp .env.example .env
# Set FORCE_DEMO_MODE=true in .env for a credential-free UI demonstration.
docker compose up --build
```

Open `http://localhost:8080`.

## Quick Kubernetes deployment

**Step 1 is always a read-only inventory of the existing cluster.** Do not create a namespace, Secret, test pod, or Helm release before this passes:

```bash
export NAMESPACE=visionone-demo
export RELEASE=visionone-bank-demo
export HOST=ai-bank.example.com
export INGRESS_CLASS=nginx
export TLS_SECRET=ai-bank-tls
export SECRET_NAME=visionone-bank-demo-secrets

./scripts/cluster-inventory.sh
```

Review the generated report under `/tmp`. Continue only when the result contains no `FAIL`. Then run the requirement preflight:

```bash
./scripts/preflight-check.sh --local-only
./scripts/preflight-check.sh --cluster-only
```

Then build and deploy:

```bash
export IMAGE=registry.example.com/security/visionone-bank-demo
export TAG=1.0.0

docker build -t "$IMAGE:$TAG" .
docker push "$IMAGE:$TAG"

kubectl create namespace visionone-demo
./scripts/create-secret.sh visionone-demo visionone-bank-demo-secrets

helm upgrade --install visionone-bank-demo ./helm/visionone-bank-demo \
  --namespace visionone-demo \
  --set image.repository="$IMAGE" \
  --set image.tag="$TAG" \
  --set secrets.create=false \
  --set secrets.existingSecret=visionone-bank-demo-secrets \
  --set ingress.hosts[0].host=ai-bank.example.com \
  --set ingress.tls[0].hosts[0]=ai-bank.example.com \
  --set config.publicBaseUrl=https://ai-bank.example.com
```

Use `helm/visionone-bank-demo/values-trend-id.example.yaml` as a ready example for the `trend-id.top` DNS zone.

## Documentation

1. Run [`docs/PREREQUISITE_AND_CONFLICT_CHECK.md`](docs/PREREQUISITE_AND_CONFLICT_CHECK.md).
2. Continue with [`docs/VISION_ONE_INTEGRATION.md`](docs/VISION_ONE_INTEGRATION.md).
3. Use [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) during the customer demonstration.
4. Review [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/SECURITY_NOTES.md`](docs/SECURITY_NOTES.md).

## Important behavior

- `FORCE_DEMO_MODE=true` is a visual/local fallback, not evidence of a live Vision One integration.
- `FILE_SECURITY_DEMO_FALLBACK=true` locally detects the EICAR test string if the live SDK is unavailable. The response explicitly marks `demoFallback: true`. Helm defaults it to `false` to avoid accidental live claims.
- The complete EICAR signature is not stored in the container image. Generate it only when needed with `scripts/create-eicar-sample.sh` or the UI button.
- AI Scanner enforcement is not simulated as a product function. The real scanner targets are provided for TMAS assessment; AI Guard supplies runtime enforcement.
- Never use production customer data, real card numbers, or a production LLM account in this demo.
