"""Export the sole canonical Custom GPT instruction contract."""

from pathlib import Path
import sys


def canonical_instructions() -> str:
    candidates = (
        Path(__file__).resolve().parents[2] / "instructions/custom-gpt-entry-strategy.md",
        Path(sys.prefix) / "share/entry-strategy/custom-gpt-entry-strategy.md",
    )
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError("canonical Custom GPT instructions are not installed")
