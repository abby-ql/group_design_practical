"""
tests/test_edge_cases.py
========================
Unit tests covering the five explicitly supported edge cases described in
docs/edge_cases.md.

Run with:
    pytest -q tests/test_edge_cases.py

Each test:
1. Scores a representative fixture text.
2. Asserts the expected edge-case reason type appears in `reasons`.
3. Asserts the reason includes `triggered_by` and `suggestion` fields.
4. Asserts `triggered_by` contains the expected cue string.
5. (Where applicable) asserts the matched term is correct.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from app.core.scoring import (
    detect_quote,
    detect_sarcasm,
    detect_ambiguities,
    detect_political_non_political,
    detect_trend_context_shift,
    match_topics,
    score_item,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "edge_cases.json")


def _load_fixture(edge_case_id: str) -> Dict[str, Any]:
    with open(FIXTURES_PATH, "r", encoding="utf-8") as fh:
        fixtures = json.load(fh)
    for f in fixtures:
        if f["id"] == edge_case_id:
            return f
    raise KeyError(f"Fixture '{edge_case_id}' not found in {FIXTURES_PATH}")


def _parse_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _find_edge_reason(reasons: List[Dict[str, Any]], reason_type: str) -> Optional[Dict[str, Any]]:
    """Return the first edge_case reason with the given type, or None."""
    return next(
        (r for r in reasons if r.get("signal") == "edge_case" and r.get("type") == reason_type),
        None,
    )


def _assert_reason_schema(reason: Dict[str, Any]) -> None:
    """Every edge-case reason must have triggered_by and suggestion fields."""
    assert "triggered_by" in reason, f"Missing 'triggered_by' in reason: {reason}"
    assert "suggestion" in reason, f"Missing 'suggestion' in reason: {reason}"
    assert isinstance(reason["triggered_by"], str) and reason["triggered_by"], \
        "'triggered_by' must be a non-empty string"
    assert isinstance(reason["suggestion"], str) and reason["suggestion"], \
        "'suggestion' must be a non-empty string"


def _assert_json_serialisable(obj: Any) -> None:
    """All reasons/decomposition entries must be JSON-serialisable."""
    json.dumps(obj)  # raises TypeError if not serialisable


# ---------------------------------------------------------------------------
# Edge case 1: Sarcasm / Irony
# ---------------------------------------------------------------------------

class TestSarcasmIrony:
    """Edge case: sarcasm / irony marker detected."""

    def test_detect_sarcasm_returns_cue(self):
        cue = detect_sarcasm("This is great... /s")
        assert cue is not None, "Expected sarcasm cue, got None"
        assert "/s" in cue

    def test_detect_sarcasm_none_on_plain_text(self):
        assert detect_sarcasm("This is great!") is None

    def test_score_returns_possible_sarcasm_reason(self):
        fixture = _load_fixture("ec_sarcasm")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_sarcasm")
        assert reason is not None, (
            f"Expected 'possible_sarcasm' reason in: {result.reasons}"
        )

    def test_sarcasm_reason_has_triggered_by_and_suggestion(self):
        fixture = _load_fixture("ec_sarcasm")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_sarcasm")
        _assert_reason_schema(reason)
        assert fixture["expected"]["triggered_by_contains"] in reason["triggered_by"], (
            f"Expected '{fixture['expected']['triggered_by_contains']}' in triggered_by: "
            f"{reason['triggered_by']}"
        )

    def test_sarcasm_discounts_sentiment(self):
        base = score_item("This is terrible.", datetime(2020, 1, 1, tzinfo=timezone.utc))
        sarc = score_item("This is terrible. /s", datetime(2020, 1, 1, tzinfo=timezone.utc))
        base_sent = next(d for d in base.decomposition if d["signal"] == "sentiment")["contribution"]
        sarc_sent = next(d for d in sarc.decomposition if d["signal"] == "sentiment")["contribution"]
        assert sarc_sent <= base_sent, \
            "Sarcasm discount should not increase the sentiment contribution"

    def test_reasons_json_serialisable(self):
        fixture = _load_fixture("ec_sarcasm")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        _assert_json_serialisable(result.reasons)


# ---------------------------------------------------------------------------
# Edge case 2: Quoting someone else
# ---------------------------------------------------------------------------

class TestQuotingSomeoneElse:
    """Edge case: post is quoting another person's words."""

    def test_detect_quote_returns_cue_for_double_quotes(self):
        cue = detect_quote('He said "this is wrong"')
        assert cue is not None, "Expected quote cue, got None"
        assert "quotation" in cue.lower()

    def test_detect_quote_returns_cue_for_reported_speech(self):
        cue = detect_quote("She said the project was done.")
        assert cue is not None
        assert "said" in cue.lower()

    def test_detect_quote_none_on_plain_text(self):
        assert detect_quote("I think this is wrong.") is None

    def test_score_returns_possible_quote_reason(self):
        fixture = _load_fixture("ec_quote")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_quote")
        assert reason is not None, (
            f"Expected 'possible_quote' reason in: {result.reasons}"
        )

    def test_quote_reason_has_triggered_by_and_suggestion(self):
        fixture = _load_fixture("ec_quote")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_quote")
        _assert_reason_schema(reason)
        assert fixture["expected"]["triggered_by_contains"] in reason["triggered_by"].lower(), (
            f"Expected '{fixture['expected']['triggered_by_contains']}' in triggered_by: "
            f"{reason['triggered_by']}"
        )

    def test_quote_discounts_toxicity(self):
        plain = score_item('You are an idiot.', datetime(2020, 1, 1, tzinfo=timezone.utc))
        quoted = score_item('He said "You are an idiot."', datetime(2020, 1, 1, tzinfo=timezone.utc))
        plain_tox = next(d for d in plain.decomposition if d["signal"] == "toxicity")["contribution"]
        quoted_tox = next(d for d in quoted.decomposition if d["signal"] == "toxicity")["contribution"]
        assert quoted_tox <= plain_tox, \
            "Quote discount should not increase the toxicity contribution"

    def test_reasons_json_serialisable(self):
        fixture = _load_fixture("ec_quote")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        _assert_json_serialisable(result.reasons)


