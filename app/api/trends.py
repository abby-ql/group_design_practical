\
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query
from sqlmodel import select

from app.core.db import get_session
from app.core.models import TrendTopic
from app.core.trends import ingest_and_store_trends

router = APIRouter()


@router.get("/current")
def current(limit: int = Query(default=30, ge=1, le=200)) -> Dict[str, Any]:
    with get_session() as session:
        trends = session.exec(select(TrendTopic).order_by(TrendTopic.volume.desc()).limit(limit)).all()
        return {"trends": trends, "count": len(trends)}


@router.post("/ingest")
def ingest(top_k: int = Query(default=20, ge=5, le=100)) -> Dict[str, Any]:
    topics = ingest_and_store_trends(top_k=top_k)
    return {"ingested": len(topics), "trends": topics}
