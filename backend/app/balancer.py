from typing import List, Dict, Tuple, Optional, Any, cast
from itertools import combinations
from dataclasses import dataclass
import trueskill
from sqlalchemy.orm import Session
from .models import Player


@dataclass
class PlayerInfo:
    id: int
    name: str
    mu: float
    sigma: float
    mmr: float
    overall_impact: float
    total_games: int
    aggression_score: float = 50.0
    avg_first_damage_timing: float = 300.0
    avg_combat_score: float = 25.0
    economic_score: float = 60.0
    efficiency_score: float = 55.0

    @classmethod
    def from_player(cls, player: Player) -> "PlayerInfo":
        avg_fdt = player.avg_first_damage_timing or 300
        avg_combat = player.avg_combat_score or 25

        return cls(
            id=player.id,
            name=player.name,
            mu=player.mu,
            sigma=player.sigma,
            mmr=player.mmr,
            overall_impact=player.avg_overall_impact or 50.0,
            total_games=player.total_games,
            aggression_score=player.avg_aggression_score or 50.0,
            avg_first_damage_timing=avg_fdt,
            avg_combat_score=avg_combat,
            economic_score=player.avg_economic_score or 60.0,
            efficiency_score=player.avg_efficiency_score or 55.0,
        )


@dataclass
class TeamSuggestion:
    team_1: List[PlayerInfo]
    team_2: List[PlayerInfo]
    team_1_mmr: float
    team_2_mmr: float
    mmr_difference: float
    win_probability: float
    match_quality: float
    team_1_avg_impact: float = 0.0
    team_2_avg_impact: float = 0.0
    impact_balance_score: float = 1.0
    playstyle_balance_score: float = 1.0
    balance_prediction_id: Optional[int] = None


