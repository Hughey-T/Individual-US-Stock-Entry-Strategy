import unittest
from entry_strategy.engine import ConversationEngine


class EngineTests(unittest.TestCase):
    def test_initial_is_one_through_eight(self):
        e = ConversationEngine()
        s, r = e.start("acme")
        seen = [r.phase]
        self.assertTrue(r.prompt_next)
        for _ in range(7):
            seen.append(e.handle(s, "次").phase)
        self.assertEqual(seen, list(range(1, 9)))
        self.assertFalse(e._result(s).prompt_next)
        with self.assertRaises(ValueError):
            e.handle(s, "次")

    def test_update_is_two_phases(self):
        e = ConversationEngine()
        s, _ = e.start("ACME")
        one = e.handle(s, "更新")
        two = e.handle(s, "次")
        self.assertEqual((one.mode, one.phase, one.prompt_next), ("update", 1, True))
        self.assertEqual((two.phase, two.prompt_next), (2, False))
