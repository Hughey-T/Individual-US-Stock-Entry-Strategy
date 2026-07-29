"""Typed state and output building blocks for the canonical strategy contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Action = Literal["現在購入", "条件待ち", "購入計画中止", "個別銘柄分析へ差し戻し"]
Route = Literal["現在値", "押し目", "上抜け", "イベント通過後"]
WaitingUse = Literal["押し目用", "上抜け用", "イベント後用", "条件失効により未使用"]
MediumTermStructure = Literal["上昇", "レンジ", "下降", "判定困難"]
ShortTermState = Literal[
    "上昇加速",
    "通常調整",
    "深い調整",
    "反転試行",
    "反転確認",
    "上抜け試行",
    "上抜け確認",
    "ブレイク失敗",
    "下落加速",
    "判定困難",
]
EventDominance = Literal["高", "中", "低"]
Asymmetry = Literal["有利", "やや有利", "中立", "やや不利", "不利", "判定困難"]


@dataclass(frozen=True)
class PriceZone:
    internal_id: str
    label: str
    low: float
    high: float
    currency: Literal["USD"] = "USD"

    def __post_init__(self) -> None:
        if not self.internal_id.strip() or not self.label.strip() or self.low >= self.high:
            raise ValueError("価格帯にはID、自然語ラベル、low < highが必要です")

    def describe(self) -> str:
        return f"{self.label}である{self.low:g}～{self.high:g}ドル"


@dataclass(frozen=True)
class ZoneRevision:
    phase: int
    old_zone: PriceZone
    new_zone: PriceZone
    reason: str
    plan_impact: str


@dataclass(frozen=True)
class ConditionalPurchase:
    route: Route
    percent: int
    condition: str
    before_event: bool


@dataclass
class Allocation:
    current_purchase_pct: int
    conditional_purchases: list[ConditionalPurchase]
    pre_event_cap_pct: int
    waiting_pct: int
    waiting_use: list[WaitingUse]
    rationale: str
    adjustment_factors: list[str]
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
    schema_version: Literal["2.0.0"]
    ticker: str
    mode: Literal["initial", "update"] = "initial"
    current_phase: int = 0
    initial_complete: bool = False
    zones_locked: bool = False
    zones_locked_at_phase: int | None = None
    price_zones: dict[str, PriceZone] = field(default_factory=dict)
    zone_revisions: list[ZoneRevision] = field(default_factory=list)
    medium_term_structure: MediumTermStructure | None = None
    short_term_state: ShortTermState | None = None
    event_dominance: EventDominance | None = None
    price_asymmetry: Asymmetry | None = None
    decision: Decision | None = None
    plan_expiry: str | None = None
    next_review: str | None = None

    def lock_zones(self, zones: list[PriceZone]) -> None:
        if self.mode != "initial" or self.current_phase != 4 or self.zones_locked:
            raise ValueError("主要価格帯は初回Phase 4で一度だけ固定できます")
        if not zones or len({zone.internal_id for zone in zones}) != len(zones):
            raise ValueError("一意なIDを持つ価格帯が少なくとも一つ必要です")
        self.price_zones = {zone.internal_id: zone for zone in zones}
        self.zones_locked = True
        self.zones_locked_at_phase = 4

    def revise_zone(self, zone_id: str, replacement: PriceZone, reason: str, impact: str) -> None:
        if not self.zones_locked or self.current_phase < 4 or zone_id not in self.price_zones:
            raise ValueError("Phase 4以降の固定済み価格帯だけを変更できます")
        if replacement.internal_id != zone_id:
            raise ValueError("価格帯変更で内部IDを変更できません")
        if not reason.strip() or not impact.strip():
            raise ValueError("価格帯変更には理由と購入計画への影響が必要です")
        old = self.price_zones[zone_id]
        self.zone_revisions.append(
            ZoneRevision(self.current_phase, old, replacement, reason.strip(), impact.strip())
        )
        self.price_zones[zone_id] = replacement
