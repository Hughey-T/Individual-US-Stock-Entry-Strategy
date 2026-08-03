import copy
import unittest

from entry_strategy.models import EntryState, PriceZone
from entry_strategy.validation import (
    REQUIRED_ADVERSARIAL_CHECKS,
    REQUIRED_OUTCOME_METRICS,
    REQUIRED_SIMULATION_SCENARIOS,
    ValidationError,
    validate_allocation,
    validate_adversarial_review,
    validate_decision_ledger,
    validate_event_policy,
    validate_outcome,
    validate_simulations,
    validate_snapshot,
    validate_routes,
    validate_update_diff,
    validate_zone_freshness,
)


class SemanticCompletionTests(unittest.TestCase):
    def allocation(self) -> dict:
        return {
            "current_purchase_pct": 20,
            "conditional_purchases": [
                {
                    "route": "PULLBACK_ROUTE",
                    "percent": 20,
                    "condition": "value and support confirmation",
                    "before_event": True,
                }
            ],
            "pre_event_cap_pct": 40,
            "waiting_pct": 60,
            "waiting_use": ["post_event"],
            "rationale": "independent signals",
            "adjustment_factors": ["thesis validity"],
            "unit": "target_position_percent",
        }

    def test_snapshot_price_and_corporate_action_mutations(self):
        valid = {
            "current_reference_price": 100,
            "currency": "USD",
            "price_sources": [100, 100.1],
            "tolerance": 0.2,
            "stale": False,
            "corporate_actions": [
                {"type": "split", "adjusted": True},
                {"type": "dividend", "adjusted": True},
            ],
        }
        validate_snapshot(valid)
        cases = {
            "conflicting": {"price_sources": [100, 102]},
            "stale": {"stale": True},
            "missing": {"current_reference_price": None},
            "currency": {"currency": "EUR"},
            "split": {"corporate_actions": [{"type": "split", "adjusted": False}]},
            "dividend": {"corporate_actions": [{"type": "dividend", "adjusted": False}]},
        }
        for name, mutation in cases.items():
            candidate = {**valid, **mutation}
            with self.subTest(name=name), self.assertRaises(ValidationError):
                validate_snapshot(candidate)

    def test_all_entry_gate_states_freeze(self):
        gates = (
            "ENTRY_PLANNING_ALLOWED",
            "ENTRY_PLANNING_CONDITIONAL",
            "WAIT_WITHOUT_PLAN",
            "NO_ENTRY",
            "RETURN_TO_INDIVIDUAL_ANALYSIS",
            "INSUFFICIENT_EVIDENCE",
        )
        for gate in gates:
            state = EntryState("3.0.0", "ACME", current_phase=2)
            state.freeze_entry_gate(gate, ["evidence"])
            self.assertEqual(state.independent_entry_gate, gate)

    def test_hard_terminal_gate_zero_purchase_for_all_terminal_states(self):
        for gate in (
            "NO_ENTRY",
            "RETURN_TO_INDIVIDUAL_ANALYSIS",
            "INSUFFICIENT_EVIDENCE",
        ):
            candidate = self.allocation()
            with self.subTest(gate=gate), self.assertRaises(ValidationError):
                validate_allocation(candidate, gate)
        zero = self.allocation()
        zero["current_purchase_pct"] = 0
        zero["conditional_purchases"][0]["percent"] = 0
        zero["waiting_pct"] = 100
        zero["pre_event_cap_pct"] = 0
        validate_allocation(zero, "NO_ENTRY")

    def test_zone_mutations_and_staleness(self):
        with self.assertRaises(ValueError):
            PriceZone("bad", "inverted", 10, 9)
        state = EntryState("3.0.0", "ACME", current_phase=7)
        with self.assertRaises(ValueError):
            state.lock_zones([PriceZone("a", "a", 10, 20), PriceZone("b", "b", 19, 30)])
        with self.assertRaises(ValueError):
            state.lock_zones([PriceZone("a", "a", 10, 20, adjusted=False)])
        state.lock_zones([PriceZone("a", "a", 10, 20)])
        state.current_phase = 8
        with self.assertRaises(ValueError):
            state.revise_zone("a", PriceZone("a", "a", 11, 21), "", "impact", ["e"])
        with self.assertRaises(ValidationError):
            validate_zone_freshness({"generation": 1, "expiry": "5 days"}, current_generation=2)

    def test_event_dominance_and_binary_exception(self):
        for dominance in ("LOW", "MANAGEABLE", "DOMINANT", "UNKNOWN"):
            validate_event_policy(dominance, self.allocation())
        with self.assertRaises(ValidationError):
            validate_event_policy("BINARY", self.allocation())
        exception = {
            "reason": "explicit user policy and asymmetric value",
            "maximum_ratio": 40,
            "downside": "material gap",
            "permanent_loss_concern": "reviewed",
            "gap_risk_acknowledgement": True,
            "invalidation": "thesis change",
            "post_event_mandatory_review": True,
        }
        validate_event_policy("BINARY", self.allocation(), exception)
        invalid = copy.deepcopy(exception)
        invalid["post_event_mandatory_review"] = False
        with self.assertRaises(ValidationError):
            validate_event_policy("BINARY", self.allocation(), invalid)

    def test_route_priority_overlap_transition_and_expiry(self):
        base = {
            "route_id": "one",
            "priority": 1,
            "price_condition": "p",
            "valuation_condition": "v",
            "volume_condition": "volume",
            "relative_strength_condition": "rs",
            "market_condition": "market",
            "event_condition": "event",
            "failure_condition": "failure",
            "expiry": "5 trading days",
        }
        duplicate_priority = [base, {**base, "route_id": "two"}]
        with self.assertRaisesRegex(ValidationError, "priorities"):
            validate_routes(duplicate_priority)
        overlap = [{**base, "overlap_with": ["two"]}]
        with self.assertRaisesRegex(ValidationError, "overlap"):
            validate_routes(overlap)
        validate_routes([{**base, "overlap_with": ["two"], "transition": "generation-2"}])
        with self.assertRaisesRegex(ValidationError, "expired"):
            validate_routes([{**base, "expired": True}])

    def test_required_simulation_coverage_and_contradictions(self):
        results = [
            {
                "scenario": scenario,
                "triggered_route": "NO_ROUTE",
                "triggered_ratio": 0,
                "route_precedence": None,
                "unused_ratio": 100,
                "invalidation": False,
                "contradictory_actions": False,
                "duplicate_allocation": False,
                "stale_zone": False,
                "reevaluation_required": scenario == "expiry",
            }
            for scenario in sorted(REQUIRED_SIMULATION_SCENARIOS)
        ]
        validate_simulations(results)
        with self.assertRaisesRegex(ValidationError, "missing"):
            validate_simulations(results[:-1])
        contradictory = copy.deepcopy(results)
        contradictory[0]["contradictory_actions"] = True
        with self.assertRaisesRegex(ValidationError, "contradictory"):
            validate_simulations(contradictory)

    def test_update_diff_and_outcome_maturity_future_leakage(self):
        validate_update_diff(
            [
                {"changed": True, "old": 1, "new": 2},
                {"changed": False, "old": 1, "new": 1},
            ]
        )
        for invalid in (
            {"changed": True, "old": 1, "new": 1},
            {"changed": False, "old": 1, "new": 2},
        ):
            with self.assertRaises(ValidationError):
                validate_update_diff([invalid])
        validate_outcome(
            {"status": "not_matured", "observation_cutoff": "2026-02-01T00:00:00Z"},
            "2026-01-01T00:00:00Z",
        )
        validate_outcome(
            {
                "status": "matured",
                "observation_cutoff": "2026-02-01T00:00:00Z",
                "metrics": {key: 0 for key in REQUIRED_OUTCOME_METRICS},
            },
            "2026-01-01T00:00:00Z",
        )
        with self.assertRaises(ValidationError):
            validate_outcome(
                {
                    "status": "not_matured",
                    "observation_cutoff": "2026-02-01T00:00:00Z",
                    "metrics": {"future": 1},
                },
                "2026-01-01T00:00:00Z",
            )

    def test_adversarial_review_and_decision_ledger_contracts(self):
        review = {
            "checks": {
                key: f"reasoned assessment for {key}" for key in REQUIRED_ADVERSARIAL_CHECKS
            },
            "resulting_gate": "ENTRY_PLANNING_CONDITIONAL",
            "new_evidence": [],
        }
        validate_adversarial_review(review)
        incomplete = copy.deepcopy(review)
        incomplete["checks"].pop("chase_risk")
        with self.assertRaisesRegex(ValidationError, "countercase"):
            validate_adversarial_review(incomplete)

        ledger = {
            "strategy_identity": "strategy-1",
            "security_identity": "ACME:XNAS:USD",
            "analysis_handoff_identity": "handoff-1",
            "as_of": "2026-01-01T00:00:00Z",
            "source_cutoff": "2026-01-01T00:00:00Z",
            "reference_price": 100,
            "valuation_reference_range": {"low": 90, "high": 130},
            "technical_zones": [],
            "thesis_signal": "supportive",
            "valuation_signal": "acceptable",
            "price_signal": "neutral",
            "event_signal": "MANAGEABLE",
            "market_regime_signal": "mixed",
            "entry_gate": "ENTRY_PLANNING_CONDITIONAL",
            "current_action": "WAIT_FOR_PULLBACK",
            "active_routes": ["PULLBACK_ROUTE"],
            "route_priority": ["PULLBACK_ROUTE"],
            "ratios": {"waiting": 100},
            "pre_event_maximum": 0,
            "invalidation": {},
            "expiry": "10 trading days",
            "confidence": "medium",
            "strongest_reason": "value",
            "strongest_objection": "event",
            "artifact_hashes": ["a" * 64],
        }
        validate_decision_ledger(ledger)
        ledger.pop("expiry")
        with self.assertRaisesRegex(ValidationError, "fields missing"):
            validate_decision_ledger(ledger)
