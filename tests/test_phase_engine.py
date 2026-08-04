import unittest
from entry_strategy.engine import INITIAL_PHASES, UPDATE_PHASES, ConversationEngine


class EngineTests(unittest.TestCase):
    def test_initial_12_and_update_5(self):
        e = ConversationEngine()
        s, r = e.start("acme")
        got = [r]
        for _ in range(11):
            got.append(e.handle(s, "次"))
        self.assertEqual([x.phase for x in got], list(INITIAL_PHASES))
        self.assertFalse(got[-1].prompt_next)
        updates = [e.handle(s, "更新")]
        for _ in range(4):
            updates.append(e.handle(s, "次"))
        self.assertEqual([x.phase for x in updates], list(UPDATE_PHASES))
        self.assertFalse(updates[-1].prompt_next)

    def test_exact_commands_and_bulk_rejected(self):
        e = ConversationEngine()
        s, _ = e.start("ACME")
        for command in (" 次", "次 ", "次を実行", "一括実行", "continue", "更新"):
            with self.subTest(command=command), self.assertRaises(ValueError):
                e.handle(s, command)
        self.assertEqual(s.current_phase, 1)

    def test_early_stop_terminal(self):
        e = ConversationEngine()
        s, _ = e.start("ACME")
        s.early_stop(
            "INSUFFICIENT_EVIDENCE",
            reason="price missing",
            missing_evidence=["price"],
            required_next_action="refresh",
            reactivation_condition="price available",
            monitoring_condition="source",
        )
        with self.assertRaisesRegex(ValueError, "terminal"):
            e.handle(s, "次")
