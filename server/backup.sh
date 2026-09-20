#!/usr/bin/env bash
set -euo pipefail
umask 077

APP_DIR=/opt/openmaic
BACKUP_DIR=/var/backups/openmaic
mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"

was_running=$(docker compose -f compose.yml ps --status running -q openmaic)
if [ -n "$was_running" ]; then
  docker compose -f compose.yml stop openmaic
fi
restart_app() {
  if [ -n "$was_running" ]; then
    docker compose -f compose.yml start openmaic
  fi
}

stage=$(mktemp -d "$BACKUP_DIR/.stage.XXXXXXXX")
cleanup() { rm -rf -- "$stage"; }
trap 'cleanup; restart_app' EXIT

docker compose -f compose.yml exec -T postgres pg_dump -U openmaic -d openmaic -Fc > "$stage/postgres.dump"
mkdir -p "$stage/data"
volume_dir=$(docker volume inspect --format '{{.Mountpoint}}' openmaic_openmaic-data)
test -d "$volume_dir"
cp -a "$volume_dir/." "$stage/data/"
docker compose -f compose.yml exec -T postgres pg_restore --list < "$stage/postgres.dump" > /dev/null
restart_app
was_running=

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$BACKUP_DIR/openmaic-$timestamp.tar.gz"
tar -C "$stage" -czf "$archive.tmp" postgres.dump data
tar -tzf "$archive.tmp" > /dev/null
mv "$archive.tmp" "$archive"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'openmaic-*.tar.gz' -mtime +6 -delete
echo "Backup saved: $archive"
