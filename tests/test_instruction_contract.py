import unittest
from pathlib import Path
from entry_strategy.engine import INITIAL_PHASES, PHASE_SECTIONS, UPDATE_PHASES
from entry_strategy.export import canonical_instructions

ROOT = Path(__file__).parents[1]


class ContractTests(unittest.TestCase):
    def test_export_and_phases(self):
        c = canonical_instructions()
        self.assertEqual(c, (ROOT / "instructions/custom-gpt-entry-strategy.md").read_text())
        self.assertEqual(INITIAL_PHASES, tuple(range(1, 13)))
        self.assertEqual(UPDATE_PHASES, tuple(range(1, 6)))
        for p in INITIAL_PHASES:
            self.assertIn(("initial", p), PHASE_SECTIONS)
        for p in UPDATE_PHASES:
            self.assertIn(("update", p), PHASE_SECTIONS)

    def test_normative_features(self):
        c = canonical_instructions()
        for term in (
            "standalone_static",
            "standalone_runtime",
            "pipeline",
            "FACTS",
            "Phase 2",
            "Phase 7",
            "NO_ENTRY",
            "WAIT_WITHOUT_PLAN",
            "RETURN_TO_INDIVIDUAL_ANALYSIS",
            "BINARY",
            "40",
            "simulation",
            "not_matured",
            "future leakage",
            "one response contains exactly one Phase",
        ):
            self.assertIn(term, c)

    def test_forbidden_execution_absent(self):
        c = canonical_instructions()
        for forbidden in ("broker_api", "market_order", "bulk execution is permitted"):
            self.assertNotIn(forbidden, c)
