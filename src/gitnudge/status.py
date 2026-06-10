"""Nudge decision logic (pure). No I/O, no subprocess."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .gitio import DiffStats

DEFAULT_LINE_THRESHOLD = 50
FILE_THRESHOLD = 5


@dataclass(frozen=True)
class StatusReport:
    should_nudge: bool
    files_touched: int
    insertions: int
    deletions: int
    seconds_since_last: int | None


def evaluate(
    stats: DiffStats,
    last_ts: int | None,
    threshold: int = DEFAULT_LINE_THRESHOLD,
    now: float | None = None,
) -> StatusReport:
    files_touched = stats.files_changed + stats.untracked
    lines_changed = stats.insertions + stats.deletions
    should_nudge = lines_changed >= threshold or files_touched >= FILE_THRESHOLD

    seconds_since_last: int | None = None
    if last_ts is not None:
        seconds_since_last = int((now if now is not None else time.time()) - last_ts)

    return StatusReport(
        should_nudge=should_nudge,
        files_touched=files_touched,
        insertions=stats.insertions,
        deletions=stats.deletions,
        seconds_since_last=seconds_since_last,
    )
