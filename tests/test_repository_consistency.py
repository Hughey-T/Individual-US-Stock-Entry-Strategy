import json
from pathlib import Path
import unittest

from entry_strategy.engine import INITIAL_PHASES, UPDATE_PHASES
from entry_strategy.export import canonical_instructions

ROOT = Path(__file__).parents[1]


class RepositoryConsistencyTests(unittest.TestCase):
    def test_phase_surfaces_agree(self):
        readme = (ROOT / "README.md").read_text()
        initial = json.loads((ROOT / "samples/initial-12-phase-trace.json").read_text())
        update = json.loads((ROOT / "samples/update-5-phase-trace.json").read_text())
        schema = json.loads((ROOT / "schemas/entry-strategy-contract-v3.schema.json").read_text())
        self.assertEqual(initial["phases"], list(INITIAL_PHASES))
        self.assertEqual(update["phases"], list(UPDATE_PHASES))
        self.assertIn("Initial 12 Phase / Update 5 Phase", readme)
        self.assertEqual(schema["properties"]["contract_version"]["const"], "3.0.0")
        contract = canonical_instructions()
        for marker in (
            "Initial Phase 6",
            "Initial Phase 7",
            "Initial Phase 9",
            "Initial Phase 10",
            "Initial Phase 11",
            "Initial Phase 12",
            "Update Phase 2",
            "Update Phase 3",
            "Update Phase 5",
        ):
            self.assertIn(marker, contract)

    def test_forbidden_wording_and_canonical_markers(self):
        contract = canonical_instructions()
        for required in (
            "session_local",
            "accepted: true",
            "readback verification",
            "Bulk execution is always forbidden",
            "Do not flood ordinary responses",
            "zero purchase allocation",
        ):
            self.assertIn(required, contract)
        production = "\n".join(
            path.read_text(errors="ignore")
            for path in [
                ROOT / "src/entry_strategy/api.py",
                ROOT / "src/entry_strategy/runtime.py",
                ROOT / "src/entry_strategy/storage.py",
            ]
        )
        for forbidden in ("broker_api", "market_order", "portfolio_optimizer"):
            self.assertNotIn(forbidden, production)

    def test_v3_schema_contains_semantic_contract_objects(self):
        schema = json.loads((ROOT / "schemas/entry-strategy-contract-v3.schema.json").read_text())
        definitions = schema["$defs"]
        for name in ("adversarial_review", "simulation_result", "decision_ledger", "outcome"):
            with self.subTest(name=name):
                self.assertIn(name, definitions)
                self.assertFalse(definitions[name]["additionalProperties"])