# ---------------------------------------------------------------------------
# Edge case 3: Ambiguous terms
# ---------------------------------------------------------------------------

class TestAmbiguousTerms:
    """Edge case: a term in the post has multiple plausible meanings."""

    def test_detect_ambiguities_finds_shoot(self):
        text = "Big shoot tomorrow for the product photos. Need to book a studio."
        ambiguities = detect_ambiguities(text)
        terms = [a["term"] for a in ambiguities]
        assert "shoot" in terms, f"Expected 'shoot' in ambiguities: {terms}"

    def test_detect_ambiguities_records_matched_hints(self):
        text = "Big shoot tomorrow for the product photos. Need to book a studio."
        ambiguities = detect_ambiguities(text)
        shoot = next(a for a in ambiguities if a["term"] == "shoot")
        assert shoot["hint_hit"], "Expected hint_hit=True for photography shoot"
        assert shoot["matched_hints"], "Expected non-empty matched_hints"

    def test_score_returns_possible_ambiguity_reason(self):
        fixture = _load_fixture("ec_ambiguity")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_ambiguity")
        assert reason is not None, (
            f"Expected 'possible_ambiguity' reason in: {result.reasons}"
        )
        assert reason.get("term") == fixture["expected"]["term"]

    def test_ambiguity_reason_has_triggered_by_and_suggestion(self):
        fixture = _load_fixture("ec_ambiguity")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_ambiguity")
        _assert_reason_schema(reason)

    def test_ambiguity_reason_includes_meanings(self):
        fixture = _load_fixture("ec_ambiguity")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_ambiguity")
        assert "meanings" in reason and isinstance(reason["meanings"], list), \
            "Ambiguity reason must include a 'meanings' list"

    def test_reasons_json_serialisable(self):
        fixture = _load_fixture("ec_ambiguity")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        _assert_json_serialisable(result.reasons)


