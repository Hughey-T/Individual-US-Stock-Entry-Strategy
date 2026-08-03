"""Stateful runtime orchestration without analytical decision generation."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from .engine import ConversationEngine, PHASE_SECTIONS
from .models import EntryState, EntryGate, Mode
from .storage import Store
from .validation import ValidationError, strict_json_loads


class Runtime:
    """Validate phase ordering and persist immutable caller-generated records."""

    def __init__(self, root: Path):
        self.store = Store(root)

    def _state_path(self, session_id: str) -> Path:
        return self.store._session(session_id) / "state.json"  # noqa: SLF001

    def _write_state(self, session_id: str, state: EntryState) -> None:
        path = self._state_path(session_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(state), sort_keys=True, ensure_ascii=False))
        os.replace(temporary, path)

    def _read_state_unlocked(self, session_id: str) -> EntryState:
        path = self._state_path(session_id)
        if not path.is_file() or path.is_symlink():
            raise ValidationError("unknown session")
        data = json.loads(path.read_text())
        # Runtime orchestration state deliberately excludes analytical zone/decision hydration.
        return EntryState(
            schema_version=data["schema_version"],
            ticker=data["ticker"],
            mode=data["mode"],
            usage_mode=data["usage_mode"],
            current_phase=data["current_phase"],
            initial_complete=data["initial_complete"],
            terminal=data["terminal"],
            terminal_reason=data["terminal_reason"],
            independent_entry_gate=data["independent_entry_gate"],
            independent_gate_hash=data["independent_gate_hash"],
            reconciliation_disclosed=data["reconciliation_disclosed"],
            persistence_state=data["persistence_state"],
        )

    def create_session(self, ticker: str, mode: Mode) -> dict[str, Any]:
        if mode == "standalone_static":
            raise ValidationError(
                "static sessions are conversation-local and not runtime-persisted"
            )
        session_id = str(uuid4())
        state, result = ConversationEngine().start(ticker, mode)
        with self.store.session_lock(session_id):
            self._write_state(session_id, state)
        return {"session_id": session_id, "state": asdict(state), "next_contract": asdict(result)}

    def resume(self, session_id: str) -> dict[str, Any]:
        with self.store.session_lock(session_id):
            state = self._read_state_unlocked(session_id)
            return {"state": asdict(state), "next_contract": self._contract(state)}

    @staticmethod
    def _contract(state: EntryState) -> dict[str, Any]:
        return {
            "mode": state.mode,
            "phase": state.current_phase,
            "required_sections": PHASE_SECTIONS[(state.mode, state.current_phase)],
            "terminal": state.terminal,
        }

    def next_contract(self, session_id: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.resume(session_id)["next_contract"])

    def submit_phase(
        self, session_id: str, raw: bytes, expected_phase: str | None = None
    ) -> dict[str, Any]:
        payload = strict_json_loads(raw)
        if not isinstance(payload, dict):
            raise ValidationError("artifact must be an object")
        # One session lock spans validation, publication, and state advancement.
        # Store.publish re-enters the same process RLock and filesystem flock.
        with self.store.session_lock(session_id):
            state = self._read_state_unlocked(session_id)
            phase_identity = f"{state.mode}-{state.current_phase}"
            supplied_phase = expected_phase or payload.get("phase_identity")
            if supplied_phase != phase_identity:
                raise ValidationError("phase artifact does not match current contract")
            if phase_identity == "initial-2" and not state.independent_entry_gate:
                raise ValidationError("Phase 2 requires a frozen independent entry gate")
            if (
                phase_identity == "initial-3"
                and state.usage_mode == "pipeline"
                and not state.reconciliation_disclosed
            ):
                raise ValidationError("pipeline Phase 3 requires reconciliation disclosure")
            maximum = 12 if state.mode == "initial" else 5
            active_info = (
                self.store._verify_unlocked(session_id)
                if (self.store._session(session_id) / "active").exists()  # noqa: SLF001
                else None
            )
            completed = (
                state.current_phase == maximum
                and state.persistence_state == "integrity_verified"
                and active_info is not None
                and active_info["manifest"]["phase_identity"] == phase_identity
            )
            if completed:
                assert active_info is not None
                active = active_info["active"]
                active_path = (
                    self.store._session(session_id) / "generations" / active / "artifact.json"
                )  # noqa: SLF001
                if payload != strict_json_loads(active_path.read_bytes()):
                    raise ValidationError("final Phase is immutable and complete")
            receipt = self.store.publish(session_id, phase_identity, raw, _already_locked=True)
            state.persistence_state = "integrity_verified"
            if state.current_phase == maximum:
                if state.mode == "initial":
                    state.initial_complete = True
            else:
                state.current_phase += 1
            self._write_state(session_id, state)
            return {**receipt, "next_contract": self._contract(state)}

    def freeze_entry_gate(
        self, session_id: str, gate: EntryGate, evidence: list[str]
    ) -> dict[str, Any]:
        with self.store.session_lock(session_id):
            state = self._read_state_unlocked(session_id)
            state.freeze_entry_gate(gate, evidence)
            self._write_state(session_id, state)
            return {"frozen": True, "gate": gate, "gate_hash": state.independent_gate_hash}

    def disclose_reconciliation(self, session_id: str) -> dict[str, bool]:
        with self.store.session_lock(session_id):
            state = self._read_state_unlocked(session_id)
            state.disclose_reconciliation()
            self._write_state(session_id, state)
            return {"disclosed": True}

    def terminal_stop(
        self,
        session_id: str,
        gate: EntryGate,
        *,
        reason: str,
        missing_evidence: list[str],
        required_next_action: str,
        reactivation_condition: str,
        monitoring_condition: str,
    ) -> dict[str, Any]:
        with self.store.session_lock(session_id):
            state = self._read_state_unlocked(session_id)
            state.early_stop(
                gate,
                reason=reason,
                missing_evidence=missing_evidence,
                required_next_action=required_next_action,
                reactivation_condition=reactivation_condition,
                monitoring_condition=monitoring_condition,
            )
            self._write_state(session_id, state)
            return {"terminal": True, **(state.terminal_reason or {})}

    def start_update(self, session_id: str) -> dict[str, Any]:
        with self.store.session_lock(session_id):
            state = self._read_state_unlocked(session_id)
            if not state.initial_complete or state.mode == "update":
                raise ValidationError("update requires a completed initial strategy")
            state.mode = "update"
            state.current_phase = 1
            self._write_state(session_id, state)
            return self._contract(state)

    def active_plan(self, session_id: str) -> Any:
        return self.store.read_active(session_id)

    def superseded(self, session_id: str) -> list[str]:
        generations = self.store.history(session_id)
        active = self.store.verify(session_id)["active"]
        return [generation for generation in generations if generation != active]

    def ledger(self, session_id: str) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "active": self.store.verify(session_id)["active"],
            "generations": self.store.history(session_id),
        }

    def integrity(self, session_id: str) -> dict[str, Any]:
        return self.store.verify(session_id)

    def backup(self, destination: Path) -> dict[str, Any]:
        return self.store.backup(destination)

    def restore(self, archive: Path, destination: Path) -> Runtime:
        return Runtime(Store.restore(archive, destination).root)

    @staticmethod
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "analysis_generated": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
