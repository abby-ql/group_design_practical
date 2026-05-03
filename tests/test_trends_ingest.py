import pytest
from unittest.mock import patch
from sqlmodel import create_engine, Session, SQLModel

from app.core.trends import ingest_and_store_trends, fetch_headlines
from app.api.trends import current
from app.core.models import TrendTopic

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://")
    # Need to import all models before creating metadata
    from app.core import models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_snapshot_ingest_and_current(session: Session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRENDS_SOURCE", "snapshot")
    
    # Mock get_session in both trends.py files to return our test session
    with patch("app.core.trends.get_session") as mock_core_db, \
         patch("app.api.trends.get_session") as mock_api_db:
        
        # The context manager needs to return our session
        mock_core_db.return_value.__enter__.return_value = session
        mock_api_db.return_value.__enter__.return_value = session
        
        topics = ingest_and_store_trends()
        assert len(topics) > 0
        assert topics[0].source == "snapshot"
        
        # Verify the database has the exact number of topics
        from sqlmodel import select
        db_topics = session.exec(select(TrendTopic)).all()
        assert len(db_topics) == len(topics)
        
        # Test /current endpoint returns consistent sorted list
        res = current(limit=30)
        assert res["count"] == len(topics)
        
        # Verify sorting logic (volume desc, term asc)
        trends = res["trends"]
        for i in range(len(trends) - 1):
            t1, t2 = trends[i], trends[i+1]
            assert t1.volume >= t2.volume
            if t1.volume == t2.volume:
                assert t1.term <= t2.term

def test_fetch_headlines_govuk(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRENDS_SOURCE", "govuk")
    
    # We will mock feedparser.parse to return a predefined structure
    with patch("app.core.trends.feedparser.parse") as mock_parse:
        class MockEntry:
            def __init__(self, title):
                self.title = title
        
        class MockFeed:
            def __init__(self):
                self.entries = [MockEntry("Gov.uk Headline 1"), MockEntry("Gov.uk Headline 2")]
                
        mock_parse.return_value = MockFeed()
        
        source_name, headlines = fetch_headlines()
        
        assert source_name == "govuk:https://www.gov.uk/search/all.atom"
        assert headlines == ["Gov.uk Headline 1", "Gov.uk Headline 2"]
        mock_parse.assert_called_once_with("https://www.gov.uk/search/all.atom")

