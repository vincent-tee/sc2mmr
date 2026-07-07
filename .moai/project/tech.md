# SC2 MMR Tracker - Technical Documentation

**Retired 2026-07-02.** This file was auto-generated 2025-12-05 and its formulas are stale and actively misleading — e.g. it states `MMR = 1000 + 40*mu` and TrueSkill `beta=4.166, tau=0.0833`; the current (verified 2026-07-02, resolved via the rating consolidation campaign) formula is `MMR = 1000 + 100*mu - 200*sigma` with `beta=5.0, tau=0.25`. Do not use this file's algorithm section for anything.

**Current sources of truth:**
- Rating formulas, TrueSkill config, team-balancing math: `.claude/skills/sc2-rating-theory-reference/SKILL.md`
- All configuration settings, CORS, mypy suppressions: `.claude/skills/sc2mmr-config-and-flags/SKILL.md`
- Tech stack, dependencies, environment setup: `.claude/skills/sc2mmr-build-and-env/SKILL.md`
- Running/operating the app, deployment reality: `.claude/skills/sc2mmr-run-and-operate/SKILL.md`
- Known tech debt: `.moai/docs/tech-debt-log.md`
