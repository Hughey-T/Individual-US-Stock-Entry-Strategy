import unittest
from entry_strategy.validation import (
    ValidationError,
    assess_price_discrepancy,
    validate_allocation,
    validate_freshness,
)


class ValidationTests(unittest.TestCase):
    def valid(self):
        return {
            "current_purchase_pct": 20,
            "conditional_purchases": [
                {
                    "route": "PULLBACK_ROUTE",
                    "percent": 30,
                    "condition": "support reversal",
                    "before_event": True,
                },
                {
                    "route": "BREAKOUT_ROUTE",
                    "percent": 10,
                    "condition": "confirmed",
                    "before_event": False,
                },
            ],
            "pre_event_cap_pct": 50,
            "waiting_pct": 40,
            "waiting_use": ["pullback"],
            "rationale": "signals",
            "adjustment_factors": ["relative strength", "event dominance"],
            "unit": "target_position_percent",
        }

    def test_valid_and_arithmetic_mutations(self):
        validate_allocation(self.valid())
        for mutate in (
            lambda d: d.update(current_purchase_pct=41),
            lambda d: d.update(waiting_pct=39),
            lambda d: d.update(pre_event_cap_pct=49),
            lambda d: d.update(unit="wealth"),
        ):
            d = self.valid()
            mutate(d)
            with self.assertRaises(ValidationError):
                validate_allocation(d)

    def test_duplicate_and_binary_exception(self):
        d = self.valid()
        d["conditional_purchases"].append(dict(d["conditional_purchases"][0]))
        d["waiting_pct"] = 10
        with self.assertRaisesRegex(ValidationError, "重複"):
            validate_allocation(d)
        d = self.valid()
        with self.assertRaisesRegex(ValidationError, "binary"):
            validate_allocation(d, event_dominance="BINARY")

    def test_price_and_freshness(self):
        self.assertIn("限定分析", assess_price_discrepancy([215.9, 216.1], 5, 7, [216]))
        with self.assertRaises(ValidationError):
            validate_freshness(90, "主要判断に使用")
