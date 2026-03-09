\
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlmodel import select

from app.core.db import get_session
from app.core.models import Alert, Item, TrendTopic
from app.core.scoring import score_item


_BUCKET_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _current_trends_as_dicts(session) -> List[Dict[str, Any]]:
    trends = session.exec(select(TrendTopic)).all()
    return [
        {
            "term": t.term,
            "volume": t.volume,
            "tone": t.tone,
            "last_seen": t.last_seen,
            "source": t.source,
        }
        for t in trends
    ]


def run_cross_match(limit_items: int = 500) -> Tuple[int, List[Alert]]:
    """
    Cross-match current trends with historical items.
    Baseline: exact overlap match; create an Alert when overlap causes bucket increase.
    Returns (num_created, alerts_created).
    """
    created: List[Alert] = []
    now = _now_utc()

    with get_session() as session:
        items = session.exec(select(Item).limit(limit_items)).all()
        trends = _current_trends_as_dicts(session)

        for it in items:
            baseline = score_item(it.text, it.created_at, current_trends=None)
            with_trends = score_item(it.text, it.created_at, current_trends=trends)

            old_bucket = baseline.bucket
            new_bucket = with_trends.bucket

            if _BUCKET_ORDER.get(new_bucket, 0) <= _BUCKET_ORDER.get(old_bucket, 0):
                continue

            # Identify which trend term(s) overlapped, if any
            overlaps = []
            for d in with_trends.decomposition:
                if d.get("signal") == "trend_overlap":
                    overlaps = d.get("overlaps", []) or []
                    break
            if not overlaps:
                continue

            # Create one alert per overlap term (easy UI)
            for ov in overlaps:
                term = ov.get("term")
                if not term:
                    continue

                # avoid duplicates: same item + trend_term on same day
                existing = session.exec(
                    select(Alert)
                    .where(Alert.item_id == it.id)
                    .where(Alert.trend_term == term)
                ).first()
                if existing:
                    continue

                alert = Alert(
                    id=str(uuid.uuid4()),
                    created_at=now,
                    item_id=it.id,
                    trend_term=term,
                    old_bucket=old_bucket,
                    new_bucket=new_bucket,
                    risk_delta=round(with_trends.total_score - baseline.total_score, 2),
                    details={
                        "baseline_score": baseline.total_score,
                        "with_trends_score": with_trends.total_score,
                        "overlap": ov,
                        "note": "Risk indicator increased due to trend overlap (demo heuristic).",
                    },
                )
                session.add(alert)
                created.append(alert)

        session.commit()

    return len(created), created
