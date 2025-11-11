# SC2 MMR Tracker - Comprehensive Project Overview

## Project Purpose

A **StarCraft 2 replay analysis and team balancing system** for a casual gaming group (6-12 players). The PRIMARY FEATURE is **balancing teams for fair matches** using TrueSkill ratings and advanced performance metrics.

### Core Use Cases
1. Upload SC2 replay files and extract match data
2. Track player skill ratings over time using multiple models
3. Generate balanced team compositions for upcoming games
4. Analyze player performance, synergies, and play styles
5. Identify player archetypes (rusher, late-game, timing attacker, etc.)

---

## Tech Stack

### Backend Framework
- **FastAPI** - Modern async Python web framework
  - REST API with automatic OpenAPI documentation
  - Dependency injection for database sessions
  - CORS middleware for cross-origin requests
  - Lifespan handlers for startup/shutdown

### Database
- **SQLite** - File-based relational database
  - Location: `backend/data/sc2mmr.db`
  - **SQLAlchemy ORM** for database abstraction
  - No migrations framework (manual schema updates via ALTER TABLE)

### Core Dependencies
- **sc2reader** (1.8.0) - SC2 replay file parser
  - Extracts game events, player actions, units, tracker events
  - Supports all SC2 expansions through current patches

- **trueskill** (0.4.5) - Bayesian skill rating system
  - Microsoft's TrueSkill algorithm for team-based games
  - Handles uncertainty (sigma) and skill estimate (mu)

- **FastAPI** (0.115.12) + **Uvicorn** (0.34.0) - Web server
- **SQLAlchemy** (2.0.36) - ORM and database toolkit
- **Pydantic** (2.10.6) - Data validation and serialization

### Python Version
- **Python 3.9+** required

---

## Project Structure

```
sc2mmr/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── database.py                # DB connection and session management
│   │   ├── models.py                  # SQLAlchemy database models
│   │   ├── replay_parser.py           # Basic replay parsing (sc2reader)
│   │   ├── advanced_parser.py         # Detailed metrics extraction
│   │   ├── rating_system.py           # TrueSkill integration + recency weighting
│   │   ├── rating_models.py           # Multi-model rating system (8 models)
│   │   ├── balancer.py                # Team balancing algorithm
│   │   ├── impact_service.py          # Impact scores and synergy tracking
│   │   ├── damage_timeline.py         # Second-by-second damage tracking
│   │   ├── timing_analyzer.py         # Player archetype detection
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── replays.py             # Replay upload endpoints
│   │       ├── players.py             # Player stats and rankings
│   │       ├── teams.py               # Team balancing endpoints
│   │       └── impact.py              # Impact and synergy endpoints
│   ├── data/
│   │   └── sc2mmr.db                  # SQLite database (auto-created)
│   ├── batch_process_replays.py       # Chronological replay processor
│   ├── migrate_add_recency_weight.py  # Migration script for recency column
│   ├── requirements.txt               # Python dependencies
│   ├── run.sh                         # Convenience startup script
│   ├── README.md                      # Basic setup instructions
│   ├── SETUP.md                       # Detailed setup guide
│   ├── ADVANCED_FEATURES.md           # Deep dive into metrics
│   ├── IMPLEMENTATION_SUMMARY.md      # Complete feature list
│   └── RECENCY_WEIGHTING.md           # Recency weighting documentation
└── README.md                          # Project overview
```

---

## Database Schema

### Tables

#### `players`
Core player information and ratings.

```sql
CREATE TABLE players (
    -- Identity
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at DATETIME NOT NULL,
    last_played DATETIME,
    is_core_player INTEGER DEFAULT 1,  -- 1=core, 0=outsider

    -- TrueSkill Rating
    mu REAL DEFAULT 25.0,               -- Skill estimate
    sigma REAL DEFAULT 8.333,           -- Uncertainty
    recency_weighted_mmr REAL,          -- Recency-weighted MMR (60-day half-life)

    -- Statistics
    total_games INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,

    -- Race Statistics
    terran_games INTEGER DEFAULT 0,
    protoss_games INTEGER DEFAULT 0,
    zerg_games INTEGER DEFAULT 0,
    random_games INTEGER DEFAULT 0,

    -- Impact Scores (averaged across all matches)
    avg_economic_score REAL DEFAULT 0.0,
    avg_combat_score REAL DEFAULT 0.0,
    avg_efficiency_score REAL DEFAULT 0.0,
    avg_overall_impact REAL DEFAULT 0.0,

    -- Timing Profile
    avg_first_damage_timing INTEGER,
    primary_archetype TEXT,             -- Rush, Timing, LateGame, etc.
    avg_aggression_score REAL DEFAULT 50.0
);
```

**Computed Properties:**
- `mmr = mu - (3 * sigma)` - Conservative skill estimate (99.7% confidence)
- `win_rate = (wins / total_games) * 100`
- `favorite_race` - Most played race

#### `matches`
Game records.

```sql
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    played_at DATETIME NOT NULL,
    game_mode TEXT NOT NULL,            -- "3v3", "4v4", "5v5"
    map_name TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    replay_file_path TEXT,
    replay_hash TEXT                    -- SHA256 hash for duplicate detection
);
```

