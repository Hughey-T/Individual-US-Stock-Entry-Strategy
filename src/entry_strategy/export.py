"""Custom GPT export functions."""

from pathlib import Path


def canonical_instructions() -> str:
    path = Path(__file__).resolve().parents[2] / "instructions" / "custom-gpt-entry-strategy.md"
    return path.read_text(encoding="utf-8")
