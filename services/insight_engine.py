"""Local, explainable wellness insight engine (no database, no external AI service).

All analysis runs on the user's own mood entries inside the application server.
Every insight carries the evidence it was derived from, so the user can see
"why am I seeing this?". Wording is supportive and non-clinical: these are
patterns in self-reported data, not diagnoses.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

# An entry is a dict: {"date": date, "score": 1..5, "stress": 1..10, "energy": 1..10}
Entry = Dict

SLOPE_THRESHOLD = 0.08   # mood-score change per day that counts as a trend


def linear_slope(values: List[float]) -> Optional[float]:
    """Least-squares slope of values against 0..n-1. None if fewer than 2 values."""
    n = len(values)
    if n < 2:
        return None
    mx = (n - 1) / 2
    my = sum(values) / n
    den = sum((i - mx) ** 2 for i in range(n))
    if den == 0:
        return None
    return sum((i - mx) * (v - my) for i, v in enumerate(values)) / den


def trend_direction(scores: List[float]) -> Tuple[str, Optional[float]]:
    """Return ('improving'|'declining'|'steady'|'insufficient', slope)."""
    if len(scores) < 4:
        return "insufficient", None
    slope = linear_slope(scores)
    if slope is None:
        return "insufficient", None
    if slope >= SLOPE_THRESHOLD:
        return "improving", round(slope, 2)
    if slope <= -SLOPE_THRESHOLD:
        return "declining", round(slope, 2)
    return "steady", round(slope, 2)


def trailing_run(values: List[float], predicate) -> int:
    """How many of the most recent values in a row satisfy the predicate."""
    run = 0
    for v in reversed(values):
        if predicate(v):
            run += 1
        else:
            break
    return run


def trailing_rising_steps(values: List[float]) -> int:
    """Number of consecutive strictly-increasing steps at the end of the series."""
    steps = 0
    for i in range(len(values) - 1, 0, -1):
        if values[i] > values[i - 1]:
            steps += 1
        else:
            break
    return steps


def _avg(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 1) if values else None


def weekly_comparison(entries: List[Entry], today: date) -> Dict:
    """Compare the last 7 days with the 7 days before them."""
    this_start = today - timedelta(days=6)
    prev_start = today - timedelta(days=13)
    cur = [e for e in entries if this_start <= e["date"] <= today]
    prev = [e for e in entries if prev_start <= e["date"] < this_start]

    def block(rows):
        return {
            "count": len(rows),
            "mood": _avg([e["score"] for e in rows]),
            "stress": _avg([e["stress"] for e in rows]),
            "energy": _avg([e["energy"] for e in rows]),
        }

    return {"this_week": block(cur), "previous_week": block(prev)}


def build_insights(entries: List[Entry], today: date = None) -> List[Dict]:
    """Return a list of insight dicts: {id, title, message, tone, evidence}.

    tone is one of: 'positive', 'info', 'support'.
    """
    today = today or date.today()
    rows = sorted(entries, key=lambda e: e["date"])[-14:]
    insights: List[Dict] = []

    if len(rows) < 3:
        return [{
            "id": "need-data",
            "title": "Keep logging",
            "message": "A few more daily check-ins will unlock personalised patterns here.",
            "tone": "info",
            "evidence": [f"{len(rows)} check-in(s) in the last 14 days (3 needed)"],
        }]

    scores = [e["score"] for e in rows]
    stress = [e["stress"] for e in rows]
    energy = [e["energy"] for e in rows]

    # 1. Mood trend
    direction, slope = trend_direction(scores)
    if direction == "improving":
        insights.append({
            "id": "mood-improving", "title": "Your mood is trending upward", "tone": "positive",
            "message": "Your recent check-ins show a gentle upward trend. Notice what has been helping and keep it going.",
            "evidence": [f"{len(rows)} check-ins analysed", f"Mood slope about +{slope} points per day"],
        })
    elif direction == "declining":
        insights.append({
            "id": "mood-declining", "title": "Your mood has dipped recently", "tone": "support",
            "message": "Your recent check-ins trend lower. Small restful activities or talking with someone you trust can help.",
            "evidence": [f"{len(rows)} check-ins analysed", f"Mood slope about {slope} points per day"],
        })

    # 2. Consecutive low-mood days
    low_run = trailing_run(scores, lambda v: v <= 2)
    if low_run >= 3:
        insights.append({
            "id": "low-mood-run", "title": f"{low_run} low-mood days in a row", "tone": "support",
            "message": "You have recorded low moods for several days. You do not have to handle this alone. "
                       "Consider reaching out to a friend, family member, or a professional if it continues.",
            "evidence": [f"Last {low_run} entries were Sad or Very Low"],
        })

    # 3. Rising stress
    rising = trailing_rising_steps(stress)
    recent_stress = _avg(stress[-3:])
    if rising >= 3:
        insights.append({
            "id": "stress-rising", "title": "Stress has been building", "tone": "support",
            "message": "Your stress rating rose several days in a row. A short breathing or relaxation break may help.",
            "evidence": [f"Stress rose on {rising} consecutive check-ins", f"Latest value {stress[-1]}/10"],
        })
    elif recent_stress is not None and recent_stress >= 7:
        insights.append({
            "id": "stress-high", "title": "Stress is running high", "tone": "support",
            "message": "Your last few stress ratings were high. Consider a short break or a calming activity today.",
            "evidence": [f"Average of last 3 stress ratings: {recent_stress}/10"],
        })

    # 4. Low energy
    recent_energy = _avg(energy[-5:])
    if recent_energy is not None and recent_energy <= 3:
        insights.append({
            "id": "energy-low", "title": "Energy has been low", "tone": "info",
            "message": "Your energy ratings are low lately. Rest, hydration, light movement and regular sleep can help.",
            "evidence": [f"Average of last {min(5, len(energy))} energy ratings: {recent_energy}/10"],
        })

    # 5. Sustained good mood
    week_avg = _avg(scores[-7:])
    if week_avg is not None and week_avg >= 4 and not any(i["id"] == "mood-improving" for i in insights):
        insights.append({
            "id": "mood-good", "title": "A good stretch", "tone": "positive",
            "message": "Your mood has been consistently positive this past week. Worth noting what is working for you.",
            "evidence": [f"Average mood score {week_avg}/5 over the last {min(7, len(scores))} check-ins"],
        })

    # 6. Week-on-week stress change
    cmp_ = weekly_comparison(rows, today)
    t, p = cmp_["this_week"], cmp_["previous_week"]
    if t["stress"] is not None and p["stress"] is not None and t["count"] >= 3 and p["count"] >= 3:
        delta = round(t["stress"] - p["stress"], 1)
        if delta <= -1:
            insights.append({
                "id": "stress-down", "title": "Stress is lower than last week", "tone": "positive",
                "message": "Your average stress rating dropped compared with the previous week.",
                "evidence": [f"This week {t['stress']}/10 vs last week {p['stress']}/10"],
            })

    if not insights:
        insights.append({
            "id": "steady", "title": "Things look steady", "tone": "info",
            "message": "No strong pattern stands out in your recent entries. Consistent check-ins keep this picture accurate.",
            "evidence": [f"{len(rows)} check-ins analysed"],
        })

    order = {"support": 0, "positive": 1, "info": 2}
    # Most important first: supportive notes, with a sustained low-mood run on top
    insights.sort(key=lambda i: (order[i["tone"]], i["id"] != "low-mood-run"))
    return insights


def weekly_report_text(entries: List[Entry], today: date = None) -> str:
    """Plain-language weekly summary. Contains only aggregate numbers."""
    today = today or date.today()
    cmp_ = weekly_comparison(entries, today)
    t, p = cmp_["this_week"], cmp_["previous_week"]
    if t["count"] == 0:
        return "No check-ins were recorded in the last 7 days."

    parts = [f"You logged {t['count']} check-in{'s' if t['count'] != 1 else ''} in the last 7 days. "
             f"Average mood {t['mood']}/5, stress {t['stress']}/10, energy {t['energy']}/10."]

    if p["count"] > 0:
        def change(label, cur, prev, unit, higher_is_better):
            d = round(cur - prev, 1)
            if abs(d) < 0.3:
                return f"{label} was about the same as the week before."
            word = "higher" if d > 0 else "lower"
            return f"{label} was {abs(d)} {unit} {word} than the week before."
        parts.append(change("Mood", t["mood"], p["mood"], "points", True))
        parts.append(change("Stress", t["stress"], p["stress"], "points", False))
        parts.append(change("Energy", t["energy"], p["energy"], "points", True))
    else:
        parts.append("There is no earlier week to compare with yet.")
    return " ".join(parts)
