import unittest
from pathlib import Path
from entry_strategy.engine import INITIAL_PHASES, UPDATE_PHASES
from entry_strategy.export import canonical_instructions

ROOT = Path(__file__).parents[1]


class ContractTests(unittest.TestCase):
    def test_phase_counts_and_canonical_export(self):
        self.assertEqual(INITIAL_PHASES, tuple(range(1, 9)))
        self.assertEqual(UPDATE_PHASES, (1, 2))
        self.assertEqual(
            canonical_instructions(),
            (ROOT / "instructions/custom-gpt-entry-strategy.md").read_text(),
        )

    def test_required_contract_terms(self):
        t = canonical_instructions()
        for term in [
            "中期構造",
            "短期状態",
            "イベント支配度",
            "価格非対称性",
            "カバレッジ表",
            "実行カード",
            "個別条件失敗",
            "計画全体無効化",
            "投資仮説再評価",
            "目標ポジション100%",
            "Phase 8",
        ]:
            self.assertIn(term, t)

    def test_no_forbidden_execution_features_in_schema(self):
        text = " ".join(p.read_text() for p in (ROOT / "schemas").glob("*.json"))
        for term in ["market_order", "limit_order", "broker_api", "risk_amount_position_size"]:
            self.assertNotIn(term, text)
