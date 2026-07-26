#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

SCRIPT_DIR="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
  pwd
)"
REPO_ROOT="$(
  cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1
  pwd
)"

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Usage:
  deploy/run.sh preflight <runtime-config.env>
  deploy/run.sh start     <runtime-config.env>
  deploy/run.sh replace   <runtime-config.env>
  deploy/run.sh status    <runtime-config.env>
  deploy/run.sh logs      <runtime-config.env>
  deploy/run.sh stop      <runtime-config.env>

Actions:
  preflight  Validate Docker, image, external env file, and data volume.
  start      Start a new container. Fails if the name already exists.
  replace    Remove the named container first, then start a replacement.
  status     Show container state and runtime protections.
  logs       Show the latest 200 container log lines.
  stop       Gracefully stop the container without deleting it.

Runtime config keys:
  CONTAINER_NAME
  APP_IMAGE
  APP_ENV_FILE
  HOST_PORT
  DATA_VOLUME
USAGE
}

trim() {
  local value="$1"

  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"

  printf '%s' "$value"
}

ACTION="${1:-}"
CONFIG_FILE="${2:-}"

case "$ACTION" in
  preflight|start|replace|status|logs|stop)
    ;;
  -h|--help|help|"")
    usage
    exit 0
    ;;
  *)
    usage >&2
    die "unsupported action: $ACTION"
    ;;
esac

[[ -n "$CONFIG_FILE" ]] || die "runtime config file is required"
[[ -f "$CONFIG_FILE" ]] || die "runtime config file not found: $CONFIG_FILE"

declare -A CONFIG=()

