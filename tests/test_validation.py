import json
import unittest
from pathlib import Path
from entry_strategy.models import Allocation, Decision, EntryState, PriceZone
from entry_strategy.validation import (
    ValidationError,
    assess_price_discrepancy,
    validate_allocation,
    validate_freshness,
    validate_state,
)

ROOT = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    def valid_allocation(self):
        return {
            "current_purchase_pct": 20,
            "conditional_purchases_pct": [30, 10],
            "pre_event_cap_pct": 60,
            "waiting_pct": 40,
            "waiting_use": ["押し目用"],
            "rationale": "support",
            "unit": "target_position_percent",
        }

    def test_allocation_and_condition_cap(self):
        validate_allocation(self.valid_allocation())

    def test_invalid_fixture_rejected(self):
        with self.assertRaises(ValidationError):
            validate_allocation(json.loads((ROOT / "fixtures/invalid/allocation.json").read_text()))

    def test_zone_lock_and_revision_audit(self):
        s = EntryState("1.0.0", "ACME")
        z = PriceZone("s", "主要支持帯", 209, 216)
        s.lock_zones([z], 4)
        with self.assertRaises(ValueError):
            s.lock_zones([z], 4)
        with self.assertRaises(ValueError):
            s.revise_zone("s", PriceZone("s", "主要支持帯", 210, 217), "", "impact")
        s.revise_zone(
            "s", PriceZone("s", "主要支持帯", 210, 217), "split adjustment", "conditions move"
        )
        self.assertEqual(s.zone_revisions[0].old_zone.low, 209)
        self.assertIn("主要支持帯", s.price_zones["s"].describe())

    def test_phase5_requires_locked_zones(self):
        with self.assertRaises(ValidationError):
            validate_state(EntryState("1.0.0", "ACME", current_phase=5))

    def test_price_boundary_forces_limited(self):
        self.assertIn("限定分析", assess_price_discrepancy([215.9, 216.1], 5, 7, [216]))

    def test_stale_supply_not_primary(self):
        with self.assertRaises(ValidationError):
            validate_freshness(90, "主要判断に使用")

    def test_low_event_cannot_be_only_route(self):
        a = Allocation(**self.valid_allocation())
        d = Decision(
            "条件待ち", ["イベント通過後"], ["イベント通過後"], a, "均衡", "中", "r", "risk", "miss"
        )
        s = EntryState("1.0.0", "ACME", current_phase=4, event_dominance="低", decision=d)
        with self.assertRaises(ValidationError):
            validate_state(s)
