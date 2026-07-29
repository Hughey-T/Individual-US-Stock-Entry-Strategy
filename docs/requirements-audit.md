# 要件1～26 compliance matrix

判定語は `verified complete`、`not applicable`、`blocked` のみを使う。各完了判定は具体的な実装と挙動テストへ対応付ける。

| 要件 | 判定 | 実装証拠 | 検証証拠 |
|---:|---|---|---|
| 1 | verified complete | 正本§1、Decision/Allocation分離 | `test_instruction_contract.py::test_critical_output_contracts_are_explicit` |
| 2 | verified complete | 正本§1–2、§14の絶対条件・対象外 | `test_instruction_contract.py::test_canonical_export_is_exact_and_standalone` |
| 3 | verified complete | instructions、engine、models、schemas、validation、migration、fixtures、samples、OpenAPI、docs、export | `test_repository_validation.py`、全unittest |
| 4 | verified complete | `Decision`の行動・経路・比率・リスク、保守的migration | `test_migration.py`全6判定、Schema enumテスト |
| 5 | verified complete | 正本§3–11、`INITIAL_PHASES`、`PHASE_SECTIONS` | `test_phase_engine.py::test_initial_emits_exactly_one_phase_then_stops` |
| 6 | verified complete | 正本§2、engineのcommand遷移 | `test_only_documented_commands_advance`、初回/更新停止テスト |
| 7 | verified complete | `EntryState.lock_zones/revise_zone`、state Schema依存 | `test_zone_cannot_lock_before_or_after_phase4`、`test_zone_lock_and_audited_revision` |
| 8 | verified complete | 正本§11の日足条件と§14対象外 | 正本契約テスト、禁止surface検索テスト |
| 9 | verified complete | model Literal、state/output Schema enum | output/state fixtureのSchema検証 |
| 10 | verified complete | 正本§10.1、`validate_allocation` | `test_allocation_has_no_cap_or_accounting_bypass` |
| 11 | verified complete | output `invalidations`必須4欄、正本§11.1 | Schema missing-field拒否テスト |
| 12 | verified complete | event_dominance enumと低/中/高ルール | `test_route_priority_and_low_event_rule`、Schema enum拒否 |
| 13 | verified complete | data_freshness必須構造、`validate_freshness` | output fixture Schema検証、`test_price_boundary_and_freshness` |
| 14 | verified complete | `assess_price_discrepancy`境界優先 | `test_price_boundary_and_freshness` |
| 15 | verified complete | outputのplan_expiry/next_review必須、正本§11.2 | output Schema missing-field検証、repository validation |
| 16 | verified complete | coverageのenum・必須行構造 | 空items/不正追加propertyのSchema拒否 |
| 17 | verified complete | execution_card 15項目、自然語数値pattern | 数値なし条件と未知注文fieldのSchema拒否 |
| 18 | verified complete | engine更新2 Phase、update review Schema/sample | `test_update_requires_initial_completion_and_has_two_phases`、repository validation |
| 19 | verified complete | 正本§14、HTTP/注文実装なし | 禁止surfaceテスト、OpenAPI `paths: {}` |
| 20 | verified complete | behavioral/schema/integration tests | READMEのunittest/validation全成功 |
| 21 | verified complete | 全artifactが正本を参照、CI追加 | canonical export同一性、repository validation |
| 22 | verified complete | migration全6判定・矛盾/未知拒否 | `test_migration.py` |
| 23 | verified complete | docs/design.mdの判断記録 | 全static/runtime checks |
| 24 | verified complete | 8+2 Phase、多軸、ロック、鮮度、期限、CI | READMEの全コマンドと本表の各テスト |
| 25 | verified complete | 旧語はmigration文脈だけ、現行surfaceから除外 | `test_old_user_facing_design_and_execution_features_absent`、最終rg監査 |
| 26 | verified complete | commit/PR説明と最終報告で結果を提示 | git履歴、CI/ローカル実行結果 |
| 実保存データの移行 | not applicable | 初期リポジトリに保存データなし。互換仕様は要件22で実装 | legacy fixtureとmigration test |

`blocked`項目はない。
