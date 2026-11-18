"""Pure analytics helpers (no database access), easy to unit test."""
from datetime import date
from typing import List
from timeutil import local_today


WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def calculate_streaks(dates: List[date], today: date = None):
    """
    Return (current_streak, best_streak) for a list of check-in dates.
    A streak is a run of consecutive calendar days. The current streak is
    still alive if the latest check-in was today or yesterday.
    """
    today = today or local_today()
    unique = sorted(set(dates))
    if not unique:
        return 0, 0

    best = run = 1
    for prev, cur in zip(unique, unique[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        best = max(best, run)

    current = 0
    if (today - unique[-1]).days <= 1:
        current = 1
        for i in range(len(unique) - 1, 0, -1):
            if (unique[i] - unique[i - 1]).days == 1:
                current += 1
            else:
                break
    return current, best


def weekday_averages(pairs):
    """
    pairs: iterable of (date, mood_score). Returns a list of 7 values
    (Mon..Sun): the average mood score for that weekday, or None if the
    weekday has no entries.
    """
    sums = [0.0] * 7
    counts = [0] * 7
    for d, score in pairs:
        sums[d.weekday()] += score
        counts[d.weekday()] += 1
    return [round(sums[i] / counts[i], 1) if counts[i] else None for i in range(7)]


def pearson(xs, ys):
    """Pearson correlation coefficient, or None when it cannot be computed."""
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs)
    sy = sum((y - my) ** 2 for y in ys)
    if sx == 0 or sy == 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return round(cov / (sx ** 0.5 * sy ** 0.5), 2)
