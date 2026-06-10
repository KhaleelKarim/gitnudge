from gitnudge.gitio import DiffStats
from gitnudge.status import FILE_THRESHOLD, evaluate


def make_stats(files=0, ins=0, dels=0, untracked=0) -> DiffStats:
    return DiffStats(files_changed=files, insertions=ins, deletions=dels, untracked=untracked)


def test_below_threshold_does_not_nudge():
    report = evaluate(make_stats(files=1, ins=10, dels=5), last_ts=1000, now=2000)
    assert report.should_nudge is False
    assert report.files_touched == 1
    assert report.insertions == 10
    assert report.deletions == 5


def test_at_line_threshold_nudges():
    # Default line threshold is 50; 30 + 20 = 50 hits the bar.
    report = evaluate(make_stats(files=2, ins=30, dels=20), last_ts=1000, now=2000)
    assert report.should_nudge is True


def test_above_line_threshold_nudges():
    report = evaluate(make_stats(files=1, ins=100, dels=0), last_ts=1000, now=2000)
    assert report.should_nudge is True


def test_file_threshold_nudges_with_only_a_few_lines():
    # 5 files touched with tiny diffs should still nudge — lots of churn surface.
    report = evaluate(make_stats(files=FILE_THRESHOLD, ins=1, dels=0), last_ts=1000, now=2000)
    assert report.should_nudge is True


def test_untracked_counts_toward_files_touched():
    # 3 modified + 2 untracked = 5 files touched, hits the file threshold.
    report = evaluate(make_stats(files=3, ins=1, dels=0, untracked=2), last_ts=1000, now=2000)
    assert report.files_touched == 5
    assert report.should_nudge is True


def test_custom_threshold_respected():
    stats = make_stats(files=1, ins=20, dels=0)
    assert evaluate(stats, last_ts=1000, now=2000, threshold=10).should_nudge is True
    assert evaluate(stats, last_ts=1000, now=2000, threshold=100).should_nudge is False


def test_no_last_commit_handled():
    report = evaluate(make_stats(files=1, ins=5, dels=0), last_ts=None, now=2000)
    assert report.seconds_since_last is None
    # No prior commit ≠ crash. should_nudge still driven by diff size.
    assert report.should_nudge is False


def test_seconds_since_last_computed():
    report = evaluate(make_stats(), last_ts=1000, now=2500)
    assert report.seconds_since_last == 1500
