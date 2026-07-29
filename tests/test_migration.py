import json
import unittest
from pathlib import Path
from entry_strategy.migration import LegacyFormatError, is_legacy, migrate_legacy


class MigrationTests(unittest.TestCase):
    def test_conservative_migration(self):
        d = json.loads((Path(__file__).parents[1] / "fixtures/legacy/five-phase.json").read_text())
        self.assertTrue(is_legacy(d))
        n = migrate_legacy(d)
        self.assertTrue(n["legacy"]["manual_review_required"])
        self.assertEqual(n["current_action"], "個別銘柄分析へ差し戻し")

    def test_unknown_rejected(self):
        with self.assertRaises(LegacyFormatError):
            migrate_legacy({"phase_count": 5, "decision_label": "X"})
