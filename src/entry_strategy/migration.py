"""Explicit, conservative legacy detection and migration."""

from __future__ import annotations

from typing import Any


class LegacyFormatError(ValueError):
    pass


def is_legacy(data: dict[str, Any]) -> bool:
    return "legacy_decision" in data or "decision_label" in data or data.get("phase_count") == 5


def migrate_legacy(data: dict[str, Any]) -> dict[str, Any]:
    if not is_legacy(data):
        raise LegacyFormatError("旧形式ではありません")
    label = data.get("legacy_decision", data.get("decision_label"))
    if label not in {"A", "B", "C", "D", "E", "F"}:
        raise LegacyFormatError("認識できない旧判定です。手動確認してください")
    return {
        "schema_version": "1.0.0",
        "ticker": data.get("ticker", "UNKNOWN"),
        "current_action": "個別銘柄分析へ差し戻し",
        "routes": [],
        "legacy": {
            "legacy_decision": label,
            "migration_warning": "旧判定は複数概念を混在させるため自動対応付けしていません",
            "manual_review_required": True,
        },
    }
