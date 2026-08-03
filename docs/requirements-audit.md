# Current-state audit and version matrix

Audit baseline: branch `main` was requested as authority; checkout supplied to this task was branch `work` at `209c3e523bbb5e3545256f0b0af9f50768993bb0`, with no configured remote/default-branch symbolic ref. The baseline consistently described contract/package 2.0.0, Initial 8, Update 2, exact commands, Phase-4 zone locking, Japanese action/routes, target-position allocation, 40% cap, pre-event cap, waiting use, three invalidation concepts, expiry and update review. It contained three schemas, Python models/engine/semantic validator, samples, fixtures, OpenAPI design, unit tests, README/design/validation/migration/phase/API docs, and CI. No runtime HTTP server, Dockerfile, durable ledger/publication store, blind two-stage handoff, independent five-signal gate, adversarial Phase, or simulation Phase existed.

| Surface | Baseline | Preferred/final |
|---|---|---|
| Canonical prose / package | 2.0.0 | 3.0.0 |
| Initial / Update | 8 / 2 | 12 / 5 |
| Zone lock | Initial 4 | Initial 7, after events |
| Modes | static conversation | static, optional runtime, pipeline |
| Gate | action-adjacent | immutable independent Phase 2 gate |
| Upstream | direct | blind then Phase 3 reconciliation |
| Signals | mixed narrative | five independent objects |
| Countercase/simulation | scenario narrative | dedicated Phase 9 / Phase 11 |
| Persistence | none | atomic immutable generations + ledger history |
| API/Docker | design only / absent | optional authenticated runtime / image |

The schema/Python/sample vocabulary in v2 was internally aligned but README called OpenAPI design-only while API documentation discussed a future runtime. Contract 3.0 resolves this by labeling the included runtime optional and never deployed by implication. Legacy schemas/fixtures remain for read-only compatibility; the strict v3 schema is additive. Full feature mapping is in the sole normative contract; implementation enforces structural rather than analytical judgments.
