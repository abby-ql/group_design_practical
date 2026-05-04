# Issue #4 Work Summary (Backtesting "Suddenly Risky")

## What we implemented

- **Replay-time scoring support**: added `as_of` to `app/core/scoring.py::score_item(...)` so trend recency + age exposure are computed relative to a historical timestamp (instead of wall-clock “now”).
- **Offline backtesting script**: added `scripts/backtest_rescore.py` to replay `data/trend_history_uk_demo.csv` across the fixed synthetic items in `data/items_synthetic.csv`, producing:
  - `reports/backtest_results.csv`
  - `reports/backtest_results.json`
  - deterministic selection of **3 case studies** where risk moves **low -> medium/high**.
- **Evaluation artefact**: created/filled `reports/evaluation.md` with:
  - scoring summary + precision/recall trade-offs
  - 3 case studies (before/after with explanations)
  - brief error analysis (false positives/false negatives) + harm reduction via explanations.
- **Tests**:
  - `tests/test_backtest_rescore.py` for `as_of` behavior + core backtest transitions
  - updated `tests/test_trend_overlap.py` to keep it deterministic.
- **Documentation**: updated `README.md` with how to run the backtest and where to find outputs.

## How to run / demo

- Run:
  - `python -m scripts.backtest_rescore`
- Check:
  - `reports/backtest_results.csv`
  - `reports/evaluation.md`

## Proposed scoring improvements / extensions (future)

- **Trend matching quality**: move beyond exact term overlap to configurable similarity (TF-IDF / embeddings) while keeping explanations (show top matched terms).
- **Use trend metadata**: incorporate trend `volume` and `tone` into the trend-overlap contribution (currently dominated by recency + sensitivity).
- **Better disambiguation**: use `item_metadata.edge_case` (when present) to override/adjust ambiguity and quoting/sarcasm heuristics, reducing avoidable false positives.
- **Context-aware toxic style cues**: refine caps/punctuation heuristics (e.g., exclude ALL-CAPS acronyms, detect “shouting” vs emphasis).
- **Calibration**: tune weights/thresholds in `config/scoring.yaml` based on a labeled synthetic evaluation set to balance precision/recall more explicitly.

