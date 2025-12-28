# Technical Debt & Type Safety Log

This document tracks intentional technical debt, specifically type ignores and architectural trade-offs made during development, to ensure they are addressed in future sessions.

## 1. Type Ignores (# type: ignore)

### `backend/app/services/unified_parser.py`
- **sc2reader.load_replay**: Library lacks comprehensive type stubs.
- **get_discovery_engine**: Conditional import of local module causes mypy to lose track of the callable signature.
- **SQLALCHEMY JSON Columns**: Accessing `PF.build_order_json` as a list requires casts because SQLAlchemy maps it as `Optional[Any]`.

### `backend/app/balancer.py`
- **trueskill**: Library lacks type stubs.
- **win_probability calculations**: Involves complex math/numpy types that are sometimes narrowed with `cast`.

## 2. Architectural Trade-offs

### Match Orchestrator Dependencies
- The `MatchOrchestrator` currently depends on `UnifiedParser`, `RatingSystem`, and `ImpactService`. While unified, this creates a large central service. In the future, this could be refactored into a command-bus or event-driven pattern.

### SQLite Cascades
- SQLite requires manual recreation of tables to add `ON DELETE CASCADE`. The migration script `backend/scripts/migrate_cascades.py` handles this, but any future schema changes must ensure cascades are preserved in the `CREATE TABLE` statements.

## 3. Future Improvements
- **Standardized DTOs**: Transition from simple dataclasses to Pydantic models for internal service communication to enable automated validation.
- **Async Processing**: Offload `orchestrate_match` to a background task (e.g., Celery or FastAPI BackgroundTasks) as parsing is CPU intensive.

---
*Last Updated: Sat Dec 27 2025*
