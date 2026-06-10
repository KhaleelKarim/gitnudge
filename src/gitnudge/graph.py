"""Heatmap rendering logic (pure). No I/O, no subprocess."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta

from rich.text import Text

GLYPHS = ("·", "░", "▓", "█")
DEFAULT_WEEKS = 12

# Rich styles paired with GLYPHS: dim for zero, increasing green intensity.
_STYLES = ("dim", "green", "green3", "bright_green")


def bucket_by_day(timestamps: list[int]) -> dict[date, int]:
    counter: Counter[date] = Counter()
    for ts in timestamps:
        counter[datetime.fromtimestamp(ts).date()] += 1
    return dict(counter)


def _glyph_for(count: int, q1: int, q2: int, q3: int) -> str:
    if count <= 0:
        return GLYPHS[0]
    if count < q1:
        return GLYPHS[1]
    if count < q3:
        return GLYPHS[2]
    return GLYPHS[3]


def _quartiles(counts: list[int]) -> tuple[int, int, int]:
    nonzero = sorted(c for c in counts if c > 0)
    if not nonzero:
        return (1, 2, 3)  # placeholder; no nonzero data to map
    n = len(nonzero)
    q1 = nonzero[n // 4]
    q2 = nonzero[n // 2]
    q3 = nonzero[(3 * n) // 4]
    # Force strictly increasing bands so the glyph mapping has 4 distinct
    # bins even when all counts are similar.
    q2 = max(q2, q1 + 1)
    q3 = max(q3, q2 + 1)
    return (q1, q2, q3)


def render(buckets: dict[date, int], weeks: int = DEFAULT_WEEKS) -> Text:
    today = date.today()
    # Anchor rightmost column on the current week (Sunday-start).
    # Grid: rows 0..6 are Sun..Sat; column 0 is the oldest week.
    end_of_grid = today - timedelta(days=(today.weekday() + 1) % 7) + timedelta(days=6)
    start = end_of_grid - timedelta(weeks=weeks) + timedelta(days=1)

    counts: list[int] = []
    days: list[date] = []
    cursor = start
    while cursor <= end_of_grid:
        days.append(cursor)
        counts.append(buckets.get(cursor, 0))
        cursor += timedelta(days=1)

    q1, q2, q3 = _quartiles(counts)

    text = Text()
    for row in range(7):
        for col in range(weeks):
            idx = col * 7 + row
            if idx >= len(counts) or days[idx] > today:
                text.append("  ")
                continue
            count = counts[idx]
            glyph = _glyph_for(count, q1, q2, q3)
            style = _STYLES[GLYPHS.index(glyph)]
            text.append(glyph + " ", style=style)
        text.append("\n")
    return text