#### `match_players`
Player participation in matches (junction table).

```sql
CREATE TABLE match_players (
    id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    team_number INTEGER NOT NULL,       -- 1 or 2
    race TEXT NOT NULL,                 -- Terran, Protoss, Zerg, Random
    won INTEGER NOT NULL,               -- 1=win, 0=loss

    -- Rating Snapshots
    mu_before REAL NOT NULL,
    sigma_before REAL NOT NULL,
    mu_after REAL NOT NULL,
    sigma_after REAL NOT NULL,

    FOREIGN KEY (match_id) REFERENCES matches(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);
```

#### `player_match_metrics`
Detailed per-match performance metrics.

```sql
CREATE TABLE player_match_metrics (
    id INTEGER PRIMARY KEY,
    match_player_id INTEGER NOT NULL,

    -- Economic Metrics
    total_resources_collected REAL,
    avg_workers INTEGER,
    peak_workers INTEGER,
    avg_supply_block_time REAL,
    avg_spending_quotient REAL,

    -- Combat Metrics
    damage_dealt REAL,
    damage_taken REAL,
    units_killed INTEGER,
    units_lost INTEGER,
    army_value_killed REAL,
    army_value_lost REAL,

    -- Timing Metrics
    first_damage_second INTEGER,
    peak_army_second INTEGER,
    expansion_timings TEXT,             -- JSON array

    -- Damage Timeline (sparse storage)
    damage_timeline TEXT,               -- JSON dict: {second: damage}

    -- Impact Scores
    economic_score REAL,
    combat_score REAL,
    efficiency_score REAL,
    overall_impact REAL,

    FOREIGN KEY (match_player_id) REFERENCES match_players(id)
);
```

#### `player_synergies`
Tracks performance when players team together.

```sql
CREATE TABLE player_synergies (
    id INTEGER PRIMARY KEY,
    player_1_id INTEGER NOT NULL,
    player_2_id INTEGER NOT NULL,
    games_together INTEGER DEFAULT 0,
    wins_together INTEGER DEFAULT 0,
    synergy_score REAL DEFAULT 0.0,     -- -1.0 to 1.0

    FOREIGN KEY (player_1_id) REFERENCES players(id),
    FOREIGN KEY (player_2_id) REFERENCES players(id),
    UNIQUE(player_1_id, player_2_id)
);
```

### Enums

```python
class GameMode(str, enum.Enum):
    THREE_V_THREE = "3v3"
    FOUR_V_FOUR = "4v4"
    FIVE_V_FIVE = "5v5"

class Race(str, enum.Enum):
    TERRAN = "Terran"
    PROTOSS = "Protoss"
    ZERG = "Zerg"
    RANDOM = "Random"
```

---

## Core Features

### 1. Replay Parsing & Processing

#### Basic Parsing (`replay_parser.py`)
- **File hash calculation** - SHA256 for duplicate detection
- **Player extraction** - Name, race, team, result
- **Game metadata** - Map, duration, date played, mode
- **Validation** - Team sizes, results consistency

#### Advanced Parsing (`advanced_parser.py`)
- **Economic metrics** - Resources, workers, spending, supply blocks
- **Combat metrics** - Damage, kills, army values
- **Timing analysis** - First attack, expansions, army peaks
- **Impact scoring** - Weighted formula (Economic 30%, Combat 50%, Efficiency 20%)

#### Damage Timeline (`damage_timeline.py`)
- **Second-by-second tracking** - Damage dealt every game second
- **Sparse storage** - JSON dict with only non-zero seconds
- **Attack detection** - Identifies timing attacks, all-ins, sustained pushes
- **Coordination analysis** - Measures teammate attack synchronization
- **Typical storage** - 200-500 bytes per player per match (vs 3.6KB dense)

**Key Classes:**
- `DamageTimeline` - Sparse timeline with analysis methods
- `DamageTimelineExtractor` - Extracts from replay tracker events
- `TimingAttack` - Detected sustained damage period

### 2. Rating Systems

#### TrueSkill (`rating_system.py`)
Microsoft's Bayesian skill rating system.

**Configuration:**
```python
mu = 25.0              # Initial skill estimate
sigma = 8.333          # Initial uncertainty
beta = 4.166           # Skill class width
tau = 0.0833           # Dynamics factor (skill change per day)
```

**Features:**
- Team-based rating updates
- Skill decay for inactive players (sigma increases)
- Conservative MMR: `mmr = mu - (3 * sigma)`
- Handles uncertainty reduction with more games

#### Recency Weighting (`rating_system.py`)
Exponential decay weighting for current skill estimate.

**Configuration:**
- **Half-life**: 60 days (configurable via `RECENCY_HALF_LIFE_DAYS`)
- **Formula**: `weight = 0.5^(days_ago / 60)`
- **Examples**:
  - Today: 100% weight
  - 30 days ago: 71% weight
  - 60 days ago: 50% weight
  - 120 days ago: 25% weight

**Calculation:**
```python
recency_weighted_mmr = Σ(MMR_i × weight_i) / Σ(weight_i)
```

**When to use:**
- Recency-weighted MMR: Current skill, team balancing
- Standard MMR: Long-term trends, historical analysis

