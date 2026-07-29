import unittest

from entry_strategy.migration import LEGACY_LABELS, LegacyFormatError, is_legacy, migrate_legacy


class MigrationTests(unittest.TestCase):
    def test_all_recognized_legacy_labels_are_conservative(self):
        for label, description in LEGACY_LABELS.items():
            for rendered in (label, f"{label}：{description}"):
                with self.subTest(rendered=rendered):
                    data = {"ticker": "acme", "phase_count": 5, "decision_label": rendered}
                    self.assertTrue(is_legacy(data))
                    migrated = migrate_legacy(data)
                    self.assertEqual(migrated["current_action"], "個別銘柄分析へ差し戻し")
                    self.assertEqual(migrated["legacy"]["legacy_decision"], label)
                    self.assertTrue(migrated["legacy"]["manual_review_required"])

    def test_unknown_inconsistent_and_ambiguous_formats_rejected(self):
        cases = [
            {"phase_count": 5, "decision_label": "X"},
            {"phase_count": 8, "decision_label": "A"},
            {"phase_count": 5},
            {"phase_count": 5, "decision_label": "A", "legacy_decision": "B"},
            {"schema_version": "2.0.0", "ticker": "ACME"},
        ]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(LegacyFormatError):
                migrate_legacy(data)
