"""Typed building blocks for entry-strategy contract 3.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Literal

CONTRACT_VERSION = "3.0.0"
Mode = Literal["standalone_static", "standalone_runtime", "pipeline"]
EntryGate = Literal[
    "ENTRY_PLANNING_ALLOWED",
    "ENTRY_PLANNING_CONDITIONAL",
    "WAIT_WITHOUT_PLAN",
    "NO_ENTRY",
    "RETURN_TO_INDIVIDUAL_ANALYSIS",
    "INSUFFICIENT_EVIDENCE",
]
Action = Literal[
    "ENTER_NOW_CONDITIONALLY",
    "WAIT_FOR_PULLBACK",
    "WAIT_FOR_BREAKOUT_CONFIRMATION",
    "WAIT_FOR_EVENT",
    "WAIT_WITHOUT_ACTIVE_PLAN",
    "NO_ENTRY",
    "RETURN_TO_ANALYSIS",
]
Route = Literal[
    "CURRENT_PRICE_ROUTE", "PULLBACK_ROUTE", "BREAKOUT_ROUTE", "POST_EVENT_ROUTE", "NO_ROUTE"
]
EventDominance = Literal["LOW", "MANAGEABLE", "DOMINANT", "BINARY", "UNKNOWN"]
PersistenceState = Literal[
    "not_generated",
    "generated_not_persisted",
    "persisted_pending_verification",
    "integrity_verified",
    "failed_terminal",
    "expired",
    "superseded",
    "session_local",
]


@dataclass(frozen=True)
class PriceZone:
    internal_id: str
    label: str
    low: float
    high: float
    currency: Literal["USD"] = "USD"
    adjusted: bool = True
    zone_type: str = "support_reference"

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
    changed_evidence: tuple[str, ...]
    plan_impact: str
    revision_timestamp: str
    previous_hash: str
    new_hash: str


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
    waiting_use: list[str]
    rationale: str
    adjustment_factors: list[str]
    unit: Literal["target_position_percent"] = "target_position_percent"


@dataclass
class Decision:
    current_action: Action
    routes: list[Route]
    route_priority: list[Route]
    allocation: Allocation
    avoided_risk: str
    confidence: Literal["high", "medium", "low"]
    primary_reason: str
    primary_short_term_risk: str
    missed_opportunity_risk: str
    return_to_stock_analysis: bool = False


@dataclass
class EntryState:
    schema_version: str
    ticker: str
    mode: Literal["initial", "update"] = "initial"
    usage_mode: Mode = "standalone_static"
    current_phase: int = 0
    initial_complete: bool = False
    terminal: bool = False
    terminal_reason: dict[str, Any] | None = None
    zones_locked: bool = False
    zones_locked_at_phase: int | None = None
    price_zones: dict[str, PriceZone] = field(default_factory=dict)
    zone_revisions: list[ZoneRevision] = field(default_factory=list)
    independent_entry_gate: EntryGate | None = None
    independent_gate_hash: str | None = None
    reconciliation_disclosed: bool = False
    event_dominance: EventDominance | None = None
    decision: Decision | None = None
    plan_expiry: str | None = None
    next_review: str | None = None
    persistence_state: PersistenceState = "session_local"

    def freeze_entry_gate(self, gate: EntryGate, evidence: list[str]) -> None:
        if self.mode != "initial" or self.current_phase != 2 or self.independent_entry_gate:
            raise ValueError("独立entry gateはInitial Phase 2で一度だけ固定できます")
        self.independent_entry_gate = gate
        raw = json.dumps({"gate": gate, "evidence": evidence}, sort_keys=True).encode()
        self.independent_gate_hash = sha256(raw).hexdigest()

    def disclose_reconciliation(self) -> None:
        if self.current_phase < 3 or not self.independent_entry_gate:
            raise ValueError("上流照合はPhase 2 entry gate固定後だけ開示できます")
        self.reconciliation_disclosed = True

    def early_stop(
        self,
        gate: EntryGate,
        *,
        reason: str,
        missing_evidence: list[str],
        required_next_action: str,
        reactivation_condition: str,
        monitoring_condition: str,
    ) -> None:
        if gate not in {
            "NO_ENTRY",
            "RETURN_TO_INDIVIDUAL_ANALYSIS",
            "INSUFFICIENT_EVIDENCE",
            "WAIT_WITHOUT_PLAN",
        }:
            raise ValueError("early stopにはterminal entry gateが必要です")
        self.terminal = True
        self.independent_entry_gate = self.independent_entry_gate or gate
        self.terminal_reason = {
            "terminal_state": gate,
            "reason": reason,
            "missing_evidence": missing_evidence,
            "required_next_action": required_next_action,
            "reactivation_condition": reactivation_condition,
            "monitoring_condition": monitoring_condition,
        }
        self.persistence_state = (
            "failed_terminal" if self.usage_mode != "standalone_static" else "session_local"
        )

    def lock_zones(self, zones: list[PriceZone]) -> None:
        if self.mode != "initial" or self.current_phase != 7 or self.zones_locked:
            raise ValueError("主要価格帯はInitial Phase 7で一度だけ固定できます")
        if not zones or len({z.internal_id for z in zones}) != len(zones):
            raise ValueError("一意なIDを持つ価格帯が少なくとも一つ必要です")
        ordered = sorted(zones, key=lambda z: z.low)
        if any(a.high >= b.low for a, b in zip(ordered, ordered[1:])):
            raise ValueError("価格帯は重複できません")
        if any(not z.adjusted or z.currency != "USD" for z in zones):
            raise ValueError("価格帯はUSDかつcorporate-action調整済みでなければなりません")
        self.price_zones = {z.internal_id: z for z in zones}
        self.zones_locked = True
        self.zones_locked_at_phase = 7

    def revise_zone(
        self,
        zone_id: str,
        replacement: PriceZone,
        reason: str,
        impact: str,
        changed_evidence: list[str] | None = None,
        timestamp: str | None = None,
    ) -> None:
        if not self.zones_locked or self.current_phase < 7 or zone_id not in self.price_zones:
            raise ValueError("Phase 7以降の固定済み価格帯だけを変更できます")
        if replacement.internal_id != zone_id:
            raise ValueError("価格帯変更で内部IDを変更できません")
        if not reason.strip() or not impact.strip() or not changed_evidence:
            raise ValueError("価格帯変更には理由、変更証拠、影響が必要です")
        old = self.price_zones[zone_id]

        def digest(zone: PriceZone) -> str:
            return sha256(json.dumps(zone.__dict__, sort_keys=True).encode()).hexdigest()

        self.zone_revisions.append(
            ZoneRevision(
                self.current_phase,
                old,
                replacement,
                reason.strip(),
                tuple(changed_evidence),
                impact.strip(),
                timestamp or datetime.now(timezone.utc).isoformat(),
                digest(old),
                digest(replacement),
            )
        )
        self.price_zones[zone_id] = replacement