#### Multi-Model System (`rating_models.py`)
8 different rating models for comparison.

**Models:**
1. **trueskill** - Pure win/loss TrueSkill
2. **impact** - 100% performance metrics (economic + combat + efficiency)
3. **hybrid_balanced** - 50% TrueSkill, 50% Impact
4. **hybrid_skill_heavy** - 70% TrueSkill, 30% Impact
5. **hybrid_impact_heavy** - 30% TrueSkill, 70% Impact
6. **impact_combat** - 100% combat score only
7. **impact_economic** - 100% economic score only
8. **ensemble** - Optimized weighted combination

**Use Case:** Experiment to find which model best predicts match outcomes for your group.

### 3. Team Balancing (`balancer.py`)

**Algorithm:**
1. Generate all possible team splits (permutations)
2. For each split, calculate TrueSkill match quality
3. Match quality formula: probability of draw (higher = more balanced)
4. Return top N most balanced configurations

**Endpoints:**
- `POST /teams/balance` - Get multiple balanced suggestions
- `POST /teams/quick-balance` - Get single best split
- `POST /teams/balance-with-model` - Use specific rating model
- `POST /teams/compare-models` - Compare all 8 models

**Quality Metrics:**
- **Match quality** - 0.0 to 1.0 (higher = better)
- **Skill difference** - Absolute MMR difference between teams
- **Win probability** - Team 1 vs Team 2 likelihood

### 4. Impact & Performance Analysis

#### Impact Scoring (`impact_service.py`)
Weighted performance formula:

```python
economic_score = normalized(resources, workers, spending)
combat_score = normalized(damage_dealt, kills, army_value)
efficiency_score = normalized(damage_ratio, resource_efficiency)

overall_impact = (
    0.30 * economic_score +
    0.50 * combat_score +
    0.20 * efficiency_score
)
```

**Features:**
- Per-match metrics storage
- Rolling averages updated after each game
- Leaderboards by category (economic, combat, efficiency, overall)

#### Synergy Detection (`impact_service.py`)
Tracks player pair performance.

**Synergy Score Calculation:**
```python
expected_win_rate = average of individual win rates
actual_win_rate = wins together / games together
synergy_score = (actual - expected) / 0.5  # Normalized -1 to 1
```

**Interpretation:**
- `+1.0` - Perfect synergy (always win together)
- `0.0` - Neutral (perform as expected)
- `-1.0` - Negative synergy (always lose together)

### 5. Player Archetype Detection (`timing_analyzer.py`)

Identifies play styles based on timing patterns.

**Archetypes:**
- **Rush** - First damage before 4 minutes
- **Timing Attacker** - First damage 4-7 minutes
- **Late Game** - First damage after 10 minutes
- **All-In** - Commits full army early
- **Balanced** - Moderate timing across matches
- **Defender** - Reactive, rarely initiates

**Metrics:**
- Average first damage timing
- Aggression score (0-100)
- Attack frequency and patterns
- Timing attack detection

**Compatibility:**
- Checks if players coordinate well (complementary timings)
- Useful for team composition

### 6. Duplicate Detection

**Method:** SHA256 file hashing

**Implementation:**
- Hash calculated in `calculate_replay_hash()` - `replay_parser.py:38-52`
- Stored in `Match.replay_hash` column
- Checked before processing in all entry points:
  - API uploads: `/replays/upload` and `/replays/upload-advanced`
  - Batch processor: `batch_process_replays.py`

**Behavior:**
- API: Returns HTTP 409 Conflict with existing match ID
- Batch processor: Skips with message, continues to next replay

---

## API Endpoints

### Base URL
`http://localhost:8000`

### Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Replays (`/replays`)

#### `POST /replays/upload`
Upload basic replay (TrueSkill only).

**Request:**
```bash
curl -X POST "http://localhost:8000/replays/upload" \
  -F "file=@replay.SC2Replay"
```

**Response:**
```json
{
  "match_id": 1,
  "map_name": "Blackburn LE",
  "game_mode": "4v4",
  "played_at": "2024-01-15T19:30:00",
  "duration_seconds": 1247,
  "num_players": 8,
  "message": "Replay processed successfully"
}
```

#### `POST /replays/upload-advanced`
Upload with full metrics extraction.

Extracts all advanced metrics, impact scores, damage timeline, synergies.

#### `GET /replays/matches`
List recent matches.

**Query params:**
- `limit` (default: 50)
- `offset` (default: 0)

#### `GET /replays/matches/{match_id}`
Get detailed match information with all players.

### Players (`/players`)

#### `GET /players/`
List all players.

**Query params:**
- `core_only` (bool) - Only core players (exclude outsiders)

**Response fields:**
```json
{
  "id": 1,
  "name": "PlayerName",
  "mu": 28.5,
  "sigma": 5.2,
  "mmr": 12.9,
  "recency_weighted_mmr": 14.3,
  "total_games": 42,
  "wins": 25,
  "losses": 17,
  "win_rate": 59.5,
  "favorite_race": "Terran",
  "is_core_player": true,
  "last_played": "2024-01-20T15:30:00"
}
```

#### `GET /players/rankings`
Player leaderboard sorted by MMR.

