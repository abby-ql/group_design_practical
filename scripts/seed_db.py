\
from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd
from sqlmodel import select

from app.core.db import init_db, get_session
from app.core.models import Item, TrendTopic


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> None:
    init_db()

    repo_root = os.path.dirname(os.path.dirname(__file__))
    items_path = os.path.join(repo_root, "data", "items_synthetic.csv")
    trends_path = os.path.join(repo_root, "data", "trends_snapshot_today.json")

    df = pd.read_csv(items_path)
    items = []
    for _, row in df.iterrows():
        items.append(Item(
            id=row["id"],
            user_id=row["user_id"],
            platform=row["platform"],
            visibility=row["visibility"],
            language=row.get("language","en"),
            created_at=parse_dt(row["created_at"]),
            text=row["text"],
            edge_case=(None if pd.isna(row.get("edge_case")) else str(row.get("edge_case"))),
            metadata=json.loads(row["metadata_json"]) if isinstance(row["metadata_json"], str) else {},
        ))

    with get_session() as session:
        existing_ids = set([i.id for i in session.exec(select(Item.id)).all()])
        to_add = [i for i in items if i.id not in existing_ids]
        for it in to_add:
            session.add(it)
        session.commit()
        print(f"Seeded items: {len(to_add)} (skipped {len(items)-len(to_add)} existing)")

    # Seed trends snapshot (offline demo)
    if os.path.exists(trends_path):
        snap = json.load(open(trends_path, "r", encoding="utf-8"))
        with get_session() as session:
            for t in snap.get("trends", []):
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
            session.commit()
        print("Seeded sample trends snapshot.")

    print("Done.")


if __name__ == "__main__":
    main()
