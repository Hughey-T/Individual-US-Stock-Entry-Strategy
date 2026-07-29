import json
import unittest
from pathlib import Path

from entry_strategy.models import Allocation, ConditionalPurchase, Decision, EntryState, PriceZone
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
            "conditional_purchases": [
                {"route": "押し目", "percent": 30, "condition": "支持反転", "before_event": True},
                {
                    "route": "上抜け",
                    "percent": 10,
                    "condition": "出来高確認",
                    "before_event": False,
                },
            ],
            "pre_event_cap_pct": 50,
            "waiting_pct": 40,
            "waiting_use": ["押し目用"],
            "rationale": "支持確認の基本範囲からイベント支配度で抑制",
            "adjustment_factors": ["相対強度", "イベント支配度"],
            "unit": "target_position_percent",
        }

    def test_valid_allocation(self):
        validate_allocation(self.valid_allocation())

    def test_allocation_has_no_cap_or_accounting_bypass(self):
        cases = []
        for mutate in (
            lambda d: d.update(current_purchase_pct=41),
            lambda d: d["conditional_purchases"][0].update(percent=41),
            lambda d: d.update(waiting_pct=39),
            lambda d: d.update(pre_event_cap_pct=49),
            lambda d: d.update(waiting_use=[]),
            lambda d: d.update(unit="total_asset_percent"),
            lambda d: d.update(adjustment_factors=["資産総額"]),
        ):
            data = self.valid_allocation()
            mutate(data)
            cases.append(data)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                validate_allocation(data)

    def test_zero_waiting_forbids_waiting_use(self):
        data = self.valid_allocation()
        data["conditional_purchases"][1]["percent"] = 50
        data["waiting_pct"] = 0
        data["waiting_use"] = ["上抜け用"]
        with self.assertRaises(ValidationError):
            validate_allocation(data)

    def test_invalid_fixture_rejected_for_condition_cap(self):
        data = json.loads((ROOT / "fixtures/invalid/allocation.json").read_text())
        with self.assertRaisesRegex(ValidationError, "40%"):
            validate_allocation(data)

    def test_zone_cannot_lock_before_or_after_phase4(self):
        zone = PriceZone("support", "主要支持帯", 209, 216)
        for phase in (0, 1, 3, 5, 8):
            state = EntryState("2.0.0", "ACME", current_phase=phase)
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                state.lock_zones([zone])

    def test_zone_lock_and_audited_revision(self):
        state = EntryState("2.0.0", "ACME", current_phase=4)
        original = PriceZone("support", "主要支持帯", 209, 216)
        state.lock_zones([original])
        self.assertEqual(state.zones_locked_at_phase, 4)
        state.current_phase = 6
        with self.assertRaisesRegex(ValueError, "理由.*影響"):
            state.revise_zone("support", PriceZone("support", "主要支持帯", 210, 217), "", "影響")
        with self.assertRaisesRegex(ValueError, "内部ID"):
            state.revise_zone("support", PriceZone("other", "主要支持帯", 210, 217), "分割", "更新")
        replacement = PriceZone("support", "主要支持帯", 210, 217)
        state.revise_zone("support", replacement, "分割調整", "全条件を1ドル上方修正")
        revision = state.zone_revisions[0]
        self.assertEqual(
            (revision.phase, revision.old_zone, revision.new_zone), (6, original, replacement)
        )
        self.assertIn("210～217ドル", replacement.describe())

    def test_state_cross_field_invariants(self):
        with self.assertRaises(ValidationError):
            validate_state(EntryState("2.0.0", "ACME", current_phase=5))
        inconsistent = EntryState("2.0.0", "ACME", zones_locked=True)
        with self.assertRaises(ValidationError):
            validate_state(inconsistent)

    def test_route_priority_and_low_event_rule(self):
        allocation = Allocation(
            current_purchase_pct=20,
            conditional_purchases=[ConditionalPurchase("イベント通過後", 40, "決算確認", False)],
            pre_event_cap_pct=20,
            waiting_pct=40,
            waiting_use=["イベント後用"],
            rationale="イベント支配度で抑制",
            adjustment_factors=["イベント支配度"],
        )
        decision = Decision(
            "条件待ち",
            ["イベント通過後"],
            ["イベント通過後"],
            allocation,
            "均衡",
            "中",
            "理由",
            "リスク",
            "取り逃し",
        )
        state = EntryState(
            "2.0.0", "ACME", current_phase=4, event_dominance="低", decision=decision
        )
        with self.assertRaisesRegex(ValidationError, "低支配度"):
            validate_state(state)
        decision.routes = ["押し目", "イベント通過後"]
        with self.assertRaisesRegex(ValidationError, "優先順位"):
            validate_state(state)

    def test_price_boundary_and_freshness(self):
        self.assertIn("限定分析", assess_price_discrepancy([215.9, 216.1], 5, 7, [216]))
        self.assertEqual(assess_price_discrepancy([210, 211], 5, 7, [216]), "継続可能")
        with self.assertRaises(ValidationError):
            validate_freshness(90, "主要判断に使用")
        validate_freshness(90, "鮮度不足のため方向判断には不使用")
