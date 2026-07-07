#!/usr/bin/env python3
"""
Backfill Achievements Script

WRITES TO THE DB when run without --dry-run (Rule 1 applies - back up
backend/data/sc2mmr.db before running for real).

Context: achievement awarding (AchievementService.check_and_award_all) was never
wired into the live replay-upload path. A one-time manual run of
POST /achievements/check-all on 2025-12-28 seeded player_achievements for whoever
had games at that moment, but nothing has re-checked achievements since - not for
matches played afterward, and not for players whose total_games only crossed
above 0 after that date. This script re-runs the same check-all logic for every
player who currently qualifies, so historical achievements catch up to the
present state of the database. Going forward, achievements are awarded live on
each new-match upload (see app/api/replays.py and
app/services/match_orchestrator.py), so this script should only need to be run
again if it is ever suspected achievements have drifted out of sync (e.g. after
a bulk data repair).

This mirrors POST /achievements/check-all (same player filter: total_games > 0,
no is_ai exclusion - matching that endpoint's existing, established behavior)
but adds an honest --dry-run mode that performs zero writes: it computes
eligibility with AchievementService's own (side-effect-free) stats/check helpers
and only calls AchievementService.award_achievement (which does the actual
db.add + db.commit) when --dry-run is not passed.

Usage:
    cd backend && python scripts/backfill_achievements.py --dry-run   # report only, no writes
    cd backend && python scripts/backfill_achievements.py             # actually award
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Player, Achievement, PlayerAchievement
from app.services.achievement_service import AchievementService


def backfill(dry_run: bool = False) -> None:
    db = SessionLocal()

    try:
        players = db.query(Player).filter(Player.total_games > 0).all()
        print(f"Found {len(players)} players with total_games > 0")

        all_achievements = (
            db.query(Achievement).filter(Achievement.is_active == True).all()
        )

        players_with_new = 0
        total_new = 0

        for player in players:
            if dry_run:
                stats = AchievementService._calculate_player_stats(db, player.id)
                earned_codes = {
                    pa.achievement.code
                    for pa in db.query(PlayerAchievement)
                    .join(Achievement)
                    .filter(PlayerAchievement.player_id == player.id)
                    .all()
                }

                would_award = []
                for achievement in all_achievements:
                    if achievement.code in earned_codes:
                        continue
                    should_award, trigger_value = AchievementService._check_achievement(
                        db, player, achievement, stats, None
                    )
                    if should_award:
                        would_award.append((achievement.code, trigger_value))

                if would_award:
                    players_with_new += 1
                    total_new += len(would_award)
                    codes = ", ".join(code for code, _ in would_award)
                    print(f"  {player.name}: would award {len(would_award)} -> {codes}")
            else:
                newly_awarded = AchievementService.check_and_award_all(db, player.id)
                if newly_awarded:
                    players_with_new += 1
                    total_new += len(newly_awarded)
                    codes = ", ".join(a["code"] for a in newly_awarded)
                    print(f"  {player.name}: awarded {len(newly_awarded)} -> {codes}")

        print()
        print("=" * 60)
        print(
            f"Players checked: {len(players)} | Players with new achievements: "
            f"{players_with_new} | Total new achievements: {total_new}"
        )

        if dry_run:
            print("\n[DRY RUN - no changes made]")
        else:
            print(f"\nSuccessfully awarded {total_new} new achievements")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill player achievements")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be awarded without making changes",
    )
    args = parser.parse_args()

    backfill(dry_run=args.dry_run)
