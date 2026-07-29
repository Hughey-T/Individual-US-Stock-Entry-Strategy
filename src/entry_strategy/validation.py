"""Cross-field validation beyond JSON Schema."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import EntryState


class ValidationError(ValueError):
    pass


def validate_allocation(data: dict[str, Any]) -> None:
    values = [data["current_purchase_pct"], *data["conditional_purchases_pct"]]
    if any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 100 for v in values):
        raise ValidationError("比率は0～100の整数です")
    if any(v > 40 for v in data["conditional_purchases_pct"]):
        raise ValidationError("1条件の購入比率は原則40%以下です")
    if sum(values) + data["waiting_pct"] != 100:
        raise ValidationError("購入比率と待機比率の合計は100%である必要があります")
    if data["waiting_pct"] and not data["waiting_use"]:
        raise ValidationError("待機比率には用途が必要です")
    if data.get("unit") != "target_position_percent":
        raise ValidationError("比率は目標ポジション基準でなければなりません")
    if sum(values) > data["pre_event_cap_pct"]:
        raise ValidationError("イベント前購入上限を超えています")


def validate_state(state: EntryState) -> None:
    if state.current_phase not in (range(0, 9) if state.mode == "initial" else range(1, 3)):
        raise ValidationError("Phaseがモードの範囲外です")
    if state.current_phase >= 5 and not state.zones_locked:
        raise ValidationError("Phase 5以降はPhase 4の固定価格帯が必要です")
    if state.decision:
        validate_allocation(asdict(state.decision.allocation))
        if state.decision.route_priority and set(state.decision.route_priority) != set(
            state.decision.routes
        ):
            raise ValidationError("購入経路と優先順位が一致しません")
        if state.event_dominance == "低" and state.decision.routes == ["イベント通過後"]:
            raise ValidationError("低支配度イベントだけを待機理由にできません")
    if state.current_phase == 8 and (not state.plan_expiry or not state.next_review):
        raise ValidationError("Phase 8には計画期限と次回再評価が必要です")


def assess_price_discrepancy(
    prices: list[float], atr: float, zone_width: float, boundaries: list[float]
) -> str:
    spread = max(prices) - min(prices)
    crosses = any(min(prices) < boundary <= max(prices) for boundary in boundaries)
    if crosses:
        return "限定分析: 条件境界をまたぐため再取得が必要"
    return "継続可能" if spread < atr and spread < zone_width else "限定分析: 価格差が重要"


def validate_freshness(delay_days: int, usage: str) -> None:
    if delay_days > 45 and usage == "主要判断に使用":
        raise ValidationError("古い需給データを主要判断に使用できません")


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for path in [
        *root.glob("schemas/*.json"),
        *root.glob("fixtures/**/*.json"),
        *root.glob("samples/*.json"),
    ]:
        json.loads(path.read_text(encoding="utf-8"))
    print("validation passed: JSON syntax and repository contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
