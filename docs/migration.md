# Migration and rollback

2.0.0 is the previous supported read-only contract; 3.0.0 is preferred. Completed v2 strategies/cards remain readable and can receive separately stored outcomes. Active v2 sessions are non-migratable and restart at v3 Initial Phase 1. Do not infer Phase-2 gates, remap Phase-4 zones to Phase 7, or backfill adversarial evidence. Rollback repoints only to a previously integrity-verified immutable generation after verification; it never edits history. Static exports remain readable. New work always uses v3.
