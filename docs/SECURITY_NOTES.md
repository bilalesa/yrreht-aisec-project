# Security Notes

This application intentionally includes a vulnerable scanner target. Treat it as a demo workload, not a production banking application.

## Required controls

- Use a dedicated namespace and non-production cluster or node pool.
- Protect the public site with authentication, VPN, source-IP restriction, or short-lived access.
- Set `AI_SCANNER_TARGET_TOKEN` and do not expose the target endpoints anonymously.
- Use separate least-privilege API keys and rotate them after customer demonstrations.
- Store credentials in Kubernetes Secret or an external secret manager, not in Git, ConfigMap, or browser local storage.
- Keep `ALLOW_RUNTIME_CONFIG=false` for shared or public environments.
- Keep `AI_GUARD_FALLBACK=block` unless fail-open behavior is explicitly accepted.
- Keep TLS enabled for Ingress and all external API connections.
- Use only EICAR for malware detection tests. Do not upload real malware.
- Do not use real customer data or actual financial identifiers.

## Deliberately vulnerable endpoint

`/api/ai/vulnerable/v1/chat/completions` may disclose a synthetic system prompt and dummy data. Restrict it to the TMAS scanner source and presenter workstation.

For NGINX Ingress, add source restriction annotations or place the app behind an authenticated reverse proxy. A NetworkPolicy alone cannot restrict internet clients after traffic enters the Ingress Controller unless the ingress architecture preserves/enforces source identity.

## Demo fallback flags

- `FORCE_DEMO_MODE=true`: local regex-based AI Guard-like behavior.
- `FILE_SECURITY_DEMO_FALLBACK=true`: local EICAR string detection when SDK is missing or fails.

These flags are designed to prevent an empty demo, but they must never be presented as live Vision One telemetry. Disable both when collecting product validation evidence.

## Logging

The app avoids logging API keys. Review upstream proxy and application debug settings before enabling verbose logs because prompt or response content could contain test data.

## Persistence

Uploaded files are persisted under `/data/clean` or `/data/quarantine`. Define retention and delete test files after the session:

```bash
kubectl -n visionone-demo exec deployment/visionone-bank-demo -- \
  sh -c 'rm -f /data/clean/* /data/quarantine/*'
```
