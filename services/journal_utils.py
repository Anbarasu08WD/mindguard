"""Pure helper functions for journal features (no database access)."""
import re
from datetime import datetime
from typing import Dict, List

WORDS_PER_MINUTE = 200


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text or ""))


def reading_minutes(words: int) -> int:
    """Estimated reading time in whole minutes (minimum 1)."""
    return max(1, round(words / WORDS_PER_MINUTE))


def sort_entries(entries: List[Dict], order: str) -> List[Dict]:
    """Sort decrypted entry dicts. Unknown orders fall back to newest first."""
    if order == "oldest":
        return sorted(entries, key=lambda e: e["created_at"])
    if order == "longest":
        return sorted(entries, key=lambda e: e["words"], reverse=True)
    return sorted(entries, key=lambda e: e["created_at"], reverse=True)


def journal_stats(entries: List[Dict]) -> Dict:
    total_words = sum(e["words"] for e in entries)
    last = max((e["created_at"] for e in entries), default=None)
    return {
        "count": len(entries),
        "total_words": total_words,
        "avg_words": round(total_words / len(entries)) if entries else 0,
        "last_written": last,
    }


def build_markdown_export(entries: List[Dict], owner_name: str) -> str:
    """Build a Markdown document of the owner's decrypted entries."""
    lines = [
        "# MindGuard journal export",
        f"Owner: {owner_name}",
        f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Entries: {len(entries)}",
        "",
    ]
    for e in sorted(entries, key=lambda x: x["created_at"]):
        lines.append(f"## {e['title']}")
        lines.append(f"*{e['created_at'].strftime('%A, %B %d, %Y %H:%M')}*")
        lines.append("")
        lines.append(e["content"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)
