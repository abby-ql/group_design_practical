\
from datetime import datetime, timezone

from app.core.scoring import score_item
from app.core.trends import extract_trend_terms


def test_score_returns_decomposition_and_reasons():
    item = score_item("Someone was an idiot!!!", datetime(2020, 1, 1, tzinfo=timezone.utc), current_trends=None)
    assert item.total_score >= 0
    assert item.bucket in {"low","medium","high","critical"}
    assert isinstance(item.reasons, list)
    assert isinstance(item.decomposition, list)
    # toxicity should appear
    assert any(r.get("signal") == "toxicity" for r in item.reasons)


def test_sarcasm_discount_applies():
    base = score_item("This is terrible.", datetime(2020,1,1,tzinfo=timezone.utc), current_trends=None)
    sarc = score_item("This is terrible... /s", datetime(2020,1,1,tzinfo=timezone.utc), current_trends=None)
    # sarcasm should not increase sentiment contribution
    base_sent = next(d for d in base.decomposition if d["signal"] == "sentiment")["contribution"]
    sarc_sent = next(d for d in sarc.decomposition if d["signal"] == "sentiment")["contribution"]
    assert sarc_sent <= base_sent


def test_extract_trend_terms_deterministic_sort_and_drop_terms():
    headlines = ["today alpha", "today bravo"]

    out1 = extract_trend_terms(headlines, top_k=2)
    out2 = extract_trend_terms(headlines, top_k=2)

    assert out1 == out2
    terms = [row["term"] for row in out1]
    assert "today" not in terms
    assert terms == ["alpha", "bravo"]
    assert [row["volume"] for row in out1] == [1, 1]
