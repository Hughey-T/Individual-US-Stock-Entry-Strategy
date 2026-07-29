import re
import unittest
from pathlib import Path

from entry_strategy.engine import INITIAL_PHASES, PHASE_SECTIONS, UPDATE_PHASES
from entry_strategy.export import canonical_instructions

ROOT = Path(__file__).parents[1]


class ContractTests(unittest.TestCase):
    def test_canonical_export_is_exact_and_standalone(self):
        contract = canonical_instructions()
        self.assertEqual(contract, (ROOT / "instructions/custom-gpt-entry-strategy.md").read_text())
        self.assertIn("このファイルだけを Custom GPT", contract)
        self.assertGreater(len(contract.splitlines()), 200)

    def test_phase_contract_is_complete(self):
        self.assertEqual(INITIAL_PHASES, tuple(range(1, 9)))
        self.assertEqual(UPDATE_PHASES, (1, 2))
        contract = canonical_instructions()
        for phase in INITIAL_PHASES:
            self.assertRegex(contract, rf"初回Phase {phase}[：:]")
            self.assertIn(("initial", phase), PHASE_SECTIONS)
        for phase in UPDATE_PHASES:
            self.assertRegex(contract, rf"更新Phase {phase}[：:]")
            self.assertIn(("update", phase), PHASE_SECTIONS)
        for marker in ["**入力**", "**必須分析・出力**", "**禁止**", "**進行**"]:
            self.assertGreaterEqual(contract.count(marker), 10)

    def test_critical_output_contracts_are_explicit(self):
        contract = canonical_instructions()
        for term in [
            "現在行動",
            "経路優先順位",
            "現在購入比率",
            "イベント前購入上限",
            "待機用途",
            "中期構造",
            "短期状態",
            "イベント支配度",
            "価格非対称性",
            "観測日",
            "公表日",
            "計画の有効期限",
            "個別購入条件の失敗",
            "エントリー計画全体の無効化",
            "投資仮説の再評価",
            "カバレッジ表",
            "最終実行カード",
        ]:
            self.assertIn(term, contract)
        self.assertIn("1条件の購入比率は40%以下", contract)
        self.assertIn("旧価格帯", contract)
        self.assertIn("新価格帯", contract)

    def test_old_user_facing_design_and_execution_features_absent(self):
        current_surfaces = [
            ROOT / "instructions/custom-gpt-entry-strategy.md",
            ROOT / "schemas/entry-strategy-state.schema.json",
            ROOT / "schemas/entry-strategy-output.schema.json",
            ROOT / "samples/final-execution-card.json",
        ]
        text = "\n".join(path.read_text() for path in current_surfaces)
        for forbidden in ["A：即時", "全5段階", "F→E→D/C→B→A", "broker_api", "market_order"]:
            self.assertNotIn(forbidden, text)
        self.assertIsNone(re.search(r"必須.{0,12}8[%％]|8[%％].{0,12}必須", text))
