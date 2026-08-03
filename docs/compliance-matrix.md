# v3 compliance matrix

Status was determined from executable code and tests, not prior reports. `IMPLEMENTED_AND_TESTED` means a named automated test exercises the implementation; CI references `.github/workflows/ci.yml` unless stated otherwise.

| Requirement ID | Requirement | Implementation | Schema | Validator/Runtime | Tests | CI | Documentation | Status |
|---|---|---|---|---|---|---|---|---|
| C01 | Contract version | `models.CONTRACT_VERSION`, package 3.0.0 | v3 root `contract_version` | repository schema check | `ContractTests.test_export_and_phases` | unit/validation | canonical, README | IMPLEMENTED_AND_TESTED |
| C02 | Initial 12 Phase | `engine.INITIAL_PHASES`, `PHASE_SECTIONS` | `phase` | `ConversationEngine`/`Runtime` | `EngineTests.test_initial_12_and_update_5`, runtime full E2E | Python matrix | canonical | IMPLEMENTED_AND_TESTED |
| C03 | Update 5 Phase | `engine.UPDATE_PHASES` | `phase` | `Runtime.start_update` | engine/runtime full E2E | Python matrix | canonical | IMPLEMENTED_AND_TESTED |
| C04 | Exact commands | `ConversationEngine.handle` | N/A | exact string comparison | `EngineTests.test_exact_commands_and_bulk_rejected` cases | unit | canonical | IMPLEMENTED_AND_TESTED |
| C05 | State machine/resume | `EntryState`, `ConversationEngine` | phase/state definitions | `Runtime.resume` | runtime full E2E | unit | design | IMPLEMENTED_AND_TESTED |
| C06 | standalone_static | `Mode`, `session_local` | mode enum | engine; runtime rejects persistence | static boundary tests | unit | README | IMPLEMENTED_AND_TESTED |
| C07 | standalone_runtime | `Mode` | mode enum | `Runtime.create_session` | runtime full E2E | unit/smoke | API docs | IMPLEMENTED_AND_TESTED |
| C08 | pipeline | `Mode` | mode enum | runtime staged protocol | pipeline E2E | unit | canonical | IMPLEMENTED_AND_TESTED |
| C09 | Blind intake | canonical projection | `$defs.blind` closed object | Phase contract | pipeline E2E/canonical assertions | validation | canonical | IMPLEMENTED_AND_TESTED |
| C10 | Reconciliation disclosure | state flag | `$defs.reconciliation` | `disclose_reconciliation` | premature/order cases | unit | canonical | IMPLEMENTED_AND_TESTED |
| C11 | Immutable Phase-2 gate | `freeze_entry_gate`, gate hash | `$defs.gate` | overwrite rejection/persistence | pipeline overwrite test | unit | canonical | IMPLEMENTED_AND_TESTED |
| C12 | Evidence taxonomy | canonical classifications | `$defs.evidence.classification` | `validate_evidence` cutoff/classification | `V3Tests.test_semantics` | validation | canonical | IMPLEMENTED_AND_TESTED |
| C13 | Five signals | canonical + type enums | `$defs.signals` closed object | schema validation | schema/canonical contract tests | validation | canonical | IMPLEMENTED_AND_TESTED |
| C14 | Six entry gates | `EntryGate` | `$defs.gate` | freeze/terminal validation | all-gates parameterized subtests | unit | canonical | IMPLEMENTED_AND_TESTED |
| C15 | Terminal early stop | `EntryState.early_stop` | `$defs.terminal` | engine stops progression | `EngineTests.test_early_stop_terminal` | unit | canonical | IMPLEMENTED_AND_TESTED |
| C16 | Value/technical separation | distinct canonical/types | `$defs.value`, `$defs.zone` | schema/type checks | canonical/schema tests | validation | canonical/design | IMPLEMENTED_AND_TESTED |
| C17 | Event-aware Phase-7 lock | `lock_zones` | zone definition | phase/adjustment/overlap checks | zone mutation tests | unit | canonical | IMPLEMENTED_AND_TESTED |
| C18 | Zone revision chain | `ZoneRevision`, `revise_zone` | `$defs.revision` | mandatory evidence/impact/hashes | v3 revision test | unit | canonical | IMPLEMENTED_AND_TESTED |
| C19 | Route exclusivity | route contract | `$defs.route` | `validate_routes` | duplicate/overlap route tests | unit | canonical | IMPLEMENTED_AND_TESTED |
| C20 | Route precedence/transition | route priority/transition | route priority | `validate_routes` | missing precedence/transition tests | unit | canonical | IMPLEMENTED_AND_TESTED |
| C21 | Allocation arithmetic/40% | `Allocation` | `$defs.allocation` | `validate_allocation` | allocation mutation tests | unit | canonical | IMPLEMENTED_AND_TESTED |
| C22 | Pre-event cap | allocation field | pre-event field | before-event sum check | allocation/event tests | unit | canonical | IMPLEMENTED_AND_TESTED |
| C23 | Adversarial review | Initial Phase 9 contract | Phase artifact | phase progression | phase/canonical consistency tests | E2E | canonical | IMPLEMENTED_AND_TESTED |
| C24 | Simulation coverage | Phase 11 contract | Phase artifact | `validate_simulations` 14-scenario set | simulation coverage/contradiction test | unit | canonical | IMPLEMENTED_AND_TESTED |
| C25 | Four invalidation layers | canonical policy | route/terminal fields | route/simulation coverage | canonical contract assertions | forbidden audit | canonical | IMPLEMENTED_AND_TESTED |
| C26 | Expiry | route/zone contract | route expiry | route condition and zone freshness | route/zone tests | unit | canonical | IMPLEMENTED_AND_TESTED |
| C27 | Update post-mortem separation | Update Phase 2 sections | Phase artifact | phase contract | engine/runtime E2E | unit | canonical | IMPLEMENTED_AND_TESTED |
| C28 | Supersession | immutable generations | manifest | `Runtime.superseded` | runtime full E2E | unit | canonical/API | IMPLEMENTED_AND_TESTED |
| C29 | Decision ledger | immutable history | decision ledger object | `Runtime.ledger` | runtime full E2E | unit | canonical/API | IMPLEMENTED_AND_TESTED |
| C30 | Outcome evaluation | canonical metrics | `$defs.outcome` | `validate_outcome`, `REQUIRED_OUTCOME_METRICS` | maturity/full-metric/future leakage test | unit | canonical | IMPLEMENTED_AND_TESTED |
| C31 | Publication integrity | generation manifests | publication metadata | `Store.publish/verify` | publication, tamper, rollback tests | unit | canonical/API | IMPLEMENTED_AND_TESTED |
| C32 | Strict JSON | strict loader | JSON schemas | `require_object` at every API body and publication boundary | strict JSON publication and API-boundary tests | validation | validation docs | IMPLEMENTED_AND_TESTED |
| C33 | Runtime API operations | `api.Handler` | OpenAPI paths | `Runtime` orchestration | runtime/API tests and Docker smoke | unit/docker | API docs | IMPLEMENTED_AND_TESTED |
| C34 | Bearer authentication | `Handler._auth` fail-closed | bearer scheme | missing/wrong token 401 | HTTP API test/smoke | docker | API docs | IMPLEMENTED_AND_TESTED |
| C35 | Persistent storage | `/data` volume, `Store` | N/A | atomic filesystem generations | restart/restore/runtime E2E | docker | README/API | IMPLEMENTED_AND_TESTED |
| C36 | Session locking | N/A | N/A | process Lock + `fcntl.flock` | concurrent submission test | unit | API docs | IMPLEMENTED_AND_TESTED |
| C37 | Backup/restore | `POST /backups`, `POST /restores` | closed restore request | verified tar backup, safe staged restore | round-trip/tamper/traversal/API tests | unit | API docs | IMPLEMENTED_AND_TESTED |
| C38 | Docker | Dockerfile nonroot/volume | N/A | health/runtime process | `scripts/docker-smoke.sh` | docker job | README | IMPLEMENTED_AND_TESTED |
| C39 | Migration | legacy reader/migration | legacy schemas retained | conservative migration | `MigrationTests` | unit | migration docs | IMPLEMENTED_AND_TESTED |
| C40 | Rollback | immutable history/safe active pointer | manifest | failed publish cannot replace verified active | rollback safety test | unit | migration docs | IMPLEMENTED_AND_TESTED |
| C41 | Canonical instructions | sole normative file/export | N/A | export exactness | `ContractTests` | forbidden audit | canonical | IMPLEMENTED_AND_TESTED |
| C42 | User terminology restrictions | user-rendering section | N/A | forbidden wording audit | contract/repository audit tests | CI audit | canonical | IMPLEMENTED_AND_TESTED |
| C43 | Samples | 12/5 traces and legacy samples | strict JSON | repository validation | sample/phase consistency test | validation | README | IMPLEMENTED_AND_TESTED |
| C44 | CI | Python 3.11–3.13 + Docker | N/A | all commands | workflow syntax/content test | GitHub Actions | validation docs | IMPLEMENTED_AND_TESTED |
| C45 | Documentation | README + audit/design/API/migration/matrices | N/A | markdown link checker | documentation checks | docs job | docs directory | IMPLEMENTED_AND_TESTED |

No brokerage, order execution, market-data acquisition, external LLM, wealth sizing, forced percentage stop, or portfolio optimization is implemented; these are deliberately prohibited boundaries rather than missing functionality.
