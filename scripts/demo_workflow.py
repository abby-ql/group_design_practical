\
"""
Small helper script (optional):
1) seed DB with sample items + sample trends
2) run cross-match to create alerts
"""
from app.core.db import init_db
from app.core.matching import run_cross_match

def main():
    init_db()
    created, alerts = run_cross_match(limit_items=500)
    print(f"Created alerts: {created}")
    for a in alerts[:10]:
        print(a.item_id, a.trend_term, a.old_bucket, "->", a.new_bucket, "delta", a.risk_delta)

if __name__ == "__main__":
    main()
