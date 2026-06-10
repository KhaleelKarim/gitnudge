"""History scoring logic (pure). No I/O, no subprocess."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from .gitio import Commit

# --- tunable constants (module-level so they're easy to adjust) ---
VAGUE_MESSAGES = frozenset({
    "update", "updates", "fix", "fixes", "wip",
    "asdf", "stuff", "changes", "commit", "final", "done", "misc",
})
VAGUE_PENALTY, VAGUE_CAP = 5, 30
BURST_PENALTY, BURST_CAP = 10, 30
SHORT_SPAN_PENALTY = 20      # history shorter than this much wall time
SHORT_SPAN_SECS = 3600       # 1 hour
LOW_VOLUME_PENALTY = 15
LOW_VOLUME_MIN = 5
BURST_WINDOW_SECS = 60
BURST_MIN_COMMITS = 3
DUPLICATE_THRESHOLD = 3
GRADE_THRESHOLDS = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]


@dataclass(frozen=True)
class Finding:
    check: str
    status: Literal["pass", "warn"]
    detail: str


@dataclass(frozen=True)
class HealthReport:
    findings: list[Finding]
    score: int
    grade: str


def _vague_count(commits: list[Commit]) -> tuple[int, list[str]]:
    """Return (count, examples) of commits with vague subject messages."""
    examples: list[str] = []
    for c in commits:
        if c.message.strip().lower() in VAGUE_MESSAGES:
            examples.append(c.message)
    return len(examples), examples


def _duplicate_messages(commits: list[Commit]) -> list[tuple[str, int]]:
    """Messages used DUPLICATE_THRESHOLD+ times, with their counts."""
    counter = Counter(c.message for c in commits)
    return [(msg, n) for msg, n in counter.items() if n >= DUPLICATE_THRESHOLD]


def _find_bursts(commits: list[Commit]) -> list[list[Commit]]:
    """Walk in chronological order; collect clusters of BURST_MIN_COMMITS+
    commits within any BURST_WINDOW_SECS window. Skip past each cluster
    to avoid double-counting overlapping windows."""
    ordered = sorted(commits, key=lambda c: c.timestamp)
    bursts: list[list[Commit]] = []
    i = 0
    while i <= len(ordered) - BURST_MIN_COMMITS:
        window_end = ordered[i].timestamp + BURST_WINDOW_SECS
        j = i
        while j < len(ordered) and ordered[j].timestamp <= window_end:
            j += 1
        cluster = ordered[i:j]
        if len(cluster) >= BURST_MIN_COMMITS:
            bursts.append(cluster)
            i = j  # skip past the whole cluster
        else:
            i += 1
    return bursts


def _grade(score: int) -> str:
    for threshold, letter in GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "F"


def score(commits: list[Commit]) -> HealthReport:
    findings: list[Finding] = []
    score_val = 100

    if not commits:
        findings.append(Finding("volume", "warn", "no commits to grade"))
        return HealthReport(findings=findings, score=0, grade="F")

    # 1. Message quality — vague + duplicates
    vague_n, vague_examples = _vague_count(commits)
    if vague_n:
        penalty = min(vague_n * VAGUE_PENALTY, VAGUE_CAP)
        score_val -= penalty
        sample = ", ".join(repr(m) for m in vague_examples[:3])
        findings.append(Finding(
            "vague messages",
            "warn",
            f"{vague_n} vague subject(s) (-{penalty}). e.g. {sample}",
        ))
    else:
        findings.append(Finding("vague messages", "pass", "no vague subjects"))

    dupes = _duplicate_messages(commits)
    if dupes:
        sample = ", ".join(f"{n}×{msg!r}" for msg, n in dupes[:3])
        findings.append(Finding(
            "duplicate messages",
            "warn",
            f"{len(dupes)} message(s) used {DUPLICATE_THRESHOLD}+ times: {sample}",
        ))
    else:
        findings.append(Finding("duplicate messages", "pass", "no duplicated subjects"))

    # 2. Pacing — bursts + total span
    bursts = _find_bursts(commits)
    if bursts:
        penalty = min(len(bursts) * BURST_PENALTY, BURST_CAP)
        score_val -= penalty
        findings.append(Finding(
            "burst pacing",
            "warn",
            f"{len(bursts)} burst(s) of {BURST_MIN_COMMITS}+ commits inside "
            f"{BURST_WINDOW_SECS}s (-{penalty})",
        ))
    else:
        findings.append(Finding("burst pacing", "pass", "no commit bursts"))

    timestamps = [c.timestamp for c in commits]
    span = max(timestamps) - min(timestamps)
    if len(commits) >= 2 and span < SHORT_SPAN_SECS:
        score_val -= SHORT_SPAN_PENALTY
        findings.append(Finding(
            "history span",
            "warn",
            f"entire history spans {span}s (< {SHORT_SPAN_SECS}s) "
            f"(-{SHORT_SPAN_PENALTY})",
        ))
    else:
        findings.append(Finding("history span", "pass", f"history spans {span}s"))

    # 3. Volume
    if len(commits) < LOW_VOLUME_MIN:
        score_val -= LOW_VOLUME_PENALTY
        findings.append(Finding(
            "volume",
            "warn",
            f"only {len(commits)} commit(s) (< {LOW_VOLUME_MIN}) "
            f"(-{LOW_VOLUME_PENALTY})",
        ))
    else:
        findings.append(Finding("volume", "pass", f"{len(commits)} commits"))

    score_val = max(0, score_val)
    return HealthReport(findings=findings, score=score_val, grade=_grade(score_val))
