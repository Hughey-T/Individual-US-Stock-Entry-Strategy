import unittest

from entry_strategy.engine import PHASE_SECTIONS, ConversationEngine


class EngineTests(unittest.TestCase):
    def test_initial_emits_exactly_one_phase_then_stops(self):
        engine = ConversationEngine()
        state, result = engine.start("acme")
        results = [result]
        for _ in range(7):
            results.append(engine.handle(state, "次"))
        self.assertEqual([result.phase for result in results], list(range(1, 9)))
        self.assertTrue(all(result.mode == "initial" for result in results))
        self.assertTrue(all(result.prompt_next for result in results[:7]))
        self.assertTrue(
            all(result.footer == "「次」と送信してください。" for result in results[:7])
        )
        self.assertFalse(results[-1].prompt_next)
        self.assertIsNone(results[-1].footer)
        self.assertTrue(state.initial_complete)
        with self.assertRaisesRegex(ValueError, "最終Phase"):
            engine.handle(state, "次")

    def test_result_sections_are_unique_to_current_phase(self):
        engine = ConversationEngine()
        state, result = engine.start("ACME")
        self.assertEqual(result.required_sections, PHASE_SECTIONS[("initial", 1)])
        second = engine.handle(state, "次")
        self.assertEqual(second.required_sections, PHASE_SECTIONS[("initial", 2)])
        self.assertNotEqual(result.required_sections, second.required_sections)

    def test_update_requires_initial_completion_and_has_two_phases(self):
        engine = ConversationEngine()
        state, _ = engine.start("ACME")
        with self.assertRaisesRegex(ValueError, "初回Phase 8"):
            engine.handle(state, "更新")
        for _ in range(7):
            engine.handle(state, "次")
        one = engine.handle(state, "更新")
        two = engine.handle(state, "次")
        self.assertEqual((one.mode, one.phase, one.prompt_next), ("update", 1, True))
        self.assertEqual(
            (two.mode, two.phase, two.prompt_next, two.footer), ("update", 2, False, None)
        )
        with self.assertRaisesRegex(ValueError, "最終Phase"):
            engine.handle(state, "次")

    def test_only_documented_commands_advance(self):
        engine = ConversationEngine()
        state, _ = engine.start("ACME")
        with self.assertRaisesRegex(ValueError, "次.*更新"):
            engine.handle(state, "continue")
        self.assertEqual(state.current_phase, 1)
