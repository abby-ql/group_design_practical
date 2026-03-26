\
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import feedparser
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.core.db import get_session
from app.core.models import TrendTopic

from app.core.scoring import _CFG  # reuse stopwords

_ANALYZER = SentimentIntensityAnalyzer()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fetch_headlines() -> Tuple[str, List[str]]:
    """
    Fetch a list of UK headline strings.
    Returns (source_name, headlines).
    """
    source = os.getenv("TRENDS_SOURCE", "rss").lower().strip()
    if source == "newsapi":
        api_key = os.getenv("NEWSAPI_KEY", "").strip()
        if not api_key:
            raise RuntimeError("NEWSAPI_KEY is required when TRENDS_SOURCE=newsapi")

        country = os.getenv("NEWSAPI_COUNTRY", "gb")
        page_size = int(os.getenv("NEWSAPI_PAGE_SIZE", "50"))

        url = "https://newsapi.org/v2/top-headlines"
        resp = requests.get(url, params={"country": country, "pageSize": page_size, "apiKey": api_key}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        headlines = [a.get("title") for a in data.get("articles", []) if a.get("title")]
        return "newsapi_top_headlines", headlines

    # RSS fallback
    rss_url = os.getenv("RSS_URL", "https://feeds.bbci.co.uk/news/uk/rss.xml")
    feed = feedparser.parse(rss_url)
    headlines = []
    for entry in feed.entries[:80]:
        title = getattr(entry, "title", None)
        if title:
            headlines.append(str(title))
    return f"rss:{rss_url}", headlines


def _tokenize_for_trends(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9']+", text)
    stop = _CFG["stopwords"]
    tokens = [t for t in tokens if t not in stop and len(t) >= 3]
    return tokens


def extract_trend_terms(headlines: List[str], top_k: int = 20) -> List[Dict]:
    """
    Simple frequency-based trend terms (unigrams + bigrams).
    """
    unigram: Dict[str, int] = {}
    bigram: Dict[str, int] = {}
    for h in headlines:
        toks = _tokenize_for_trends(h)
        for t in toks:
            unigram[t] = unigram.get(t, 0) + 1
        for a, b in zip(toks, toks[1:]):
            bg = f"{a} {b}"
            bigram[bg] = bigram.get(bg, 0) + 1

    # Merge by taking top terms from both, then sort deterministically:
    # volume desc, then term asc.
    candidates: Dict[str, int] = {}
    for k, v in unigram.items():
        candidates[k] = max(candidates.get(k, 0), v)
    for k, v in bigram.items():
        # prefer bigrams only if they appear at least twice
        if v >= 2:
            candidates[k] = max(candidates.get(k, 0), v)

    drop_terms = _CFG.get("scoring", {}).get("trend_extraction", {}).get("drop_terms", [])
    drop_set = {str(t).lower() for t in drop_terms}
    sorted_candidates = sorted(candidates.items(), key=lambda kv: (-kv[1], kv[0]))
    # Filter first so we return top_k non-generic results (unless candidates are insufficient).
    top = [(t, v) for (t, v) in sorted_candidates if t not in drop_set][:top_k]

    # Compute tone per term (avg sentiment of headlines containing the term)
    results: List[Dict] = []
    for term, vol in top:
        scores = []
        for h in headlines:
            h_l = h.lower()
            if (" " in term and term in h_l) or (re.search(rf"\b{re.escape(term)}\b", h_l)):
                scores.append(_ANALYZER.polarity_scores(h)["compound"])
        tone = float(sum(scores) / len(scores)) if scores else 0.0
        results.append({"term": term, "volume": int(vol), "tone": round(tone, 3)})
    return results


def ingest_and_store_trends(top_k: int = 20) -> List[TrendTopic]:
    """
    Fetch headlines, extract terms, upsert TrendTopic rows.
    """
    source_name, headlines = fetch_headlines()
    extracted = extract_trend_terms(headlines, top_k=top_k)
    now = _now_utc()

    topics = [
        TrendTopic(term=e["term"], volume=e["volume"], tone=e["tone"], last_seen=now, source=source_name)
        for e in extracted
    ]

    with get_session() as session:
        for t in topics:
            existing = session.get(TrendTopic, t.term)
            if existing:
                existing.volume = t.volume
                existing.tone = t.tone
                existing.last_seen = t.last_seen
                existing.source = t.source
            else:
                session.add(t)
        session.commit()

    return topics