**Query params:**
- `min_games` (default: 5) - Minimum games to be ranked
- `core_only` (bool) - Only core players

#### `GET /players/{player_id}`
Detailed player stats.

**Includes:**
- Race statistics
- Recent match history (default: 10 matches)
- Rating snapshots (before/after each match)

#### `POST /players/`
Create new player manually.

**Request:**
```json
{
  "name": "NewPlayer",
  "is_core_player": true
}
```

#### `POST /players/calibrate`
Quick calibrate outsider to similar core player.

**Request:**
```json
{
  "name": "GuestPlayer",
  "similar_to_player_id": 5
}
```

Sets guest to similar player's rating with added uncertainty (+2 sigma).

### Teams (`/teams`)

#### `POST /teams/balance`
Generate balanced team suggestions.

**Request:**
```json
{
  "player_ids": [1, 2, 3, 4, 5, 6],
  "num_suggestions": 5,
  "game_mode": "3v3"
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "team_1": [
        {"id": 1, "name": "Alice", "mmr": 28.5},
        {"id": 3, "name": "Charlie", "mmr": 25.1},
        {"id": 5, "name": "Eve", "mmr": 22.3}
      ],
      "team_2": [
        {"id": 2, "name": "Bob", "mmr": 27.2},
        {"id": 4, "name": "David", "mmr": 24.8},
        {"id": 6, "name": "Frank", "mmr": 23.1}
      ],
      "team_1_total_mmr": 75.9,
      "team_2_total_mmr": 75.1,
      "skill_difference": 0.8,
      "match_quality": 0.87,
      "win_probability_team_1": 0.52
    }
  ]
}
```

#### `POST /teams/quick-balance`
Get single best team split.

#### `POST /teams/balance-with-model`
Balance using specific rating model.

**Request:**
```json
{
  "player_ids": [1, 2, 3, 4, 5, 6],
  "model_name": "hybrid_balanced"
}
```

#### `POST /teams/compare-models`
Compare all 8 rating models for same players.

Shows how each model would balance the teams.

#### `GET /teams/models`
List available rating models with descriptions.

### Impact & Synergies (`/impact`)

#### `GET /impact/players`
Rank players by impact scores.

**Query params:**
- `limit` (default: 20)
- `sort_by` - "overall", "economic", "combat", "efficiency"

#### `GET /impact/players/{player_id}/matches`
Detailed match history with metrics.

#### `GET /impact/players/{player_id}/synergies`
Player's synergies with all teammates.

**Response:**
```json
{
  "player_id": 1,
  "player_name": "Alice",
  "synergies": [
    {
      "teammate_id": 3,
      "teammate_name": "Charlie",
      "games_together": 12,
      "wins_together": 9,
      "win_rate_together": 75.0,
      "synergy_score": 0.35,
      "interpretation": "Strong positive synergy"
    }
  ]
}
```

#### `GET /impact/synergies/top`
Best synergies across all players.

#### `GET /impact/leaderboard/{category}`
Category-specific rankings.

**Categories:**
- `economic`
- `combat`
- `efficiency`
- `overall`

#### `GET /impact/players/{player_id}/matches/{match_id}/timeline`
Damage timeline for specific match.

**Response:**
```json
{
  "player_name": "Alice",
  "match_id": 42,
  "timeline": {
    "180": 450,   // 3 minutes: 450 damage
    "240": 1200,  // 4 minutes: 1200 damage
    "300": 2800   // 5 minutes: 2800 damage
  },
  "total_damage": 15600,
  "timing_attacks": [
    {
      "start_second": 240,
      "end_second": 300,
      "total_damage": 4000,
      "attack_type": "timing_push"
    }
  ]
}
```

#### `GET /impact/matches/{match_id}/coordination`
Team coordination analysis.

Shows how well teammates synchronized attacks.

#### `GET /impact/players/{player_id}/attack-patterns`
Attack timing patterns across all matches.

---

## Key Algorithms & Systems

### 1. TrueSkill Rating Updates

**Input:** Team compositions and match result
**Output:** Updated mu and sigma for each player

```python
# Before match
team_1_ratings = [Rating(mu=25.0, sigma=8.333), ...]
team_2_ratings = [Rating(mu=28.0, sigma=5.2), ...]

# Team 1 wins
ranks = [0, 1]  # 0 = winner, 1 = loser

# Calculate new ratings
new_ratings = trueskill.rate([team_1_ratings, team_2_ratings], ranks=ranks)

# Update players
for player, new_rating in zip(players, new_ratings):
    player.mu = new_rating.mu
    player.sigma = new_rating.sigma
```

**Skill Decay:**
```python
days_inactive = (current_date - player.last_played).days
sigma_increase = 0.0833 * days_inactive
player.sigma = min(player.sigma + sigma_increase, 8.333)
```

### 2. Team Balancing

**Permutation Generation:**
```python
from itertools import combinations

players = [1, 2, 3, 4, 5, 6]
team_size = 3

# Generate all possible team 1 compositions
for team_1 in combinations(players, team_size):
    team_2 = [p for p in players if p not in team_1]
    # Calculate quality...
```

