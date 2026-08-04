# Optional private runtime

The runtime validates and stores Custom-GPT-created JSON; it does not research, fetch market data, or make investment decisions. Set a non-empty `ENTRY_STRATEGY_TOKEN`, mount `ENTRY_STRATEGY_DATA=/data`, and run `python -m entry_strategy.api`. Only `/health` is public; all session and backup operations require `Authorization: Bearer …`. Missing token configuration is fail-closed.

## Operations

`POST /sessions` creates `standalone_runtime` or `pipeline` sessions. `GET /sessions/{id}/next` returns the current Phase contract and `/resume` returns persisted progression. Phase artifacts are submitted to `POST /sessions/{id}/phases/{initial-N|update-N}`. Phase 2 gate freeze, Phase 3 reconciliation disclosure, and update start have dedicated endpoints. Active plan, superseded generations, ledger, and integrity are read endpoints. The complete interface is in `openapi.yaml`.

## Concurrency and persistence

Each session uses both an in-process mutex and an advisory filesystem `flock`. A submission must name the current Phase; stale concurrent submissions are rejected. Publications write an immutable temporary generation, verify raw and canonical SHA-256, byte length and exact inventory, then atomically move the active pointer. A failed publication leaves the previously verified pointer unchanged. `/data` is a Docker persistent volume and the container runs as nonroot user `app`.

## Backup and restore

`Runtime.backup` locks and verifies every active session before atomically creating a gzipped tar archive and returning its SHA-256. `Store.restore` requires an empty destination, rejects absolute/traversal paths, links and symlinks, extracts into staging, verifies every active generation, and only then moves data into the destination. Authenticated `POST /backups` and `POST /restores` expose these administrative operations; deployments must restrict the token and allowed filesystem mounts. Every API request body uses the same strict UTF-8, duplicate-key, and non-finite-number rejection as publication input. After restore, call the integrity endpoint for each session. The implementation's presence does not imply deployment.
