"""Safe, in-place chronological rating recalculation.

Updates existing Player and MatchPlayer rows through the app's normal DB
session (FK-enforced -- see the PRAGMA foreign_keys=ON listener in
app/database.py) rather than a separate raw connection. Never deletes or
recreates MatchPlayer rows, so child tables (PlayerMatchMetrics,
PerformanceFeatures) can never be orphaned by this running -- this is the
fix for the danger the independent review found in the standalone
scripts/recalculate_all_mmrs.py (docs/reviews/2026-09-14-independent-review.md):
that script deletes and rebuilds match_players with a fresh connection that
does not install the same foreign-key hook.

Rating of record is pure TrueSkill (Session 8,
docs/superpowers/campaign/rating-consolidation-log.md) -- this recalculates
mu/sigma/display MMR only. hybrid_mmr/unified_mmr/recency_weighted_mmr are
untouched, same as every other rating path this session.
"""
from collections import defaultdict

import trueskill
from sqlalchemy.orm import Session

from ..models import Player, Match, MatchPlayer
from ..rating_system import RatingSystem
from ..rating_policy import decayed_sigma, typical_session_gap, rate_teams


def record_unrated(mp: MatchPlayer, rating: trueskill.Rating) -> None:
    mp.mu_before = mp.mu_after = rating.mu
    mp.sigma_before = mp.sigma_after = rating.sigma
    mp.mmr_before = mp.mmr_after = RatingSystem.calculate_display_mmr(rating.mu, rating.sigma)


def recalculate_ratings_in_place(db: Session) -> dict:
    """Recompute mu/sigma/display-MMR for every player and match_player row,
    processing matches chronologically. Returns a small stats dict."""
    players = db.query(Player).all()
    players_by_id = {p.id: p for p in players}
    for p in players:
        p.mu = 25.0
        p.sigma = 8.333
        p.mmr = RatingSystem.calculate_display_mmr(25.0, 8.333)
        p.total_games = 0
        p.wins = 0
        p.losses = 0
        p.terran_games = 0
        p.protoss_games = 0
        p.zerg_games = 0
        p.random_games = 0
        p.last_played = None
    db.flush()

    matches = db.query(Match).order_by(Match.played_at.asc()).all()
    state = {}
    history = defaultdict(list)
    matches_processed = 0
    matches_skipped = 0

    for match in matches:
        mps = db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        team1 = [mp for mp in mps if mp.team_number == 1]
        team2 = [mp for mp in mps if mp.team_number == 2]
        winners = {mp.team_number for mp in mps if mp.won}
        if not team1 or not team2 or len(winners) != 1:
            for mp in mps:
                record_unrated(mp, state.get(mp.player_id) or trueskill.Rating(mu=25.0, sigma=8.333))
            matches_skipped += 1
            continue

        now = match.played_at
        for mp in team1 + team2:
            pid = mp.player_id
            old = state.get(pid) or trueskill.Rating(mu=25.0, sigma=8.333)
            prior_times = history[pid]
            days = (now - prior_times[-1]).days if prior_times else 0
            gap = typical_session_gap(prior_times + [now])
            state[pid] = trueskill.Rating(
                mu=old.mu, sigma=decayed_sigma(old.sigma, days, len(prior_times), gap)
            )

        team1_ratings = [state[mp.player_id] for mp in team1]
        team2_ratings = [state[mp.player_id] for mp in team2]
        team1_won = 1 in winners
        new_t1, new_t2 = rate_teams(team1_ratings, team2_ratings, team1_won)

        for group, olds, news in ((team1, team1_ratings, new_t1), (team2, team2_ratings, new_t2)):
            for mp, old_r, new_r in zip(group, olds, news):
                mp.mu_before, mp.sigma_before = old_r.mu, old_r.sigma
                mp.mu_after, mp.sigma_after = new_r.mu, new_r.sigma
                mp.mmr_before = RatingSystem.calculate_display_mmr(old_r.mu, old_r.sigma)
                mp.mmr_after = RatingSystem.calculate_display_mmr(new_r.mu, new_r.sigma)
                state[mp.player_id] = new_r

        for mp in team1 + team2:
            history[mp.player_id].append(now)
            player = players_by_id.get(mp.player_id)
            if player is None:
                continue
            player.total_games += 1
            if mp.won:
                player.wins += 1
            else:
                player.losses += 1
            if not player.last_played or now > player.last_played:
                player.last_played = now
            race_attr = f"{mp.race.value.lower()}_games"
            if hasattr(player, race_attr):
                setattr(player, race_attr, getattr(player, race_attr) + 1)

        matches_processed += 1

    for pid, rating in state.items():
        player = players_by_id.get(pid)
        if player is None:
            continue
        player.mu = rating.mu
        player.sigma = rating.sigma
        player.mmr = RatingSystem.calculate_display_mmr(rating.mu, rating.sigma)

    db.commit()
    return dict(
        players_updated=len(players),
        matches_processed=matches_processed,
        matches_skipped=matches_skipped,
    )