while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="${raw_line%$'\r'}"
  stripped="$(trim "$line")"

  [[ -z "$stripped" ]] && continue
  [[ "$stripped" == \#* ]] && continue
  [[ "$stripped" == *=* ]] || die "invalid config line: $line"

  key="$(trim "${stripped%%=*}")"
  value="$(trim "${stripped#*=}")"

  case "$key" in
    CONTAINER_NAME|APP_IMAGE|APP_ENV_FILE|HOST_PORT|DATA_VOLUME)
      ;;
    *)
      die "unsupported runtime config key: $key"
      ;;
  esac

  [[ -z "${CONFIG[$key]+x}" ]] || die "duplicate config key: $key"
  CONFIG["$key"]="$value"
done < "$CONFIG_FILE"

CONTAINER_NAME="${CONFIG[CONTAINER_NAME]:-}"
APP_IMAGE="${CONFIG[APP_IMAGE]:-}"
APP_ENV_FILE="${CONFIG[APP_ENV_FILE]:-}"
HOST_PORT="${CONFIG[HOST_PORT]:-}"
DATA_VOLUME="${CONFIG[DATA_VOLUME]:-}"

[[ -n "$CONTAINER_NAME" ]] || die "CONTAINER_NAME is required"
[[ -n "$APP_IMAGE" ]] || die "APP_IMAGE is required"
[[ -n "$APP_ENV_FILE" ]] || die "APP_ENV_FILE is required"
[[ -n "$HOST_PORT" ]] || die "HOST_PORT is required"
[[ -n "$DATA_VOLUME" ]] || die "DATA_VOLUME is required"

[[ "$CONTAINER_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]+$ ]] \
  || die "invalid CONTAINER_NAME"

[[ "$DATA_VOLUME" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]+$ ]] \
  || die "invalid DATA_VOLUME"

[[ "$HOST_PORT" =~ ^[0-9]+$ ]] \
  || die "HOST_PORT must be numeric"

(( HOST_PORT >= 1 && HOST_PORT <= 65535 )) \
  || die "HOST_PORT must be between 1 and 65535"

command -v docker >/dev/null 2>&1 \
  || die "docker command was not found"

container_exists() {
  docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1
}

validate_runtime_inputs() {
  local env_real
  local repo_real
  local mode
  local permission

  docker image inspect "$APP_IMAGE" >/dev/null 2>&1 \
    || die "Docker image not found: $APP_IMAGE"

  [[ "$APP_ENV_FILE" = /* ]] \
    || die "APP_ENV_FILE must be an absolute path"

  [[ -f "$APP_ENV_FILE" ]] \
    || die "external application env file not found: $APP_ENV_FILE"

  [[ -r "$APP_ENV_FILE" ]] \
    || die "external application env file is not readable"

  env_real="$(readlink -f "$APP_ENV_FILE")"
  repo_real="$(readlink -f "$REPO_ROOT")"

  case "$env_real" in
    "$repo_real"|"$repo_real"/*)
      die "APP_ENV_FILE must remain outside the Git repository"
      ;;
  esac

  mode="$(stat -c '%a' "$APP_ENV_FILE")"
  permission=$((8#$mode))

  if (( permission & 077 )); then
    die \
      "APP_ENV_FILE permissions are too open: $mode; use chmod 600 or 400"
  fi
}

ensure_data_volume() {
  local created=0

  if ! docker volume inspect "$DATA_VOLUME" >/dev/null 2>&1; then
    docker volume create "$DATA_VOLUME" >/dev/null
    created=1
    printf 'Created volume: %s\n' "$DATA_VOLUME"
  fi

  if (( created )); then
    docker run --rm \
      --user 0:0 \
      --volume "${DATA_VOLUME}:/data" \
      --entrypoint /bin/sh \
      "$APP_IMAGE" \
      -lc '
        mkdir -p /data/clean /data/quarantine
        chown -R 10001:10001 /data
      '
  fi

  docker run --rm \
    --user 10001:10001 \
    --volume "${DATA_VOLUME}:/data" \
    --entrypoint /bin/sh \
    "$APP_IMAGE" \
    -lc '
      test -w /data
      mkdir -p /data/clean /data/quarantine
      touch /data/.deployment-write-test
      rm -f /data/.deployment-write-test
    '

  printf 'Volume writable by application user: %s\n' "$DATA_VOLUME"
}

wait_for_container() {
  local attempt
  local state
  local health

  for attempt in $(seq 1 40); do
    state="$(
      docker inspect \
        --format '{{.State.Status}}' \
        "$CONTAINER_NAME" \
        2>/dev/null || true
    )"

    health="$(
      docker inspect \
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
        "$CONTAINER_NAME" \
        2>/dev/null || true
    )"

    printf \
      'Health attempt %02d: state=%s health=%s\n' \
      "$attempt" \
      "${state:-missing}" \
      "${health:-missing}"

    if [[ "$state" == "running" && "$health" == "healthy" ]]; then
      return 0
    fi

    if [[ "$state" == "running" && "$health" == "none" ]]; then
      return 0
    fi

    if [[ "$state" == "exited" || "$state" == "dead" ]]; then
      break
    fi

    sleep 2
  done

  docker logs "$CONTAINER_NAME" --tail=200 >&2 || true
  die "container did not become healthy"
}

show_status() {
  container_exists || die "container not found: $CONTAINER_NAME"

  docker inspect "$CONTAINER_NAME" \
    --format 'Container={{.Name}}
Image={{.Config.Image}}
User={{.Config.User}}
Status={{.State.Status}}
Health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}
Restarts={{.RestartCount}}
ReadOnly={{.HostConfig.ReadonlyRootfs}}
RestartPolicy={{.HostConfig.RestartPolicy.Name}}
Tmpfs={{json .HostConfig.Tmpfs}}
SecurityOpt={{json .HostConfig.SecurityOpt}}
Ports={{json .HostConfig.PortBindings}}
Mounts={{range .Mounts}}{{.Type}}:{{.Name}}:{{.Destination}} {{end}}'
}

start_container() {
  local replace_existing="$1"

  validate_runtime_inputs

  if container_exists; then
    if [[ "$replace_existing" == "true" ]]; then
      printf 'Removing existing container: %s\n' "$CONTAINER_NAME"
      docker rm -f "$CONTAINER_NAME" >/dev/null
    else
      die \
        "container already exists: $CONTAINER_NAME; use the replace action explicitly"
    fi
  fi

  ensure_data_volume

  docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --env-file "$APP_ENV_FILE" \
    --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,noexec,size=160m,mode=1777 \
    --security-opt no-new-privileges:true \
    --volume "${DATA_VOLUME}:/data" \
    --publish "${HOST_PORT}:8080" \
    "$APP_IMAGE" \
    >/dev/null

  printf \
    'Started %s using %s on host port %s\n' \
    "$CONTAINER_NAME" \
    "$APP_IMAGE" \
    "$HOST_PORT"

  wait_for_container
  show_status
}

case "$ACTION" in
  preflight)
    validate_runtime_inputs
    ensure_data_volume
    printf 'Preflight passed for: %s\n' "$CONTAINER_NAME"
    ;;

  start)
    start_container false
    ;;

  replace)
    start_container true
    ;;

  status)
    show_status
    ;;

  logs)
    container_exists || die "container not found: $CONTAINER_NAME"
    docker logs "$CONTAINER_NAME" --tail=200
    ;;

  stop)
    container_exists || die "container not found: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME"
    ;;
esac
