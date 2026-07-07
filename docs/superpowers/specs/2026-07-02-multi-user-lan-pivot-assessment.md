# Assessment: Multi-User Pivot for One LAN-Party Group

**Created:** 2026-07-02
**Status:** Assessment (no implementation yet)
**Scope:** make the currently single-user, single-machine app usable by the members of ONE friend group — several people on their own devices, sometimes simultaneously, during and between game nights. Explicitly NOT multi-tenant SaaS.

---

## 1. Current single-user assumptions (all verified 2026-07-02)

| # | Assumption baked in today | Evidence | Breaks when |
|---|---|---|---|
| 1 | Browser and backend are the same machine | `frontend/src/api/client.ts:12` — `API_BASE_URL = import.meta.env.VITE_API_BASE_URL \|\| 'http://localhost:8000'` | Anyone else opens the app: their browser calls **their own** localhost → dead API |
| 2 | CORS allows localhost only | `backend/app/config.py` `cors_origins` = 5173/3000/3001 localhost | LAN-IP origin is rejected even if #1 is fixed via absolute URL |
| 3 | One writer at a time | SQLite `journal_mode = delete` (NOT WAL — verified live); writes lock readers and vice versa | Two friends upload replays at once → `database is locked` 500s |
| 4 | Parsing can hog the process | replay parsing is synchronous CPU-bound in the request path (known weak point, architecture contract WP) | Simultaneous uploads at game night stack up; UI stalls |
| 5 | One person uploads each game | file-hash dedup only: `ix_matches_replay_hash` is UNIQUE (identical file → 409, race-safe) but `game_fingerprint` (same game, different observer's file) is non-unique AND not wired into the HTTP upload path — orchestrator-only | Two players each upload their own recording of the SAME match → duplicate match, double MMR movement. **The single most likely multi-user data corruption.** |
| 6 | Uploads arrive in played order | upload path applies rating updates in upload order, not `played_at` order | Someone uploads last week's replay after tonight's → ratings drift until the next full recalc |
| 7 | The operator is trusted | zero auth; merge players, set-winner, bulk-reprocess, ML train endpoints are open; no rate limiting; `max_replay_size_mb` is a DEAD setting (no size limit enforced) | Anyone on the network (or a guest's laptop malware) can corrupt data or fill the disk |
| 8 | Server started from `backend/` | DB path and `replays/`/`failed_replays/` are cwd-relative; starting uvicorn from repo root silently creates a fresh empty DB | Any "just run it" instruction that forgets the cwd |
| 9 | Maintenance never overlaps usage | `recalculate_all_mmrs.py` DELETES all match_players/performance_features then rebuilds | Recalc while someone browses/uploads → 500s, or worse, a mid-rebuild upload interleaves |
| 10 | Backups are safe file copies | house-rule backup is `cp` of the live DB | `cp` during a write (journal_mode=delete) can capture a torn state; fine today only because nothing else writes |
| 11 | Guests are created one at a time | `ix_players_name` is UNIQUE | Two devices add guest "Bob" simultaneously → one gets an IntegrityError (needs graceful handling, not a 500) |

## 2. Recommended pivot — three small phases

### Phase A — Reachability (one evening of work)
1. **Serve the built frontend from FastAPI** (`StaticFiles` mounting `frontend/dist` at `/`). Everyone browses `http://<host-LAN-IP>:8000`. Same-origin kills the CORS and API-base problems in one move (set `VITE_API_BASE_URL=''` → relative URLs at build time).
2. Backend already binds `0.0.0.0` (run.sh) — keep, but see Phase B item 4 before exposing beyond the LAN.
3. For remote play between parties: **Tailscale** (or any VPN) rather than port-forwarding — keeps assumption #7 survivable because only group devices can reach it.

### Phase B — Concurrency + data safety (the real work; each item routes through change-control)
1. **Enable WAL** + `busy_timeout` (e.g. 5000ms) in `app/database.py` engine setup. WAL gives concurrent readers during writes — the single highest-value change for multi-user SQLite. Backup procedure must then use `sqlite3 .backup`/`VACUUM INTO` semantics (python `Connection.backup()`), not bare `cp`.
2. **Wire `game_fingerprint` dedup into the HTTP upload path** (`/replays/upload` + `/upload-advanced`), and consider making the index UNIQUE after deduplicating history. This closes edge case #5. (The repair tooling — `deduplicate_games.py` — already exists if duplicates slip in.)
3. **Serialize rating mutation**: a process-level asyncio lock (or single worker queue) around match-creation + rating-update so concurrent uploads commit one at a time; parses can still run in parallel threads. Cheap and sufficient at friend-group volume (<1 write/sec).
4. **Minimal protection for destructive endpoints**: one shared admin token (env var, `X-Admin-Token` header) on merge/set-winner/bulk-reprocess/train/reset-class endpoints. Not user accounts — one group, trusted-ish; the token just prevents accidents and guests' stray scripts. Revive `max_replay_size_mb` (currently dead) as an enforced upload limit.
5. **Out-of-order uploads**: cheapest honest fix is operational — batch-upload old replays, then run the full recalc (existing ritual). Optional code fix later: auto-flag "match older than latest" uploads and prompt a recalc.
6. **Maintenance mode**: recalc script takes an exclusive flag (or the admin stops the server) — never run recalc against a live multi-user server.

### Phase C — Game-night operations ritual (documentation, no code)
- Pre-party: backup (WAL-aware), start server from `backend/`, share the URL.
- During: one designated uploader per match OR rely on B2's fingerprint dedup; guests added via the existing Add Guest flow (handle duplicate-name IntegrityError gracefully — B-item).
- Post-party: batch upload stragglers → full recalc → glance at `db_health.py`.

## 3. Edge-case catalog (one group, multiple users)

| Edge case | Likelihood at a LAN party | Covered by |
|---|---|---|
| Same game uploaded by 2+ observers (different files) | HIGH — everyone has the replay | B2 (fingerprint dedup in HTTP path) |
| Identical file uploaded twice | HIGH | already safe (UNIQUE replay_hash → 409) |
| Concurrent uploads lock the DB | HIGH on upload-everything night | B1 (WAL) + B3 (serialize) |
| Old replay uploaded after new ones | MEDIUM | B5 / C ritual (recalc) |
| Two devices browsing while one uploads | CERTAIN | B1 (WAL readers) |
| Recalc during live use | MEDIUM (someone "fixes" mid-party) | B6 |
| Duplicate guest names created concurrently | LOW-MEDIUM | B4-adjacent graceful 409 |
| Oversized/garbage file upload | LOW | B4 (size limit; parse failures already land in failed_uploads) |
| Phone browsers (small screens) at the table | CERTAIN | existing responsive UI — verify on the balance + upload pages specifically |
| Host machine dies mid-party | LOW | C backups; SQLite file restore is trivial |
| Two people trigger ML train simultaneously | LOW | B4 token; training is in-memory/log-only today |

## 4. Explicit non-goals (don't build these)
- **User accounts / OAuth / per-user permissions** — one trusted group; a shared admin token is the ceiling.
- **PostgreSQL migration** — SQLite + WAL comfortably handles ~20 readers and sub-1/sec writes; migrating would invalidate the cascade tooling and backup ritual for zero felt benefit.
- **Cloud/multi-tenant hosting** — the DB is a 40MB file belonging to one group; a LAN host + Tailscale covers remote needs.
- **Websocket live-sync** — polling/refetch (TanStack Query) is fine at this scale.

## 5. Suggested order & effort
A1+A2 (static serving + relative API base): ~1 session. B1 (WAL+backup change): small, do with A. B2 (fingerprint dedup): 1 session incl. tests — highest data-integrity value. B3+B4: 1 session. B5/B6/C: documentation + one script flag. Everything routes through `sc2mmr-change-control` (B1's backup-procedure change updates house rule 1's command).

## Provenance and maintenance
All "verified" claims checked live 2026-07-02: client.ts:12, cors_origins, `PRAGMA journal_mode` = delete, index uniqueness via `PRAGMA index_list(matches)` / `(players)`, dead `max_replay_size_mb` (zero consumers), game_fingerprint absent from HTTP upload path (grep `app/api/replays.py`), recalc delete-and-rebuild at `scripts/recalculate_all_mmrs.py:96-99`. Re-verify with: `python3 -c "import sqlite3;print(sqlite3.connect('backend/data/sc2mmr.db').execute('PRAGMA journal_mode').fetchone())"` and `grep -n game_fingerprint backend/app/api/replays.py`.
