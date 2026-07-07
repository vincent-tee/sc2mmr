from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..config import settings
from ..models import Match, Player, PlayerRivalry


class RivalryService:
    @staticmethod
    def calculate_all_rivalries(db: Session) -> int:
        """
        Scan all matches and populate player_rivalries table.
        Returns count of rivalries created/updated.
        """
        # AI opponents (Computer (Easy)/(Elite)/etc.) are practice-mode
        # fillers, not real rivals for a real-life friend group - exclude
        # them from rivalry tracking, same as the leaderboard excludes them
        # from rankings (Player.is_ai == 0 in app/api/leaderboard.py).
        ai_player_ids = {
            pid for (pid,) in db.query(Player.id).filter(Player.is_ai == 1).all()
        }

        # Get all matches
        matches = db.query(Match).order_by(Match.played_at).all()

        rivalry_data = {}  # (p1_id, p2_id) -> stats

        for match in matches:
            participants = match.participants
            team1 = [
                p
                for p in participants
                if p.team_number == 1 and p.player_id not in ai_player_ids
            ]
            team2 = [
                p
                for p in participants
                if p.team_number == 2 and p.player_id not in ai_player_ids
            ]

            # Each player on team1 vs each player on team2
            for p1 in team1:
                for p2 in team2:
                    # Ensure consistent ordering
                    pid1, pid2 = (
                        min(p1.player_id, p2.player_id),
                        max(p1.player_id, p2.player_id),
                    )
                    key = (pid1, pid2)

                    if key not in rivalry_data:
                        rivalry_data[key] = {
                            "games": 0,
                            "p1_wins": 0,
                            "p2_wins": 0,
                            "last_match": match,
                            "mmr_swings": [],
                        }

                    rivalry_data[key]["games"] += 1

                    # Determine winner (p1 is the participant object for pid1 if pid1 == p1.player_id)
                    part_1 = p1 if p1.player_id == pid1 else p2
                    # part_2 = p2 if p2.player_id == pid2 else p1 # The other one

                    if part_1.won:
                        rivalry_data[key]["p1_wins"] += 1
                    else:
                        rivalry_data[key]["p2_wins"] += 1

                    # Track MMR swing. Prefer the actual stored display-MMR
                    # snapshot (mmr_after - mmr_before) - it reflects
                    # whichever display formula was live when the match was
                    # recorded, sigma term included. Fall back to the
                    # mu-only approximation only for legacy rows that
                    # predate the mmr_before/after snapshot columns.
                    if part_1.mmr_before is not None and part_1.mmr_after is not None:
                        swing = abs(part_1.mmr_after - part_1.mmr_before)
                    else:
                        swing = (
                            abs(part_1.mu_after - part_1.mu_before)
                            * settings.mmr_mu_multiplier
                        )
                    rivalry_data[key]["mmr_swings"].append(swing)

                    if match.played_at >= rivalry_data[key]["last_match"].played_at:
                        rivalry_data[key]["last_match"] = match

        # Save to database
        count = 0
        for (pid1, pid2), data in rivalry_data.items():
            rivalry = (
                db.query(PlayerRivalry)
                .filter(
                    and_(
                        PlayerRivalry.player1_id == pid1,
                        PlayerRivalry.player2_id == pid2,
                    )
                )
                .first()
            )

            if not rivalry:
                rivalry = PlayerRivalry(player1_id=pid1, player2_id=pid2)
                db.add(rivalry)

            rivalry.games_against = data["games"]
            rivalry.player1_wins = data["p1_wins"]
            rivalry.player2_wins = data["p2_wins"]

            swings = data["mmr_swings"]
            rivalry.avg_mmr_swing = sum(swings) / len(swings) if swings else 0
            rivalry.biggest_upset_mmr = max(swings) if swings else 0

            rivalry.last_match_id = data["last_match"].id
            rivalry.last_match_at = data["last_match"].played_at

            rivalry.rivalry_score = RivalryService.calculate_score(
                data["games"],
                data["p1_wins"],
                data["p2_wins"],
                (datetime.utcnow() - data["last_match"].played_at).days,
            )
            rivalry.updated_at = datetime.utcnow()
            count += 1

        db.commit()
        return count

    @staticmethod
    def calculate_score(games, p1_wins, p2_wins, recency_days):
        if games < 3:
            return 0.0

        # Volume component (0-40 points)
        volume_score = min(games * 2, 40)

        # Closeness component (0-40 points)
        total = p1_wins + p2_wins
        if total > 0:
            # Ratio of min wins to max wins
            win_ratio = min(p1_wins, p2_wins) / max(p1_wins, p2_wins)
            closeness_score = win_ratio * 40
        else:
            closeness_score = 0

        # Recency component (0-20 points)
        if recency_days <= 7:
            recency_score = 20
        elif recency_days <= 30:
            recency_score = 15
        elif recency_days <= 90:
            recency_score = 10
        else:
            recency_score = 5

        return volume_score + closeness_score + recency_score
