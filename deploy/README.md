# TF Bank Rev 118 Deployment

The application runs as UID/GID `10001:10001` with:

- a read-only root filesystem;
- writable `/tmp` backed by a 160 MB `tmpfs`;
- `no-new-privileges`;
- a persistent Docker volume mounted at `/data`;
- secrets loaded from an external environment file.

## Build

```bash
docker build \
  --progress=plain \
  --tag tfbank-demo:118.0.0 \
  .
```

## Runtime configuration

Never store credentials in this repository.

Create a private runtime configuration outside the repository:

```bash
mkdir -p "$HOME/tfbank-secrets"

cp deploy/backup.env.example \
  "$HOME/tfbank-secrets/backup-release.env"

chmod 600 \
  "$HOME/tfbank-secrets/backup-release.env"
```

Example runtime configuration:

```text
CONTAINER_NAME=tfbank-demo-backup
APP_IMAGE=tfbank-demo:118.0.0
APP_ENV_FILE=/home/ec2-user/tfbank-secrets/backup.env
HOST_PORT=18081
DATA_VOLUME=tfbank-backup-data
```

`APP_ENV_FILE` must use an absolute path, remain outside the Git repository,
and have permission mode `600` or `400`.

## Preflight

```bash
deploy/run.sh preflight \
  "$HOME/tfbank-secrets/backup-release.env"
```

## Start

```bash
deploy/run.sh start \
  "$HOME/tfbank-secrets/backup-release.env"
```

The `start` action refuses to overwrite an existing container.

## Explicit replacement

```bash
deploy/run.sh replace \
  "$HOME/tfbank-secrets/backup-release.env"
```

The `replace` action removes only the configured container. It does not
delete its persistent Docker volume.

## Status and logs

```bash
deploy/run.sh status \
  "$HOME/tfbank-secrets/backup-release.env"

deploy/run.sh logs \
  "$HOME/tfbank-secrets/backup-release.env"
```

## Stop

```bash
deploy/run.sh stop \
  "$HOME/tfbank-secrets/backup-release.env"
```

Stopping a container does not remove its data volume.
