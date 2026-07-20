# Validation Record

Validation performed on 20 July 2026 after the prerequisite/conflict audit and existing-cluster inventory correction.

## Automated tests

```text
9 passed
```

Covered:

- Health endpoint.
- Application preflight endpoint and blocker/warning reporting.
- Secret values not exposed by settings endpoint.
- Normal chat allowed in demo guard mode.
- Prompt-injection request blocked.
- Vulnerable scanner endpoint discloses synthetic test content.
- Protected scanner endpoint blocks the same test.
- Clean file classification.
- EICAR quarantine classification.
- Scanner token validation and prompt extraction.

## Static validation

- All shell scripts, including the new read-only `cluster-inventory.sh`, passed `bash -n` syntax validation.
- Frontend JavaScript passed `node --check`.
- Python source passed byte-code compilation.
- Helm values and Chart metadata parsed as valid YAML.
- The complete EICAR test signature is not stored as a static project/container file.

## Runtime smoke test

Validated with a fresh Uvicorn process and isolated temporary data directory on localhost:

- `/healthz` returned HTTP 200.
- `/api/health` returned HTTP 200.
- `/api/preflight` returned `ready=true` in local demo mode and clearly identified fallback warnings.
- `/api/settings` returned non-secret configuration only.
- Normal chat returned `status=allowed`.
- Prompt injection returned `status=blocked`.
- Vulnerable OpenAI-compatible endpoint returned the intentional synthetic system-prompt weakness.
- Protected endpoint returned HTTP 400 for the same system-prompt extraction attempt.
- Clean test file returned `status=clean`.
- Runtime-generated EICAR test file returned `status=quarantined` with `demoFallback=true`.

## Helm validation status

The chart source and values were inspected and YAML-validated. The resource fullname helper was corrected to use standard Helm release-aware naming, reducing cross-release name collisions. The chart also contains a render-time guard that rejects `ReadWriteOnce` persistence when multi-replica or HPA scaling is enabled.

A real `helm lint`/`helm template` execution was **not** possible in this sandbox because the Helm binary is unavailable and the sandbox cannot download external binaries directly. The included `scripts/preflight-check.sh` runs `helm lint` automatically on the deployment workstation and treats a lint failure as a blocker.

## Not validated in this environment

- Live calls to a customer TrendAI Vision One tenant, because no tenant credentials were placed in the build environment.
- Container image build/push and registry admission, because a Docker/Podman daemon and registry credentials were unavailable.
- Actual deployment to the user's Kubernetes cluster, because no kubeconfig/current context was available.
- Worker-node image pull, Ingress routing, DNS, certificate chain, proxy behavior, NetworkPolicy enforcement, and external TMAS reachability.

These are intentionally covered first by the read-only `scripts/cluster-inventory.sh`, then by `scripts/preflight-check.sh --active-network`, the cluster checks, and the deployment validation procedure. Deployment should not proceed while the preflight summary reports `FAIL>0`.

## Hosted-only configuration

- AI Guard endpoint is derived exclusively from `TMV1_REGION`.
- No `TMV1_AI_GUARD_BASE_URL` override is exposed.
- No `trend-ai-security` namespace or self-hosted AI Guard service is required.
