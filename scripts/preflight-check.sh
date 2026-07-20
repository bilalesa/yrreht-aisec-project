#!/usr/bin/env bash
set -uo pipefail

MODE="full"
ACTIVE_NETWORK_CHECK="${ACTIVE_NETWORK_CHECK:-false}"
for arg in "$@"; do
  case "$arg" in
    --local-only) MODE="local" ;;
    --cluster-only) MODE="cluster" ;;
    --active-network) ACTIVE_NETWORK_CHECK="true" ;;
    -h|--help)
      cat <<'HELP'
Usage: ./scripts/preflight-check.sh [--local-only|--cluster-only] [--active-network]

Environment variables:
  NAMESPACE=visionone-demo
  RELEASE=visionone-bank-demo
  HOST=ai-bank.trend-id.top
  INGRESS_CLASS=nginx
  TLS_SECRET=ai-bank-trend-id-tls
  SECRET_NAME=visionone-bank-demo-secrets
  STORAGE_CLASS=""                 # blank means default StorageClass
  TMV1_REGION=sg
  FILE_SECURITY_REGION=ap-southeast-1
  LLM_CHAT_URL=""                  # optional external LLM URL
  APP_IMAGE=""                     # optional image pull test
  REPLICA_COUNT=1
  AUTOSCALING_ENABLED=false
  AUTOSCALING_MAX=1
  PERSISTENCE_ENABLED=true
  PERSISTENCE_ACCESS_MODE=ReadWriteOnce
  NETWORK_POLICY_ENABLED=false
  NETWORK_TEST_IMAGE=curlimages/curl:8.10.1
HELP
      exit 0
      ;;
    *) printf 'Unknown argument: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

NAMESPACE="${NAMESPACE:-visionone-demo}"
RELEASE="${RELEASE:-visionone-bank-demo}"
HOST="${HOST:-ai-bank.trend-id.top}"
INGRESS_CLASS="${INGRESS_CLASS:-nginx}"
TLS_SECRET="${TLS_SECRET:-ai-bank-trend-id-tls}"
SECRET_NAME="${SECRET_NAME:-visionone-bank-demo-secrets}"
STORAGE_CLASS="${STORAGE_CLASS:-}"
TMV1_REGION="${TMV1_REGION:-sg}"
FILE_SECURITY_REGION="${FILE_SECURITY_REGION:-ap-southeast-1}"
LLM_CHAT_URL="${LLM_CHAT_URL:-}"
APP_IMAGE="${APP_IMAGE:-}"
REPLICA_COUNT="${REPLICA_COUNT:-1}"
AUTOSCALING_ENABLED="${AUTOSCALING_ENABLED:-false}"
AUTOSCALING_MAX="${AUTOSCALING_MAX:-1}"
PERSISTENCE_ENABLED="${PERSISTENCE_ENABLED:-true}"
PERSISTENCE_ACCESS_MODE="${PERSISTENCE_ACCESS_MODE:-ReadWriteOnce}"
NETWORK_POLICY_ENABLED="${NETWORK_POLICY_ENABLED:-false}"
NETWORK_TEST_IMAGE="${NETWORK_TEST_IMAGE:-curlimages/curl:8.10.1}"

PASS=0
WARN=0
FAIL=0
pass() { PASS=$((PASS+1)); printf '[PASS] %s\n' "$*"; }
warn() { WARN=$((WARN+1)); printf '[WARN] %s\n' "$*"; }
fail() { FAIL=$((FAIL+1)); printf '[FAIL] %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
truthy() { case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in 1|true|yes|on) return 0;; *) return 1;; esac; }

printf '\nVisionOne Bank Demo preflight\n'
printf 'Run ./scripts/cluster-inventory.sh first; this preflight is not a substitute for full existing-app inventory.\n'
printf 'Mode=%s Namespace=%s Release=%s Host=%s\n\n' "$MODE" "$NAMESPACE" "$RELEASE" "$HOST"

