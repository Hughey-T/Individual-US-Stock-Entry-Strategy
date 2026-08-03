"""Schema, temporal, route, allocation, and publication validation."""

from __future__ import annotations
import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from .models import EntryState

ALLOCATION_FACTORS = {
    "thesis validity",
    "valuation expected return",
    "medium-term structure",
    "short-term state",
    "volatility",
    "relative strength",
    "event dominance",
    "market regime",
    "plan robustness",
    "existing holding reference status",
    "中期構造",
    "短期状態",
    "ボラティリティ",
    "相対強度",
    "イベント支配度",
    "市場環境",
    "判断確信度",
    "既存保有の有無",
}
WAITING_USES = {
    "pullback",
    "breakout",
    "post_event",
    "expired_unused",
    "押し目用",
    "上抜け用",
    "イベント後用",
    "条件失効により未使用",
}
TERMINAL_GATES = {"NO_ENTRY", "RETURN_TO_INDIVIDUAL_ANALYSIS", "INSUFFICIENT_EVIDENCE"}


class ValidationError(ValueError):
    pass


def strict_json_loads(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("malformed UTF-8") from exc

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out = {}
        for k, v in items:
            if k in out:
                raise ValidationError(f"duplicate JSON key: {k}")
            out[k] = v
        return out

    def invalid(value: str) -> None:
        raise ValidationError(f"non-finite number: {value}")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except json.JSONDecodeError as exc:
        raise ValidationError("malformed JSON") from exc


def require_object(raw: bytes, *, context: str = "JSON") -> dict[str, Any]:
    """Decode a strict JSON object for every external runtime boundary."""
    value = strict_json_loads(raw)
    if not isinstance(value, dict):
        raise ValidationError(f"{context} must be an object")
    return value


def _pct(v: Any, n: str) -> int:
    if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 100:
        raise ValidationError(f"{n}は0～100の整数です")
    return v


def validate_allocation(
    data: dict[str, Any],
    entry_gate: str | None = None,
    active_routes: set[str] | None = None,
    event_dominance: str | None = None,
    binary_exception: dict[str, Any] | None = None,
) -> None:
    current = _pct(data["current_purchase_pct"], "現在購入比率")
    waiting = _pct(data["waiting_pct"], "待機比率")
    cap = _pct(data["pre_event_cap_pct"], "イベント前購入上限")
    conditional = data["conditional_purchases"]
    if not isinstance(conditional, list):
        raise ValidationError("条件成立時購入は配列です")
    total = current
    before = current
    seen = set()
    for item in conditional:
        pct = _pct(item["percent"], "条件成立時比率")
        if pct > 40 or current > 40:
            raise ValidationError("1条件の購入比率は40%以下です")
        route = item["route"]
        if route in seen:
            raise ValidationError("同一routeへ重複配分できません")
        seen.add(route)
        total += pct
        before += pct if item.get("before_event") is True else 0
        if not str(item.get("condition", "")).strip():
            raise ValidationError("判定可能な条件が必要です")
        if active_routes is not None and route not in active_routes and pct:
            raise ValidationError("inactive routeは0%です")
    if total + waiting != 100:
        raise ValidationError("購入比率と待機比率の合計は100%です")
    uses = data["waiting_use"]
    if waiting > 0 and (not uses or any(x not in WAITING_USES for x in uses)):
        raise ValidationError("待機比率には用途が必要です")
    if waiting == 0 and uses:
        raise ValidationError("待機比率0%では用途を指定できません")
    if before > cap:
        raise ValidationError("event前比率がpre-event maximumを超えています")
    if data.get("unit") != "target_position_percent":
        raise ValidationError("比率は目標ポジション基準です")
    if not data.get("adjustment_factors") or any(
        x not in ALLOCATION_FACTORS for x in data["adjustment_factors"]
    ):
        raise ValidationError("許可された比率要因だけを使用します")
    if not str(data.get("rationale", "")).strip():
        raise ValidationError("比率理由が必要です")
    if entry_gate in TERMINAL_GATES and (current or any(i["percent"] for i in conditional)):
        raise ValidationError("terminal entry gateでは全購入比率0%です")
    if event_dominance == "BINARY" and before:
        required = {
            "reason",
            "maximum_ratio",
            "downside",
            "permanent_loss_concern",
            "gap_risk_acknowledgement",
            "invalidation",
            "post_event_mandatory_review",
        }
        if (
            not binary_exception
            or not required <= binary_exception.keys()
            or before > binary_exception["maximum_ratio"]
        ):
            raise ValidationError("binary eventのevent前経路には完全な限定例外が必要です")


def validate_routes(routes: list[dict[str, Any]]) -> None:
    ids = [r["route_id"] for r in routes]
    priorities = [r["priority"] for r in routes]
    if len(ids) != len(set(ids)):
        raise ValidationError("route IDs must be unique")
    if len(priorities) != len(set(priorities)):
        raise ValidationError("route priorities must be unique")
    for r in routes:
        if r.get("expired") is True:
            raise ValidationError("expired route cannot remain eligible")
        for key in (
            "price_condition",
            "valuation_condition",
            "volume_condition",
            "relative_strength_condition",
            "market_condition",
            "event_condition",
            "failure_condition",
            "expiry",
        ):
            if not str(r.get(key, "")).strip():
                raise ValidationError(f"route condition missing: {key}")
        if r.get("overlap_with") and not r.get("transition") and not r.get("exclusive_precedence"):
            raise ValidationError("overlapにはpriorityまたはroute transitionが必要です")


def validate_evidence(records: list[dict[str, Any]], source_cutoff: str) -> None:
    cutoff = datetime.fromisoformat(source_cutoff.replace("Z", "+00:00"))
    for r in records:
        for k in ("source", "as_of", "retrieved_at", "classification"):
            if not r.get(k):
                raise ValidationError(f"evidence {k} is required")
        if r["classification"] not in {
            "FACTS",
            "COMPANY_CLAIMS",
            "EXTERNAL_ESTIMATES",
            "AI_ASSUMPTIONS",
            "AI_JUDGMENTS",
            "UNRESOLVED",
        }:
            raise ValidationError("invalid information classification")
        if (
            datetime.fromisoformat(r["as_of"].replace("Z", "+00:00")) > cutoff
            or datetime.fromisoformat(r["retrieved_at"].replace("Z", "+00:00")) > cutoff
        ):
            raise ValidationError("future evidence is forbidden")


def validate_update_cutoff(previous: str, new: str) -> None:
    old = datetime.fromisoformat(previous.replace("Z", "+00:00"))
    nxt = datetime.fromisoformat(new.replace("Z", "+00:00"))
    if nxt <= old:
        raise ValidationError("update source cutoff must be a strictly later UTC instant")


def validate_state(state: EntryState) -> None:
    maximum = 12 if state.mode == "initial" else 5
    if state.current_phase not in range(0, maximum + 1):
        raise ValidationError("Phaseが範囲外です")
    if state.zones_locked != bool(state.price_zones):
        raise ValidationError("価格帯ロックと価格帯が不一致です")
    if state.zones_locked and state.zones_locked_at_phase != 7:
        raise ValidationError("価格帯の固定Phaseは7です")
    if state.mode == "initial" and state.current_phase < 7 and state.zones_locked:
        raise ValidationError("Phase 7より前に価格帯を固定できません")
    if state.reconciliation_disclosed and not state.independent_entry_gate:
        raise ValidationError("entry gate固定前のreconciliationは禁止です")
    if state.decision:
        validate_allocation(
            asdict(state.decision.allocation),
            state.independent_entry_gate,
            set(state.decision.routes),
            state.event_dominance,
        )


def assess_price_discrepancy(
    prices: list[float], atr: float, zone_width: float, boundaries: list[float]
) -> str:
    if len(prices) < 2 or atr <= 0 or zone_width <= 0:
        raise ValidationError("複数価格と正のATR・価格帯幅が必要です")
    spread = max(prices) - min(prices)
    return (
        "限定分析: 条件境界をまたぐため再取得が必要"
        if any(min(prices) < b <= max(prices) for b in boundaries)
        else ("継続可能" if spread < atr and spread < zone_width else "限定分析: 価格差が重要")
    )


def validate_freshness(delay_days: int, usage: str) -> None:
    if delay_days < 0 or usage not in {
        "主要判断に使用",
        "補助的に使用",
        "鮮度不足のため方向判断には不使用",
    }:
        raise ValidationError("鮮度指定が不正です")
    if delay_days > 45 and usage == "主要判断に使用":
        raise ValidationError("古いデータを主要判断に使用できません")


def validate_output(data: dict[str, Any]) -> None:
    validate_allocation(data["decision"]["allocation"], data.get("entry_gate"))


def validate_repository(root: Path) -> None:
    import jsonschema

    for path in (root / "schemas").glob("*.json"):
        jsonschema.Draft202012Validator.check_schema(strict_json_loads(path.read_bytes()))
    for path in list((root / "samples").glob("*.json")) + list(
        (root / "fixtures/valid").glob("*.json")
    ):
        strict_json_loads(path.read_bytes())
    bad = json.loads((root / "fixtures/invalid/allocation.json").read_text())
    try:
        validate_allocation(bad)
    except ValidationError:
        pass
    else:
        raise ValidationError("invalid fixture accepted")


def _main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--all", action="store_true", required=True)
    p.parse_args()
    validate_repository(Path(__file__).resolve().parents[2])
    print("validation passed: strict JSON, schemas, samples, fixtures")
    return 0


REQUIRED_SIMULATION_SCENARIOS = {
    "sharp_rise",
    "normal_pullback",
    "support_bounce",
    "support_break",
    "breakout_maintained",
    "failed_breakout",
    "pre_event_trigger",
    "event_gap_up",
    "event_gap_down",
    "market_selloff",
    "sector_selloff",
    "thesis_deterioration",
    "volatility_spike",
    "expiry",
}

REQUIRED_ADVERSARIAL_CHECKS = {
    "cash_superior",
    "chase_risk",
    "false_support",
    "false_breakout",
    "short_covering",
    "market_beta",
    "event_gap_risk",
    "thesis_valid_price_unattractive",
    "valuation_attractive_structure_unstable",
    "technical_strength_thesis_deterioration",
    "current_vs_waiting_expected_value",
    "opportunity_cost_overstatement",
    "loss_avoidance_overstatement",
    "unknown_information",
    "route_reversal",
}

REQUIRED_LEDGER_FIELDS = {
    "strategy_identity",
    "security_identity",
    "analysis_handoff_identity",
    "as_of",
    "source_cutoff",
    "reference_price",
    "valuation_reference_range",
    "technical_zones",
    "thesis_signal",
    "valuation_signal",
    "price_signal",
    "event_signal",
    "market_regime_signal",
    "entry_gate",
    "current_action",
    "active_routes",
    "route_priority",
    "ratios",
    "pre_event_maximum",
    "invalidation",
    "expiry",
    "confidence",
    "strongest_reason",
    "strongest_objection",
    "artifact_hashes",
}

REQUIRED_OUTCOME_METRICS = {
    "route_trigger_rate",
    "trigger_timing",
    "post_trigger_return",
    "benchmark_relative_return",
    "sector_relative_return",
    "maximum_favorable_excursion",
    "maximum_adverse_excursion",
    "atr_normalized_adverse_excursion",
    "false_breakout_rate",
    "support_failure_rate",
    "event_gap_result",
    "waiting_opportunity_cost",
    "current_entry_result",
    "pullback_route_result",
    "breakout_route_result",
    "post_event_route_result",
    "no_entry_result",
    "return_to_analysis_result",
    "ratio_adequacy",
    "invalidation_timing",
    "expiry_effectiveness",
    "plan_robustness",
    "confidence_calibration",
}


def validate_adversarial_review(review: dict[str, Any]) -> None:
    checks = review.get("checks")
    if not isinstance(checks, dict) or set(checks) != REQUIRED_ADVERSARIAL_CHECKS:
        raise ValidationError("adversarial review must cover the complete countercase set")
    if any(not isinstance(value, str) or not value.strip() for value in checks.values()):
        raise ValidationError("every adversarial check requires a reasoned conclusion")
    if review.get("resulting_gate") not in {
        "ENTRY_PLANNING_ALLOWED",
        "ENTRY_PLANNING_CONDITIONAL",
        "WAIT_WITHOUT_PLAN",
        "NO_ENTRY",
        "RETURN_TO_INDIVIDUAL_ANALYSIS",
        "INSUFFICIENT_EVIDENCE",
    }:
        raise ValidationError("adversarial review requires a valid resulting gate")
    if not isinstance(review.get("new_evidence"), list):
        raise ValidationError("adversarial review new evidence must be an explicit list")


def validate_decision_ledger(ledger: dict[str, Any]) -> None:
    missing = REQUIRED_LEDGER_FIELDS - ledger.keys()
    if missing:
        raise ValidationError(f"decision ledger fields missing: {sorted(missing)}")
    for field in ("strategy_identity", "security_identity", "as_of", "source_cutoff"):
        if not ledger[field]:
            raise ValidationError(f"decision ledger {field} is required")
    hashes = ledger["artifact_hashes"]
    if (
        not isinstance(hashes, list)
        or not hashes
        or any(
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in hashes
        )
    ):
        raise ValidationError("decision ledger artifact hashes must be SHA-256 values")


def validate_snapshot(data: dict[str, Any]) -> None:
    price = data.get("current_reference_price")
    if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
        raise ValidationError("current reference price is required and must be positive")
    if data.get("currency") != "USD":
        raise ValidationError("snapshot currency mismatch")
    prices = data.get("price_sources", [])
    if len(prices) >= 2 and max(prices) - min(prices) > data.get("tolerance", 0):
        raise ValidationError("conflicting prices")
    if data.get("stale") is True:
        raise ValidationError("stale price")
    actions = data.get("corporate_actions", [])
    for action in actions:
        if action.get("type") in {"split", "dividend"} and action.get("adjusted") is not True:
            raise ValidationError("corporate action adjustment required")


def validate_simulations(results: list[dict[str, Any]]) -> None:
    scenarios = [result.get("scenario") for result in results]
    if len(scenarios) != len(set(scenarios)):
        raise ValidationError("duplicate simulation scenario")
    missing = REQUIRED_SIMULATION_SCENARIOS - set(scenarios)
    if missing:
        raise ValidationError(f"simulation coverage missing: {sorted(missing)}")
    for result in results:
        required = {
            "triggered_route",
            "triggered_ratio",
            "route_precedence",
            "unused_ratio",
            "invalidation",
            "contradictory_actions",
            "duplicate_allocation",
            "stale_zone",
            "reevaluation_required",
        }
        if not required <= result.keys():
            raise ValidationError("simulation result fields missing")
        if result["contradictory_actions"] or result["duplicate_allocation"]:
            raise ValidationError("simulation found contradictory action or duplicate allocation")


def validate_outcome(outcome: dict[str, Any], plan_cutoff: str) -> None:
    status = outcome.get("status")
    if status not in {"not_matured", "matured"}:
        raise ValidationError("invalid outcome maturity")
    observation = datetime.fromisoformat(outcome["observation_cutoff"].replace("Z", "+00:00"))
    cutoff = datetime.fromisoformat(plan_cutoff.replace("Z", "+00:00"))
    if observation <= cutoff:
        raise ValidationError("outcome observation must follow plan cutoff")
    if status == "not_matured" and outcome.get("metrics"):
        raise ValidationError("not matured outcome cannot contain future metrics")
    if status == "matured":
        metrics = outcome.get("metrics")
        if not isinstance(metrics, dict) or set(metrics) != REQUIRED_OUTCOME_METRICS:
            raise ValidationError("matured outcome requires the complete metric set")


def validate_update_diff(items: list[dict[str, Any]]) -> None:
    for item in items:
        changed = item.get("changed")
        old, new = item.get("old"), item.get("new")
        if changed is True and old == new:
            raise ValidationError("changed item has identical values")
        if changed is False and old != new:
            raise ValidationError("unchanged item differs")


def validate_zone_freshness(zone: dict[str, Any], *, current_generation: int) -> None:
    if zone.get("generation") != current_generation:
        raise ValidationError("stale zone")
    expiry = zone.get("expiry")
    if not expiry:
        raise ValidationError("zone expiry required")


def validate_event_policy(
    dominance: str,
    allocation: dict[str, Any],
    binary_exception: dict[str, Any] | None = None,
) -> None:
    if dominance not in {"LOW", "MANAGEABLE", "DOMINANT", "BINARY", "UNKNOWN"}:
        raise ValidationError("invalid event dominance")
    validate_allocation(allocation, event_dominance=dominance, binary_exception=binary_exception)
    if dominance == "BINARY" and binary_exception:
        if binary_exception.get("post_event_mandatory_review") is not True:
            raise ValidationError("binary exception requires mandatory post-event review")


if __name__ == "__main__":
    raise SystemExit(_main())
