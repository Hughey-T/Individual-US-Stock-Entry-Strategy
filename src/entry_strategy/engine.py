"""Conversation state machine enforcing one response per Phase."""

from __future__ import annotations

from dataclasses import dataclass

from .models import EntryState

INITIAL_PHASES = tuple(range(1, 9))
UPDATE_PHASES = (1, 2)


@dataclass(frozen=True)
class PhaseResult:
    mode: str
    phase: int
    prompt_next: bool
    footer: str | None


class ConversationEngine:
    def start(self, ticker: str) -> tuple[EntryState, PhaseResult]:
        state = EntryState(schema_version="1.0.0", ticker=ticker.upper(), current_phase=1)
        return state, self._result(state)

    def handle(self, state: EntryState, message: str) -> PhaseResult:
        command = message.strip()
        if command == "更新":
            state.mode = "update"
            state.current_phase = 1
            return self._result(state)
        if command != "次":
            raise ValueError("有効な進行入力は「次」または「更新」です")
        maximum = 8 if state.mode == "initial" else 2
        if state.current_phase >= maximum:
            raise ValueError("最終Phase終了後に進行できません")
        state.current_phase += 1
        return self._result(state)

    @staticmethod
    def _result(state: EntryState) -> PhaseResult:
        maximum = 8 if state.mode == "initial" else 2
        prompt = state.current_phase < maximum
        return PhaseResult(
            state.mode,
            state.current_phase,
            prompt,
            "「次」と送信してください。" if prompt else None,
        )