if [[ "$MODE" != "cluster" ]]; then
  printf '%s\n' '== Local/build requirements =='
  for cmd in bash curl openssl python3; do
    if have "$cmd"; then pass "$cmd is installed"; else fail "$cmd is required"; fi
  done
  if have docker; then
    docker info >/dev/null 2>&1 && pass "Docker daemon is reachable" || fail "Docker CLI exists but daemon is not reachable"
  elif have podman; then
    podman info >/dev/null 2>&1 && pass "Podman is reachable" || fail "Podman exists but is not reachable"
  else
    fail "Docker or Podman is required to build the image"
  fi
  if have helm; then
    pass "Helm is installed: $(helm version --short 2>/dev/null || true)"
    if helm lint ./helm/visionone-bank-demo >/tmp/visionone-bank-demo-helm-lint.log 2>&1; then
      pass "Helm chart lint passed"
    else
      fail "Helm chart lint failed; see /tmp/visionone-bank-demo-helm-lint.log"
    fi
  else
    fail "Helm 3 is required"
  fi
  if have kubectl; then pass "kubectl is installed"; else fail "kubectl is required"; fi
  if have tmas; then pass "TMAS CLI is installed"; else warn "TMAS CLI is not installed yet; required only for live AI Scanner"; fi
  if have jq; then pass "jq is installed"; else warn "jq is optional but recommended for readable API output"; fi

  for path in Dockerfile requirements.txt app/main.py helm/visionone-bank-demo/Chart.yaml scripts/cluster-inventory.sh scripts/create-secret.sh; do
    [[ -f "$path" ]] && pass "Project file exists: $path" || fail "Missing project file: $path"
  done
  if [[ -f app/static/eicar.com.txt ]]; then
    fail "EICAR is embedded in the container build context; this may be blocked by registry malware scanning"
  else
    pass "No static EICAR file is embedded in the application image"
  fi

  if [[ "$PERSISTENCE_ENABLED" == "true" && "$PERSISTENCE_ACCESS_MODE" == "ReadWriteOnce" ]]; then
    if (( REPLICA_COUNT > 1 )) || { truthy "$AUTOSCALING_ENABLED" && (( AUTOSCALING_MAX > 1 )); }; then
      fail "ReadWriteOnce persistence conflicts with multi-replica/HPA; use one replica or an RWX volume"
    else
      pass "Replica and RWO persistence settings are compatible"
    fi
  fi
  printf '\n'
fi

