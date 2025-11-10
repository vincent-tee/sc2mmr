# SC2 MMR Tracker - Setup Guide

## Getting Started

### 1. Install Python Dependencies

First, navigate to the backend directory and install required packages:

```bash
cd backend
pip install -r requirements.txt
```

Or use a virtual environment (recommended):

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Server

From the `backend` directory:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the convenience script from the project root:

```bash
chmod +x run.sh
./run.sh
```

### 3. Verify Installation

Open your browser and visit:
- **API**: http://localhost:8000
- **Interactive Documentation**: http://localhost:8000/docs

You should see the API documentation interface.

### 4. Test the API

Try the health check endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

## Loading Your Replay Data

### Option 1: Upload Replays via API

Use the web interface at http://localhost:8000/docs:

1. Go to `POST /replays/upload`
2. Click "Try it out"
3. Upload a .SC2Replay file
4. Click "Execute"

### Option 2: Batch Process Historical Replays (RECOMMENDED)

This is the best way to build your initial database! The batch processor:
- ✅ Sorts replays chronologically
- ✅ Shows predictions before each match
- ✅ Gradually builds accurate ratings
- ✅ Shows prediction accuracy improving over time

**Basic usage:**

```bash
cd backend
python batch_process_replays.py /path/to/your/replay/folder
```

**With predictions (recommended for first run):**

```bash
python batch_process_replays.py /path/to/your/replay/folder --show-predictions
```

This will:
1. Find all .SC2Replay files in the folder (including subfolders)
2. Sort them by date played
3. For each replay (in order):
   - Show current player ratings
   - Predict which team will win
   - Process the replay
   - Update ratings based on actual result
   - Show if prediction was correct

**With verbose output:**

```bash
python batch_process_replays.py /path/to/your/replay/folder --show-predictions --verbose
```

This adds detailed rating changes for each player after every match.

**Example output:**

```
[1/50] Processing replay from 2024-01-15 19:30:00
File: game_001.SC2Replay

📊 PREDICTION:
   Team 1: Player1, Player2, Player3
   Team 1 MMR: 15.0
   Team 2: Player4, Player5, Player6
   Team 2 MMR: 15.0
   Win Probability - Team 1: 50.0%
   Win Probability - Team 2: 50.0%
   Match Quality: 1.000
   Predicted Winner: Team 1
   Actual Winner: Team 1
   ✅ Prediction CORRECT!

✅ Processed successfully
   Map: Blackburn LE
   Mode: 3v3
   Players: 6

[2/50] Processing replay from 2024-01-15 20:15:00
...
```

**At the end, you'll see:**

```
BATCH PROCESSING COMPLETE
========================
Total replays processed: 45
Total replays skipped: 5

Prediction Accuracy: 68.9%
Correct predictions: 31
Incorrect predictions: 14

Note: Accuracy improves as ratings stabilize!

📊 FINAL PLAYER RANKINGS (min 3 games)
------------------------------------------------
Rank   Player               MMR        Record       Win Rate
------------------------------------------------
1      Player1              18.45      12-3         80.0%
2      Player2              16.23      10-5         66.7%
3      Player3              15.87      9-6          60.0%
...
```

### Why Use Batch Processing?

The TrueSkill algorithm works exactly like you described:

1. **Initial state**: All players start at MMR ~0 (mu=25, sigma=8.333)
2. **Prediction**: Before each match, the system predicts the winner based on current ratings
3. **Update**: After seeing the result, ratings are adjusted
4. **Convergence**: Over time, ratings become more accurate

You'll see:
- Early matches: ~50% prediction accuracy (ratings not calibrated yet)
- Middle matches: Accuracy improves as ratings stabilize
- Later matches: 65-75% accuracy (as good as ratings can predict team games)

The `--show-predictions` flag lets you watch this learning process in action!

## Next Steps

After loading your replay data:

1. **View Player Rankings**
   ```bash
   curl http://localhost:8000/players/rankings?min_games=5
   ```

2. **Balance Teams for Your Next Session**

   Get all players:
   ```bash
   curl http://localhost:8000/players/
   ```

   Then balance (replace with your player IDs):
   ```bash
   curl -X POST http://localhost:8000/teams/balance \
     -H "Content-Type: application/json" \
     -d '{"player_ids": [1,2,3,4,5,6], "top_n": 5}'
   ```

3. **Add New Replays After Each Session**

   Either upload via API or run batch processor on new replays only.

## Troubleshooting

### "Module not found" errors
Make sure you're in the `backend` directory and dependencies are installed:
```bash
cd backend
pip install -r requirements.txt
```

### Database errors
The database is auto-created on first run at `backend/data/sc2mmr.db`. If you have issues:
```bash
# Delete and recreate (WARNING: loses all data)
rm backend/data/sc2mmr.db
# Restart the server to recreate
```

### Replay parsing errors
Some replays might fail to parse. Common reasons:
- Corrupted replay file
- Non-standard game mode (not 3v3, 4v4, or 5v5)
- Custom game settings

The batch processor will skip these and continue with valid replays.

## Running Tests

```bash
cd backend
pytest tests/test_basic.py -v
```

## Tips for Best Results

1. **Process replays chronologically**: This gives the most accurate rating evolution
2. **Need at least 5-10 games per player**: For ratings to stabilize
3. **Watch prediction accuracy**: Should reach 60-70% as ratings improve
4. **Re-run predictions**: You can delete the database and re-process to see different ordering effects
5. **Regular updates**: Add new replays after each session to keep ratings current

## Common Questions

**Q: Why are all players rated ~0 initially?**
A: Default TrueSkill rating is mu=25, sigma=8.333, which gives MMR = 25 - 3*8.333 ≈ 0. This is normal!

**Q: Why do ratings change so much at first?**
A: High sigma (uncertainty) means large rating swings. After ~10 games, sigma decreases and ratings stabilize.

**Q: Can I reset and start over?**
A: Yes! Delete `backend/data/sc2mmr.db` and re-run the batch processor.

**Q: What if I have custom team sizes?**
A: Currently supports 3v3, 4v4, 5v5. Other modes will be skipped.

**Q: Can I exclude certain replays?**
A: Move them to a different folder before batch processing.

## Ready to Go!

You're all set! Start by batch processing your historical replays to build the rating database, then use the team balancer before your next gaming session.

Happy gaming! 🎮
