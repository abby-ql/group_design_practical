from __future__ import annotations

from datetime import datetime, timedelta, timezone

import os

from app.core.scoring import score_item
from scripts.backtest_rescore import compute_bucket_events, rescore_items_for_snapshot, select_case_studies


def test_score_item_as_of_controls_trend_recency(monkeypatch):
    """
    Regression test:
    if `as_of` moves forward in time, trend overlap recency must decay accordingly.
    """
    monkeypatch.setenv("TREND_HALF_LIFE_HOURS", "8")

    text = "covid coronavirus vaccine booster nhs"  # topic-only baseline = 17.5 (low)
    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    last_seen = created_at
    trends = [{"term": "vaccine", "volume": 100, "tone": 0.0, "last_seen": last_seen, "source": "unit_test"}]

    # At the same time as `last_seen`, recency == 1 => trend overlap pushes low -> medium.
    as_of_recent = created_at
    as_of_later = created_at + timedelta(hours=24)  # recency == 0.125 for half-life 8h

    recent = score_item(text, created_at, current_trends=trends, as_of=as_of_recent)
    later = score_item(text, created_at, current_trends=trends, as_of=as_of_later)

    assert recent.bucket == "medium"
    assert later.bucket == "low"


def test_backtest_rescore_low_to_medium_transition(monkeypatch):
    """
    Unit test for backtest core logic:
    given a tiny synthetic timeline, a trend term appearing recently must cause
    a low -> medium bucket transition.
    """
    monkeypatch.setenv("TREND_HALF_LIFE_HOURS", "8")

    as_of = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    created_at = as_of

    items = [
        {
            "id": "item-1",
            "created_at": created_at,
            "text": "covid coronavirus vaccine booster nhs",
            "edge_case": None,
        }
    ]

    trends_old = [{"term": "vaccine", "volume": 100, "tone": 0.0, "last_seen": as_of - timedelta(hours=24), "source": "unit_test"}]
    trends_recent = [{"term": "vaccine", "volume": 100, "tone": 0.0, "last_seen": as_of, "source": "unit_test"}]

    rows_old = rescore_items_for_snapshot(items, trends_old, as_of=as_of)
    rows_recent = rescore_items_for_snapshot(items, trends_recent, as_of=as_of)

    # Baseline should remain low; only trend recency changes.
    assert rows_old[0]["baseline_bucket"] == "low"
    assert rows_old[0]["with_trends_bucket"] == "low"

    assert rows_recent[0]["baseline_bucket"] == "low"
    assert rows_recent[0]["with_trends_bucket"] == "medium"

    events = compute_bucket_events(rows_old + rows_recent)
    # Only the recent scenario should be captured as a low -> medium/high event.
    assert len(events) == 1
    assert events[0]["item_id"] == "item-1"
    assert events[0]["with_trends_bucket"] == "medium"

    case_studies = select_case_studies(events, k=1)
    assert len(case_studies) == 1
    assert case_studies[0]["with_trends_bucket"] == "medium"

