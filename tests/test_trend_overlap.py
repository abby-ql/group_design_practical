\
from datetime import datetime, timezone

from app.core.scoring import score_item


def test_trend_overlap_increases_score_when_term_matches():
    created_at = datetime(2018, 1, 1, tzinfo=timezone.utc)
    now = datetime(2026, 3, 2, tzinfo=timezone.utc)
    # Provide a recent trend term
    trends = [{"term": "coronavirus", "last_seen": now, "volume": 100, "tone": -0.2, "source": "unit_test"}]
    base = score_item("Reading about coronavirus updates.", created_at, current_trends=None)
    with_trends = score_item("Reading about coronavirus updates.", created_at, current_trends=trends)
    assert with_trends.total_score >= base.total_score
    trend_part = next(d for d in with_trends.decomposition if d["signal"] == "trend_overlap")
    assert trend_part["contribution"] > 0
