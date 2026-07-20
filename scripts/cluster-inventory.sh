#!/usr/bin/env bash
set -uo pipefail

# Read-only Kubernetes inventory and collision assessment.
# This script never creates, patches, or deletes cluster resources.

NAMESPACE="${NAMESPACE:-visionone-demo}"
RELEASE="${RELEASE:-visionone-bank-demo}"
CHART_NAME="${CHART_NAME:-visionone-bank-demo}"
NAME_OVERRIDE="${NAME_OVERRIDE:-}"
FULLNAME_OVERRIDE="${FULLNAME_OVERRIDE:-}"
HOST="${HOST:-ai-bank.trend-id.top}"
INGRESS_CLASS="${INGRESS_CLASS:-nginx}"
TLS_SECRET="${TLS_SECRET:-ai-bank-trend-id-tls}"
SECRET_NAME="${SECRET_NAME:-visionone-bank-demo-secrets}"
SERVICE_ACCOUNT_CREATE="${SERVICE_ACCOUNT_CREATE:-true}"
PERSISTENCE_ENABLED="${PERSISTENCE_ENABLED:-true}"
INGRESS_ENABLED="${INGRESS_ENABLED:-true}"
AUTOSCALING_ENABLED="${AUTOSCALING_ENABLED:-false}"
NETWORK_POLICY_ENABLED="${NETWORK_POLICY_ENABLED:-false}"
REPORT_FILE="${REPORT_FILE:-/tmp/visionone-bank-demo-cluster-inventory-$(date +%Y%m%d-%H%M%S).txt}"

if [[ -n "$FULLNAME_OVERRIDE" ]]; then
  RESOURCE_NAME="$FULLNAME_OVERRIDE"
else
  base_name="${NAME_OVERRIDE:-$CHART_NAME}"
  if [[ "$RELEASE" == *"$base_name"* ]]; then
    RESOURCE_NAME="$RELEASE"
  else
    RESOURCE_NAME="${RELEASE}-${base_name}"
  fi
fi
RESOURCE_NAME="${RESOURCE_NAME:0:63}"
RESOURCE_NAME="${RESOURCE_NAME%-}"

