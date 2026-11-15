"""Pure helpers for the admin dashboard (no database access)."""
import csv
import io
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple


def fill_daily_series(counts: Dict[date, int], days: int, today: date) -> Tuple[List[str], List[int]]:
    """Zero-fill a {date: count} mapping into `days` consecutive days ending today."""
    labels, values = [], []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        labels.append(d.strftime("%b %d"))
        values.append(int(counts.get(d, 0)))
    return labels, values


def parse_date_param(value: str) -> Optional[date]:
    """Parse YYYY-MM-DD from a query string; None if blank or invalid."""
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def clamp_page(page, total_items: int, per_page: int) -> Tuple[int, int]:
    """Return (page, total_pages) with the page forced into a valid range."""
    total_pages = max(1, -(-total_items // per_page))
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    return min(max(page, 1), total_pages), total_pages


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection in exported text cells."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def audit_rows_to_csv(rows) -> str:
    """rows: iterable of objects with log_id, action, event_status, user_id, ip_address, timestamp."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["log_id", "timestamp_utc", "action", "status", "user_id", "ip_address"])
    for r in rows:
        w.writerow([
            r.log_id, r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), _csv_safe(r.action),
            _csv_safe(r.event_status), r.user_id if r.user_id is not None else "",
            _csv_safe(r.ip_address),
        ])
    return buf.getvalue()
