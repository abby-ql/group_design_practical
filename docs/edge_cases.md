# Edge Cases: Canonical List

This document defines the five edge cases explicitly supported by the scoring engine
(`app/core/scoring.py`). Each edge case has a defined detection mechanism, a
`reason` type emitted in the API response, and a test fixture in
`tests/fixtures/edge_cases.json` with a corresponding test in
`tests/test_edge_cases.py`.

---

## 1. Sarcasm / Irony

**Reason type:** `possible_sarcasm`

**What it is:** The author uses language that appears negative (or positive) on the surface
but means the opposite. Common in social media commentary and political satire.

**Detection cues (heuristic):**
- Explicit `/s` marker (Reddit convention: "sarcasm")
- Phrase `yeah right`
- Pattern: `sure … definitely` in the same text

**What triggers it:** The `detect_sarcasm()` function returns the matched cue string,
which is recorded in `reasons[].triggered_by`.

**Score impact:** When sarcasm is detected the sentiment contribution is multiplied by
`sarcasm_sentiment_multiplier` (default `0.6`) to avoid over-penalising ironic negativity.

**Suggestion to user:** Read the full context before drawing conclusions. The sarcasm
marker may itself be ironic.

**Example:**
```
Sure, increasing taxes will *definitely* make everything better... /s
```

---

## 2. Quoting Someone Else

**Reason type:** `possible_quote`

**What it is:** The post reproduces another person's words rather than expressing the
author's own view. A harmful-looking quote may have been shared to criticise, not endorse.

**Detection cues (heuristic):**
- Curly or straight double quotation marks enclosing content
- Block-quote prefix (`>`)
- Retweet prefix (`RT `)
- Reported-speech phrase: `he said`, `she said`, `they said`

**What triggers it:** The `detect_quote()` function returns the matched cue string,
recorded in `reasons[].triggered_by`.

**Score impact:** Toxicity and topic contributions are multiplied by
`quote_discount_multiplier` (default `0.75`) when a quote is detected.

**Suggestion to user:** Consider whether the quoted content reflects the author's intent
before acting on the score. Adding attribution context helps reviewers.

**Example:**
```
He said "all politicians are corrupt" — I disagree, but it's everywhere online.
```

---

## 3. Ambiguous Terms

**Reason type:** `possible_ambiguity`

**What it is:** A word or phrase in the post has more than one plausible meaning, making
it hard to assess intent without additional context. Common examples include `corona`
(beer brand vs. virus) and `shoot` (photography vs. violence).

**Detection:** `detect_ambiguities()` searches the text for every term listed in
`config/topics.yaml` under `ambiguous_terms`. When a match is found, disambiguation
hints (additional words that point to a specific meaning) are also checked.

**Fields in reason:**
- `term` — the matched ambiguous word
- `meanings` — list of possible meanings from config
- `matched_hints` — hint words found in the text (may be empty)
- `hint_hit` — `true` if at least one hint was found

**Suggestion to user:** Add surrounding context or topic tags to help tools and reviewers
identify the intended meaning.

**Example:**
```
Big shoot tomorrow for the product photos. Need to book a studio.
```
(`shoot` matched; hints `studio`, `photos` → photography context)

---

## 4. Political Terms Used Non-Politically

**Reason type:** `possible_political_term_non_political`

**What it is:** A term that belongs to a politics-related topic (e.g. `labour`,
`conservative`) appears in the text, but context clues indicate it is used in an
entirely different sense — medical, financial, or idiomatic.

**Detection:** `detect_political_non_political()` fires when:
1. The `politics` topic matched at least one term, AND
2. That same term is also listed in `ambiguous_terms`, AND
3. At least one disambiguation hint in the text suggests a non-political reading.

**Config entries affected:**
| Term | Political meaning | Non-political meaning | Example hints |
|------|-------------------|-----------------------|---------------|
| `labour` | UK Labour Party | Childbirth / physical work | `hospital`, `pain`, `pains`, `midwife` |
| `conservative` | UK Conservative Party / right-wing ideology | Cautious or modest (estimate) | `estimate`, `forecast`, `approach` |

**Suggestion to user:** Consider whether the political topic score applies here. Rewording
(e.g. "cautious estimate" instead of "conservative estimate") can reduce false positives.

**Example:**
```
Conservative estimate: this refactor will take 2 days, not 2 hours.
```
(`conservative` matched politics topic; hint `estimate` → non-political)

---

## 5. Multi-Meaning Trend Term (Context Shift)

**Reason type:** `possible_trend_context_shift`

**What it is:** A word that is currently trending (e.g. `corona` during a pandemic) appears
in the post, but the text context strongly suggests the *other*, non-trending meaning
(e.g. the beer brand). The trend-overlap score may therefore be inflated.

**Detection:** `detect_trend_context_shift()` fires when:
1. An ambiguous term is present in the text, AND
2. That same term appears in the current trends list (`current_trends` parameter), AND
3. At least one disambiguation hint in the text points to the non-trending meaning.

**Relationship to edge case 3:** This is a specialised sub-case of ambiguity that
additionally requires the term to be actively trending. It generates a separate reason
entry so the UI can specifically warn about potential trend-score inflation.

**Suggestion to user:** The trend-overlap score may be inflated. Check whether the
trending context applies before acting on the score.

**Example (with `corona` in the trends list):**
```
Summer vibes: corona with lime on the balcony 🍻
```
(`corona` trending as virus term; hint `lime` → beer context)

---

## Schema Guarantee

Every edge-case reason entry in the `reasons` array is guaranteed to include:

| Field | Type | Description |
|-------|------|-------------|
| `signal` | `"edge_case"` | Fixed value for all edge-case reasons |
| `type` | `str` | One of the five reason types above |
| `triggered_by` | `str` | Human-readable description of the matched pattern or term |
| `explanation` | `str` | What the engine detected and why it matters |
| `suggestion` | `str` | Neutral, actionable suggestion for the content owner |

All `reasons` entries are JSON-serialisable (strings, lists of strings, booleans, and
numbers only — no `datetime` objects or other non-serialisable types).