PASS=0
WARN=0
FAIL=0
pass() { PASS=$((PASS+1)); printf '[PASS] %s\n' "$*"; }
warn() { WARN=$((WARN+1)); printf '[WARN] %s\n' "$*"; }
fail() { FAIL=$((FAIL+1)); printf '[FAIL] %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
section() { printf '\n===== %s =====\n' "$*"; }

check_owned_resource() {
  local kind="$1" name="$2"
  if ! kubectl -n "$NAMESPACE" get "$kind" "$name" >/dev/null 2>&1; then
    pass "No existing $kind named $NAMESPACE/$name"
    return
  fi

  local owner managed_by
  owner="$(kubectl -n "$NAMESPACE" get "$kind" "$name" -o jsonpath='{.metadata.annotations.meta\.helm\.sh/release-name}' 2>/dev/null || true)"
  managed_by="$(kubectl -n "$NAMESPACE" get "$kind" "$name" -o jsonpath='{.metadata.labels.app\.kubernetes\.io/managed-by}' 2>/dev/null || true)"

  if [[ "$owner" == "$RELEASE" && "$managed_by" == "Helm" ]]; then
    warn "$kind $NAMESPACE/$name already belongs to Helm release $RELEASE; treat deployment as an upgrade"
  else
    fail "$kind $NAMESPACE/$name already exists and is not owned by Helm release $RELEASE (owner=${owner:-none}, managed-by=${managed_by:-none})"
  fi
}

main() {
  printf 'VisionOne Bank Demo — READ-ONLY cluster inventory\n'
  printf 'Namespace=%s Release=%s ResourceName=%s Host=%s\n' "$NAMESPACE" "$RELEASE" "$RESOURCE_NAME" "$HOST"
  printf 'Report=%s\n' "$REPORT_FILE"

  section "Safety and context"
  if ! have kubectl; then
    fail "kubectl is not installed"
    return
  fi
  if ! kubectl version --request-timeout=10s >/dev/null 2>&1; then
    fail "Cannot reach Kubernetes API using the current kubeconfig context"
    return
  fi
  context="$(kubectl config current-context 2>/dev/null || true)"
  cluster_server="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true)"
  pass "Kubernetes API reachable"
  printf 'Current context: %s\nAPI server: %s\n' "${context:-unknown}" "${cluster_server:-unknown}"
  warn "Confirm this is the intended non-production/demo cluster before continuing"

  section "Cluster nodes and capacity"
  kubectl get nodes -o wide 2>/dev/null || true
  if kubectl top nodes >/dev/null 2>&1; then
    printf '\nCurrent node utilization:\n'
    kubectl top nodes 2>/dev/null || true
  else
    warn "kubectl top nodes unavailable; Metrics Server may be absent or access may be restricted"
  fi

  section "Existing applications — cluster wide"
  printf '%s\n' '-- Deployments / StatefulSets / DaemonSets --'
  kubectl get deployments.apps,statefulsets.apps,daemonsets.apps -A -o wide 2>/dev/null || true
  printf '\n%s\n' '-- Services --'
  kubectl get services -A -o wide 2>/dev/null || true
  printf '\n%s\n' '-- Ingresses --'
  kubectl get ingresses.networking.k8s.io -A -o wide 2>/dev/null || true
  if have helm; then
    printf '\n%s\n' '-- Helm releases --'
    helm list -A 2>/dev/null || warn "Helm exists but releases could not be listed"
  else
    warn "Helm is not installed locally; Helm ownership is still checked from Kubernetes metadata where possible"
  fi

  section "Target namespace inventory"
  if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
    pass "Namespace $NAMESPACE already exists"
    kubectl get namespace "$NAMESPACE" --show-labels 2>/dev/null || true
    printf '\nResources currently in %s:\n' "$NAMESPACE"
    kubectl -n "$NAMESPACE" get deployments.apps,statefulsets.apps,daemonsets.apps,pods,services,ingresses.networking.k8s.io,persistentvolumeclaims,configmaps,secrets,serviceaccounts,horizontalpodautoscalers.autoscaling,networkpolicies.networking.k8s.io 2>/dev/null || true
  else
    pass "Namespace $NAMESPACE does not exist; a dedicated namespace can be created"
  fi

  section "Exact resource-name collision check"
  # These names are rendered by the Helm chart for the selected release/name overrides.
  for kind in deployment.apps service configmap; do
    check_owned_resource "$kind" "$RESOURCE_NAME"
  done
  [[ "$PERSISTENCE_ENABLED" == "true" ]] && check_owned_resource persistentvolumeclaim "$RESOURCE_NAME"
  [[ "$INGRESS_ENABLED" == "true" ]] && check_owned_resource ingress.networking.k8s.io "$RESOURCE_NAME"
  [[ "$SERVICE_ACCOUNT_CREATE" == "true" ]] && check_owned_resource serviceaccount "$RESOURCE_NAME"
  [[ "$AUTOSCALING_ENABLED" == "true" ]] && check_owned_resource horizontalpodautoscaler.autoscaling "$RESOURCE_NAME"
  [[ "$NETWORK_POLICY_ENABLED" == "true" ]] && check_owned_resource networkpolicy.networking.k8s.io "$RESOURCE_NAME"

  if kubectl -n "$NAMESPACE" get secret "$SECRET_NAME" >/dev/null 2>&1; then
    warn "Application Secret $NAMESPACE/$SECRET_NAME already exists; confirm it is intended for this demo and do not overwrite blindly"
  else
    pass "No existing application Secret named $NAMESPACE/$SECRET_NAME"
  fi
  if [[ -n "$TLS_SECRET" ]] && kubectl -n "$NAMESPACE" get secret "$TLS_SECRET" >/dev/null 2>&1; then
    tls_type="$(kubectl -n "$NAMESPACE" get secret "$TLS_SECRET" -o jsonpath='{.type}' 2>/dev/null || true)"
    if [[ "$tls_type" == "kubernetes.io/tls" ]]; then
      warn "TLS Secret $NAMESPACE/$TLS_SECRET already exists; verify its certificate SAN contains $HOST"
    else
      fail "Object $NAMESPACE/$TLS_SECRET exists but is not a kubernetes.io/tls Secret (type=${tls_type:-unknown})"
    fi
  else
    pass "No conflicting TLS Secret named $NAMESPACE/$TLS_SECRET"
  fi

  section "Ingress and hostname collision check"
  if kubectl get ingressclass "$INGRESS_CLASS" >/dev/null 2>&1; then
    pass "IngressClass $INGRESS_CLASS exists"
  else
    classes="$(kubectl get ingressclass -o name 2>/dev/null | tr '\n' ' ' || true)"
    fail "IngressClass $INGRESS_CLASS not found; available=${classes:-none}"
  fi

  host_rows="$(kubectl get ingress -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .spec.rules[*]}{.host}{" "}{end}{"\n"}{end}' 2>/dev/null || true)"
  host_conflicts="$(printf '%s\n' "$host_rows" | awk -v h="$HOST" '{for(i=3;i<=NF;i++) if($i==h) print $0}' || true)"
  if [[ -z "$host_conflicts" ]]; then
    pass "Hostname $HOST is not used by another Ingress"
  elif printf '%s\n' "$host_conflicts" | grep -qE "^${NAMESPACE}[[:space:]]+${RESOURCE_NAME}[[:space:]]"; then
    warn "Hostname $HOST is already attached to this chart resource; this appears to be an upgrade"
  else
    fail "Hostname $HOST is already used: $host_conflicts"
  fi

  section "Namespace policy, quota, and admission controls"
  if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
    psa="$(kubectl get ns "$NAMESPACE" -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/enforce}' 2>/dev/null || true)"
    printf 'Pod Security enforce level: %s\n' "${psa:-not-set}"
    printf '\nResourceQuota:\n'
    kubectl -n "$NAMESPACE" get resourcequota 2>/dev/null || true
    printf '\nLimitRange:\n'
    kubectl -n "$NAMESPACE" get limitrange 2>/dev/null || true
    printf '\nNetworkPolicy:\n'
    kubectl -n "$NAMESPACE" get networkpolicy -o wide 2>/dev/null || true
    np_count="$(kubectl -n "$NAMESPACE" get networkpolicy --no-headers 2>/dev/null | wc -l | tr -d ' ' || true)"
    if [[ "${np_count:-0}" != "0" ]]; then
      warn "$np_count NetworkPolicy object(s) already exist in $NAMESPACE; verify ingress from the controller and egress to Vision One/File Security"
    else
      pass "No existing NetworkPolicy in $NAMESPACE"
    fi
  fi

  policy_engines="$(kubectl get pods -A -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name' --no-headers 2>/dev/null | grep -Ei 'kyverno|gatekeeper|opa-|admission|policy-controller' || true)"
  if [[ -n "$policy_engines" ]]; then
    warn "Admission/policy controller detected; dry-run the Helm manifest before deployment"
    printf '%s\n' "$policy_engines"
  else
    pass "No common admission policy engine was detected by pod name"
  fi

  section "Storage and existing claims"
  kubectl get storageclass 2>/dev/null || true
  printf '\nPVCs cluster wide:\n'
  kubectl get pvc -A -o wide 2>/dev/null || true

  section "Potential AI/LLM services already in cluster"
  ai_services="$(kubectl get svc -A -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name,TYPE:.spec.type,PORTS:.spec.ports[*].port' --no-headers 2>/dev/null | grep -Ei 'ai-guard|aiguard|litellm|llm|model|inference|openai' || true)"
  if [[ -n "$ai_services" ]]; then
    warn "Existing AI/LLM-related services detected; confirm whether the demo should integrate with or remain isolated from them"
    printf '%s\n' "$ai_services"
  else
    pass "No AI/LLM-related Service names were detected"
  fi

  section "Inventory decision"
  printf 'Summary: PASS=%d WARN=%d FAIL=%d\n' "$PASS" "$WARN" "$FAIL"
  if (( FAIL > 0 )); then
    printf 'Decision: STOP — resolve collisions/failures before creating namespace, Secret, image pull test, or Helm release.\n'
    return 2
  fi
  printf 'Decision: INVENTORY CLEAR WITH %d WARNING(S) — review warnings before continuing to preflight.\n' "$WARN"
}

mkdir -p "$(dirname "$REPORT_FILE")"
set +e
main 2>&1 | tee "$REPORT_FILE"
rc=${PIPESTATUS[0]}
set -e
exit "$rc"