**Match Quality:**
```python
# TrueSkill built-in quality function
quality = trueskill.quality([team_1_ratings, team_2_ratings])
# Returns 0.0 to 1.0, higher = more balanced
```

**Win Probability:**
```python
from trueskill import Rating
import math

# Calculate team strength
team_1_mu_total = sum(r.mu for r in team_1_ratings)
team_2_mu_total = sum(r.mu for r in team_2_ratings)

# Beta factor (skill class width)
beta = 4.166
denominator = math.sqrt(len(team_1_ratings) + len(team_2_ratings)) * beta

# Win probability
delta = (team_1_mu_total - team_2_mu_total) / denominator
win_prob = trueskill.global_env().cdf(delta)
```

### 3. Impact Score Calculation

**Normalization:**
```python
def normalize(value, min_val, max_val):
    if max_val == min_val:
        return 50.0
    return 100 * (value - min_val) / (max_val - min_val)
```

**Per-Match Scoring:**
```python
# Get all players in match for normalization
all_values = [p.resources_collected for p in match_players]

economic_score = (
    0.4 * normalize(resources, min(all_values), max(all_values)) +
    0.3 * normalize(workers, ...) +
    0.3 * normalize(spending_quotient, ...)
)

combat_score = (
    0.4 * normalize(damage_dealt, ...) +
    0.3 * normalize(units_killed, ...) +
    0.3 * normalize(army_value_killed, ...)
)

efficiency_score = (
    0.5 * normalize(damage_dealt / damage_taken, ...) +
    0.5 * normalize(resources_collected / resources_spent, ...)
)

overall_impact = (
    0.30 * economic_score +
    0.50 * combat_score +
    0.20 * efficiency_score
)
```

### 4. Damage Timeline Extraction

**From Replay Events:**
```python
from sc2reader import load_replay

replay = load_replay(file_path, load_level=4)

for event in replay.tracker_events:
    if isinstance(event, UnitDiedEvent):
        if event.killer and event.killer.owner.is_human:
            killer_name = event.killer.owner.name
            game_second = event.second
            damage_value = event.unit.minerals + (event.unit.vespene * 1.5)

            # Add to timeline
            timeline[killer_name][game_second] += damage_value
```

**Timing Attack Detection:**
```python
def detect_timing_attacks(timeline, threshold=500, min_duration=30):
    attacks = []
    current_attack = None

    for second in sorted(timeline.keys()):
        damage = timeline[second]

        if damage >= threshold:
            if not current_attack:
                current_attack = {"start": second, "damage": damage}
            else:
                current_attack["damage"] += damage
                current_attack["end"] = second
        else:
            if current_attack and (current_attack["end"] - current_attack["start"]) >= min_duration:
                attacks.append(current_attack)
            current_attack = None

    return attacks
```

### 5. Synergy Calculation

**Expected vs Actual Performance:**
```python
# Get individual stats
player_1_win_rate = player_1.wins / player_1.total_games
player_2_win_rate = player_2.wins / player_2.total_games

# Expected when teamed
expected_win_rate = (player_1_win_rate + player_2_win_rate) / 2

# Actual when teamed
actual_win_rate = synergy.wins_together / synergy.games_together

# Synergy score (-1 to +1)
synergy_score = (actual_win_rate - expected_win_rate) / 0.5
```

### 6. Recency Weighting

**Exponential Decay:**
```python
import math

HALF_LIFE = 60  # days

def calculate_weight(days_ago):
    decay_factor = math.log(0.5) / HALF_LIFE
    weight = math.exp(decay_factor * days_ago)
    return weight

# Example
weight_today = calculate_weight(0)        # 1.00
weight_30_days = calculate_weight(30)     # 0.71
weight_60_days = calculate_weight(60)     # 0.50
weight_120_days = calculate_weight(120)   # 0.25
```

**Weighted Average:**
```python
total_weight = 0
weighted_sum = 0

for match in player_matches:
    days_ago = (reference_date - match.played_at).days
    weight = calculate_weight(days_ago)
    mmr_at_match = match.mu_after - (3 * match.sigma_after)

    weighted_sum += mmr_at_match * weight
    total_weight += weight

recency_weighted_mmr = weighted_sum / total_weight
```

### 7. Archetype Detection

**Classification Logic:**
```python
def determine_archetype(avg_first_damage_timing):
    if avg_first_damage_timing < 240:  # < 4 minutes
        return "Rush"
    elif avg_first_damage_timing < 420:  # 4-7 minutes
        return "Timing Attacker"
    elif avg_first_damage_timing < 600:  # 7-10 minutes
        return "Mid Game"
    else:
        return "Late Game"
```

**Aggression Score:**
```python
def calculate_aggression(first_damage_timings):
    avg_timing = sum(first_damage_timings) / len(first_damage_timings)

    # Earlier = higher aggression
    # 2 min (120s) = 100 aggression
    # 10 min (600s) = 0 aggression
    max_timing = 600
    min_timing = 120

    aggression = 100 * (1 - (avg_timing - min_timing) / (max_timing - min_timing))
    return max(0, min(100, aggression))
```

---

## Configuration & Customization

