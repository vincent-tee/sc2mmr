# SC2 MMR Replay Re-Upload Guide

This guide explains how to re-upload all your replays to ensure advanced parsing and ML features are extracted.

## What Changed

### New Features Added
1. **Replay File Storage**: Successful uploads now save the `.SC2Replay` file to `replays/` directory
2. **Automatic ML Feature Extraction**: Every upload now extracts build orders, upgrades, abilities
3. **Bulk Re-process Endpoint**: Re-extract ML features from saved replays
4. **Gaming UI Components**: RankBadge, VSScreen, MMRTicker, RaceBackground integrated

## Re-Upload Process

### Option 1: Fresh Start (Recommended)

If you want a clean slate with all replays having full ML features:

```bash
# Step 1: Backup existing database (optional)
cd backend
cp data/sc2mmr.db data/sc2mmr.db.backup

# Step 2: Reset database to clean state
python scripts/reset_database.py

# Step 3: Start the backend server
uvicorn app.main:app --reload --port 8000

# Step 4: Upload all replays using the advanced endpoint
# You can use the frontend UI or curl:

# Using curl for a single replay:
curl -X POST "http://localhost:8000/api/replays/upload-advanced" \
  -F "file=@/path/to/your/replay.SC2Replay"

# Using a script to upload all replays in a folder:
for replay in /path/to/replays/*.SC2Replay; do
  echo "Uploading: $replay"
  curl -X POST "http://localhost:8000/api/replays/upload-advanced" \
    -F "file=@$replay"
  sleep 0.5  # Small delay to avoid overwhelming server
done
```

### Option 2: Keep Existing Data + Re-upload Missing

If you have some replays already processed and want to add more:

```bash
# Step 1: Start the backend
cd backend
uvicorn app.main:app --reload --port 8000

# Step 2: Upload new replays (duplicates will be detected and skipped)
for replay in /path/to/replays/*.SC2Replay; do
  curl -X POST "http://localhost:8000/api/replays/upload-advanced" \
    -F "file=@$replay"
done

# Step 3: Bulk re-process to extract ML features for existing matches
curl -X POST "http://localhost:8000/api/replays/bulk-reprocess" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

### Option 3: Use Frontend Upload UI

1. Start both backend and frontend:
   ```bash
   # Terminal 1 - Backend
   cd backend
   uvicorn app.main:app --reload --port 8000

   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

2. Open http://localhost:5173 in your browser

3. Navigate to "Upload Replays" page

4. Drag & drop or select multiple `.SC2Replay` files

5. The system will:
   - Parse each replay
   - Save the replay file to `replays/`
   - Extract basic + advanced metrics
   - Extract ML features (build orders, upgrades, abilities)
   - Calculate PIM (Performance Impact Modifier)
   - Update player ratings with hybrid MMR

## Verification Steps

### 1. Check Replay Files Are Saved

```bash
# Should see your replay files here
ls -la backend/replays/
```

### 2. Check ML Features Were Extracted

```bash
# Connect to SQLite and check performance_features table
sqlite3 backend/data/sc2mmr.db

# Count matches with ML features
SELECT COUNT(*) FROM performance_features WHERE pim IS NOT NULL;

# See sample ML features
SELECT
  mp.id,
  p.name,
  pf.detected_build_type,
  pf.pim,
  pf.total_abilities
FROM performance_features pf
JOIN match_players mp ON pf.match_player_id = mp.id
JOIN players p ON mp.player_id = p.id
LIMIT 10;

# Check build orders
SELECT
  p.name,
  json_extract(pf.build_order_json, '$[0].unit_type') as first_unit,
  pf.detected_build_type
FROM performance_features pf
JOIN match_players mp ON pf.match_player_id = mp.id
JOIN players p ON mp.player_id = p.id
WHERE pf.build_order_json IS NOT NULL
LIMIT 10;
```

### 3. Check Hybrid MMR Is Working

```bash
# In SQLite
SELECT
  name,
  mu,
  mmr,
  hybrid_mmr,
  avg_pim
FROM players
ORDER BY hybrid_mmr DESC
LIMIT 10;
```

### 4. Verify via API

```bash
# Get players with hybrid MMR
curl http://localhost:8000/api/players/ | jq '.[0:5] | .[] | {name, mmr: .current_mmr, hybrid_mmr, avg_pim}'

# Get matches with ML features
curl http://localhost:8000/api/replays/matches-with-players?limit=5 | jq '.matches[0]'
```

## Bulk Re-process Endpoint

For matches that were uploaded before ML feature extraction was integrated:

```bash
# Re-process ALL matches (skip those with existing features)
curl -X POST "http://localhost:8000/api/replays/bulk-reprocess" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'

# Re-process specific matches
curl -X POST "http://localhost:8000/api/replays/bulk-reprocess" \
  -H "Content-Type: application/json" \
  -d '{"match_ids": [1, 2, 3, 4, 5], "force": false}'

# Force re-process (even if features exist)
curl -X POST "http://localhost:8000/api/replays/bulk-reprocess" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

**Response Example:**
```json
{
  "total": 100,
  "processed": 85,
  "skipped": 10,
  "failed": 5,
  "errors": [
    {"match_id": 15, "error": "Replay file not found"},
    {"match_id": 42, "error": "Feature extraction returned no results"}
  ]
}
```

## Troubleshooting

### "Replay file not found" in bulk reprocess

This means the original replay wasn't saved (uploaded before storage was enabled).

**Solution**: Re-upload the replay using `/upload-advanced` endpoint.

### Duplicate replay detected

The system prevents duplicate uploads by checking the replay hash.

**Solution**: This is expected behavior. The replay is already processed.

### ML features are NULL

Check if the replay file was saved:
```sql
SELECT id, map_name, replay_file_path FROM matches WHERE id = <match_id>;
```

If `replay_file_path` is NULL, re-upload the replay.

### PIM is 0 for all players

This can happen if performance metrics (damage, resources, etc.) weren't extracted.

**Solution**: Use the `/upload-advanced` endpoint (not basic `/upload`).

## Configuration

You can configure replay storage in `.env` file:

```bash
# Enable/disable replay file storage
REPLAY_STORAGE_ENABLED=true

# Change storage directory
REPLAY_STORAGE_DIR=replays
```

## ML Features Extracted

Each replay now extracts:

| Feature | Description |
|---------|-------------|
| `build_order_json` | Full build sequence with timings |
| `detected_build_type` | Classified as rush/macro/timing/cheese |
| `upgrades_json` | All upgrades with categories |
| `first_attack_upgrade_second` | Timing of first attack upgrade |
| `abilities_json` | Ability usage counts (Stim, EMP, etc.) |
| `abilities_per_minute` | APM-style ability metric |
| `supply_block_seconds` | Total time supply blocked |
| `harassment_response_score` | How well player defended harass |
| `pim` | Performance Impact Modifier (-0.5 to +0.5) |

## What's Next

After re-uploading all replays:

1. **ML Training Data**: With 100+ matches, the build order classifier can be retrained
2. **PIM Analysis**: View which players perform above/below expectations
3. **Gaming UI**: Check out the new RankBadge, VSScreen components in the frontend
4. **Team Balance**: Team generator now considers hybrid MMR

---

**Last Updated**: 2025-12-10
**Related SPEC**: SPEC-REFACTOR-001, SPEC-ML-001
