"""
Tests for extended hot topics: space_exploration and conflict_war.
These follow the same pattern as tests/test_scoring.py.

Run with:
    pytest -q tests/test_topics_extended.py
"""

from datetime import datetime, timezone

from app.core.scoring import score_item


FIXED_DATE = datetime(2026, 4, 9, tzinfo=timezone.utc)


def _topic_names(result) -> list:
    """Return list of matched topic names from the decomposition."""
    topics_entry = next(
        (d for d in result.decomposition if d["signal"] == "topics"), None
    )
    if topics_entry is None:
        return []
    return [t["topic"] for t in topics_entry.get("topics", [])]


def _topic_contribution(result) -> float:
    """Return total topics contribution from the decomposition."""
    entry = next(
        (d for d in result.decomposition if d["signal"] == "topics"), None
    )
    return entry["contribution"] if entry else 0.0


def test_space_terms_trigger_space_exploration_topic():
    """Clear space-related text should match the space_exploration topic."""
    text = "NASA's Artemis mission returns astronauts to the moon."
    result = score_item(text, FIXED_DATE, current_trends=None)

    assert _topic_contribution(result) > 0, (
        "Expected topics contribution > 0 for space text"
    )
    assert "space_exploration" in _topic_names(result), (
        f"Expected 'space_exploration' in matched topics, got: {_topic_names(result)}"
    )
    # Reasons list should include a topics entry
    assert any(r.get("signal") == "topics" for r in result.reasons), (
        "Expected 'topics' signal in reasons"
    )


def test_space_topic_trend_overlap_amplifies_score():
    """When 'moon landing' is also a trending term, score should be higher."""
    text = "Moon landing mission launched today — watch live!"

    trend = {
        "term": "moon landing",
        "last_seen": FIXED_DATE,
        "volume": 90,
        "tone": 0.0,
        "source": "unit_test",
    }

    score_no_trend = score_item(text, FIXED_DATE, current_trends=None).total_score
    score_with_trend = score_item(text, FIXED_DATE, current_trends=[trend]).total_score

    assert score_with_trend > score_no_trend, (
        f"Expected trend overlap to raise score: "
        f"no_trend={score_no_trend}, with_trend={score_with_trend}"
    )

    result_with_trend = score_item(text, FIXED_DATE, current_trends=[trend])
    trend_entry = next(
        (d for d in result_with_trend.decomposition if d["signal"] == "trend_overlap"),
        None,
    )
    assert trend_entry is not None and trend_entry["contribution"] > 0, (
        "Expected trend_overlap decomposition entry with positive contribution"
    )


def test_war_terms_trigger_conflict_war_topic():
    """Literal conflict text should match the conflict_war topic."""
    text = "Troops advanced to the frontline as the ceasefire collapsed."
    result = score_item(text, FIXED_DATE, current_trends=None)

    assert _topic_contribution(result) > 0, (
        "Expected topics contribution > 0 for conflict text"
    )
    assert "conflict_war" in _topic_names(result), (
        f"Expected 'conflict_war' in matched topics, got: {_topic_names(result)}"
    )
    assert any(r.get("signal") == "topics" for r in result.reasons), (
        "Expected 'topics' signal in reasons"
    )


def test_literal_war_scores_higher_than_figurative_war():
    """
    A text with many conflict_war keyword matches should score higher on the
    topics signal than a figurative use of 'war' with no supporting terms.
    """
    text_figurative = "The price war between supermarkets continues."
    text_literal = "NATO troops engaged in the conflict zone after the invasion."

    contrib_figurative = _topic_contribution(
        score_item(text_figurative, FIXED_DATE, current_trends=None)
    )
    contrib_literal = _topic_contribution(
        score_item(text_literal, FIXED_DATE, current_trends=None)
    )

    assert contrib_literal > contrib_figurative, (
        f"Expected literal conflict text to have higher topic contribution: "
        f"literal={contrib_literal}, figurative={contrib_figurative}"
    )
