"""
AI-Powered Match Commentary Generator

Analyzes replay data and generates natural language insights about matches.
Provides play-by-play style commentary highlighting key moments and performances.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import timedelta

from .models import Match, MatchPlayer, Player, PlayerMatchMetrics
from .advanced_parser import PlayerMetrics


class MatchCommentaryGenerator:
    """Generates AI-powered commentary for SC2 matches."""

    @staticmethod
    def generate_match_summary(db: Session, match_id: int) -> Dict:
        """
        Generate comprehensive commentary for a match.

        Args:
            db: Database session
            match_id: Match ID to analyze

        Returns:
            Dictionary with commentary sections
        """
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return {"error": "Match not found"}

        # Get all participants
        match_players = (
            db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
        )

        # Get metrics
        players_with_metrics = []
        for mp in match_players:
            player = db.query(Player).filter(Player.id == mp.player_id).first()
            metrics = (
                db.query(PlayerMatchMetrics)
                .filter(PlayerMatchMetrics.match_player_id == mp.id)
                .first()
            )

            players_with_metrics.append(
                {"match_player": mp, "player": player, "metrics": metrics}
            )

        # Generate commentary sections
        commentary = {
            "match_id": match_id,
            "overview": MatchCommentaryGenerator._generate_match_overview(
                match, match_players
            ),
            "key_moments": MatchCommentaryGenerator._generate_key_moments(
                match, players_with_metrics
            ),
            "player_performances": MatchCommentaryGenerator._generate_player_performances(
                players_with_metrics
            ),
            "mvp_analysis": MatchCommentaryGenerator._generate_mvp_analysis(
                players_with_metrics
            ),
            "team_analysis": MatchCommentaryGenerator._generate_team_analysis(
                players_with_metrics
            ),
            "match_summary": MatchCommentaryGenerator._generate_final_summary(
                match, players_with_metrics
            ),
            "shap_impacts": MatchCommentaryGenerator._get_shap_impacts(
                db, match_players
            ),
        }

        return commentary

    @staticmethod
    def _get_shap_impacts(db: Session, match_players: List[MatchPlayer]) -> List[Dict]:
        """Get SHAP impacts from PerformanceFeatures if available, else recalculate."""
        if not match_players:
            return []

        try:
            from .models import PerformanceFeatures

            # Try to get from stored features first (check any player in the match)
            mp_ids = [mp.id for mp in match_players]
            perf = (
                db.query(PerformanceFeatures)
                .filter(PerformanceFeatures.match_player_id.in_(mp_ids))
                .filter(PerformanceFeatures.ml_shap_values.isnot(None))
                .first()
            )

            if perf and perf.ml_shap_values:
                # Return the stored SHAP impacts
                return perf.ml_shap_values  # type: ignore

            # Fallback to recalculation (for older matches without stored SHAP)
            from .services.xgboost_predictor import get_xgboost_predictor

            predictor = get_xgboost_predictor()

            team1_ids = [mp.player_id for mp in match_players if mp.team_number == 1]
            team2_ids = [mp.player_id for mp in match_players if mp.team_number == 2]

            if not team1_ids or not team2_ids:
                return []

            prediction = predictor.predict(db, team1_ids, team2_ids)
            return prediction.get("shap_impacts", [])
        except Exception:
            return []

    @staticmethod
    def _generate_match_overview(match: Match, match_players: List[MatchPlayer]) -> str:
        """Generate opening commentary about the match."""
        duration_min = match.duration_seconds // 60
        duration_sec = match.duration_seconds % 60

        team_1 = [mp for mp in match_players if mp.team_number == 1]
        team_2 = [mp for mp in match_players if mp.team_number == 2]

        team_1_won = any(mp.won for mp in team_1)

        overview = f"This {match.game_mode.value} match on {match.map_name} lasted {duration_min} minutes and {duration_sec} seconds. "

        if match.duration_seconds < 300:
            overview += "This was a quick match with an early deciding moment. "
        elif match.duration_seconds > 1200:
            overview += (
                "This was an extended battle with both teams fighting for position. "
            )

        overview += f"Team {'1' if team_1_won else '2'} emerged victorious."

        return overview

    @staticmethod
    def _generate_key_moments(
        match: Match, players_with_metrics: List[Dict]
    ) -> List[str]:
        """Identify and describe key moments in the match."""
        moments = []

        # Group by team
        team_1 = [p for p in players_with_metrics if p["match_player"].team_number == 1]
        team_2 = [p for p in players_with_metrics if p["match_player"].team_number == 2]

        # Earliest expansion timing
        early_expands = []
        for p in players_with_metrics:
            if p["metrics"] and p["metrics"].first_expansion_timing:
                early_expands.append(
                    (p["player"].name, p["metrics"].first_expansion_timing)
                )

        if early_expands:
            early_expands.sort(key=lambda x: x[1])
            fastest = early_expands[0]
            moments.append(
                f"⏱️ {fastest[0]} executed a fast expansion at {fastest[1]} seconds, "
                f"gaining an early economic advantage."
            )

        # Early aggression
        early_damage = []
        for p in players_with_metrics:
            if (
                p["metrics"]
                and hasattr(p["metrics"], "first_damage_timing")
                and p["metrics"].first_damage_timing
            ):
                if p["metrics"].first_damage_timing < 180:  # Under 3 minutes
                    early_damage.append(
                        (p["player"].name, p["metrics"].first_damage_timing)
                    )

        if early_damage:
            early_damage.sort(key=lambda x: x[1])
            aggressor = early_damage[0]
            moments.append(
                f"⚔️ {aggressor[0]} applied early pressure at {aggressor[1]} seconds, "
                f"forcing defensive responses from opponents."
            )

        # Dominant performance
        top_impacts = sorted(
            [
                (p["player"].name, p["metrics"].overall_impact)
                for p in players_with_metrics
                if p["metrics"]
            ],
            key=lambda x: x[1],
            reverse=True,
        )

        if top_impacts and top_impacts[0][1] > 70:
            moments.append(
                f"💪 {top_impacts[0][0]} delivered a dominant performance with an impact score of {top_impacts[0][1]:.1f}/100."
            )

        # Economic powerhouse
        top_economy = sorted(
            [
                (p["player"].name, p["metrics"].total_resources_collected)
                for p in players_with_metrics
                if p["metrics"]
            ],
            key=lambda x: x[1],
            reverse=True,
        )

        if top_economy and top_economy[0][1] > 50000:
            moments.append(
                f"💰 {top_economy[0][0]} amassed {top_economy[0][1]:,} resources, "
                f"establishing economic dominance."
            )

        # Combat excellence
        top_damage = sorted(
            [
                (p["player"].name, p["metrics"].damage_dealt, p["metrics"].damage_ratio)
                for p in players_with_metrics
                if p["metrics"]
            ],
            key=lambda x: x[1],
            reverse=True,
        )

        if top_damage and top_damage[0][1] > 10000:
            moments.append(
                f"🎯 {top_damage[0][0]} dealt {top_damage[0][1]:,} damage with a {top_damage[0][2]:.2f}:1 damage ratio, "
                f"showcasing superior combat micro."
            )

        return moments if moments else ["No significant moments detected."]

    @staticmethod
    def _generate_player_performances(
        players_with_metrics: List[Dict],
    ) -> Dict[str, str]:
        """Generate commentary for each player's performance."""
        performances = {}

        for p in players_with_metrics:
            player_name = p["player"].name
            mp = p["match_player"]
            metrics = p["metrics"]

            if not metrics:
                performances[player_name] = "Performance data not available."
                continue

            # Determine play style
            if metrics.combat_score > metrics.economic_score + 20:
                style = "aggressive, combat-focused"
            elif metrics.economic_score > metrics.combat_score + 20:
                style = "macro-oriented, economy-focused"
            else:
                style = "balanced"

            # Build commentary
            result = "won" if mp.won else "lost"
            mmr_change = (
                f"+{int(abs(mp.mmr_change))}"
                if mp.mmr_change > 0
                else f"-{int(abs(mp.mmr_change))}"
            )

            commentary = (
                f"{player_name} ({mp.race.value}) {result} with a {style} approach. "
                f"Impact Score: {metrics.overall_impact:.1f}/100 "
                f"(Economy: {metrics.economic_score:.1f}, Combat: {metrics.combat_score:.1f}, "
                f"Efficiency: {metrics.efficiency_score:.1f}). "
            )

            # Add specific highlights
            highlights = []

            if metrics.damage_ratio > 2.0:
                highlights.append(
                    f"exceptional {metrics.damage_ratio:.1f}:1 damage efficiency"
                )

            if metrics.spending_efficiency > 0.9:
                highlights.append(
                    f"excellent {metrics.spending_efficiency * 100:.0f}% spending efficiency"
                )

            if metrics.units_killed > metrics.units_lost * 2:
                highlights.append(
                    f"dominant {metrics.units_killed} kills to {metrics.units_lost} losses"
                )

            if highlights:
                commentary += "Highlights: " + ", ".join(highlights) + ". "

            commentary += f"Rating change: {mmr_change} MMR."

            performances[player_name] = commentary

        return performances

    @staticmethod
    def _generate_mvp_analysis(players_with_metrics: List[Dict]) -> Dict:
        """Identify and analyze the MVP of the match."""
        # Separate winning and losing teams
        winners = [p for p in players_with_metrics if p["match_player"].won]
        losers = [p for p in players_with_metrics if not p["match_player"].won]

        # Find MVP (highest impact on winning team)
        if winners:
            mvp = max(
                winners,
                key=lambda p: p["metrics"].overall_impact if p["metrics"] else 0,
            )

            mvp_metrics = mvp["metrics"]
            mvp_name = mvp["player"].name

            analysis = {
                "player_name": mvp_name,
                "team": mvp["match_player"].team_number,
                "impact_score": mvp_metrics.overall_impact if mvp_metrics else 0,
                "reasoning": "",
            }

            if mvp_metrics:
                reasons = []

                if mvp_metrics.combat_score >= 70:
                    reasons.append(
                        f"exceptional combat performance ({mvp_metrics.combat_score:.1f}/100)"
                    )

                if mvp_metrics.economic_score >= 70:
                    reasons.append(
                        f"strong economic foundation ({mvp_metrics.economic_score:.1f}/100)"
                    )

                if mvp_metrics.damage_ratio > 2.5:
                    reasons.append(
                        f"outstanding {mvp_metrics.damage_ratio:.1f}:1 damage efficiency"
                    )

                if mvp_metrics.units_killed > 50:
                    reasons.append(f"{mvp_metrics.units_killed} unit kills")

                analysis["reasoning"] = (
                    f"{mvp_name} earned MVP honors through "
                    + ", ".join(reasons)
                    + f". Their overall impact of {mvp_metrics.overall_impact:.1f}/100 was the highest on their team."
                )
            else:
                analysis["reasoning"] = (
                    f"{mvp_name} made the biggest contribution to their team's victory."
                )

            return analysis

        return {"player_name": "Unknown", "reasoning": "MVP could not be determined."}

    @staticmethod
    def _generate_team_analysis(players_with_metrics: List[Dict]) -> Dict:
        """Analyze team composition and synergy."""
        team_1 = [p for p in players_with_metrics if p["match_player"].team_number == 1]
        team_2 = [p for p in players_with_metrics if p["match_player"].team_number == 2]

        def analyze_team(team, team_num):
            if not team:
                return "No data available"

            # Calculate team averages
            metrics_list = [p["metrics"] for p in team if p["metrics"]]
            if not metrics_list:
                return "Performance metrics not available"

            avg_impact = sum(m.overall_impact for m in metrics_list) / len(metrics_list)
            avg_econ = sum(m.economic_score for m in metrics_list) / len(metrics_list)
            avg_combat = sum(m.combat_score for m in metrics_list) / len(metrics_list)
            avg_efficiency = sum(m.efficiency_score for m in metrics_list) / len(
                metrics_list
            )

            total_damage = sum(m.damage_dealt for m in metrics_list)
            total_resources = sum(m.total_resources_collected for m in metrics_list)

            won = team[0]["match_player"].won

            analysis = (
                f"Team {team_num} {'won' if won else 'lost'} with an average impact of {avg_impact:.1f}/100. "
                f"The team showed {'strong' if avg_econ > 60 else 'moderate'} economic play ({avg_econ:.1f}) "
                f"and {'aggressive' if avg_combat > 60 else 'defensive'} combat ({avg_combat:.1f}). "
                f"Combined, they dealt {total_damage:,} damage and collected {total_resources:,} resources. "
            )

            # Identify team strengths
            if avg_efficiency > 70:
                analysis += "The team displayed excellent efficiency and coordination. "
            elif avg_efficiency < 50:
                analysis += (
                    "The team struggled with resource efficiency and decision-making. "
                )

            return analysis

        return {"team_1": analyze_team(team_1, 1), "team_2": analyze_team(team_2, 2)}

    @staticmethod
    def _generate_final_summary(match: Match, players_with_metrics: List[Dict]) -> str:
        """Generate closing summary of the match."""
        team_1 = [p for p in players_with_metrics if p["match_player"].team_number == 1]
        team_2 = [p for p in players_with_metrics if p["match_player"].team_number == 2]

        team_1_won = team_1[0]["match_player"].won if team_1 else False

        # Calculate team totals
        team_1_impact = (
            sum(p["metrics"].overall_impact for p in team_1 if p["metrics"])
            / len(team_1)
            if team_1
            else 0
        )
        team_2_impact = (
            sum(p["metrics"].overall_impact for p in team_2 if p["metrics"])
            / len(team_2)
            if team_2
            else 0
        )

        impact_diff = abs(team_1_impact - team_2_impact)

        if impact_diff < 10:
            closeness = "closely contested"
        elif impact_diff < 20:
            closeness = "competitive"
        else:
            closeness = "decisive"

        summary = (
            f"In this {closeness} {match.game_mode.value} match on {match.map_name}, "
            f"Team {'1' if team_1_won else '2'} secured the victory. "
        )

        if impact_diff < 10:
            summary += (
                "Both teams performed admirably with nearly matched impact scores, "
            )
            summary += "making this a true test of skill and teamwork. "
        else:
            summary += f"The winning team demonstrated superior overall performance with an average impact "
            summary += f"advantage of {impact_diff:.1f} points. "

        # Find standout player
        all_impacts = [
            (p["player"].name, p["metrics"].overall_impact)
            for p in players_with_metrics
            if p["metrics"]
        ]
        if all_impacts:
            top_player = max(all_impacts, key=lambda x: x[1])
            summary += (
                f"{top_player[0]} stood out as the top performer across both teams."
            )

        return summary
