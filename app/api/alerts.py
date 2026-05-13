\
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Query
from sqlmodel import select

from app.core.db import get_session
from app.core.models import Alert, Item
from app.core.matching import run_cross_match

router = APIRouter()


@router.post("/run")
def run(limit_items: int = Query(default=200, ge=1, le=2000)) -> Dict[str, Any]:
    created_count, created = run_cross_match(limit_items=limit_items)
    return {"created": created_count, "alerts": created}


@router.get("")
def list_alerts(limit: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    with get_session() as session:
        alerts = session.exec(select(Alert).order_by(Alert.created_at.desc()).limit(limit)).all()

        # enrich with item text (demo convenience)
        items = {it.id: it for it in session.exec(select(Item).where(Item.id.in_([a.item_id for a in alerts]))).all()} if alerts else {}

        out = []
        for a in alerts:
            it = items.get(a.item_id)
            out.append({
                "id": a.id,
                "created_at": a.created_at,
                "trend_term": a.trend_term,
                "old_bucket": a.old_bucket,
                "new_bucket": a.new_bucket,
                "risk_delta": a.risk_delta,
                "item_id": a.item_id,
                "item_text": it.text if it else None,
                "details": a.details,
            })

        return {"alerts": out, "count": len(out)}