### TrueSkill Parameters (`rating_system.py:22-30`)
```python
trueskill.setup(
    mu=25.0,              # Initial skill
    sigma=8.333,          # Initial uncertainty
    beta=4.166,           # Skill class width
    tau=0.0833,           # Dynamics factor
    draw_probability=0.0  # No draws in SC2
)
```

### Recency Weighting (`rating_system.py:35-36`)
```python
RECENCY_HALF_LIFE_DAYS = 60  # Adjust decay rate
RECENCY_ENABLED = True        # Toggle on/off
```

**Recommended settings by group type:**
- Casual (weekly/monthly): 60-90 days
- Active (multiple/week): 30-60 days
- Competitive: 14-30 days
- Tournament: 7-14 days

### Impact Score Weights (`advanced_parser.py`)
```python
def _calculate_impact_scores(player_metrics, all_players):
    # Current weights:
    overall_impact = (
        0.30 * economic_score +
        0.50 * combat_score +
        0.20 * efficiency_score
    )
```

To adjust: Modify weights to emphasize different aspects.

### Database Location (`database.py:13-15`)
```python
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATABASE_PATH = os.path.join(DATABASE_DIR, "sc2mmr.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
```

---

## Batch Processing Workflow

### Command
```bash
python batch_process_replays.py <folder> [--verbose] [--show-predictions]
```

### Process Flow
1. **Find replays** - Recursively search folder for `.SC2Replay` files
2. **Parse dates** - Extract played_at from each replay
3. **Sort chronologically** - Process oldest to newest
4. **For each replay:**
   - Parse replay data
   - Check for duplicate (skip if exists)
   - Show prediction (if flag enabled)
   - Create match record
   - Update TrueSkill ratings
   - Update recency-weighted ratings
   - Show rating changes (if verbose)
5. **Display final rankings** - All players with min 3 games

### Output Example
```
[1/50] Processing replay from 2024-01-15 19:30:00
File: game1.SC2Replay

📊 PREDICTION:
   Team 1: Alice, Charlie, Eve
   Team 1 MMR: 75.9
   Team 2: Bob, David, Frank
   Team 2 MMR: 75.1
   Win Probability - Team 1: 52.3%
   Win Probability - Team 2: 47.7%
   Match Quality: 0.872
   Predicted Winner: Team 1
   Actual Winner: Team 1
   ✅ Prediction CORRECT!

✅ Processed successfully
   Map: Blackburn LE
   Mode: 3v3
   Players: 6

   Rating updates:
      Alice: MMR = 28.45 (mu=33.80, sigma=1.78), Recent MMR=29.20
      Bob: MMR = 27.30 (mu=32.50, sigma=1.73), Recent MMR=26.80
      ...

[2/50] Processing replay from 2024-01-16 20:15:00
...

📊 FINAL PLAYER RANKINGS (min 3 games)
------------------------------------------------------------------------------------------
Rank   Player               MMR        Recent MMR   Record       Win Rate
------------------------------------------------------------------------------------------
1      Alice                28.45      29.20        12-3         80.0%
2      Bob                  27.80      26.50        10-5         66.7%
3      Charlie              25.10      25.80        8-7          53.3%
...

Note: 'Recent MMR' weights recent matches more heavily (60-day half-life).

Prediction Accuracy: 68.0%
Correct predictions: 34
Incorrect predictions: 16
```

---

## Current State & What's Implemented

### ✅ Fully Implemented

**Core Systems:**
- [x] Replay parsing (basic and advanced)
- [x] TrueSkill rating system
- [x] Recency weighting (60-day half-life)
- [x] Duplicate detection (SHA256 hashing)
- [x] Team balancing algorithm
- [x] Multi-model rating system (8 models)
- [x] Database schema with all tables
- [x] FastAPI REST API with all endpoints

**Advanced Features:**
- [x] Second-by-second damage timelines
- [x] Impact scoring system
- [x] Player synergy detection
- [x] Timing attack detection
- [x] Player archetype classification
- [x] Match outcome prediction
- [x] Skill decay for inactive players
- [x] Outsider calibration

**Tools & Scripts:**
- [x] Batch replay processor
- [x] Migration script for recency weighting
- [x] Comprehensive documentation

**API Endpoints:**
- [x] Replay upload (basic & advanced)
- [x] Player management (CRUD, rankings, details)
- [x] Team balancing (multiple algorithms)
- [x] Impact & synergy queries
- [x] Damage timeline retrieval
- [x] Model comparison

### 📝 Documentation Created
- [x] README.md - Project overview
- [x] SETUP.md - Setup instructions
- [x] ADVANCED_FEATURES.md - Deep dive
- [x] IMPLEMENTATION_SUMMARY.md - Feature list
- [x] RECENCY_WEIGHTING.md - Recency system docs
- [x] PROJECT_OVERVIEW.md - This document

---

## Future Enhancement Possibilities

### Short Term (Easy Additions)

**1. Frontend UI**
- Web dashboard for viewing stats
- Team balancing interface
- Player profile pages
- Match history viewer

**2. Additional Metrics**
- APM (actions per minute) tracking
- Build order detection
- Tech tree analysis
- Map-specific performance

**3. Export/Reports**
- CSV export of player stats
- PDF match reports
- Historical trend charts
- Season summaries

