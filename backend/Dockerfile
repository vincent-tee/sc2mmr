# SC2MMR backend for Cloud Run.
#
# SQLite persistence: the DB lives on the container's ephemeral disk and is
# continuously replicated to GCS by Litestream. On boot, entrypoint.sh
# restores the latest replica before starting the app. This REQUIRES the
# service to run with max-instances=1 (SQLite has one writer; two instances
# would fork the database).
#
# Build (from the repo's backend/ directory):
#   docker build -t sc2mmr-backend .
#
# See DEPLOYMENT.md at the repo root for the full Cloud Run runbook.
FROM python:3.10-slim

# Litestream binary, pinned, copied from the official image
COPY --from=litestream/litestream:0.3.13 /usr/local/bin/litestream /usr/local/bin/litestream

WORKDIR /srv/backend

# Python dependencies first, for build-layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code. .dockerignore keeps the local DB, replays, logs and
# backups out of the image - state comes from Litestream/GCS at runtime.
# The trained ML model artifact is the one data/ file that ships baked in.
COPY app ./app
COPY config ./config
COPY data/xgboost_model.pkl ./data/xgboost_model.pkl
COPY litestream.yml /etc/litestream.yml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p data replays failed_replays

# The app resolves the DB, replay dirs and abilities config relative to the
# backend directory / cwd, so run from there (matches local convention).
ENV PYTHONUNBUFFERED=1

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
