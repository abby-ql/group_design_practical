from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.db import init_db, get_session
from app.core.matching import run_cross_match
from app.core.models import TrendTopic
from scripts.seed_db import parse_dt, main as seed_main


def upsert_snapshot_trends(snapshot_path: str) -> int:
    """
    Offline ingest helper: load data/trends_snapshot_today.json and upsert TrendTopic rows
    Avoids any network/API dependency and does not require Issue 3 prerequisite
    """
    p = Path(snapshot_path)
    if not p.exists():
        raise FileNotFoundError(f"Snapshot trends file not found: {snapshot_path}")

    snap = json.loads(p.read_text(encoding="utf-8"))
    trends = snap.get("trends", [])

    updated = 0
    with get_session() as session:
        for t in trends:
            term = t["term"]
            existing = session.get(TrendTopic, term)

            obj = TrendTopic(
                term=term,
                volume=int(t["volume"]),
                tone=float(t.get("tone", 0.0)),
                last_seen=parse_dt(t.get("last_seen")),
                source="sample_snapshot",
            )

            if existing:
                existing.volume = obj.volume
                existing.tone = obj.tone
                existing.last_seen = obj.last_seen
                existing.source = obj.source
            else:
                session.add(obj)

            updated += 1

        session.commit()

    return updated


def _print_summary(created_count: int, alerts: List[Any]) -> None:
    print(f"Alerts created: {created_count}")
    for a in alerts[:3]:
        # a is an Alert model
        print(
            f"- item_id={a.item_id} term={a.trend_term} {a.old_bucket} -> {a.new_bucket} delta={a.risk_delta}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily demo pipeline: trends -> cross-match -> alerts")
    parser.add_argument("--source", choices=["snapshot", "rss", "newsapi"], default="snapshot")
    parser.add_argument("--limit-items", type=int, default=200)
    parser.add_argument(
        "--snapshot-path",
        default=str(Path(__file__).resolve().parents[1] / "data" / "trends_snapshot_today.json"),
    )
    args = parser.parse_args()
    init_db()
    seed_main()
    if args.source == "snapshot":
        n = upsert_snapshot_trends(args.snapshot_path)
        print(f"Ingested snapshot trends: {n}")
    else:
        os.environ["TRENDS_SOURCE"] = args.source
        print(f"Using live trends source: {args.source} (run POST /trends/ingest manually)")

    created_count, created_alerts = run_cross_match(limit_items=args.limit_items)
    _print_summary(created_count, created_alerts)


if __name__ == "__main__":
    main()