# ---------------------------------------------------------------------------
# Edge case 4: Political terms used non-politically
# ---------------------------------------------------------------------------

class TestPoliticalTermNonPolitical:
    """Edge case: a political topic term is used in a non-political sense."""

    def test_detect_political_non_political_conservative_estimate(self):
        text = "Conservative estimate: this refactor will take 2 days, not 2 hours."
        ambiguities = detect_ambiguities(text)
        topic_matches, _ = match_topics(text)
        results = detect_political_non_political(topic_matches, ambiguities)
        terms = [r["term"] for r in results]
        assert "conservative" in terms, (
            f"Expected 'conservative' flagged as political-non-political; got: {terms}"
        )

    def test_detect_political_non_political_labour_pains(self):
        text = "Long night. The labour pains are intense — heading to the hospital."
        ambiguities = detect_ambiguities(text)
        topic_matches, _ = match_topics(text)
        results = detect_political_non_political(topic_matches, ambiguities)
        terms = [r["term"] for r in results]
        assert "labour" in terms, (
            f"Expected 'labour' flagged as political-non-political; got: {terms}"
        )

    def test_detect_political_non_political_returns_empty_when_no_politics(self):
        text = "The weather is nice today."
        ambiguities = detect_ambiguities(text)
        topic_matches, _ = match_topics(text)
        results = detect_political_non_political(topic_matches, ambiguities)
        assert results == [], f"Expected no results for neutral text; got: {results}"

    def test_score_returns_possible_political_term_non_political_reason(self):
        fixture = _load_fixture("ec_political_nonpolitical")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_political_term_non_political")
        assert reason is not None, (
            f"Expected 'possible_political_term_non_political' reason in: {result.reasons}"
        )
        assert reason.get("term") == fixture["expected"]["term"]

    def test_political_nonpolitical_reason_has_triggered_by_and_suggestion(self):
        fixture = _load_fixture("ec_political_nonpolitical")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_political_term_non_political")
        _assert_reason_schema(reason)
        hint = fixture["expected"]["matched_hints_contains"]
        assert hint in reason["triggered_by"], (
            f"Expected hint '{hint}' in triggered_by: {reason['triggered_by']}"
        )

    def test_political_nonpolitical_reason_includes_matched_hints(self):
        fixture = _load_fixture("ec_political_nonpolitical")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        reason = _find_edge_reason(result.reasons, "possible_political_term_non_political")
        assert "matched_hints" in reason and isinstance(reason["matched_hints"], list), \
            "Reason must include a 'matched_hints' list"

    def test_reasons_json_serialisable(self):
        fixture = _load_fixture("ec_political_nonpolitical")
        result = score_item(fixture["text"], _parse_dt(fixture["created_at"]))
        _assert_json_serialisable(result.reasons)


# ---------------------------------------------------------------------------
# Edge case 5: Multi-meaning trend term (context shift)
# ---------------------------------------------------------------------------