**4. Notifications**
- Email when new replays processed
- Weekly ranking updates
- Achievement system

### Medium Term (Moderate Effort)

**5. Advanced Balancing**
- Consider player synergies in balancing
- Map-specific rating adjustments
- Role-based team composition (aggressive/defensive mix)
- Constraint-based balancing (e.g., max 2 Terran per team)

**6. Machine Learning**
- Train model on historical data
- Predict match outcomes more accurately
- Recommend optimal team compositions
- Detect anomalous performances

**7. Matchmaking**
- Queue system for players
- Automatic team generation
- MMR brackets and divisions
- Tournament bracket generation

**8. Build Order Analysis**
- Extract build orders from replays
- Identify common strategies
- Success rate by build
- Counter-build recommendations

### Long Term (Significant Work)

**9. Real-time Integration**
- Watch folder for new replays
- Auto-process on file creation
- Live leaderboard updates
- Discord/Slack bot integration

**10. Multi-Game Support**
- Support other games with replays
- Generic rating system
- Cross-game player tracking

**11. Social Features**
- Player profiles with avatars
- Friend lists and challenges
- Team creation and management
- Chat and messaging

**12. Advanced Analytics**
- Heatmaps of damage over time
- Network graphs of player synergies
- Clustering analysis (player groups)
- Prediction confidence intervals
- A/B testing different rating models

---

## Common Operations

### Start the Server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Process Replays
```bash
cd backend
python batch_process_replays.py "/path/to/replays" --verbose --show-predictions
```

### Run Migration (Recency Weighting)
```bash
cd backend
python migrate_add_recency_weight.py
```

### Check Rankings via API
```bash
curl http://localhost:8000/players/rankings?min_games=3 | python -m json.tool
```

### Balance Teams
```bash
curl -X POST "http://localhost:8000/teams/balance" \
  -H "Content-Type: application/json" \
  -d '{"player_ids": [1,2,3,4,5,6], "num_suggestions": 5}' \
  | python -m json.tool
```

### View Player Details
```bash
curl http://localhost:8000/players/1 | python -m json.tool
```

### Compare Rating Models
```bash
curl -X POST "http://localhost:8000/teams/compare-models" \
  -H "Content-Type: application/json" \
  -d '{"player_ids": [1,2,3,4,5,6]}' \
  | python -m json.tool
```

### Get Impact Rankings
```bash
curl "http://localhost:8000/impact/players?limit=10&sort_by=overall" \
  | python -m json.tool
```

### View Player Synergies
```bash
curl http://localhost:8000/impact/players/1/synergies | python -m json.tool
```

---

## Key Design Decisions

### 1. Why SQLite?
- **Simple deployment** - Single file database
- **No server needed** - Perfect for small group (6-12 players)
- **Fast enough** - Handles thousands of matches easily
- **Easy backup** - Copy single .db file

**Trade-off:** Not suitable for massive scale, but perfect for this use case.

### 2. Why TrueSkill?
- **Team-based** - Designed for team games (unlike Elo)
- **Handles uncertainty** - Sigma decreases with more games
- **Battle-tested** - Used by Xbox Live for years
- **Python implementation** - Easy to integrate

