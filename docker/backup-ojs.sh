#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
dest=backups/full-run-2026-10-12
mkdir -p "$dest"
chmod 700 "$dest"
docker compose exec -T db sh -c 'exec mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction --routines --triggers ojs' > "$dest/ojs.sql"
docker compose exec -T ojs tar --hard-dereference -czf - -C /var/www html files > "$dest/ojs.tar.gz"
chmod 600 "$dest/ojs.sql" "$dest/ojs.tar.gz"
shasum -a 256 "$dest/ojs.sql" "$dest/ojs.tar.gz" > "$dest/SHA256SUMS"
