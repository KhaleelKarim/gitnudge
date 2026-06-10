from datetime import datetime

from gitnudge.graph import GLYPHS, _glyph_for, bucket_by_day, render


def ts(year: int, month: int, day: int, hour: int = 12) -> int:
    return int(datetime(year, month, day, hour).timestamp())


def test_bucket_by_day_empty():
    assert bucket_by_day([]) == {}


def test_bucket_by_day_sums_same_day():
    same_day = [ts(2026, 6, 1, 8), ts(2026, 6, 1, 14), ts(2026, 6, 1, 20)]
    buckets = bucket_by_day(same_day)
    assert len(buckets) == 1
    assert next(iter(buckets.values())) == 3


def test_bucket_by_day_separates_distinct_days():
    timestamps = [ts(2026, 6, 1), ts(2026, 6, 2), ts(2026, 6, 2), ts(2026, 6, 3)]
    buckets = bucket_by_day(timestamps)
    assert len(buckets) == 3
    assert sorted(buckets.values()) == [1, 1, 2]


def test_glyph_for_zero_is_dot():
    assert _glyph_for(0, q1=1, q2=3, q3=5) == GLYPHS[0]


def test_glyph_for_low_mid_high():
    # Quartile boundaries: q1=2, q2=4, q3=6
    assert _glyph_for(1, 2, 4, 6) == GLYPHS[1]   # low
    assert _glyph_for(3, 2, 4, 6) == GLYPHS[2]   # mid
    assert _glyph_for(7, 2, 4, 6) == GLYPHS[3]   # high


def test_render_empty_buckets_returns_dot_grid():
    rendered = render({}, weeks=4)
    text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
    # All cells should be the zero-glyph; no high-intensity glyphs at all.
    assert GLYPHS[3] not in text
    assert GLYPHS[0] in text


def test_render_includes_high_glyph_for_busy_days():
    busy_buckets = {datetime(2026, 6, 1).date(): 100}
    rendered = render(busy_buckets, weeks=12)
    text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
    assert GLYPHS[3] in text or GLYPHS[2] in text