class TeamBalancer:
    @staticmethod
    def get_team_rating(players: List[PlayerInfo]) -> Tuple[float, float]:
        team_mu = sum(p.mu for p in players)
        team_sigma = (sum(p.sigma**2 for p in players)) ** 0.5
        return team_mu, team_sigma

    @staticmethod
    def calculate_match_quality(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo]
    ) -> float:
        team_1_ratings = [trueskill.Rating(mu=p.mu, sigma=p.sigma) for p in team_1]
        team_2_ratings = [trueskill.Rating(mu=p.mu, sigma=p.sigma) for p in team_2]
        return trueskill.quality([team_1_ratings, team_2_ratings])

    @staticmethod
    def calculate_win_probability(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo]
    ) -> float:
        from .rating_policy import win_probability
        return win_probability(
            [trueskill.Rating(mu=p.mu, sigma=p.sigma) for p in team_1],
            [trueskill.Rating(mu=p.mu, sigma=p.sigma) for p in team_2],
        )

    @staticmethod
    def snake_draft(
        players: List[PlayerInfo], num_teams: int = 2
    ) -> Dict[str, Any]:
        """
        POC: captain's-draft team construction, a different paradigm from
        generate_team_suggestions (which exhaustively searches for the
        mathematically closest split by MMR). This is a
        transparent, explainable procedure - valued for that transparency
        and its familiar pickup-game framing, not validated as producing
        better-balanced teams than the exhaustive method. Do not present
        its output as a proven improvement without the same rigor as any
        other balance/rating claim in this project.

        Ranks all players by display MMR; the top `num_teams` become
        captains (one per team, highest MMR each). Remaining players are
        drafted in snake order (pick order reverses each round: e.g. for
        2 teams, 0,1,1,0,0,1,1,0,... ) with each captain greedily taking
        the highest-remaining-MMR player. The reversal is what keeps this
        roughly fair despite team 0 picking "first" - summed pick-rank
        across teams stays close (verified: first 10 picks split 27/28
        for a 2-team draft over a 10-player pool).
        """
        if num_teams < 2:
            raise ValueError("Need at least 2 teams")
        if len(players) < num_teams:
            raise ValueError(f"Need at least {num_teams} players, got {len(players)}")

        ranked = sorted(players, key=lambda p: p.mmr, reverse=True)
        captains = ranked[:num_teams]
        pool = ranked[num_teams:]

        teams: List[List[PlayerInfo]] = [[c] for c in captains]
        draft_log: List[Dict[str, Any]] = [
            {"pick_number": i + 1, "team_index": i, "player": c, "role": "captain"}
            for i, c in enumerate(captains)
        ]

        pick_number = num_teams
        round_num = 0
        while pool:
            order = list(range(num_teams))
            if round_num % 2 == 1:
                order.reverse()
            for team_idx in order:
                if not pool:
                    break
                pick = pool.pop(0)
                teams[team_idx].append(pick)
                pick_number += 1
                draft_log.append(
                    {
                        "pick_number": pick_number,
                        "team_index": team_idx,
                        "player": pick,
                        "role": "pick",
                    }
                )
            round_num += 1

        return {"teams": teams, "draft_log": draft_log}

    @staticmethod
    def suggest_swaps(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo], top_n: int = 3
    ) -> Dict[str, Any]:
        """
        Given a FIXED split (from a manual draft, hand-picked teams, etc.),
        suggest the best single-player swaps to improve balance. Uses the
        same proven TrueSkill match-quality/win-probability scoring as the
        exhaustive-search balancer (calculate_match_quality,
        calculate_win_probability) - not the unproven ML predictor.

        Evaluates every single-player swap between the two teams (cheap:
        len(team_1) * len(team_2) evaluations) and ranks by improvement in
        match quality. This is a LOCAL search (one swap at a time) around a
        fixed starting point, not a claim that the result is globally
        optimal - for that, use generate_team_suggestions instead, which
        enumerates every possible split from scratch.
        """
        current_quality = TeamBalancer.calculate_match_quality(team_1, team_2)
        current_win_prob = TeamBalancer.calculate_win_probability(team_1, team_2)

        candidates = []
        for i, p1 in enumerate(team_1):
            for j, p2 in enumerate(team_2):
                new_team_1 = team_1[:i] + [p2] + team_1[i + 1 :]
                new_team_2 = team_2[:j] + [p1] + team_2[j + 1 :]
                new_quality = TeamBalancer.calculate_match_quality(new_team_1, new_team_2)
                new_win_prob = TeamBalancer.calculate_win_probability(new_team_1, new_team_2)
                candidates.append(
                    {
                        "player_out_of_team_1": p1,
                        "player_out_of_team_2": p2,
                        "new_match_quality": new_quality,
                        "new_win_probability": new_win_prob,
                        "quality_delta": new_quality - current_quality,
                    }
                )

        candidates.sort(key=lambda c: -c["quality_delta"])

        return {
            "current_match_quality": current_quality,
            "current_win_probability": current_win_prob,
            "suggestions": candidates[:top_n],
        }

    @staticmethod
    def calculate_impact_balance_score(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo]
    ) -> Tuple[float, float, float]:
        team_1_avg = (
            sum(p.overall_impact for p in team_1) / len(team_1) if team_1 else 0
        )
        team_2_avg = (
            sum(p.overall_impact for p in team_2) / len(team_2) if team_2 else 0
        )

        if team_1_avg == 0 and team_2_avg == 0:
            balance_score = 1.0
        else:
            max_avg = max(team_1_avg, team_2_avg)
            min_avg = min(team_1_avg, team_2_avg)
            balance_score = min_avg / max_avg if max_avg > 0 else 1.0

        return team_1_avg, team_2_avg, balance_score

    @staticmethod
    def calculate_playstyle_balance(
        team_1: List[PlayerInfo], team_2: List[PlayerInfo]
    ) -> float:
        team_1_aggression = (
            sum(p.aggression_score for p in team_1) / len(team_1) if team_1 else 50
        )
        team_2_aggression = (
            sum(p.aggression_score for p in team_2) / len(team_2) if team_2 else 50
        )
        aggression_diff = abs(team_1_aggression - team_2_aggression)
        return 1.0 - (aggression_diff / 100.0)

    @staticmethod
    def generate_team_suggestions(
        players: List[PlayerInfo],
        top_n: int = 10,
    ) -> List[TeamSuggestion]:
        num_players = len(players)
        if num_players < 2:
            raise ValueError(f"Need at least 2 players, got {num_players}")

        if num_players % 2 == 0:
            team_1_size = num_players // 2
        else:
            team_1_size = (num_players // 2) + 1

        suggestions = []
        for team_1_indices in combinations(range(num_players), team_1_size):
            team_1 = [players[i] for i in team_1_indices]
            team_2 = [players[i] for i in range(num_players) if i not in team_1_indices]

            # Rating of record (display MMR) — owner decision 2026-07-02,
            # rating consolidation campaign Phase 5: team sums and the sort
            # key below use display MMR, the measured best predictor.
            team_1_rating = sum(p.mmr for p in team_1)
            team_2_rating = sum(p.mmr for p in team_2)
            rating_diff = abs(team_1_rating - team_2_rating)

            match_quality = TeamBalancer.calculate_match_quality(team_1, team_2)
            win_probability = TeamBalancer.calculate_win_probability(team_1, team_2)
            t1_impact, t2_impact, impact_balance = (
                TeamBalancer.calculate_impact_balance_score(team_1, team_2)
            )
            playstyle_balance = TeamBalancer.calculate_playstyle_balance(team_1, team_2)

            suggestions.append(
                TeamSuggestion(
                    team_1=team_1,
                    team_2=team_2,
                    team_1_mmr=team_1_rating,
                    team_2_mmr=team_2_rating,
                    mmr_difference=rating_diff,
                    win_probability=win_probability,
                    match_quality=match_quality,
                    team_1_avg_impact=t1_impact,
                    team_2_avg_impact=t2_impact,
                    impact_balance_score=impact_balance,
                    playstyle_balance_score=playstyle_balance,
                )
            )

        suggestions.sort(key=lambda x: (x.mmr_difference, abs(x.win_probability - 0.5)))

        def get_canonical_key(s: TeamSuggestion) -> frozenset:
            t1_ids = frozenset(p.id for p in s.team_1)
            t2_ids = frozenset(p.id for p in s.team_2)
            return frozenset([t1_ids, t2_ids])

        seen_configurations: set = set()
        unique_suggestions: List[TeamSuggestion] = []

        for s in suggestions:
            key = get_canonical_key(s)
            if key not in seen_configurations:
                seen_configurations.add(key)
                unique_suggestions.append(s)
            if len(unique_suggestions) >= top_n * 2:
                break

        return unique_suggestions[:top_n]

    @staticmethod
    def _load_player_infos(db: Session, player_ids: List[int]) -> List[PlayerInfo]:
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        if len(players) != len(player_ids):
            found_ids = {p.id for p in players}
            missing_ids = set(player_ids) - found_ids
            raise ValueError(f"Players not found: {missing_ids}")
        return [PlayerInfo.from_player(p) for p in players]

    @staticmethod
    def balance_teams(
        db: Session,
        player_ids: List[int],
        top_n: int = 10,
    ) -> List[TeamSuggestion]:
        player_infos = TeamBalancer._load_player_infos(db, player_ids)
        return TeamBalancer.generate_team_suggestions(player_infos, top_n)

    @staticmethod
    def quick_balance(db: Session, player_ids: List[int]) -> Optional[TeamSuggestion]:
        suggestions = TeamBalancer.balance_teams(db, player_ids, top_n=1)
        return suggestions[0] if suggestions else None


class BalancerStats:
    @staticmethod
    def analyze_suggestion(suggestion: TeamSuggestion) -> Dict[str, Any]:
        # Rating of record (display MMR) — consistent with generate_team_suggestions
        team_1_mmrs = [p.mmr for p in suggestion.team_1]
        team_2_mmrs = [p.mmr for p in suggestion.team_2]
        team_1_total = sum(team_1_mmrs)
        team_2_total = sum(team_2_mmrs)
        team_1_avg = team_1_total / len(team_1_mmrs) if team_1_mmrs else 0
        team_2_avg = team_2_total / len(team_2_mmrs) if team_2_mmrs else 0

        if suggestion.match_quality > 0.8:
            fairness = "Excellent"
        elif suggestion.match_quality > 0.6:
            fairness = "Good"
        elif suggestion.match_quality > 0.4:
            fairness = "Fair"
        else:
            fairness = "Poor"

        return {
            "team_1": {
                "total_mmr": round(team_1_total, 1),
                "avg_mmr": round(team_1_avg, 1),
            },
            "team_2": {
                "total_mmr": round(team_2_total, 1),
                "avg_mmr": round(team_2_avg, 1),
            },
            "balance": {
                "mmr_difference": round(suggestion.mmr_difference, 1),
                "match_quality": round(suggestion.match_quality * 100, 1),
                "win_probability_team_1": round(suggestion.win_probability * 100, 1),
                "win_probability_team_2": round(
                    (1.0 - suggestion.win_probability) * 100, 1
                ),
                "fairness_rating": fairness,
                "team_1_avg_impact": round(suggestion.team_1_avg_impact, 2),
                "team_2_avg_impact": round(suggestion.team_2_avg_impact, 2),
                "impact_balance_score": round(suggestion.impact_balance_score * 100, 1),
                "impact_difference": round(
                    abs(suggestion.team_1_avg_impact - suggestion.team_2_avg_impact), 2
                ),
            },
        }
