# Issue #4 Evaluation: Backtesting "Suddenly Risky"

## Scoring function summary (transparent) + precision vs recall trade-offs

This project uses an explainable, rule-based risk scoring function (`score_item`) that decomposes risk into the following interpretable signals:

- **Sentiment (VADER)**: rule-based mapping from compound sentiment to a small score contribution.
- **Toxicity (keyword/style list)**: matched terms from `config/toxic_terms.txt` plus simple style cues (caps/punctuation).
- **Topic tags (config keywords)**: keyword hits from `config/topics.yaml`, converted into a topic contribution with a per-topic weight and a “match density” multiplier.
- **Age (exposure bump)**: older items can resurface in high-stakes contexts, increasing score after a grace period.
- **Trend overlap delta**: exact term overlap between an item's text and the current UK trend terms, decayed by a **half-life** factor and scaled by a **topic sensitivity multiplier** (so overlap into sensitive topic categories increases impact).

### Precision vs recall

The design intentionally favors **explainability and controlled behavior** over statistical learning:

- **Higher precision / lower harm**: everything is deterministic and user-auditable (matched keywords, matched categories, trend term overlap, and trend recency decay).
- **Lower precision risk**: exact keyword/topic matching and exact overlap can cause **false positives** when the same term is used in benign, non-target contexts (e.g., policy discussion, reminders, quoting someone else, or ambiguous terms).
- **Recall considerations**: the half-life + sensitivity multiplier intentionally increase sensitivity to “context shift” (a historically low-risk item can move to medium/high when a related theme becomes prominent). This improves recall of “suddenly risky” moments, but it can also increase the chance of over-alerting.

Mitigations included by design:

- **Reasons list + decomposition** for every score flag so users can see *which* tokens and trend terms triggered the alert and *how* recency influenced it.
- **Edge-case heuristics** (e.g., quoting, sarcasm cues, ambiguity hints) to reduce over-penalising user-quoted or ironic content.

## Case studies: low -> medium driven by UK trend spikes

All case studies below were produced by offline backtesting over `data/trend_history_uk_demo.csv`. For each item:

- **Before** = score at the snapshot time with `current_trends=None`
- **After**  = score at the snapshot time with current snapshot trend terms

**Reproducibility:** run `python -m scripts.backtest_rescore`, then open `reports/backtest_results.json` and inspect the `case_studies` array. The three narratives below match those entries (same `item_id`, dates, and scores). Item IDs: `50406738-d013-4265-805e-b0330ced0b69`, `2fa5a29b-21f9-48b8-a868-2b050669883c`, `889ed15a-3847-4958-917e-8df684e89856`.

### Case study 1: "referendum" becomes newly salient (2016-06-24)

- **Item text**: `Reminder: don't share referendum without context.`
- **Item created at**: `2015-07-05T03:41:01Z`
- **Snapshot ("as_of")**: `2016-06-24T12:00:00Z`
- **Matched signals**:
  - Topic keyword hit: `politics` (matched term: `referendum`)
  - Trend overlap: `referendum` (trend recency = 1.0 at the snapshot day; sensitivity multiplier = 1.30)

**Before (no trends)**: `low` (total_score = `13.89`)  
**After (with trends)**: `medium` (total_score = `24.29`)

Why the score moved:
- The item already had a baseline risk from **politics topic matching** and an **age exposure bump**.
- The trend system then added a **trend_overlap contribution** of `10.4` due to exact overlap with a high-salience snapshot term.

### Case study 2: "vaccine" resurfacing during a 2021 spike (2021-09-01)

- **Item text**: `My take on vaccine: people are stressed.`
- **Item created at**: `2019-04-17T13:27:25Z`
- **Snapshot ("as_of")**: `2021-09-01T12:00:00Z`
- **Matched signals**:
  - Topic keyword hit: `health_public` (matched term: `vaccine`)
  - Sentiment contribution (negative): VADER compound maps to a mild negativity bump
  - Trend overlap: `vaccine` (trend recency = 1.0 at the snapshot day; sensitivity multiplier = 1.25)

**Before (no trends)**: `low` (total_score = `14.29`)  
**After (with trends)**: `medium` (total_score = `24.29`)

Why the score moved:
- The topic + age exposure bump provided a **low** baseline.
- Trend overlap contributed `10.0` (recency-weighted) at the snapshot time, pushing the bucket into **medium**.

### Case study 3: "content moderation" becomes newly salient (2026-03-02)

- **Item text**: `We need better content moderation on platforms.`
- **Item created at**: `2016-08-15T16:51:28Z`
- **Snapshot ("as_of")**: `2026-03-02T12:00:00Z`
- **Matched signals**:
  - Topic keyword hit: `online_safety` (matched term: `content moderation`)
  - Trend overlap: `content moderation` (trend recency = 1.0 at the snapshot day; sensitivity multiplier = 1.20)

**Before (no trends)**: `low` (total_score = `15.47`)  
**After (with trends)**: `medium` (total_score = `25.07`)

Why the score moved:
- Baseline was already elevated by **online_safety topic matching** and a large **age exposure bump** (older items resurface).
- Trend overlap then added a recency-weighted contribution of `9.6`, pushing the bucket to **medium**.

## Brief error analysis (false positives/false negatives) and harm reduction via explanations

### Likely false positives

Because the system is keyword- and term-overlap driven (no training required), it can flag items whose matched wording does not reflect harmful intent. Typical patterns:

- **Benign reminders and policy discussion**: the selected case studies are reminders or general advocacy, but still move bucket because the *topic term* coincides with a trending theme.
- **Quoting / reference text**: quoting someone else's words can trigger toxicity/topic matches. The engine includes a quoting detector and applies a quote discount to reduce harm.
- **Ambiguous terms and non-political usage**: for ambiguous tokens, the model reports “possible ambiguity” reasons so users can interpret the match in context (and optionally adjust configs).

How explanations reduce harm:
- Every risk score returns a **structured reason list** plus **score decomposition**. Users see exactly which topic terms matched and which trend term overlapped, along with the **recency** and **sensitivity multiplier** used for the trend contribution.
- That transparency makes it easier for a user to decide whether an alert is actionable (e.g., “this was a general reminder”) versus concerning.

### Likely false negatives

The main reasons a truly “suddenly risky” item might not be flagged:

- **Exact-match trend overlap**: trend matching is currently based on exact term overlap (phrase/word boundary heuristics). If a trend is referenced indirectly (paraphrase, synonym, new spelling), overlap may be missed.
- **Naive edge-case heuristics**: sarcasm and quoting detection are heuristic (and can fail on creative wording).
- **Incomplete toxicity/keyword lists**: toxicity is rule-based. Unseen rude language or new slang could be under-detected.

Mitigation options (future improvements / stretch):
- Similarity-based trend matching (TF-IDF) instead of exact overlap, constrained to the same config topics to preserve explainability.
- Expand `config/topics.yaml` and `config/ambiguous_terms` to cover known ambiguity patterns.

