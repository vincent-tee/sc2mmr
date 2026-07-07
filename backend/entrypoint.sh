#!/bin/sh
# Cloud Run entrypoint: restore the SQLite DB from its GCS replica (if any),
# then run uvicorn under Litestream so every write is streamed back to GCS.
#
# Required env in replicated mode:
#   LITESTREAM_GCS_BUCKET  - bucket holding the DB replica (no gs:// prefix)
# Optional:
#   LITESTREAM_GCS_PATH    - object prefix inside the bucket (default: sc2mmr-db)
#   PORT                   - injected by Cloud Run (default 8080)
#
# Without LITESTREAM_GCS_BUCKET the app starts on a plain local SQLite file
# (data is then LOST when the instance stops - fine for smoke tests only).
set -e

DB_PATH="/srv/backend/data/sc2mmr.db"
export DATABASE_URL="sqlite:///${DB_PATH}"
PORT="${PORT:-8080}"

if [ -n "$LITESTREAM_GCS_BUCKET" ]; then
    export LITESTREAM_GCS_PATH="${LITESTREAM_GCS_PATH:-sc2mmr-db}"
    echo "Litestream: restoring ${DB_PATH} from gcs://${LITESTREAM_GCS_BUCKET}/${LITESTREAM_GCS_PATH} (if replica exists)"
    litestream restore -if-db-not-exists -if-replica-exists -config /etc/litestream.yml "$DB_PATH"
    # First-boot seeding: no replica exists yet, but a plain DB copy was
    # uploaded (SEED_DB_GCS_URI, e.g. gs://bucket/seed/sc2mmr.db). Download
    # it as the starting database; litestream replicate below then creates
    # the replica from it. Subsequent boots restore from the replica and
    # ignore the seed.
    if [ ! -f "$DB_PATH" ] && [ -n "$SEED_DB_GCS_URI" ]; then
        echo "Litestream: no replica yet - seeding DB from ${SEED_DB_GCS_URI}"
        python -c "
import sys
from google.cloud import storage
uri, dest = sys.argv[1], sys.argv[2]
bucket_name, key = uri[5:].split('/', 1)
storage.Client().bucket(bucket_name).blob(key).download_to_filename(dest)
print(f'seeded {dest} from {uri}')
" "$SEED_DB_GCS_URI" "$DB_PATH"
    fi
    echo "Litestream: starting replication + app"
    exec litestream replicate -config /etc/litestream.yml \
        -exec "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"
fi

echo "WARNING: LITESTREAM_GCS_BUCKET not set - running on ephemeral local SQLite"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
