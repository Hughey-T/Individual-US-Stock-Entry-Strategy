"""Lightweight Markdown-link and forbidden-production-wording audit."""

from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
for markdown in ROOT.glob("**/*.md"):
    if any(part.startswith(".") for part in markdown.relative_to(ROOT).parts):
        continue
    text = markdown.read_text()
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" not in target and not target.startswith("#"):
            path = (markdown.parent / target.split("#", 1)[0]).resolve()
            if not path.exists():
                raise SystemExit(f"broken Markdown link: {markdown}: {target}")
production = "\n".join(
    path.read_text(errors="ignore") for path in (ROOT / "src" / "entry_strategy").glob("*.py")
)
for forbidden in ("broker_api", "market_order", "portfolio_optimizer"):
    if forbidden in production:
        raise SystemExit(f"forbidden production wording: {forbidden}")
print("repository audit passed: Markdown links and forbidden production wording")
