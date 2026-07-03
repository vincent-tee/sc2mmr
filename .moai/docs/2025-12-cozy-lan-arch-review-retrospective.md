# Retrospective: Cozy LAN Party Architecture Review (Dec 2025)

**Consolidated:** 2026-07-02 (from a 9-file, 5,026-line review bundle previously at `.moai/reviews/arch-review-cozy-lan-2025-q1/`, deleted per docs-and-writing house rules — a completed initiative doesn't need to persist as a living 9-document roadmap).

## What it was

A systematic 4-phase architecture review (base commit `0481c3a`, Dec 26 2025) covering backend (DB/service-layer/parsing), frontend (component/state/perf), integration (API contract), and a "Cozy UI" aesthetic pivot — shifting the product from "Cold Military Tactical" (Rajdhani/Orbitron fonts, dark neon, angular cards, "Command Center"/"Operatives"/"Missions" language) to "Warm LAN Party Gathering" (Poppins/Inter, warm pastels, rounded corners, "Game Hub"/"Players"/"Matches").

## What survived — verify against current sources, not this file

- **The Cozy UI pivot shipped.** The current README brands the product "SC2MMR - Friend Squad Edition" with Sunset Orange / Comic Shadows / Rounded Corners — the review's stated goal. Commits `0892cde`, `1ce9f8b`, `ff61958`, `6248b59`, `233f6f2` (and others tagged P1/P2/P3 in git log) executed most of the review's priority matrix.
- **The SQLAlchemy type-annotation blocker was resolved** — not by fixing the underlying types, but by suppression (commits `252ab48` "Add mypy.ini to suppress SQLAlchemy type errors", `23588a3` "Fix SQLAlchemy type annotation blockers"). This is tracked as ongoing intentional tech debt in `.moai/docs/tech-debt-log.md` and `sc2mmr-config-and-flags` (mypy.ini trap).
- **The service-layer extraction (SPEC-REFACTOR-001) reality** — the review found it ~60% complete with large inline-query API routes; current state is authoritatively described in `sc2mmr-architecture-contract` (which parser/rating modules are actually live, not what a Dec 2025 snapshot guessed).
- **The MCP integration guide's recommendations were NOT adopted** — as of 2026-07-02 the project runs `context7` only (playwright and figma-dev-mode-mcp-server were removed the same day this retrospective was written, per an explicit "only keep official Anthropic + context7" instruction).

## What did NOT survive and should not be trusted

The backend/frontend/integration reviews' specific line numbers, error counts, and "current state" snapshots (e.g., "100+ SQLAlchemy type errors", specific TypeScript↔Pydantic field mismatches) describe December 2025 code. The codebase has since undergone at least one "Comprehensive site redesign" (commit `233f6f2`) and the 2026-07-02 rating consolidation campaign. **Do not cite line numbers or error counts from the old review — re-verify against current code, or consult `sc2mmr-architecture-contract` / `sc2mmr-config-and-flags` / `sc2mmr-validation-and-qa`, which are ground-truth-checked as of 2026-07-02.**

## Where this ground is now covered, going forward

| Old review section | Current source of truth |
|---|---|
| Backend architecture, DB schema, service layer | `sc2mmr-architecture-contract` skill |
| TrueSkill/MMR formulas | `sc2-rating-theory-reference` skill |
| Config, mypy suppressions, CORS | `sc2mmr-config-and-flags` skill |
| Known type-safety / tech debt | `.moai/docs/tech-debt-log.md` |
| Test suite state | `sc2mmr-validation-and-qa` skill |
| Cozy UI aesthetic | the live frontend itself (README, `frontend/src`) |

No action items from the original review are carried forward here — anything still genuinely open should be re-discovered by reading current code/skills, not inherited from a 6-month-old snapshot.
