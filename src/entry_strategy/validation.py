"""JSON Schema and cross-field validation for repository artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import EntryState

ALLOCATION_FACTORS = {
    "中期構造",
    "短期状態",
    "ボラティリティ",
    "相対強度",
    "イベント支配度",
    "価格非対称性",
    "市場環境",
    "判断確信度",
    "既存保有の有無",
}
WAITING_USES = {"押し目用", "上抜け用", "イベント後用", "条件失効により未使用"}


class ValidationError(ValueError):
    """Raised when a cross-field invariant is violated."""


def _integer_percent(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
        raise ValidationError(f"{name}は0～100の整数です")
    return value


def validate_allocation(data: dict[str, Any]) -> None:
    current = _integer_percent(data["current_purchase_pct"], "現在購入比率")
    waiting = _integer_percent(data["waiting_pct"], "待機比率")
    cap = _integer_percent(data["pre_event_cap_pct"], "イベント前購入上限")
    if current > 40:
        raise ValidationError("現在値という1条件の購入比率は40%以下です")

    conditional = data["conditional_purchases"]
    if not isinstance(conditional, list):
        raise ValidationError("条件成立時購入は配列です")
    conditional_total = 0
    before_event_total = current
    for item in conditional:
        percent = _integer_percent(item["percent"], "条件成立時比率")
        if percent > 40:
            raise ValidationError("1条件の購入比率は40%以下です")
        if not str(item.get("condition", "")).strip():
            raise ValidationError("条件成立時比率には判定可能な条件が必要です")
        conditional_total += percent
        if item.get("before_event") is True:
            before_event_total += percent

    if current + conditional_total + waiting != 100:
        raise ValidationError("現在・条件成立時・待機比率の合計は100%である必要があります")
    uses = data["waiting_use"]
    if waiting > 0 and (not uses or any(use not in WAITING_USES for use in uses)):
        raise ValidationError("待機比率には許可された用途が必要です")
    if waiting == 0 and uses:
        raise ValidationError("待機比率0%では待機用途を指定できません")
    if before_event_total > cap:
        raise ValidationError("イベント前に実行可能な購入比率がイベント前上限を超えています")
    if data.get("unit") != "target_position_percent":
        raise ValidationError("比率は目標ポジション基準でなければなりません")
    factors = data.get("adjustment_factors", [])
    if not factors or any(factor not in ALLOCATION_FACTORS for factor in factors):
        raise ValidationError("比率調整要因は正本で許可された要因だけを使用します")
    if not str(data.get("rationale", "")).strip():
        raise ValidationError("基本範囲からの増減理由が必要です")


def validate_state(state: EntryState) -> None:
    allowed = range(0, 9) if state.mode == "initial" else range(1, 3)
    if state.current_phase not in allowed:
        raise ValidationError("Phaseがモードの範囲外です")
    if state.zones_locked != bool(state.price_zones):
        raise ValidationError("価格帯ロックと価格帯の有無が一致しません")
    if state.zones_locked and state.zones_locked_at_phase != 4:
        raise ValidationError("価格帯の固定Phaseは4でなければなりません")
    if state.mode == "initial" and state.current_phase >= 5 and not state.zones_locked:
        raise ValidationError("初回Phase 5以降はPhase 4の固定価格帯が必要です")
    if state.decision:
        validate_allocation(asdict(state.decision.allocation))
        if state.decision.current_action in {"現在購入", "条件待ち"} and not state.decision.routes:
            raise ValidationError("購入を行う判断には購入経路が必要です")
        if state.decision.current_action in {"購入計画中止", "個別銘柄分析へ差し戻し"} and (
            state.decision.routes
        ):
            raise ValidationError("中止または差し戻しでは購入経路を指定できません")
        if state.decision.route_priority != state.decision.routes:
            raise ValidationError("購入経路の配列順をそのまま優先順位として明示してください")
        if state.decision.current_action == "個別銘柄分析へ差し戻し" and not (
            state.decision.return_to_stock_analysis
        ):
            raise ValidationError("差し戻し行動では差し戻し要否をtrueにします")
        if state.event_dominance == "低" and state.decision.routes == ["イベント通過後"]:
            raise ValidationError("低支配度イベントだけを待機理由にできません")
    if state.mode == "initial" and state.current_phase == 8:
        required = (
            state.medium_term_structure,
            state.short_term_state,
            state.event_dominance,
            state.price_asymmetry,
            state.plan_expiry,
            state.next_review,
            state.decision,
        )
        if any(value is None or value == "" for value in required):
            raise ValidationError(
                "Phase 8には二軸状態、イベント、非対称性、判断、期限、再評価が必要です"
            )


def validate_output(data: dict[str, Any]) -> None:
    """Validate final-output relationships not expressible in JSON Schema."""
    decision = data["decision"]
    validate_allocation(decision["allocation"])
    if decision["current_action"] in {"現在購入", "条件待ち"} and not decision["routes"]:
        raise ValidationError("購入を行う判断には購入経路が必要です")
    if (
        decision["current_action"] in {"購入計画中止", "個別銘柄分析へ差し戻し"}
        and decision["routes"]
    ):
        raise ValidationError("中止または差し戻しでは購入経路を指定できません")
    if decision["route_priority"] != decision["routes"]:
        raise ValidationError("購入経路の配列順と優先順位が一致しません")
    if data["event_dominance"] == "低" and decision["routes"] == ["イベント通過後"]:
        raise ValidationError("低支配度イベントだけを購入経路にできません")
    for item in data["data_freshness"]:
        validate_freshness(item["delay_days"], item["usage"])


def assess_price_discrepancy(
    prices: list[float], atr: float, zone_width: float, boundaries: list[float]
) -> str:
    if len(prices) < 2 or atr <= 0 or zone_width <= 0:
        raise ValidationError("複数価格と正のATR・価格帯幅が必要です")
    spread = max(prices) - min(prices)
    crosses = any(min(prices) < boundary <= max(prices) for boundary in boundaries)
    if crosses:
        return "限定分析: 条件境界をまたぐため再取得が必要"
    return "継続可能" if spread < atr and spread < zone_width else "限定分析: 価格差が重要"


def validate_freshness(delay_days: int, usage: str) -> None:
    if delay_days < 0:
        raise ValidationError("遅延日数は0以上です")
    allowed = {"主要判断に使用", "補助的に使用", "鮮度不足のため方向判断には不使用"}
    if usage not in allowed:
        raise ValidationError("使用可否が不正です")
    if delay_days > 45 and usage == "主要判断に使用":
        raise ValidationError("古い需給データを主要判断に使用できません")


def validate_repository(root: Path) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise ValidationError("jsonschemaを含むdev依存をインストールしてください") from exc

    state_schema = json.loads((root / "schemas/entry-strategy-state.schema.json").read_text())
    output_schema = json.loads((root / "schemas/entry-strategy-output.schema.json").read_text())
    review_schema = json.loads(
        (root / "schemas/entry-strategy-update-review.schema.json").read_text()
    )
    for path in sorted((root / "fixtures/valid").glob("*.json")):
        payload = json.loads(path.read_text())
        schema = output_schema if "output" in path.name else state_schema
        jsonschema.validate(payload, schema)
        if "output" in path.name:
            validate_output(payload)
    for path in sorted((root / "samples").glob("*.json")):
        payload = json.loads(path.read_text())
        if path.name == "final-execution-card.json":
            jsonschema.validate(payload, output_schema)
            validate_output(payload)
        elif path.name == "update-review.json":
            jsonschema.validate(payload, review_schema)
    invalid = json.loads((root / "fixtures/invalid/allocation.json").read_text())
    try:
        validate_allocation(invalid)
    except ValidationError:
        pass
    else:
        raise ValidationError("異常fixtureが意図どおり拒否されませんでした")


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", required=True)
    parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    validate_repository(root)
    print("validation passed: schemas, valid samples/fixtures, and invalid fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
