"""
Player Playstyle & Synergy Analysis System

Analyzes player behaviors to identify:
- Micro/macro skill balance
- Timing preferences (early/mid/late game)
- Aggression vs defensive styles
- Player archetypes and synergies
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import Player, MatchPlayer, PlayerMatchMetrics


@dataclass
class PlaystyleProfile:
    """Comprehensive player playstyle profile."""
    # Core skills (0-100 scale)
    micro_skill: float  # Unit control, battles, harassment
    macro_skill: float  # Economy, production, expansion

    # Timing preferences (0-1 scale, sums to 1.0)
    early_game_weight: float  # First 10 minutes
    mid_game_weight: float    # 10-20 minutes
    late_game_weight: float   # 20+ minutes

    # Aggression (0-100 scale)
    aggression_score: float  # How aggressive/defensive

    # Primary archetype
    archetype: str  # "Rusher", "Macro Player", "All-Rounder", "Turtle", "Harasser"

    # Confidence (based on # games analyzed)
    confidence: float  # 0-1, higher = more data


@dataclass
class PlayerSynergy:
    """Synergy score between two players."""
    player_1_id: int
    player_2_id: int
    synergy_score: float  # -1 to 1 (negative = clash, positive = synergy)
    reason: str  # Human-readable explanation


class PlaystyleAnalyzer:
    """Analyzes player behavior patterns and synergies."""

    @staticmethod
    def analyze_player_playstyle(db: Session, player_id: int, recent_games: int = 20) -> PlaystyleProfile:
        """
        Analyze a player's playstyle from their recent match metrics.

        Args:
            db: Database session
            player_id: Player to analyze
            recent_games: Number of recent games to analyze

        Returns:
            PlaystyleProfile with player's behavioral tendencies
        """
        # Get player's recent match metrics
        metrics = db.query(PlayerMatchMetrics).join(MatchPlayer).filter(
            MatchPlayer.player_id == player_id
        ).order_by(
            MatchPlayer.id.desc()
        ).limit(recent_games).all()

        if not metrics:
            # Return default profile for new players
            return PlaystyleProfile(
                micro_skill=50.0,
                macro_skill=50.0,
                early_game_weight=0.33,
                mid_game_weight=0.34,
                late_game_weight=0.33,
                aggression_score=50.0,
                archetype="Unknown",
                confidence=0.0
            )

        # === MICRO SKILL ANALYSIS ===
        # Based on: combat efficiency, unit control, harassment success
        micro_indicators = []
        for m in metrics:
            # Army efficiency (kills vs losses ratio)
            if m.army_value_lost and m.army_value_lost > 0:
                kill_ratio = m.army_value_killed / m.army_value_lost
                micro_indicators.append(min(kill_ratio * 20, 100))  # Cap at 100

            # Combat score (provided by impact_service)
            if m.combat_score:
                micro_indicators.append(m.combat_score)

        micro_skill = sum(micro_indicators) / len(micro_indicators) if micro_indicators else 50.0

        # === MACRO SKILL ANALYSIS ===
        # Based on: resource collection, spending efficiency, production consistency
        macro_indicators = []
        for m in metrics:
            # Economic score (provided by impact_service)
            if m.economic_score:
                macro_indicators.append(m.economic_score)

            # Resource collection rate
            if m.minerals_collected:
                # Normalize by game length (avg ~300 minerals/min for average player)
                collection_rate = (m.minerals_collected / m.game_length_seconds) * 60
                macro_indicators.append(min((collection_rate / 300) * 50, 100))

            # Spending efficiency
            if m.avg_unspent_resources is not None:
                # Lower unspent = better (inverse score)
                spending_score = max(0, 100 - (m.avg_unspent_resources / 20))
                macro_indicators.append(spending_score)

        macro_skill = sum(macro_indicators) / len(macro_indicators) if macro_indicators else 50.0

        # === TIMING PREFERENCES ===
        early_damage_times = []
        game_lengths = []

        for m in metrics:
            if m.first_damage_timing:
                early_damage_times.append(m.first_damage_timing)
            if m.game_length_seconds:
                game_lengths.append(m.game_length_seconds)

        # Determine timing weights based on when player is most effective
        avg_first_damage = sum(early_damage_times) / len(early_damage_times) if early_damage_times else 600
        avg_game_length = sum(game_lengths) / len(game_lengths) if game_lengths else 1200

        if avg_first_damage < 360:  # < 6 min = early rusher
            early_game_weight = 0.5
            mid_game_weight = 0.3
            late_game_weight = 0.2
        elif avg_first_damage < 600:  # 6-10 min = standard timing
            early_game_weight = 0.35
            mid_game_weight = 0.40
            late_game_weight = 0.25
        elif avg_game_length > 1800:  # > 30 min games = late game player
            early_game_weight = 0.2
            mid_game_weight = 0.3
            late_game_weight = 0.5
        else:  # Balanced
            early_game_weight = 0.33
            mid_game_weight = 0.34
            late_game_weight = 0.33

        # === AGGRESSION SCORE ===
        aggression_indicators = []
        for m in metrics:
            # Early damage timing (earlier = more aggressive)
            if m.first_damage_timing:
                aggression_from_timing = max(0, 100 - (m.first_damage_timing / 10))
                aggression_indicators.append(aggression_from_timing)

            # Army value killed vs made (killing more = aggressive)
            if m.army_value_made and m.army_value_made > 0:
                kill_ratio = m.army_value_killed / m.army_value_made
                aggression_from_kills = min(kill_ratio * 50, 100)
                aggression_indicators.append(aggression_from_kills)

        aggression_score = sum(aggression_indicators) / len(aggression_indicators) if aggression_indicators else 50.0

        # === ARCHETYPE DETERMINATION ===
        archetype = PlaystyleAnalyzer._determine_archetype(
            micro_skill, macro_skill, early_game_weight, aggression_score
        )

        # === CONFIDENCE ===
        # Based on number of games analyzed (plateaus at 20 games)
        confidence = min(len(metrics) / 20.0, 1.0)

        return PlaystyleProfile(
            micro_skill=micro_skill,
            macro_skill=macro_skill,
            early_game_weight=early_game_weight,
            mid_game_weight=mid_game_weight,
            late_game_weight=late_game_weight,
            aggression_score=aggression_score,
            archetype=archetype,
            confidence=confidence
        )

    @staticmethod
    def _determine_archetype(micro: float, macro: float, early_weight: float, aggression: float) -> str:
        """Determine player archetype from stats."""
        if early_weight > 0.4 and aggression > 70:
            return "Rusher"  # Early aggression specialist
        elif macro > 70 and early_weight < 0.3:
            return "Macro Player"  # Economy-focused, late game
        elif aggression < 30 and macro > 60:
            return "Turtle"  # Defensive, economic buildup
        elif micro > 70 and aggression > 60:
            return "Harasser"  # Micro-intensive harassment
        elif abs(micro - macro) < 15:
            return "All-Rounder"  # Balanced skills
        elif micro > macro + 15:
            return "Micro Specialist"  # Combat focus
        elif macro > micro + 15:
            return "Macro Specialist"  # Economy focus
        else:
            return "Developing"  # Still finding their style

    @staticmethod
    def calculate_player_synergy(
        profile1: PlaystyleProfile,
        profile2: PlaystyleProfile,
        player1_name: str,
        player2_name: str
    ) -> PlayerSynergy:
        """
        Calculate synergy score between two players.

        Synergy considers:
        - Complementary timing preferences (early + late = good)
        - Complementary skill balance (micro + macro = good)
        - Aggression compatibility (both aggressive or both defensive = clash)

        Args:
            profile1: First player's playstyle
            profile2: Second player's playstyle
            player1_name: First player's name
            player2_name: Second player's name

        Returns:
            PlayerSynergy with score and explanation
        """
        synergy_components = []
        reasons = []

        # === TIMING SYNERGY ===
        # Complementary timing is GOOD (early player + late player = balanced team)
        timing_difference = abs(profile1.early_game_weight - profile2.early_game_weight)
        if timing_difference > 0.3:
            timing_synergy = 0.3  # Good complementary timing
            if profile1.early_game_weight > 0.4:
                reasons.append(f"{player1_name}'s early pressure complements {player2_name}'s late game")
            else:
                reasons.append(f"{player2_name}'s early pressure complements {player1_name}'s late game")
        else:
            timing_synergy = -0.1  # Both same timing = okay but not ideal
            if profile1.early_game_weight > 0.4:
                reasons.append(f"Both favor early game - may lack late game power")
            elif profile1.late_game_weight > 0.4:
                reasons.append(f"Both favor late game - may be vulnerable early")

        synergy_components.append(timing_synergy)

        # === SKILL COMPLEMENT SYNERGY ===
        # One micro-focused + one macro-focused = GREAT synergy
        micro_diff = abs(profile1.micro_skill - profile2.micro_skill)
        macro_diff = abs(profile1.macro_skill - profile2.macro_skill)

        skill_balance = (micro_diff + macro_diff) / 2
        if skill_balance > 30:
            skill_synergy = 0.25  # Highly complementary skills
            if profile1.micro_skill > profile2.micro_skill:
                reasons.append(f"{player1_name}'s micro covers {player2_name}'s macro focus")
            else:
                reasons.append(f"{player2_name}'s micro covers {player1_name}'s macro focus")
        elif skill_balance < 15:
            skill_synergy = 0.0  # Similar skills = neutral
            reasons.append(f"Similar skill profiles - straightforward duo")
        else:
            skill_synergy = 0.1  # Moderate complement

        synergy_components.append(skill_synergy)

        # === AGGRESSION COMPATIBILITY ===
        # Similar aggression levels can clash OR synergize based on archetype
        aggression_diff = abs(profile1.aggression_score - profile2.aggression_score)

        if aggression_diff < 20:
            # Similar aggression
            if profile1.aggression_score > 70:
                # Both aggressive = double commitment risk
                aggression_synergy = -0.15
                reasons.append(f"Both highly aggressive - may overcommit")
            elif profile1.aggression_score < 30:
                # Both passive = slow, controlled
                aggression_synergy = 0.1
                reasons.append(f"Both defensive - strong late game potential")
            else:
                # Both moderate
                aggression_synergy = 0.05
        else:
            # Different aggression = good balance
            aggression_synergy = 0.2
            reasons.append(f"Balanced aggression - one pressures while other secures")

        synergy_components.append(aggression_synergy)

        # === ARCHETYPE SYNERGY ===
        # Specific archetype combinations
        archetypes = {profile1.archetype, profile2.archetype}

        if "Rusher" in archetypes and "Macro Player" in archetypes:
            archetype_synergy = 0.3
            reasons.append(f"Classic combo: early rush backed by strong economy")
        elif "Harasser" in archetypes and "Turtle" in archetypes:
            archetype_synergy = 0.25
            reasons.append(f"Effective combo: harassment + secure expansion")
        elif profile1.archetype == profile2.archetype and profile1.archetype != "All-Rounder":
            archetype_synergy = -0.1
            reasons.append(f"Both {profile1.archetype}s - lacks versatility")
        else:
            archetype_synergy = 0.0

        synergy_components.append(archetype_synergy)

        # === FINAL SYNERGY SCORE ===
        # Weight by confidence (less confident = less extreme scores)
        avg_confidence = (profile1.confidence + profile2.confidence) / 2
        raw_synergy = sum(synergy_components)
        final_synergy = raw_synergy * avg_confidence

        # Clamp to [-1, 1]
        final_synergy = max(-1.0, min(1.0, final_synergy))

        # Build explanation
        reason_text = " | ".join(reasons[:3])  # Top 3 reasons

        return PlayerSynergy(
            player_1_id=0,  # Filled in by caller
            player_2_id=0,  # Filled in by caller
            synergy_score=final_synergy,
            reason=reason_text
        )

    @staticmethod
    def get_team_synergy_score(db: Session, player_ids: List[int]) -> Tuple[float, List[str]]:
        """
        Calculate overall team synergy score.

        Args:
            db: Database session
            player_ids: List of player IDs on the team

        Returns:
            Tuple of (total_synergy_score, reasons_list)
        """
        if len(player_ids) < 2:
            return 0.0, []

        # Get all player profiles
        profiles = {}
        player_names = {}
        for pid in player_ids:
            player = db.query(Player).filter(Player.id == pid).first()
            if player:
                profiles[pid] = PlaystyleAnalyzer.analyze_player_playstyle(db, pid)
                player_names[pid] = player.name

        # Calculate pairwise synergies
        synergies = []
        reasons = []

        for i, pid1 in enumerate(player_ids):
            for pid2 in player_ids[i+1:]:
                if pid1 in profiles and pid2 in profiles:
                    synergy = PlaystyleAnalyzer.calculate_player_synergy(
                        profiles[pid1],
                        profiles[pid2],
                        player_names[pid1],
                        player_names[pid2]
                    )
                    synergies.append(synergy.synergy_score)
                    if synergy.synergy_score > 0.15 or synergy.synergy_score < -0.15:
                        reasons.append(f"{player_names[pid1]} + {player_names[pid2]}: {synergy.reason}")

        # Average synergy across all pairs
        avg_synergy = sum(synergies) / len(synergies) if synergies else 0.0

        return avg_synergy, reasons
