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
    timing_adjusted_mmr: float = 0.0
    handicap_corrected_mmr: float = 0.0
    unified_mmr: float = 0.0

    @classmethod
    def from_player(cls, player: Player) -> "PlayerInfo":
        avg_fdt = player.avg_first_damage_timing or 300
        avg_combat = player.avg_combat_score or 25
        timing_bonus = (300 - avg_fdt) / 60 * 100
        timing_adjusted = player.mmr + timing_bonus
        handicap_corrected = player.handicap_corrected_mmr or player.mmr
        unified = player.unified_mmr or handicap_corrected

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
            timing_adjusted_mmr=timing_adjusted,
            handicap_corrected_mmr=handicap_corrected,
            unified_mmr=unified,
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
    ml_win_probability: Optional[float] = None
    team_1_avg_impact: float = 0.0
    team_2_avg_impact: float = 0.0
    impact_balance_score: float = 1.0
    playstyle_balance_score: float = 1.0
    total_synergy: float = 0.0


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
        team_1_mu, team_1_sigma = TeamBalancer.get_team_rating(team_1)
        team_2_mu, team_2_sigma = TeamBalancer.get_team_rating(team_2)
        delta_mu = team_1_mu - team_2_mu
        sum_sigma = (team_1_sigma**2 + team_2_sigma**2) ** 0.5
        from math import erf, sqrt

        win_prob = 0.5 * (1 + erf(delta_mu / (sum_sigma * sqrt(2))))
        return win_prob

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
        synergy_data: Optional[Dict[str, float]] = None,
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

            team1_synergy = 0.0
            team2_synergy = 0.0
            if synergy_data:

                def get_syn(p_ids):
                    key = ",".join(map(str, sorted(p_ids)))
                    return synergy_data.get(key, 0.0)

                for pair in combinations([p.id for p in team_1], 2):
                    team1_synergy += get_syn(pair)
                for pair in combinations([p.id for p in team_2], 2):
                    team2_synergy += get_syn(pair)

                if len(team_1) >= 3:
                    for trio in combinations([p.id for p in team_1], 3):
                        team1_synergy += get_syn(trio)
                if len(team_2) >= 3:
                    for trio in combinations([p.id for p in team_2], 3):
                        team2_synergy += get_syn(trio)

            total_synergy = team1_synergy + team2_synergy
            synergy_imbalance = abs(team1_synergy - team2_synergy)
            balanced_synergy_score = total_synergy - synergy_imbalance

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
                    total_synergy=balanced_synergy_score,
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

        if len(unique_suggestions) < 2:
            return unique_suggestions[:top_n]

        final = [unique_suggestions[0]]
        synergy_sorted = sorted(
            unique_suggestions[1:], key=lambda x: x.total_synergy, reverse=True
        )
        if synergy_sorted:
            final.append(synergy_sorted[0])
            remaining = [s for s in unique_suggestions if s not in final]
            final.extend(remaining)

        return final[:top_n]

    @staticmethod
    def balance_teams(
        db: Session,
        player_ids: List[int],
        top_n: int = 10,
        map_name: Optional[str] = None,
    ) -> List[TeamSuggestion]:
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        if len(players) != len(player_ids):
            found_ids = {p.id for p in players}
            missing_ids = set(player_ids) - found_ids
            raise ValueError(f"Players not found: {missing_ids}")

        from .models import GroupSynergy

        synergies = (
            db.query(GroupSynergy).filter(GroupSynergy.player_count.in_([2, 3])).all()
        )
        synergy_map = {s.player_ids_key: s.synergy_score for s in synergies}

        player_infos = []
        for p in players:
            info = PlayerInfo.from_player(p)
            if map_name:
                from .models import Match, MatchPlayer
                from sqlalchemy import func

                stats = (
                    db.query(
                        func.count(Match.id).label("total"),
                        func.sum(MatchPlayer.won).label("wins"),
                    )
                    .join(MatchPlayer, Match.id == MatchPlayer.match_id)
                    .filter(MatchPlayer.player_id == p.id)
                    .filter(Match.map_name == map_name)
                    .first()
                )
                if stats and stats.total >= 3:
                    win_rate = (stats.wins or 0) / stats.total
                    if win_rate >= 0.6:
                        info.unified_mmr += 100
                        info.mmr += 100
                    elif win_rate <= 0.4:
                        info.unified_mmr -= 50
                        info.mmr -= 50
            player_infos.append(info)
        return TeamBalancer.generate_team_suggestions(
            player_infos, top_n, synergy_data=synergy_map
        )

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
                "total_synergy": round(suggestion.total_synergy, 1),
            },
        }
