#!/usr/bin/env bash
set -euo pipefail
umask 077

cd /opt/openmaic
archive=$(find /var/backups/openmaic -maxdepth 1 -type f -name 'openmaic-*.tar.gz' | sort | tail -n 1)
test -n "$archive"
stage=$(mktemp -d /var/backups/openmaic/.restore.XXXXXXXX)
db=openmaic_restore_test
created=0
cleanup() {
  if [ "$created" = 1 ]; then
    docker compose exec -T postgres dropdb -U openmaic "$db"
  fi
  rm -rf -- "$stage"
}
trap cleanup EXIT

tar -xzf "$archive" -C "$stage"
test -s "$stage/postgres.dump"
test -n "$(find "$stage/data/classrooms" -maxdepth 1 -type f -name '*.json' -print -quit)"
docker compose exec -T postgres pg_restore --list < "$stage/postgres.dump" > /dev/null
if [ "$(docker compose exec -T postgres psql -U openmaic -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname='$db'")" = 1 ]; then
  echo 'Restore test database already exists; refusing to overwrite it.' >&2
  exit 1
fi
docker compose exec -T postgres createdb -U openmaic "$db"
created=1
docker compose exec -T postgres pg_restore -U openmaic -d "$db" --no-owner --no-privileges < "$stage/postgres.dump"
rows=$(docker compose exec -T postgres psql -U openmaic -d "$db" -Atqc 'SELECT count(*) FROM document_stages')
test "$rows" -ge 1
echo "Restore rehearsal passed: $rows saved course row(s), classroom files present."
