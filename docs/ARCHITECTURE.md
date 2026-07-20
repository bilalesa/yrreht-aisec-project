# Architecture

## Component view

```text
Browser
  |
  | HTTPS
  v
Ingress / Load Balancer
  |
  v
VisionOne Bank Demo (FastAPI, Kubernetes)
  |-- Static dashboard and demo controls
  |-- /api/chat
  |-- /api/ai/vulnerable/v1/chat/completions
  |-- /api/ai/protected/v1/chat/completions
  |-- /api/files/scan
  |
  +--> TrendAI Vision One AI Guard API
  |      - prompt inspection
  |      - response inspection
  |
  +--> OpenAI-compatible LLM endpoint (optional)
  |      - otherwise the app uses a deterministic synthetic model
  |
  +--> TrendAI Vision One File Security SDK service
  |      - synchronous scan result
  |      - clean or quarantine path on PVC
  |
  +--> Monitored S3 bucket (optional File Security Storage mode)

TMAS / AI Scanner CLI
  |
  +--> vulnerable endpoint (baseline scan)
  +--> protected endpoint  (post-AI Guard validation scan)
  |
  +--> results displayed in TrendAI Vision One
```

## AI Guard request path

```text
User prompt
  -> AI Guard applyGuardrails (input)
     -> blocked: return a controlled error
     -> allowed/redacted: send safe prompt to LLM
        -> LLM response
           -> AI Guard applyGuardrails (OpenAI response type)
              -> blocked: suppress response
              -> allowed/redacted: return safe content to browser
```

The application sends the Vision One bearer token only from the backend. It is never returned by `/api/settings` and is never embedded in JavaScript.

## AI Scanner target behavior

The vulnerable endpoint intentionally exposes synthetic weaknesses such as system-prompt leakage and dummy sensitive-data disclosure. The protected endpoint runs the same synthetic model through AI Guard before and after the LLM call.

This gives the presenter a clear sequence:

1. Assess baseline risk.
2. Enable or tune AI Guard.
3. Re-run the same AI Scanner assessment.
4. Compare successful attacks versus blocked attempts.

## File Security paths

### SDK mode

```text
Upload -> temporary file -> Vision One File Security SDK
  -> clean      -> PVC /data/clean
  -> malicious  -> PVC /data/quarantine
```

### Storage mode

```text
Upload -> monitored S3 incoming prefix -> File Security Storage scanning
                                      -> asynchronous result in Scan Activity
```

The demo app only submits the object in Storage mode; it does not fabricate an immediate malware verdict.

## Kubernetes resources

- Deployment, non-root container, read-only root filesystem.
- ClusterIP Service.
- Ingress with optional TLS.
- ConfigMap for non-secret configuration.
- Kubernetes Secret or external secret reference for credentials.
- PVC for clean/quarantine demo evidence.
- Optional HPA and NetworkPolicy.
