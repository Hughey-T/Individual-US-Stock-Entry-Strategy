"""Explicit, conservative detection of the legacy five-Phase/A–F format."""

from __future__ import annotations

from typing import Any


class LegacyFormatError(ValueError):
    """Raised when legacy input cannot be identified without guessing."""


LEGACY_LABELS = {
    "A": "即時",
    "B": "一部",
    "C": "押し目待ち",
    "D": "上抜け確認待ち",
    "E": "イベント通過待ち",
    "F": "中止",
}


def _legacy_label(data: dict[str, Any]) -> str | None:
    values = [data[key] for key in ("legacy_decision", "decision_label") if key in data]
    if len(values) > 1 and len(set(map(str, values))) != 1:
        raise LegacyFormatError("旧判定フィールド同士が矛盾しています")
    if not values:
        return None
    raw = str(values[0]).strip()
    if raw in LEGACY_LABELS:
        return raw
    for label, description in LEGACY_LABELS.items():
        if raw in {f"{label}:{description}", f"{label}：{description}"}:
            return label
    raise LegacyFormatError("認識できない旧判定です。手動確認してください")


def is_legacy(data: dict[str, Any]) -> bool:
    markers = "legacy_decision" in data or "decision_label" in data or "phase_count" in data
    if not markers:
        return False
    if "phase_count" in data and data["phase_count"] != 5:
        raise LegacyFormatError("旧形式マーカーがありますがPhase数が5ではありません")
    _legacy_label(data)
    return True


def migrate_legacy(data: dict[str, Any]) -> dict[str, Any]:
    if not is_legacy(data):
        raise LegacyFormatError("旧形式ではありません")
    label = _legacy_label(data)
    if label is None:
        raise LegacyFormatError("旧5 Phase形式に判定ラベルがありません")
    ticker = str(data.get("ticker", "UNKNOWN")).strip().upper() or "UNKNOWN"
    return {
        "schema_version": "2.0.0",
        "ticker": ticker,
        "current_action": "個別銘柄分析へ差し戻し",
        "routes": [],
        "legacy": {
            "legacy_decision": label,
            "legacy_description": LEGACY_LABELS[label],
            "migration_warning": "旧判定は行動・経路・比率・イベントを混在させるため自動対応付けしません",
            "manual_review_required": True,
        },
    }