if [[ "$MODE" != "local" ]]; then
  printf '%s\n' '== Kubernetes/cluster requirements and conflicts =='
  if ! have kubectl; then
    fail "kubectl is unavailable; cluster checks skipped"
  elif ! kubectl version --request-timeout=10s >/dev/null 2>&1; then
    fail "Cannot reach the Kubernetes API using the current context"
  else
    context="$(kubectl config current-context 2>/dev/null || true)"
    pass "Kubernetes API reachable; current context: ${context:-unknown}"

    if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
      pass "Namespace $NAMESPACE exists"
    else
      warn "Namespace $NAMESPACE does not exist yet; install script can create it"
    fi

    declare -a permissions=(
      "create deployments.apps" "create services" "create configmaps" "create secrets"
      "create serviceaccounts" "create persistentvolumeclaims" "create ingresses.networking.k8s.io"
      "create networkpolicies.networking.k8s.io" "create horizontalpodautoscalers.autoscaling"
    )
    for item in "${permissions[@]}"; do
      verb="${item%% *}"; resource="${item#* }"
      if kubectl auth can-i "$verb" "$resource" -n "$NAMESPACE" 2>/dev/null | grep -qx yes; then
        pass "RBAC permits $verb $resource in $NAMESPACE"
      else
        fail "RBAC does not permit $verb $resource in $NAMESPACE"
      fi
    done

    if kubectl get ingressclass "$INGRESS_CLASS" >/dev/null 2>&1; then
      pass "IngressClass $INGRESS_CLASS exists"
    else
      classes="$(kubectl get ingressclass -o name 2>/dev/null | tr '\n' ' ' || true)"
      fail "IngressClass $INGRESS_CLASS not found. Available: ${classes:-none}"
    fi

    ingress_rows="$(kubectl get ingress -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .spec.rules[*]}{.host}{" "}{end}{"\n"}{end}' 2>/dev/null || true)"
    host_conflicts="$(printf '%s\n' "$ingress_rows" | awk -v h="$HOST" '$0 ~ h {print}' || true)"
    if [[ -n "$host_conflicts" ]]; then
      if printf '%s\n' "$host_conflicts" | grep -qE "^${NAMESPACE}[[:space:]]+${RELEASE}[[:space:]]"; then
        warn "Host $HOST is already used by this release; deployment will be an upgrade"
      else
        fail "Host $HOST is already used by another Ingress: $host_conflicts"
      fi
    else
      pass "No existing Ingress host conflict for $HOST"
    fi

    if have helm && helm status "$RELEASE" -n "$NAMESPACE" >/dev/null 2>&1; then
      warn "Helm release $RELEASE already exists in $NAMESPACE; review values before upgrading"
    else
      pass "No conflicting Helm release named $RELEASE was detected"
    fi

    if kubectl -n "$NAMESPACE" get secret "$SECRET_NAME" >/dev/null 2>&1; then
      pass "Secret $NAMESPACE/$SECRET_NAME exists"
      for key in TMV1_API_KEY FILE_SECURITY_API_KEY AI_SCANNER_TARGET_TOKEN; do
        value="$(kubectl -n "$NAMESPACE" get secret "$SECRET_NAME" -o "jsonpath={.data.${key}}" 2>/dev/null || true)"
        [[ -n "$value" ]] && pass "Secret key $key is present" || fail "Secret key $key is missing or empty"
      done
    else
      warn "Secret $NAMESPACE/$SECRET_NAME does not exist yet; run scripts/create-secret.sh"
    fi

    if [[ -n "$TLS_SECRET" ]] && kubectl -n "$NAMESPACE" get secret "$TLS_SECRET" >/dev/null 2>&1; then
      tls_type="$(kubectl -n "$NAMESPACE" get secret "$TLS_SECRET" -o jsonpath='{.type}' 2>/dev/null || true)"
      [[ "$tls_type" == "kubernetes.io/tls" ]] && pass "TLS secret $TLS_SECRET exists and has TLS type" || warn "Secret $TLS_SECRET exists but type is $tls_type"
    elif kubectl api-resources 2>/dev/null | grep -q '^certificates[[:space:]].*cert-manager.io'; then
      warn "TLS secret $TLS_SECRET is missing; cert-manager exists, but this chart needs a Certificate resource or issuer annotation"
    else
      warn "TLS secret $TLS_SECRET is missing and cert-manager was not detected"
    fi

    if truthy "$PERSISTENCE_ENABLED"; then
      if [[ -n "$STORAGE_CLASS" ]]; then
        kubectl get storageclass "$STORAGE_CLASS" >/dev/null 2>&1 && pass "StorageClass $STORAGE_CLASS exists" || fail "StorageClass $STORAGE_CLASS does not exist"
      else
        default_sc="$(kubectl get storageclass -o jsonpath='{range .items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")]}{.metadata.name}{" "}{end}' 2>/dev/null || true)"
        [[ -n "$default_sc" ]] && pass "Default StorageClass detected: $default_sc" || fail "No default StorageClass detected; set persistence.storageClass explicitly"
      fi
    else
      pass "Persistence is disabled; StorageClass is not required"
    fi

    if truthy "$AUTOSCALING_ENABLED"; then
      if kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes >/dev/null 2>&1; then
        pass "Metrics API is available for HPA"
      else
        fail "HPA is enabled but metrics.k8s.io is unavailable"
      fi
    fi

    psa="$(kubectl get ns "$NAMESPACE" -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/enforce}' 2>/dev/null || true)"
    [[ -n "$psa" ]] && pass "Namespace Pod Security enforce level: $psa" || warn "Namespace has no Pod Security enforce label"

    if truthy "$NETWORK_POLICY_ENABLED"; then
      cni="$(kubectl get pods -A -o name 2>/dev/null | grep -Ei 'calico|cilium|antrea|weave|kube-router' | head -n 1 || true)"
      [[ -n "$cni" ]] && pass "A known NetworkPolicy-capable CNI was detected: $cni" || warn "Could not identify the CNI; verify NetworkPolicy enforcement manually"
      if [[ -n "$LLM_CHAT_URL" ]] && [[ "$LLM_CHAT_URL" =~ ^https?://(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.) ]]; then
        warn "Private LLM URL plus NetworkPolicy requires explicit private-CIDR egress rules"
      fi
    fi

    if truthy "$ACTIVE_NETWORK_CHECK"; then
      case "$TMV1_REGION" in
        us) guard_host="api.xdr.trendmicro.com" ;;
        eu) guard_host="api.eu.xdr.trendmicro.com" ;;
        jp) guard_host="api.xdr.trendmicro.co.jp" ;;
        au) guard_host="api.au.xdr.trendmicro.com" ;;
        in) guard_host="api.in.xdr.trendmicro.com" ;;
        sg) guard_host="api.sg.xdr.trendmicro.com" ;;
        mea) guard_host="api.mea.xdr.trendmicro.com" ;;
        *) guard_host="api.${TMV1_REGION}.xdr.trendmicro.com" ;;
      esac
      guard_url="https://${guard_host}/v3.0/aiSecurity/applyGuardrails"
      urls="$guard_url"
      [[ -n "$LLM_CHAT_URL" ]] && urls="$urls $LLM_CHAT_URL"

      warn "File Security raw-host connectivity check skipped; live connectivity will be validated through the File Security SDK using region ${FILE_SECURITY_REGION}"
      pod_name="${RELEASE}-preflight-$RANDOM"
      if kubectl -n "$NAMESPACE" run "$pod_name" --rm -i --restart=Never --image="$NETWORK_TEST_IMAGE" \
        --command -- sh -c 'for url in "$@"; do echo "Testing $url"; curl -kSs --connect-timeout 10 --max-time 20 -o /dev/null -w "HTTP %{http_code}\n" "$url" || exit 1; done' sh $urls; then
        pass "Active pod DNS/TLS connectivity checks passed"
      else
        fail "Active pod network check failed; inspect DNS, proxy, firewall, CA trust, and NetworkPolicy"
      fi

      if [[ -n "$APP_IMAGE" ]]; then
        image_pod="${RELEASE}-imagecheck-$RANDOM"
        kubectl -n "$NAMESPACE" delete pod "$image_pod" --ignore-not-found >/dev/null 2>&1 || true
        if kubectl -n "$NAMESPACE" run "$image_pod" --restart=Never --image="$APP_IMAGE" --command -- /bin/true >/dev/null 2>&1 \
          && kubectl -n "$NAMESPACE" wait --for=jsonpath='{.status.phase}'=Succeeded "pod/$image_pod" --timeout=120s >/dev/null 2>&1; then
          pass "Worker node can pull APP_IMAGE=$APP_IMAGE"
        else
          fail "Worker node could not pull or start APP_IMAGE=$APP_IMAGE"
          kubectl -n "$NAMESPACE" describe pod "$image_pod" 2>/dev/null | tail -n 40 || true
        fi
        kubectl -n "$NAMESPACE" delete pod "$image_pod" --ignore-not-found >/dev/null 2>&1 || true
      fi
    else
      warn "Active in-cluster DNS/TLS tests were skipped; rerun with --active-network before the demo"
    fi
  fi
  printf '\n'
fi

printf 'Summary: PASS=%d WARN=%d FAIL=%d\n' "$PASS" "$WARN" "$FAIL"
if (( FAIL > 0 )); then
  printf 'Preflight result: NOT READY\n'
  exit 2
fi
printf 'Preflight result: READY WITH %d WARNING(S)\n' "$WARN"
