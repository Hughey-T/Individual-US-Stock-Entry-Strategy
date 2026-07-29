"""Conversation state machine enforcing exactly one analysis unit per response."""

from __future__ import annotations

from dataclasses import dataclass

from .models import EntryState

INITIAL_PHASES = tuple(range(1, 9))
UPDATE_PHASES = (1, 2)

PHASE_SECTIONS: dict[tuple[str, int], tuple[str, ...]] = {
    ("initial", 1): ("起動条件", "暫定前提", "データ品質", "基準スナップショット"),
    ("initial", 2): ("市場環境", "セクター", "テーマ"),
    ("initial", 3): ("相対強度", "比較対象", "比較限界"),
    ("initial", 4): ("価格構造", "出来高", "ボラティリティ", "主要価格帯"),
    ("initial", 5): ("イベント", "需給", "希薄化", "データ鮮度"),
    ("initial", 6): ("シナリオ", "シナリオ遷移", "価格非対称性"),
    ("initial", 7): ("最終判断", "購入比率", "リスク判断"),
    ("initial", 8): ("条件付き購入計画", "無効化", "カバレッジ表", "最終実行カード"),
    ("update", 1): ("現在計画の更新", "更新後の実行カード"),
    ("update", 2): ("前回計画の事後検証",),
}


@dataclass(frozen=True)
class PhaseResult:
    mode: str
    phase: int
    required_sections: tuple[str, ...]
    prompt_next: bool
    footer: str | None


class ConversationEngine:
    def start(self, ticker: str) -> tuple[EntryState, PhaseResult]:
        normalized = ticker.strip().upper()
        if not normalized:
            raise ValueError("ティッカーが必要です")
        state = EntryState(schema_version="2.0.0", ticker=normalized, current_phase=1)
        return state, self._result(state)

    def handle(self, state: EntryState, message: str) -> PhaseResult:
        command = message.strip()
        if command == "更新":
            if not state.initial_complete:
                raise ValueError("更新は初回Phase 8の完了後に開始できます")
            state.mode = "update"
            state.current_phase = 1
            return self._result(state)
        if command != "次":
            raise ValueError("有効な進行入力は「次」または「更新」です")
        maximum = 8 if state.mode == "initial" else 2
        if state.current_phase >= maximum:
            raise ValueError("最終Phase終了後に進行できません")
        state.current_phase += 1
        if state.mode == "initial" and state.current_phase == 8:
            state.initial_complete = True
        return self._result(state)

    @staticmethod
    def _result(state: EntryState) -> PhaseResult:
        maximum = 8 if state.mode == "initial" else 2
        prompt = state.current_phase < maximum
        return PhaseResult(
            state.mode,
            state.current_phase,
            PHASE_SECTIONS[(state.mode, state.current_phase)],
            prompt,
            "「次」と送信してください。" if prompt else None,
        )
