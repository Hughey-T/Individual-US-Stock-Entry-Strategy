# v3 test matrix

All critical requested behaviors map to executable tests; there are no skipped or xfailed critical cases. Parenthesized names identify `subTest`/loop cases.

| Area | Required case | Automated test mapping | Result |
|---|---|---|---|
| Phase/state | Initial 12, Update 5, final stop | `EngineTests.test_initial_12_and_update_5`; runtime full E2E | COVERED |
| Phase/state | exact `次`/`更新`, whitespace, embedded, bulk, premature update | `EngineTests.test_exact_commands_and_bulk_rejected` (` 次`, `次 `, `次を実行`, `一括実行`, `continue`, `更新`) | COVERED |
| Phase/state | early stop | `EngineTests.test_early_stop_terminal` | COVERED |
| Modes | static/runtime/pipeline and shared phases | engine tests; `RuntimeCompletionTests.test_static_runtime_boundary_and_phase_conflict`; pipeline/full runtime E2E | COVERED |
| Resume | persisted session resume | `test_standalone_runtime_full_initial_update_resume_and_ledger` | COVERED |
| Snapshot | valid/conflict/stale/missing/currency/split/dividend | `SemanticCompletionTests.test_snapshot_price_and_corporate_action_mutations` (`conflicting`, `stale`, `missing`, `currency`, `split`, `dividend`) | COVERED |
| Evidence | future evidence/classification/source timestamps | `V3Tests.test_semantics` | COVERED |
| Cutoff | timezone-equivalent same instant | `V3Tests.test_semantics` | COVERED |
| Blind | premature disclosure, hidden projection contract, reconciliation order | `RuntimeCompletionTests.test_pipeline_gate_and_reconciliation_e2e`; canonical/schema tests | COVERED |
| Blind | fixed gate overwrite | pipeline E2E overwrite assertion | COVERED |
| Gate | allowed/conditional/wait/no-entry/return/insufficient | `SemanticCompletionTests.test_all_entry_gate_states_freeze` (six gate values) | COVERED |
| Gate | terminal cannot be offset; zero purchases | `test_hard_terminal_gate_zero_purchase_for_all_terminal_states` (three terminal gates) | COVERED |
| Zones | Phase <7, duplicate, overlap, inversion, currency, adjustment | `V3Tests.test_zone_lock_only_phase7_overlap_and_revision_chain`; `SemanticCompletionTests.test_zone_mutations_and_staleness` | COVERED |
| Zones | revision reason/evidence/impact/hash, stale generation | same zone tests | COVERED |
| Events | LOW/MANAGEABLE/DOMINANT/UNKNOWN | `test_event_dominance_and_binary_exception` loop | COVERED |
| Events | invalid BINARY pre-event; valid complete exception; mandatory review | same event test | COVERED |
| Routes | duplicate ID/priority, coverage, overlap/precedence, transition | `V3Tests.test_routes_and_terminal_ratios` plus validator mutation tests | COVERED |
| Allocation | total 100, >40, pre-event cap, waiting use, inactive, duplicate, terminal zero | `ValidationTests` and `V3Tests.test_routes_and_terminal_ratios`; terminal gate loop | COVERED |
| Adversarial | chase/cash/false breakout/support/value/thesis cases required in Phase 9 | `SemanticCompletionTests.test_adversarial_review_and_decision_ledger_contracts` using `REQUIRED_ADVERSARIAL_CHECKS` | COVERED |
| Simulation | all 14 scenarios | `SemanticCompletionTests.test_required_simulation_coverage_and_contradictions` using `REQUIRED_SIMULATION_SCENARIOS` | COVERED |
| Simulation | contradiction/duplicate allocation/missing scenario | same simulation mutation test | COVERED |
| Update | strict cutoff, changed/unchanged, Phase separation | `V3Tests.test_semantics`; `test_update_diff_and_outcome_maturity_future_leakage`; runtime Update E2E | COVERED |
| Ledger | immutable old generations, supersession, expiry representation | runtime full E2E and storage tests | COVERED |
| Outcome | not matured/matured/all required metrics/future leakage | outcome maturity test using `REQUIRED_OUTCOME_METRICS` | COVERED |
| Strict JSON | malformed UTF-8, duplicate key, NaN, Infinity | `StrictPublicationTests.test_strict_json_mutations` | COVERED |
| Publication | replay, raw/canonical/length, missing/extra, hash/canonical tamper | `V3Tests.test_publication_roundtrip_and_tamper`; runtime publication inventory test; strict publication tests | COVERED |
| Publication | traversal, symlink, collision, active-pointer tamper, rollback safety | runtime backup/publication tests | COVERED |
| Concurrency | concurrent session write | `RuntimeCompletionTests.test_concurrent_submission_only_one_current_phase_wins` | COVERED |
| Backup | backup/restore, integrity, tamper, traversal, symlink | runtime backup tests | COVERED |
| API | health, Bearer, create/next/submit/active/integrity, strict JSON on every request, restore | `ApiTests.test_health_auth_and_session_operations`; `test_request_boundaries_use_strict_json_and_restore_is_exposed`; Docker smoke | COVERED |
| Docker | build, nonroot, health, volume restart/integrity | `.github/workflows/ci.yml` docker job + `scripts/docker-smoke.sh` | COVERED |
| Canonical | README/schema/engine/samples phases agree | `RepositoryConsistencyTests.test_phase_surfaces_agree` | COVERED |
| Forbidden | no execution/broker/wealth sizing and user terminology | `RepositoryConsistencyTests.test_forbidden_wording_and_canonical_markers` | COVERED |
