from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _reload_app_modules():
    """
    app.core.db creates the SQLModel engine at import time from DATABASE_URL
    """
    for m in [
        "app.core.db",
        "app.main",
        "scripts.seed_db",
    ]:
        if m in sys.modules:
            del sys.modules[m]


@pytest.mark.integration
def test_alerts_flow_offline_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("TRENDS_SOURCE", "rss")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    _reload_app_modules()
    import app.main as main_mod
    import scripts.seed_db as seed_mod
    seed_mod.main()

    client = TestClient(main_mod.app)
    r = client.get("/trends/current")
    assert r.status_code == 200
    body = r.json()
    assert "trends" in body
    assert body["count"] >= 1
    r = client.post("/alerts/run", params={"limit_items": 200})
    assert r.status_code == 200
    run_body = r.json()
    assert "created" in run_body
    r = client.get("/alerts", params={"limit": 50})
    assert r.status_code == 200
    out = r.json()
    assert "alerts" in out
    assert "count" in out
    assert isinstance(out["alerts"], list)
    if out["alerts"]:
        a = out["alerts"][0]
        for k in ["id", "created_at", "trend_term", "old_bucket", "new_bucket", "risk_delta", "item_id", "details"]:
            assert k in a


@pytest.mark.integration
def test_risk_items_endpoint_works_offline(tmp_path, monkeypatch):
    db_path = tmp_path / "test2.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    _reload_app_modules()

    import app.main as main_mod
    import scripts.seed_db as seed_mod

    seed_mod.main()
    client = TestClient(main_mod.app)

    r = client.get("/risk/items", params={"limit": 5, "include_trends": True})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert body["count"] >= 1
    it = body["items"][0]
    assert "risk" in it
    assert "bucket" in it["risk"]
    assert "reasons" in it["risk"]
    assert "decomposition" in it["risk"]