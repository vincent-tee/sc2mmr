"""Link immutable pre-game selections only after organizer confirmation.

Roster/time matching suggests candidates. It is not sufficient evidence to
automatically attribute repeated games or replays uploaded out of order.
"""
from datetime import timedelta

from ..models import BalanceSelection, MatchPlayer, PregameJudgment, PostgameFeedback


def match_outcome(db, match, selection):
    if match.played_at is None or selection.started_at > match.played_at:
        raise ValueError("Selection must have been started before the match")
    if match.played_at - selection.started_at > timedelta(hours=2):
        raise ValueError("Match is outside this selection's two-hour start window")
    if selection.map_name and selection.map_name != match.map_name:
        raise ValueError("Match map differs from selected map")
    rows = db.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
    teams = {team: {r.player_id for r in rows if r.team_number == team} for team in (1, 2)}
    if (not all(teams.values()) or len(rows) != len(teams[1] | teams[2])
            or any(r.team_number not in (1, 2) for r in rows)):
        raise ValueError("Match must have two valid teams")
    winners = {r.team_number for r in rows if r.won}
    if len(winners) != 1 or any(bool(r.won) != (r.team_number in winners) for r in rows):
        raise ValueError("Match does not have a consistent winner")
    first = set(map(int, selection.team1_ids_key.split(',')))
    second = set(map(int, selection.team2_ids_key.split(',')))
    if first == teams[1] and second == teams[2]:
        return int(1 in winners)
    if first == teams[2] and second == teams[1]:
        return int(2 in winners)
    raise ValueError("Match teams differ from the selected teams")


def attach_match(db, match, selection):
    if selection.match_id is not None:
        if selection.match_id == match.id:
            return
        raise ValueError("Selection is already linked to another match")
    outcome = match_outcome(db, match, selection)
    changed = db.query(BalanceSelection).filter(
        BalanceSelection.id == selection.id, BalanceSelection.match_id.is_(None)
    ).update({"match_id": match.id, "team1_won": outcome}, synchronize_session=False)
    if changed != 1:
        raise ValueError("Selection was linked concurrently; refresh and retry")
    judgments = db.query(PregameJudgment).filter(PregameJudgment.selection_id == selection.id).all()
    for judgment in judgments:
        judgment.match_id = match.id
        db.query(PostgameFeedback).filter(
            PostgameFeedback.judgment_id == judgment.id, PostgameFeedback.match_id.is_(None)
        ).update({"match_id": match.id}, synchronize_session=False)
