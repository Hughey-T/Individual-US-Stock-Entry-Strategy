# Phase実装対応

Phaseの名称、必須項目、入力、出力、禁止事項、進行文言の唯一の規範は[正本指示](../instructions/custom-gpt-entry-strategy.md)である。`src/entry_strategy/engine.py`の`PHASE_SECTIONS`は初回Phase 1～8と更新Phase 1～2の実行単位を識別し、`tests/test_phase_engine.py`が開始、1応答1 Phase、最終停止、更新開始条件を実遷移で検証する。最終出力は`entry-strategy-output.schema.json`、事後検証は`entry-strategy-update-review.schema.json`で検証する。