class TestTrendContextShift:
    """Edge case: an ambiguous word is trending but used in its benign, non-trending sense."""

    def _corona_trends(self):
        return [
            {
                "term": "corona",
                "volume": 9500,
                "tone": -0.6,
                "last_seen": "2020-03-15T10:00:00Z",
                "source": "twitter",
            }
        ]

    def test_detect_trend_context_shift_fires_for_corona_beer(self):
        text = "Summer vibes: corona with lime on the balcony"
        ambiguities = detect_ambiguities(text)
        results = detect_trend_context_shift(ambiguities, self._corona_trends())
        terms = [r["term"] for r in results]
        assert "corona" in terms, (
            f"Expected 'corona' flagged as trend context shift; got: {terms}"
        )

    def test_detect_trend_context_shift_no_fire_without_trends(self):
        text = "Summer vibes: corona with lime on the balcony"
        ambiguities = detect_ambiguities(text)
        results = detect_trend_context_shift(ambiguities, current_trends=None)
        assert results == [], "Should not fire when no trend data is provided"

    def test_detect_trend_context_shift_no_fire_without_hints(self):
        # "corona" without any disambiguation hint in text
        text = "Reading about corona again today."
        ambiguities = detect_ambiguities(text)
        results = detect_trend_context_shift(ambiguities, self._corona_trends())
        assert results == [], "Should not fire when no disambiguation hint is present"

    def test_score_returns_possible_trend_context_shift_reason(self):
        fixture = _load_fixture("ec_trend_context_shift")
        result = score_item(
            fixture["text"],
            _parse_dt(fixture["created_at"]),
            current_trends=fixture["current_trends"],
        )
        reason = _find_edge_reason(result.reasons, "possible_trend_context_shift")
        assert reason is not None, (
            f"Expected 'possible_trend_context_shift' reason in: {result.reasons}"
        )
        assert reason.get("term") == fixture["expected"]["term"]

    def test_trend_context_shift_reason_has_triggered_by_and_suggestion(self):
        fixture = _load_fixture("ec_trend_context_shift")
        result = score_item(
            fixture["text"],
            _parse_dt(fixture["created_at"]),
            current_trends=fixture["current_trends"],
        )
        reason = _find_edge_reason(result.reasons, "possible_trend_context_shift")
        _assert_reason_schema(reason)
        hint = fixture["expected"]["matched_hints_contains"]
        assert hint in reason["triggered_by"], (
            f"Expected hint '{hint}' in triggered_by: {reason['triggered_by']}"
        )

    def test_trend_context_shift_reason_includes_matched_hints(self):
        fixture = _load_fixture("ec_trend_context_shift")
        result = score_item(
            fixture["text"],
            _parse_dt(fixture["created_at"]),
            current_trends=fixture["current_trends"],
        )
        reason = _find_edge_reason(result.reasons, "possible_trend_context_shift")
        assert "matched_hints" in reason and isinstance(reason["matched_hints"], list), \
            "Reason must include a 'matched_hints' list"

    def test_reasons_json_serialisable(self):
        fixture = _load_fixture("ec_trend_context_shift")
        result = score_item(
            fixture["text"],
            _parse_dt(fixture["created_at"]),
            current_trends=fixture["current_trends"],
        )
        _assert_json_serialisable(result.reasons)


# ---------------------------------------------------------------------------
# Cross-cutting property tests
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    """All score_item results must return consistent schema fields."""

    SAMPLE_TEXTS = [
        "This is a normal post about gardening.",
        'He said "you are stupid" — I reported it.',
        "Sure, this will definitely work... /s",
        "Big shoot for the magazine tomorrow.",
        "Conservative estimate: 3 days of work.",
        "Summer corona with lime — best drink.",
    ]

    @pytest.mark.parametrize("text", SAMPLE_TEXTS)
    def test_score_always_returns_required_fields(self, text):
        result = score_item(text, datetime(2022, 6, 1, tzinfo=timezone.utc))
        assert isinstance(result.total_score, float)
        assert result.bucket in {"low", "medium", "high", "critical"}
        assert isinstance(result.reasons, list)
        assert isinstance(result.decomposition, list)

    @pytest.mark.parametrize("text", SAMPLE_TEXTS)
    def test_reasons_always_json_serialisable(self, text):
        result = score_item(text, datetime(2022, 6, 1, tzinfo=timezone.utc))
        _assert_json_serialisable(result.reasons)

    @pytest.mark.parametrize("text", SAMPLE_TEXTS)
    def test_decomposition_always_json_serialisable(self, text):
        result = score_item(text, datetime(2022, 6, 1, tzinfo=timezone.utc))
        _assert_json_serialisable(result.decomposition)

    @pytest.mark.parametrize("text", SAMPLE_TEXTS)
    def test_edge_case_reasons_have_triggered_by_and_suggestion(self, text):
        result = score_item(text, datetime(2022, 6, 1, tzinfo=timezone.utc))
        for r in result.reasons:
            if r.get("signal") == "edge_case":
                _assert_reason_schema(r)
