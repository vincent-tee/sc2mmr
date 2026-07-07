---
description: How to merge duplicate player records and recalculate MMR
---
# Merging Duplicate Players

Sometimes a player might be recorded under multiple names (e.g., if they changed their StarCraft II handle or played on a smurf account). This workflow merges the duplicate player's match history, synergies, rivalries, and achievements into the canonical player profile, deletes the duplicate record, and trigger a recalculation of MMRs.

## Prerequisites

You need to know the IDs of both the duplicate player (the one to be removed) and the canonical player (the one to keep). If you only know the names, find their IDs first.

1. **Find Player IDs:**
   If you aren't sure of a player's exact ID or exact capitalization, run this command to search the database by name (e.g., searching for "dragon"):
   ```bash
   python -c "from backend.app.database import SessionLocal; from backend.app.models import Player; db = SessionLocal(); [print(f'[{r[0]}] {r[1]} ({r[2]} games)') for r in db.query(Player.id, Player.name, Player.total_games).filter(Player.name.ilike('%dragon%')).all()]; db.close()"
   ```

## Merge Steps

### 1. Dry Run the Merge

Always perform a dry run first to ensure you are merging the correct accounts and to preview how many records will be affected.

```bash
cd /Ubuntu-22.04/home/vtee/projects/sc2mmr
python backend/scripts/merge_players.py --from-id <DUPLICATE_ID> --into-id <CANONICAL_ID> --dry-run
```

Review the output to confirm that the `FROM:` (duplicate) and `INTO:` (canonical) players are exactly what you expect. 

### 2. Execute the Merge

Run the script without the `--dry-run` flag.

```bash
cd /Ubuntu-22.04/home/vtee/projects/sc2mmr
python backend/scripts/merge_players.py --from-id <DUPLICATE_ID> --into-id <CANONICAL_ID>
```
Type `yes` when prompted to proceed.

*Note: The script safely handles cases where both the canonical and duplicate accounts were in the same match by deleting the duplicate player's row from that match.*

### 3. Recalculate MMRs

Merging players alters the game history of the canonical player. A full recalculation is required so that TrueSkill, hybrid MMR, rivalries, and synergies are accurately updated system-wide.

```bash
cd /Ubuntu-22.04/home/vtee/projects/sc2mmr
python backend/scripts/recalculate_all_mmrs.py
```
