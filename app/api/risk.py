\
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlmodel import select

from app.core.db import get_session
from app.core.models import Item, ItemIn, RiskScore, RiskScoreOut, TrendTopic
from app.core.scoring import score_item

router = APIRouter()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _load_trends(session) -> List[Dict[str, Any]]:
    trends = session.exec(select(TrendTopic)).all()
    return [{"term": t.term, "volume": t.volume, "tone": t.tone, "last_seen": t.last_seen, "source": t.source} for t in trends]


@router.post("/score", response_model=RiskScoreOut)
def score(item: ItemIn, include_trends: bool = Query(default=True)) -> RiskScoreOut:
    with get_session() as session:
        trends = _load_trends(session) if include_trends else None
    return score_item(item.text, item.created_at, current_trends=trends)


@router.get("/items")
def list_items(
    limit: int = Query(default=50, ge=1, le=500),
    include_trends: bool = Query(default=True),
) -> Dict[str, Any]:
    """
    Convenience endpoint for the demo UI: returns sample items and a computed score.
    """
    with get_session() as session:
        items = session.exec(select(Item).order_by(Item.created_at.desc()).limit(limit)).all()
        trends = _load_trends(session) if include_trends else None

    out = []
    for it in items:
        rs = score_item(it.text, it.created_at, current_trends=trends)
        out.append({
            "id": it.id,
            "created_at": it.created_at,
            "platform": it.platform,
            "visibility": it.visibility,
            "text": it.text,
            "edge_case": it.edge_case,
            "risk": rs.model_dump(),
        })
    return {"items": out, "count": len(out)}
