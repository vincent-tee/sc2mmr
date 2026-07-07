# Deploying SC2MMR online (group-only)

Architecture: **Vercel** serves the built frontend; **Cloud Run** runs the
backend with the SQLite DB replicated to GCS by **Litestream**; replay files
live in a **GCS bucket**. Access is gated by a shared **group password**
(session cookie) plus an **admin token** for destructive endpoints.

Everything is opt-in via env vars: with none of them set, the app runs
locally exactly as before (open, local SQLite, local replay dirs).

## Backend env vars

| Var | Required online | Example / default | What it does |
|---|---|---|---|
| `AUTH_ENABLED` | yes | `true` (default `false`) | Master switch: every endpoint except `/health` and `/auth/*` needs a session |
| `GROUP_PASSWORD` | yes | `hunter2-but-better` | The shared squad password |
| `AUTH_SECRET` | strongly recommended | 64 random hex chars | Signs session cookies; unset = per-process random, everyone re-logs-in on each cold start |
| `ADMIN_TOKEN` | recommended | random string | Required (`X-Admin-Token` header) for rating recalc, player merge, ML retrain, check-alls. Unset = those endpoints only need the group session |
| `CORS_ORIGINS` | yes | `["https://sc2mmr.vercel.app"]` (JSON list) | Browser origin(s) allowed to call the API with credentials |
| `AUTH_COOKIE_SECURE` / `AUTH_COOKIE_SAMESITE` | no | `true` / `none` (defaults) | Correct for the cross-site Vercel+Cloud Run split; for local auth testing over http use `false` / `lax` |
| `LITESTREAM_GCS_BUCKET` | yes | `my-sc2mmr-state` | Bucket for the SQLite replica (entrypoint.sh restores on boot, replicates while running) |
| `LITESTREAM_GCS_PATH` | no | `sc2mmr-db` (default) | Object prefix for the DB replica |
| `REPLAY_GCS_BUCKET` | yes | `my-sc2mmr-state` | Bucket for replay files (uploads + the Download Replay button). Can be the same bucket as Litestream's |
| `DATABASE_URL` | no | set by entrypoint.sh | Only for non-default DB locations; local runs should leave it unset |

Frontend (Vercel) env var: `VITE_API_BASE_URL=https://<cloud-run-url>` (build-time).

## One-time GCP setup

```bash
gcloud auth login && gcloud config set project <PROJECT>
gcloud services enable run.googleapis.com artifactregistry.googleapis.com

# State bucket (DB replica + replays). Single region near you (Melbourne):
gcloud storage buckets create gs://<STATE_BUCKET> --location=australia-southeast2

# Seed the DB replica from the local database (one-off), using litestream
# locally, OR just let the first deploy start empty and re-upload replays.
# Seeding from local (recommended - keeps all history):
#   litestream replicate -exec 'sleep 5' backend/data/sc2mmr.db \
#       gcs://<STATE_BUCKET>/sc2mmr-db
# (Install litestream locally from litestream.io, run from repo root.)

# Copy existing replay files up (keeps the Download Replay button working
# for historical matches):
gcloud storage cp backend/replays/* gs://<STATE_BUCKET>/replays/
```

## Deploy the backend

```bash
cd backend
gcloud run deploy sc2mmr-api \
  --source . \
  --region australia-southeast2 \
  --allow-unauthenticated \
  --max-instances 1 \
  --memory 1Gi \
  --set-env-vars AUTH_ENABLED=true,GROUP_PASSWORD=<pw>,AUTH_SECRET=<hex>,ADMIN_TOKEN=<token> \
  --set-env-vars LITESTREAM_GCS_BUCKET=<STATE_BUCKET>,REPLAY_GCS_BUCKET=<STATE_BUCKET> \
  --set-env-vars 'CORS_ORIGINS=["https://<app>.vercel.app"]'
```

**`--max-instances 1` is not optional.** SQLite has a single writer;
Litestream replicates one instance's file. Two instances would fork the
database. `--allow-unauthenticated` is correct: the app's own password layer
is the gate (Cloud Run "authentication" would demand Google IAM tokens the
browser can't send cross-origin).

The Cloud Run service account needs `roles/storage.objectAdmin` on the state
bucket (both Litestream and replay storage use application-default creds).

## Deploy the frontend

```bash
cd frontend
npx vercel --prod   # or connect the repo in the Vercel dashboard
# In Vercel project settings set: VITE_API_BASE_URL=https://<cloud-run-url>
```

`vercel.json` already configures the Vite build and SPA rewrites.

## Smoke test

```bash
curl https://<api>/health                      # {"status":"healthy"} - no auth
curl https://<api>/players/                    # 401 - auth is on
curl -c c.txt -X POST https://<api>/auth/login -H 'Content-Type: application/json' \
     -d '{"password":"<pw>"}'                  # 200, sets cookie
curl -b c.txt https://<api>/players/ | head    # 200 - session works
```

Then open the Vercel URL in a browser: you should get the "Members Only"
screen, and the squad password should open the app.

## Operational notes

- **Uploads:** the web Upload page and `backend/upload_all_replays.py` /
  `scripts/batch_upload_replays.py` (pointed at the hosted URL) are the
  ingestion paths. The local replay-observer feature was removed 2026-07-07.
- **Admin actions** (recalculate ratings, merge players, retrain): in the
  browser run `localStorage.setItem('sc2mmr_admin_token', '<token>')` once,
  or send the `X-Admin-Token` header from curl/scripts.
- **Backups:** Litestream's GCS replica IS the live backup (point-in-time
  restore: `litestream restore`). Keep taking dated `.backup_*` copies before
  formula recalcs per house rule.
- **Cold starts:** scale-to-zero means the first request after idle takes
  ~10s (image boot + DB restore). `--min-instances 1` removes that for a few
  $/month.
- **Costs:** Cloud Run within free tier at friend-group traffic;
  GCS state ~$0.05/GB-month; Vercel Hobby free.
