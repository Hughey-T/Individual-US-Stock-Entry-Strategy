# Phase契約

Phaseの名称、内容、進行文言、更新フローの正本は[正本指示](../instructions/custom-gpt-entry-strategy.md#初回8-phase)を参照する。実装は `src/entry_strategy/engine.py`、契約テストは `tests/test_instruction_contract.py` にある。1応答は1 Phaseであり、完了後の追加進行はエラーになる。
