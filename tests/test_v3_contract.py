import json
import tempfile
import unittest
from pathlib import Path
from entry_strategy.models import EntryState, PriceZone
from entry_strategy.storage import Store
from entry_strategy.validation import (
    ValidationError,
    strict_json_loads,
    validate_allocation,
    validate_evidence,
    validate_routes,
    validate_update_cutoff,
)


class V3Tests(unittest.TestCase):
    def test_gate_blind_order_and_immutability(self):
        s = EntryState("3.0.0", "ACME", current_phase=2, usage_mode="pipeline")
        with self.assertRaises(ValueError):
            s.disclose_reconciliation()
        s.freeze_entry_gate("ENTRY_PLANNING_ALLOWED", ["e1"])
        with self.assertRaises(ValueError):
            s.freeze_entry_gate("NO_ENTRY", ["future"])
        s.current_phase = 3
        s.disclose_reconciliation()
        self.assertTrue(s.reconciliation_disclosed)

    def test_zone_lock_only_phase7_overlap_and_revision_chain(self):
        z = PriceZone("s", "support", 90, 95)
        for p in (1, 6, 8):
            with self.assertRaises(ValueError):
                EntryState("3.0.0", "X", current_phase=p).lock_zones([z])
        s = EntryState("3.0.0", "X", current_phase=7)
        s.lock_zones([z, PriceZone("r", "resistance", 100, 105)])
        s.current_phase = 10
        s.revise_zone(
            "s",
            PriceZone("s", "support", 91, 96),
            "new split-adjusted evidence",
            "routes repriced",
            ["e2"],
        )
        self.assertNotEqual(s.zone_revisions[0].previous_hash, s.zone_revisions[0].new_hash)

    def test_semantics(self):
        with self.assertRaises(ValidationError):
            validate_update_cutoff("2026-01-01T00:00:00Z", "2025-12-31T19:00:00-05:00")
        with self.assertRaises(ValidationError):
            strict_json_loads(b'{"x":1,"x":2}')
        with self.assertRaises(ValidationError):
            strict_json_loads(b'{"x":NaN}')
        with self.assertRaises(ValidationError):
            validate_evidence(
                [
                    {
                        "classification": "FACTS",
                        "source": "s",
                        "as_of": "2027-01-01T00:00:00Z",
                        "retrieved_at": "2026-01-01T00:00:00Z",
                    }
                ],
                "2026-01-01T00:00:00Z",
            )

    def test_routes_and_terminal_ratios(self):
        route = {
            "route_id": "a",
            "priority": 1,
            "price_condition": "p",
            "valuation_condition": "v",
            "volume_condition": "vol",
            "relative_strength_condition": "rs",
            "market_condition": "m",
            "event_condition": "e",
            "failure_condition": "f",
            "expiry": "5 days",
        }
        with self.assertRaises(ValidationError):
            validate_routes([route, route])
        allocation = {
            "current_purchase_pct": 1,
            "conditional_purchases": [],
            "waiting_pct": 99,
            "waiting_use": ["expired_unused"],
            "pre_event_cap_pct": 1,
            "unit": "target_position_percent",
            "adjustment_factors": ["thesis validity"],
            "rationale": "x",
        }
        with self.assertRaises(ValidationError):
            validate_allocation(allocation, "NO_ENTRY")

    def test_publication_roundtrip_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d))
            raw = json.dumps({"phase_identity": "initial-1", "phase": 1}).encode()
            receipt = store.publish("s1", "initial-1", raw)
            self.assertTrue(receipt["readback_verified"])
            self.assertEqual(store.read_active("s1"), {"phase_identity": "initial-1", "phase": 1})
            self.assertTrue(store.publish("s1", "initial-1", raw)["replay"])
            active = (Path(d) / "s1" / "active").read_text()
            (Path(d) / "s1" / "generations" / active / "artifact.json").write_text("{}")
            with self.assertRaises(ValidationError):
                store.verify("s1")
