"""Dependency-free domain models. JSON serialization uses ``dataclasses.asdict``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Action = Literal["現在購入", "条件待ち", "購入計画中止", "個別銘柄分析へ差し戻し"]
Route = Literal["現在値", "押し目", "上抜け", "イベント通過後"]


@dataclass(frozen=True)
class PriceZone:
    internal_id: str
    label: str
    low: float
    high: float
    currency: str = "USD"

    def describe(self) -> str:
        return f"{self.label}である{self.low:g}～{self.high:g}ドル"


@dataclass(frozen=True)
class ZoneRevision:
    old_zone: PriceZone
    new_zone: PriceZone
    reason: str
    plan_impact: str


@dataclass
class Allocation:
    current_purchase_pct: int
    conditional_purchases_pct: list[int]
    pre_event_cap_pct: int
    waiting_pct: int
    waiting_use: list[str]
    rationale: str
    unit: Literal["target_position_percent"] = "target_position_percent"


@dataclass
class Decision:
    current_action: Action
    routes: list[Route]
    route_priority: list[Route]
    allocation: Allocation
    avoided_risk: Literal["機会損失", "短期下落", "均衡"]
    confidence: Literal["高", "中", "低"]
    primary_reason: str
    primary_short_term_risk: str
    missed_opportunity_risk: str
    return_to_stock_analysis: bool = False


@dataclass
class EntryState:
    schema_version: str
    ticker: str
    mode: Literal["initial", "update"] = "initial"
    current_phase: int = 0
    zones_locked: bool = False
    price_zones: dict[str, PriceZone] = field(default_factory=dict)
    zone_revisions: list[ZoneRevision] = field(default_factory=list)
    medium_term_structure: str | None = None
    short_term_state: str | None = None
    event_dominance: str | None = None
    decision: Decision | None = None
    plan_expiry: str | None = None
    next_review: str | None = None

    def lock_zones(self, zones: list[PriceZone], phase: int) -> None:
        if phase != 4 or self.zones_locked:
            raise ValueError("主要価格帯はPhase 4で一度だけ固定できます")
        if not zones:
            raise ValueError("少なくとも一つの価格帯が必要です")
        self.price_zones = {zone.internal_id: zone for zone in zones}
        self.zones_locked = True

    def revise_zone(self, zone_id: str, replacement: PriceZone, reason: str, impact: str) -> None:
        if not self.zones_locked or zone_id not in self.price_zones:
            raise ValueError("固定済み価格帯だけを変更できます")
        if not reason.strip() or not impact.strip():
            raise ValueError("価格帯変更には理由と購入計画への影響が必要です")
        old = self.price_zones[zone_id]
        self.zone_revisions.append(ZoneRevision(old, replacement, reason, impact))
        self.price_zones[zone_id] = replacement
