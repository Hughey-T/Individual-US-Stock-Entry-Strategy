"""Strict one-command/one-phase state machine for contract 3.0."""

from __future__ import annotations
from dataclasses import dataclass
from .models import CONTRACT_VERSION, EntryState, Mode

INITIAL_PHASES = tuple(range(1, 13))
UPDATE_PHASES = tuple(range(1, 6))
PHASE_SECTIONS = {
    ("initial", 1): ("記録固定", "データ品質", "Blind intake"),
    ("initial", 2): ("独立Entry gate", "仮説", "価値"),
    ("initial", 3): ("上流分析との照合",),
    ("initial", 4): ("市場環境", "金利", "セクター", "テーマ"),
    ("initial", 5): ("相対強度", "競合", "値動きの質"),
    ("initial", 6): ("イベント", "需給", "希薄化", "ギャップリスク"),
    ("initial", 7): ("価格構造", "ボラティリティ", "固定参照帯"),
    ("initial", 8): ("候補経路", "条件設計"),
    ("initial", 9): ("反対仮説", "NO_ENTRY", "追いかけ買い検査"),
    ("initial", 10): ("行動", "経路優先順位", "参考比率"),
    ("initial", 11): ("無効化", "有効期限", "仮想経路テスト"),
    ("initial", 12): ("最終条件付き計画", "実行カード", "ledger"),
    ("update", 1): ("新スナップショット", "差分", "状態固定"),
    ("update", 2): ("旧計画の事後検証",),
    ("update", 3): ("Blind現在状態再評価",),
    ("update", 4): ("旧計画との照合", "帯変更", "反証"),
    ("update", 5): ("更新後計画", "supersession", "ledger"),
}


@dataclass(frozen=True)
class PhaseResult:
    mode: str
    phase: int
    required_sections: tuple[str, ...]
    prompt_next: bool
    footer: str | None


class ConversationEngine:
    def start(
        self, ticker: str, usage_mode: Mode = "standalone_static"
    ) -> tuple[EntryState, PhaseResult]:
        normalized = ticker.strip().upper()
        if not normalized:
            raise ValueError("ティッカーが必要です")
        state = EntryState(
            CONTRACT_VERSION,
            normalized,
            current_phase=1,
            usage_mode=usage_mode,
            persistence_state="session_local"
            if usage_mode == "standalone_static"
            else "not_generated",
        )
        return state, self._result(state)

    def handle(self, state: EntryState, message: str) -> PhaseResult:
        if message not in {"次", "更新"}:
            raise ValueError("有効な進行入力は正確な「次」または「更新」です")
        if state.terminal:
            raise ValueError(
                "terminal early stop後に進行できません。再開条件成立後に新規分析してください"
            )
        if message == "更新":
            if not state.initial_complete:
                raise ValueError("更新はInitial Phase 12完了後に開始できます")
            if state.mode == "update":
                raise ValueError("更新中に新しい更新を開始できません")
            state.mode = "update"
            state.current_phase = 1
            return self._result(state)
        maximum = 12 if state.mode == "initial" else 5
        if state.current_phase >= maximum:
            raise ValueError("最終Phase終了後に進行できません")
        state.current_phase += 1
        if state.mode == "initial" and state.current_phase == 12:
            state.initial_complete = True
        return self._result(state)

    @staticmethod
    def _result(state: EntryState) -> PhaseResult:
        maximum = 12 if state.mode == "initial" else 5
        prompt = state.current_phase < maximum and not state.terminal
        return PhaseResult(
            state.mode,
            state.current_phase,
            PHASE_SECTIONS[(state.mode, state.current_phase)],
            prompt,
            "「次」と送信してください。" if prompt else None,
        )
