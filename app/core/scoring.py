\
from __future__ import annotations

import os
import re
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

import yaml
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.core.models import RiskScoreOut

_ANALYZER = SentimentIntensityAnalyzer()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # repo root


def _load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_configs() -> Dict[str, Any]:
    topics_cfg = _load_yaml(os.path.join(ROOT_DIR, "config", "topics.yaml"))
    scoring_cfg = _load_yaml(os.path.join(ROOT_DIR, "config", "scoring.yaml"))

    toxic_terms_path = os.path.join(ROOT_DIR, "config", "toxic_terms.txt")
    toxic_terms: List[str] = []
    with open(toxic_terms_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            toxic_terms.append(line.lower())

    stopwords_path = os.path.join(ROOT_DIR, "config", "stopwords_en.txt")
    stopwords: set[str] = set()
    with open(stopwords_path, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if w:
                stopwords.add(w)

    return {
        "topics": topics_cfg.get("topics", []),
        "ambiguous_terms": topics_cfg.get("ambiguous_terms", []),
        "scoring": scoring_cfg,
        "toxic_terms": toxic_terms,
        "stopwords": stopwords,
    }


_CFG = load_configs()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> List[str]:
    # Keep #hashtags and words; split on non-alphanum (but keep apostrophes inside words).
    text = text.lower()
    tokens = re.findall(r"(?:#[a-z0-9_]+)|(?:[a-z0-9]+(?:'[a-z0-9]+)?)", text)
    return tokens


def detect_quote(text: str) -> Optional[str]:
    """
    Returns a short description of the matched quoting cue, or None if not detected.
    Callers can treat the return value as a boolean (truthy = quote detected).
    """
    t = text.strip()
    if "\u201c" in t or "\u201d" in t:
        return "curly quotation marks (\u201c\u201d)"
    if '"' in t:
        return "double quotation marks"
    if t.startswith(">"):
        return "block-quote prefix (>)"
    if t.lower().startswith("rt "):
        return "retweet prefix (RT)"
    if re.search(r"\b(he|she|they)\s+said\b", t.lower()):
        return "reported-speech phrase (he/she/they said)"
    return None


def detect_sarcasm(text: str) -> Optional[str]:
    """
    Returns a short description of the matched sarcasm cue, or None if not detected.
    Callers can treat the return value as a boolean (truthy = sarcasm detected).
    """
    t = text.lower()
    if "/s" in t:
        return "explicit sarcasm marker (/s)"
    if "yeah right" in t:
        return 'sarcasm phrase ("yeah right")'
    if "sure" in t and "definitely" in t:
        return 'hedging pattern ("sure \u2026 definitely")'
    return None


def detect_ambiguities(text: str) -> List[Dict[str, Any]]:
    t = text.lower()
    found: List[Dict[str, Any]] = []
    for entry in _CFG["ambiguous_terms"]:
        term = entry.get("term", "").lower()
        if not term:
            continue
        if re.search(rf"\b{re.escape(term)}\b", t):
            hints = [h.lower() for h in entry.get("disambiguation_hints", [])]
            matched_hints = [h for h in hints if h in t]
            hint_hit = bool(matched_hints)
            found.append({
                "term": term,
                "meanings": entry.get("meanings", []),
                "hint_hit": hint_hit,
                "matched_hints": matched_hints,
                "disambiguation_hints": entry.get("disambiguation_hints", []),
            })
    return found


def detect_political_non_political(
    topic_matches: List[Dict[str, Any]],
    ambiguities: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Edge case: political topic term used in a clearly non-political context.

    Fires when a term matches the 'politics' topic AND that same term is listed in
    ambiguous_terms AND at least one disambiguation hint (e.g. 'estimate', 'hospital')
    appears in the text — suggesting the non-political reading is intended.

    Returns a list of flagged entries (one per matched term).
    """
    politics_topic = next((tm for tm in topic_matches if tm["topic"] == "politics"), None)
    if not politics_topic:
        return []

    politics_terms_lower = {t.lower() for t in politics_topic.get("matched_terms", [])}
    results: List[Dict[str, Any]] = []

    for amb in ambiguities:
        term = amb["term"].lower()
        if term not in politics_terms_lower:
            continue
        if amb["hint_hit"]:
            results.append({
                "term": amb["term"],
                "meanings": amb["meanings"],
                "matched_hints": amb["matched_hints"],
            })
    return results


def detect_trend_context_shift(
    ambiguities: List[Dict[str, Any]],
    current_trends: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Edge case: multi-meaning trend term used in its benign (non-trending) sense.

    Fires when an ambiguous term also appears in the current trends list AND
    disambiguation hints in the text suggest the non-trending meaning is intended
    (e.g. 'corona' trending as a virus term, but the post is about beer).

    Returns a list of flagged entries (one per shifted term).
    """
    if not current_trends:
        return []
    trend_terms_lower = {str(tr.get("term", "")).lower().strip() for tr in current_trends}
    results: List[Dict[str, Any]] = []
    for amb in ambiguities:
        term = amb["term"].lower()
        if term in trend_terms_lower and amb["hint_hit"]:
            results.append({
                "term": amb["term"],
                "meanings": amb["meanings"],
                "matched_hints": amb["matched_hints"],
            })
    return results


def match_topics(text: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    t = text.lower()
    matched: List[Dict[str, Any]] = []
    topic_to_terms: Dict[str, List[str]] = {}
    for topic in _CFG["topics"]:
        name = topic["name"]
        terms = topic.get("terms", [])
        hits: List[str] = []
        for term in terms:
            term_l = term.lower()
            # exact word boundary match for single words; substring for multiword phrases
            if " " in term_l:
                if term_l in t:
                    hits.append(term)
            else:
                if re.search(rf"\b{re.escape(term_l)}\b", t):
                    hits.append(term)
        if hits:
            topic_to_terms[name] = hits
            matched.append({
                "topic": name,
                "description": topic.get("description", ""),
                "matched_terms": hits,
                "weight": float(topic.get("weight", 0)),
                "sensitivity": float(topic.get("sensitivity", 1.0)),
            })
    return matched, topic_to_terms


def bucket_for(score: float) -> str:
    th = _CFG["scoring"]["thresholds"]
    if score <= th["low_max"]:
        return "low"
    if score <= th["medium_max"]:
        return "medium"
    if score <= th["high_max"]:
        return "high"
    return "critical"


def score_item(
    text: str,
    created_at: datetime,
    current_trends: Optional[List[Dict[str, Any]]] = None,
) -> RiskScoreOut:
    # Compute a transparent risk indicator score (0..100-ish), plus reasons and decomposition.
    text = normalize_text(text)
    t_lower = text.lower()

    reasons: List[Dict[str, Any]] = []
    decomposition: List[Dict[str, Any]] = []
    total = 0.0

    weights = _CFG["scoring"]["weights"]
    adj = _CFG["scoring"].get("adjustments", {})

    quote_cue = detect_quote(text)
    sarcasm_cue = detect_sarcasm(text)
    is_quote = quote_cue is not None
    is_sarcasm = sarcasm_cue is not None
    ambiguities = detect_ambiguities(text)

    # Edge case reasons are added first so UI can surface them prominently.
    if is_quote:
        reasons.append({
            "signal": "edge_case",
            "type": "possible_quote",
            "triggered_by": quote_cue,
            "explanation": (
                "This item appears to be quoting someone else rather than expressing "
                "the author\u2019s own view. Scores are discounted accordingly."
            ),
            "suggestion": (
                "Consider whether the quoted content reflects the author\u2019s intent "
                "before acting on the score. Adding attribution context can help reviewers."
            ),
        })

    if is_sarcasm:
        reasons.append({
            "signal": "edge_case",
            "type": "possible_sarcasm",
            "triggered_by": sarcasm_cue,
            "explanation": (
                "A sarcasm or irony marker was detected. The surface sentiment may be "
                "the opposite of the author\u2019s actual meaning."
            ),
            "suggestion": (
                "Read the full context before drawing conclusions. Sarcasm detection is "
                "heuristic \u2014 the marker may be ironic itself."
            ),
        })

    for amb in ambiguities:
        reasons.append({
            "signal": "edge_case",
            "type": "possible_ambiguity",
            "term": amb["term"],
            "meanings": amb["meanings"],
            "hint_hit": amb["hint_hit"],
            "matched_hints": amb["matched_hints"],
            "triggered_by": f"ambiguous term \u201c{amb['term']}\u201d matched in text",
            "explanation": (
                f"The term \u201c{amb['term']}\u201d has multiple meanings "
                f"({', '.join(amb['meanings'])}). "
                + (
                    f"Context hints {amb['matched_hints']} suggest the non-default reading."
                    if amb["hint_hit"]
                    else "No disambiguation hints were found; meaning is unclear."
                )
            ),
            "suggestion": (
                "Add surrounding context (e.g. topic tags or a brief clarification) "
                "to help automated tools and human reviewers identify the intended meaning."
            ),
        })

    # 1) Sentiment (rule-based VADER)
    sent = _ANALYZER.polarity_scores(text)
    compound = float(sent["compound"])
    sent_contrib = 0.0
    if compound <= -0.5:
        sent_contrib = float(weights["sentiment"]["negative_strong"])
    elif compound <= -0.2:
        sent_contrib = float(weights["sentiment"]["negative_mild"])
    elif compound >= 0.6:
        sent_contrib = float(weights["sentiment"]["positive_strong"])

    # sarcasm discount: don't over-trust sentiment negativity
    if is_sarcasm and sent_contrib > 0:
        sent_contrib *= float(adj.get("sarcasm_sentiment_multiplier", 1.0))

    total += sent_contrib
    decomposition.append({
        "signal": "sentiment",
        "compound": compound,
        "contribution": round(sent_contrib, 2),
    })

    # 2) Toxicity (simple keywords + style cues)
    toxic_terms = _CFG["toxic_terms"]
    toxic_hits = []
    for term in toxic_terms:
        if term in t_lower:
            toxic_hits.append(term)

    toxic_contrib = 0.0
    if toxic_hits:
        toxic_contrib += len(toxic_hits) * float(weights["toxicity"]["per_term"])
    # all caps cue
    caps_ratio = sum(1 for c in text if c.isupper()) / max(1, len(text))
    if caps_ratio > 0.25 and len(text) > 20:
        toxic_contrib += float(weights["toxicity"]["all_caps_bonus"])
    # punctuation cue
    if re.search(r"([!?])\1\1+", text):
        toxic_contrib += float(weights["toxicity"]["punctuation_bonus"])

    toxic_contrib = min(toxic_contrib, float(weights["toxicity"]["max_contribution"]))

    # quote discount (to reduce harm in "someone quoted me" cases)
    if is_quote and toxic_contrib > 0:
        toxic_contrib *= float(adj.get("quote_discount_multiplier", 1.0))

    if toxic_hits:
        reasons.append({
            "signal": "toxicity",
            "matched_terms": toxic_hits,
            "triggered_by": f"toxic keyword(s) matched: {toxic_hits}",
            "explanation": "Matched mild toxic/rude terms (rule-based).",
            "suggestion": (
                "Review whether the matched terms appear in a quoting or ironic context "
                "before escalating."
            ),
        })
    total += toxic_contrib
    decomposition.append({
        "signal": "toxicity",
        "contribution": round(toxic_contrib, 2),
        "matched_terms": toxic_hits,
    })

    # 3) Topic tags (config keywords)
    topic_matches, _topic_to_terms = match_topics(text)
    topic_mult = float(weights["topics"]["topic_weight_multiplier"])
    topic_contrib = 0.0
    for tm in topic_matches:
        # basic: weight * number of matched terms (softened)
        topic_contrib += topic_mult * tm["weight"] * max(1.0, len(tm["matched_terms"]) / 2.0)

    topic_contrib = min(topic_contrib, float(weights["topics"]["max_contribution"]))
    if is_quote and topic_contrib > 0:
        topic_contrib *= float(adj.get("quote_discount_multiplier", 1.0))

    if topic_matches:
        reasons.append({
            "signal": "topics",
            "topics": topic_matches,
            "triggered_by": (
                "topic keyword(s) matched: "
                + ", ".join(
                    f"{tm['topic']}={tm['matched_terms']}" for tm in topic_matches
                )
            ),
            "explanation": "Matched topic keywords from config.",
            "suggestion": (
                "Check whether the topic match reflects the post\u2019s primary subject "
                "or is incidental (e.g. a political term used non-politically)."
            ),
        })
    total += topic_contrib
    decomposition.append({
        "signal": "topics",
        "contribution": round(topic_contrib, 2),
        "topics": topic_matches,
    })

    # -- Edge case: political term used non-politically --
    political_np = detect_political_non_political(topic_matches, ambiguities)
    for entry in political_np:
        reasons.append({
            "signal": "edge_case",
            "type": "possible_political_term_non_political",
            "term": entry["term"],
            "meanings": entry["meanings"],
            "matched_hints": entry["matched_hints"],
            "triggered_by": (
                f"political term \u201c{entry['term']}\u201d matched politics topic, "
                f"but context hint(s) {entry['matched_hints']} suggest non-political use"
            ),
            "explanation": (
                f"The term \u201c{entry['term']}\u201d matched a politics-related topic, "
                f"but words like {entry['matched_hints']} in the text suggest it may be "
                "used in a non-political sense (e.g. a cautious estimate or a medical term)."
            ),
            "suggestion": (
                "Consider whether the political topic score is appropriate here. "
                "Adding clarifying context (e.g. \u201cconservative estimate\u201d \u2192 "
                "\u201cautious estimate\u201d) can reduce false positives."
            ),
        })

    # 4) Age (exposure bump)
    now = _now_utc()
    created_at_utc = created_at.astimezone(timezone.utc) if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    age_days = (now - created_at_utc).days

    grace = float(weights["age"]["grace_days"])
    ramp = float(weights["age"]["ramp_days"])
    max_age = float(weights["age"]["max_contribution"])
    if age_days <= grace:
        age_contrib = 0.0
    else:
        age_contrib = max_age * min(1.0, (age_days - grace) / ramp)

    total += age_contrib
    decomposition.append({
        "signal": "age",
        "age_days": age_days,
        "contribution": round(age_contrib, 2),
    })

    # 5) Trend overlap delta (exact overlap)
    trend_contrib = 0.0
    overlaps: List[Dict[str, Any]] = []
    if current_trends:
        half_life = float(os.getenv("TREND_HALF_LIFE_HOURS", "48"))
        for tr in current_trends:
            term = str(tr.get("term", "")).lower().strip()
            if not term:
                continue

            # match as phrase if multiword, else word boundary
            hit = False
            if " " in term:
                if term in t_lower:
                    hit = True
            else:
                if re.search(rf"\b{re.escape(term)}\b", t_lower):
                    hit = True

            if not hit:
                continue

            last_seen = tr.get("last_seen")
            if isinstance(last_seen, str):
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                except Exception:
                    last_seen_dt = now
            elif isinstance(last_seen, datetime):
                last_seen_dt = last_seen.astimezone(timezone.utc) if last_seen.tzinfo else last_seen.replace(tzinfo=timezone.utc)
            else:
                last_seen_dt = now

            hours = (now - last_seen_dt).total_seconds() / 3600.0
            # half-life decay: exp(-ln(2)*t/half_life)
            recency = math.exp(-math.log(2) * hours / max(1e-6, half_life))

            base = float(weights["trend_overlap"]["base"])
            contrib = base * recency

            # if overlap term belongs to a sensitive topic, apply sensitivity multiplier
            sens = 1.0
            for tm in topic_matches:
                if any(term in str(mt).lower() for mt in tm.get("matched_terms", [])):
                    sens = max(sens, float(tm.get("sensitivity", 1.0)))
            contrib *= sens

            overlaps.append({
                "term": term,
                "recency": round(recency, 3),
                "sensitivity_multiplier": round(sens, 2),
                "last_seen": last_seen_dt.isoformat().replace("+00:00", "Z"),
            })
            trend_contrib += contrib

    trend_contrib = min(trend_contrib, float(weights["trend_overlap"]["max_contribution"]))
    if overlaps:
        reasons.append({
            "signal": "trend_overlap",
            "overlaps": overlaps,
            "triggered_by": f"trend term(s) matched: {[o['term'] for o in overlaps]}",
            "explanation": "Item overlaps with current UK trend terms.",
            "suggestion": (
                "Check whether the trend term is used in its trending sense or in an "
                "unrelated context (e.g. a trending health term used in a lifestyle post)."
            ),
        })
    total += trend_contrib
    decomposition.append({
        "signal": "trend_overlap",
        "contribution": round(trend_contrib, 2),
        "overlaps": overlaps,
    })

    # -- Edge case: multi-meaning trend term used in its benign/non-trending sense --
    trend_shifts = detect_trend_context_shift(ambiguities, current_trends)
    for entry in trend_shifts:
        reasons.append({
            "signal": "edge_case",
            "type": "possible_trend_context_shift",
            "term": entry["term"],
            "meanings": entry["meanings"],
            "matched_hints": entry["matched_hints"],
            "triggered_by": (
                f"trend term \u201c{entry['term']}\u201d is currently trending, "
                f"but context hint(s) {entry['matched_hints']} suggest a different meaning"
            ),
            "explanation": (
                f"The term \u201c{entry['term']}\u201d is a current trend term, "
                f"but context clues ({entry['matched_hints']}) suggest it is being used "
                "in a different sense than the trending one "
                f"(possible meanings: {', '.join(entry['meanings'])})."
            ),
            "suggestion": (
                "The trend-overlap score may be inflated. Consider whether the trending "
                "context applies before acting on the score."
            ),
        })

    # Clamp & bucket
    total = max(0.0, min(100.0, total))
    bucket = bucket_for(total)

    return RiskScoreOut(
        total_score=round(total, 2),
        bucket=bucket,
        reasons=reasons,
        decomposition=decomposition,
    )