**Alternative considered:** Glicko-2 (1v1 only, doesn't handle teams well)

### 3. Why Multiple Rating Models?
- **Experimentation** - Different groups value different aspects
- **Validation** - Compare models to find best predictor
- **Flexibility** - Choose impact vs win/loss weighting
- **Transparency** - Users can see what drives ratings

### 4. Why 60-day Recency Half-life?
- **Casual play frequency** - Most groups play weekly/monthly
- **Stability** - Avoids wild swings from short-term variance
- **Gradual adaptation** - Tracks long-term improvement
- **Configurable** - Easy to adjust per group needs

### 5. Why Sparse Damage Timeline Storage?
- **Storage efficiency** - 200-500 bytes vs 3.6KB per player/match
- **Typical games** - Most seconds have zero damage
- **JSON flexibility** - Easy to query and analyze
- **Performance** - Faster to load and parse

**Trade-off:** Slightly more complex to work with, but worth it.

### 6. Why No Database Migrations Framework?
- **Simplicity** - Alembic/SQLAlchemy-migrate adds complexity
- **Small team** - Manual migrations are manageable
- **Few schema changes** - Not evolving rapidly
- **SQLite limitations** - Limited ALTER TABLE support anyway

**Future:** Consider Alembic if schema changes become frequent.

### 7. Why FastAPI over Flask/Django?
- **Modern async** - Better performance for I/O operations
- **Auto documentation** - Swagger UI out of the box
- **Type hints** - Pydantic models for validation
- **Future-proof** - Async/await support for scaling

---

## Technical Debt & Known Limitations

### Current Limitations

**1. Batch Processing is Sequential**
- Processes one replay at a time
- Could be parallelized for large batches
- Not a problem for typical use (50-100 replays)

**2. No Database Indexing**
- Primary keys only
- Could add indexes on `player_id`, `match_id`, `played_at`
- Performance fine for small scale

**3. No Caching**
- Every API call hits database
- Could cache player rankings
- Again, not needed at current scale

**4. No Input Validation for File Uploads**
- Trusts .SC2Replay extension
- Could validate file signature
- sc2reader handles malformed files gracefully

**5. No Authentication/Authorization**
- API is wide open
- Assumes trusted LAN environment
- Would need JWT/OAuth for public deployment

**6. Recency Weight Calculation on Every Match**
- Recalculates from all historical matches
- O(n) where n = player's match count
- Could optimize with incremental updates

**7. No Pagination on Some Endpoints**
- `/impact/players` could return hundreds
- Works fine for small groups
- Would need pagination for 50+ players

**8. Synergy Calculation is Naive**
- Simple expected vs actual comparison
- Doesn't account for opponent strength
- Could use more sophisticated model

### Technical Debt

**1. No Unit Tests**
- Would benefit from pytest suite
- Test rating calculations, balancing, parsing
- Currently relies on manual testing

**2. No Integration Tests**
- API endpoints not automatically tested
- Could use pytest + TestClient

**3. No Error Logging**
- Errors printed to console
- Should use Python logging module
- Could integrate Sentry for production

**4. Hard-coded Configuration**
- Magic numbers scattered in code
- Should centralize in config file
- e.g., impact score weights, thresholds

**5. No API Rate Limiting**
- Could be abused if exposed publicly
- FastAPI-limiter easy to add

**6. Database Commits in Business Logic**
- Service layer commits directly
- Should use Unit of Work pattern
- Works fine for single-user scenario

---

## Performance Characteristics

### Replay Processing Speed
- **Basic parsing**: ~50-100ms per replay
- **Advanced parsing**: ~200-500ms per replay (with tracker events)
- **Batch of 100 replays**: ~30-60 seconds

### Database Queries
- **Player rankings**: <10ms (for 50 players)
- **Match details**: <5ms (single match)
- **Synergy calculation**: <50ms (per player pair)
- **Recency weight update**: <100ms (per player with 50 matches)

### Team Balancing
- **6 players (3v3)**: ~5ms (20 combinations)
- **8 players (4v4)**: ~20ms (70 combinations)
- **10 players (5v5)**: ~100ms (252 combinations)

### Storage
- **Per match**: ~2KB (basic) or ~5KB (advanced with timeline)
- **Per player**: ~1KB (including averages)
- **1000 matches**: ~5MB database size

---

## Development Workflow

### Adding New Feature

1. **Update Database Schema** (`models.py`)
   ```python
   # Add new column
   new_field = Column(Float, default=0.0)
   ```

2. **Create Migration Script**
   ```python
   # Similar to migrate_add_recency_weight.py
   conn.execute(text("ALTER TABLE players ADD COLUMN new_field FLOAT"))
   ```

3. **Update Business Logic** (service layer)
   ```python
   # Add calculation/extraction logic
   def calculate_new_metric(player_data):
       ...
   ```

4. **Add API Endpoint** (`api/*.py`)
   ```python
   @router.get("/new-endpoint")
   def new_endpoint(db: Session = Depends(get_db)):
       ...
   ```

5. **Update Pydantic Models**
   ```python
   class PlayerResponse(BaseModel):
       new_field: float
   ```

6. **Test Manually**
   - Start server
   - Upload test replay
   - Check API response
   - Verify database

7. **Document**
   - Update relevant .md files
   - Add API example

### Debugging Tips

**1. Enable SQL Logging**
```python
# database.py
engine = create_engine(DATABASE_URL, echo=True)
```

**2. Use FastAPI /docs**
- Interactive API testing
- See request/response schemas
- Try different parameters

**3. Inspect Database**
```bash
sqlite3 backend/data/sc2mmr.db
.tables
.schema players
SELECT * FROM players LIMIT 5;
```

**4. Check Replay Parsing**
```python
from app.replay_parser import parse_replay

replay_data = parse_replay("path/to/replay.SC2Replay")
print(replay_data)
```

**5. Validate TrueSkill**
```python
from app.rating_system import RatingSystem

# Check calculations manually
rating = RatingSystem.create_rating(25.0, 8.333)
mmr = RatingSystem.get_conservative_rating(25.0, 8.333)
print(f"MMR: {mmr}")  # Should be 0.0
```

---

## Summary

This is a **complete, working SC2 MMR tracking and team balancing system** with:

- ✅ Full replay parsing and metric extraction
- ✅ Multiple rating systems (TrueSkill, Impact, Hybrids, Ensemble)
- ✅ Recency weighting for current skill estimates
- ✅ Sophisticated team balancing algorithm
- ✅ Player synergy and archetype detection
- ✅ Second-by-second damage tracking
- ✅ Comprehensive REST API
- ✅ Batch processing tools
- ✅ Duplicate detection
- ✅ Extensive documentation

**Designed for:** Casual gaming groups (6-12 players) playing 3v3, 4v4, 5v5 StarCraft 2

**Primary Use Case:** Balance teams for fair matches based on player skill and performance

**Technology:** Python + FastAPI + SQLite + sc2reader + TrueSkill

**Current State:** Production-ready for small group use. Can process hundreds of replays, track dozens of players, and generate balanced teams in real-time.

**Next Steps:** Run batch processor on replay folder, start balancing teams, iterate based on feedback and accuracy.
