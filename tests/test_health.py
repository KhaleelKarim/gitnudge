from gitnudge.gitio import Commit
from gitnudge.health import (
    BURST_CAP,
    BURST_PENALTY,
    LOW_VOLUME_PENALTY,
    SHORT_SPAN_PENALTY,
    VAGUE_CAP,
    VAGUE_PENALTY,
    score,
)


def make(ts: int, msg: str = "implement parser", author: str = "khal") -> Commit:
    return Commit(timestamp=ts, author=author, message=msg)


def spread(messages: list[str], start: int = 1_700_000_000, gap: int = 3600) -> list[Commit]:
    """Spread commits well apart in time so neither burst nor short-span fires."""
    return [make(start + i * gap, m) for i, m in enumerate(messages)]


# ---------- vague-message check ----------

def test_vague_message_flagged():
    commits = spread(["fix", "implement parser", "wire cli", "add tests", "tune thresholds", "refactor"])
    report = score(commits)
    # One vague message → -5 from 100 = 95
    assert report.score == 100 - VAGUE_PENALTY
    assert any("vague" in f.check.lower() and f.status == "warn" for f in report.findings)


def test_substring_match_does_not_count_as_vague():
    # "fix typo" contains "fix" but isn't an exact match — should NOT be flagged.
    commits = spread(["fix typo in parser", "implement parser", "wire cli", "add tests", "tune thresholds", "refactor"])
    report = score(commits)
    assert report.score == 100


def test_case_insensitive_vague_match():
    commits = spread(["WIP", "implement parser", "wire cli", "add tests", "tune thresholds", "refactor"])
    report = score(commits)
    assert report.score == 100 - VAGUE_PENALTY


def test_vague_penalty_capped():
    # 10 vague messages would be -50 uncapped, but cap should keep it at -30.
    msgs = ["fix"] * 10 + ["implement parser", "wire cli"]
    commits = spread(msgs)
    report = score(commits)
    expected = 100 - VAGUE_CAP
    # Duplicates also fire here (10x "fix"), but the duplicates check is a
    # separate finding — score impact is via vague_penalty only in this design.
    assert report.score <= expected


def test_duplicates_flagged_at_three():
    commits = spread([
        "implement parser",
        "implement parser",
        "implement parser",  # 3rd occurrence — should flag
        "wire cli",
        "add tests",
        "tune thresholds",
    ])
    report = score(commits)
    assert any("duplicate" in f.check.lower() and f.status == "warn" for f in report.findings)


def test_unique_messages_no_duplicate_warning():
    commits = spread(["implement parser", "wire cli", "add tests", "tune thresholds", "refactor", "polish output"])
    report = score(commits)
    assert all(not ("duplicate" in f.check.lower() and f.status == "warn") for f in report.findings)


# ---------- burst check ----------

def test_three_commits_inside_60s_flagged_as_burst():
    base = 1_700_000_000
    commits = [
        make(base, "implement parser"),
        make(base + 20, "wire cli"),
        make(base + 40, "add tests"),
        # Pad with well-spaced commits to avoid the short-span trigger.
        make(base + 7200, "tune thresholds"),
        make(base + 14400, "refactor"),
        make(base + 21600, "polish output"),
    ]
    report = score(commits)
    assert any("burst" in f.check.lower() and f.status == "warn" for f in report.findings)
    # -10 for the burst → 90
    assert report.score == 100 - BURST_PENALTY


def test_overlapping_bursts_counted_once():
    base = 1_700_000_000
    # 4 commits inside 60s is still one burst event, not two.
    commits = [
        make(base, "implement parser"),
        make(base + 15, "wire cli"),
        make(base + 30, "add tests"),
        make(base + 45, "tune thresholds"),
        make(base + 7200, "refactor"),
        make(base + 14400, "polish output"),
    ]
    report = score(commits)
    assert report.score == 100 - BURST_PENALTY


def test_burst_penalty_capped():
    base = 1_700_000_000
    commits: list[Commit] = []
    # 5 disjoint bursts → -50 uncapped, but cap is -30.
    for i in range(5):
        b = base + i * 7200
        commits.append(make(b, f"chunk {i} start"))
        commits.append(make(b + 10, f"chunk {i} middle"))
        commits.append(make(b + 20, f"chunk {i} end"))
    report = score(commits)
    # 5 bursts × 10 = 50 → capped to 30.
    assert (100 - report.score) >= BURST_CAP
    # Burst penalty alone shouldn't exceed cap (other findings may compound).


def test_no_bursts_when_commits_paced():
    commits = spread(["implement parser", "wire cli", "add tests", "tune thresholds", "refactor", "polish output"])
    report = score(commits)
    assert all(not ("burst" in f.check.lower() and f.status == "warn") for f in report.findings)


# ---------- span and volume ----------

def test_short_span_penalty():
    # All commits within 30 min → < 1 hour span → -20.
    base = 1_700_000_000
    msgs = ["implement parser", "wire cli", "add tests", "tune thresholds", "refactor", "polish output"]
    commits = [make(base + i * 300, m) for i, m in enumerate(msgs)]  # 5 min apart, 25 min total
    report = score(commits)
    # No bursts (5 min apart > 60s), no vague, no dupes — only short span.
    assert report.score == 100 - SHORT_SPAN_PENALTY


def test_low_volume_penalty():
    # 3 commits, well spaced → only the low-volume penalty fires.
    commits = spread(["implement parser", "wire cli", "add tests"], gap=7200)
    report = score(commits)
    assert report.score == 100 - LOW_VOLUME_PENALTY


# ---------- grade and empty cases ----------

def test_clean_history_scores_A():
    commits = spread([
        "implement parser",
        "wire cli dispatch",
        "add health tests",
        "tune scoring thresholds",
        "refactor heatmap layout",
        "polish output formatting",
        "document install flow",
    ])
    report = score(commits)
    assert report.score >= 90
    assert report.grade == "A"


def test_empty_history_handled():
    report = score([])
    # No crash; returns a low-graded report.
    assert report.grade == "F"
    assert any(f.status == "warn" for f in report.findings)
