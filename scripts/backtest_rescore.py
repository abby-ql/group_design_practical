"""
Replay UK trend snapshots and rescore a fixed item set.

Reads ``data/trend_history_uk_demo.csv`` (by default) and ``data/items_synthetic.csv``,
runs ``score_item`` at each snapshot with ``as_of`` set to that moment, and writes
``reports/backtest_results.csv`` and ``reports/backtest_results.json`` including
selected low→medium (or higher) case studies.

Run: ``python -m scripts.backtest_rescore --help``
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

from app.core.scoring import score_item


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_ITEMS_PATH = os.path.join(ROOT_DIR, "data", "items_synthetic.csv")
DEFAULT_TREND_HISTORY_PATH = os.path.join(ROOT_DIR, "data", "trend_history_uk_demo.csv")


BUCKET_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _parse_dt(s: str) -> datetime:
    # Handles e.g. "2020-01-01T10:00:00Z".
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _parse_snapshot_day(day: str, hour: int = 12) -> datetime:
    # Turn "YYYY-MM-DD" into an aware datetime. Using midday reduces
    # “item created after snapshot” edge cases for the demo.
    dt = datetime.fromisoformat(f"{day}T{hour:02d}:00:00+00:00")
    return dt


def load_items(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            created_at = _parse_dt(row["created_at"])
            items.append(
                {
                    "id": row["id"],
                    "created_at": created_at,
                    "text": row["text"],
                    "edge_case": row.get("edge_case") or None,
                }
            )
    return items


def load_trend_history(path: str) -> List[Tuple[datetime, List[Dict[str, Any]]]]:
    """
    Returns: list[(as_of_datetime, trends_for_that_day)] sorted by date.
    """
    by_day: Dict[str, List[Dict[str, Any]]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            day = str(row["snapshot_date"])
            term = str(row["term"])
            by_day.setdefault(day, []).append(
                {
                    "term": term,
                    "volume": int(row["volume"]),
                    "tone": float(row["tone"]),
                    # `score_item` understands datetime last_seen, but we
                    # also compute an `as_of` per snapshot, so decay is stable.
                    "last_seen": _parse_snapshot_day(day),
                    "source": "trend_history_demo",
                }
            )
    out: List[Tuple[datetime, List[Dict[str, Any]]]] = []
    for day, trends in by_day.items():
        out.append((_parse_snapshot_day(day), trends))
    out.sort(key=lambda x: x[0])
    return out


def _extract_reason_signals(reasons: List[Dict[str, Any]]) -> Dict[str, Any]:
    signals: Dict[str, Any] = {"edge_case_flags": [], "matched_topic_signals": []}
    for r in reasons:
        sig = r.get("signal")
        if sig in {"edge_case"}:
            signals["edge_case_flags"].append(r.get("type") or r.get("explanation") or sig)
        if sig == "topics":
            signals["matched_topic_signals"].append(
                {"topic_names": [t.get("topic") for t in r.get("topics", [])], "explanation": r.get("explanation")}
            )
    # Also capture trend overlap terms when present.
    for r in reasons:
        if r.get("signal") == "trend_overlap":
            overlaps = r.get("overlaps", []) or []
            signals["trend_overlap_terms"] = [o.get("term") for o in overlaps if o.get("term")]
            signals["trend_overlap_details"] = overlaps
            break
    return signals


def rescore_items_for_snapshot(
    items: List[Dict[str, Any]],
    trends: List[Dict[str, Any]],
    *,
    as_of: datetime,
) -> List[Dict[str, Any]]:
    """
    Compute baseline and with-trend RiskScore buckets for each eligible item.
    """
    results: List[Dict[str, Any]] = []
    for it in items:
        # Only include items that existed at the snapshot time.
        if it["created_at"] > as_of:
            continue

        baseline = score_item(
            it["text"],
            it["created_at"],
            current_trends=None,
            as_of=as_of,
        )
        with_trends = score_item(
            it["text"],
            it["created_at"],
            current_trends=trends,
            as_of=as_of,
        )

        base_bucket = baseline.bucket
        with_bucket = with_trends.bucket
        bucket_transition = f"{base_bucket}->{with_bucket}"

        res = {
            "snapshot_as_of": as_of.isoformat().replace("+00:00", "Z"),
            "item_id": it["id"],
            "item_created_at": it["created_at"].isoformat().replace("+00:00", "Z"),
            "baseline_bucket": base_bucket,
            "with_trends_bucket": with_bucket,
            "baseline_score": baseline.total_score,
            "with_trends_score": with_trends.total_score,
            "risk_delta": round(with_trends.total_score - baseline.total_score, 2),
            "bucket_transition": bucket_transition,
        }
        # Keep report columns light; store reason snippets for case studies.
        res.update(_extract_reason_signals(with_trends.reasons))
        results.append(res)
    return results


def compute_bucket_events(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for r in rows:
        base_bucket = r["baseline_bucket"]
        with_bucket = r["with_trends_bucket"]
        if BUCKET_ORDER.get(with_bucket, -1) <= BUCKET_ORDER.get(base_bucket, -1):
            continue
        # Only keep “low -> medium/high/critical” events for the evaluation.
        if base_bucket != "low":
            continue
        if with_bucket not in {"medium", "high", "critical"}:
            continue
        events.append(
            {
                "snapshot_as_of": r["snapshot_as_of"],
                "item_id": r["item_id"],
                "item_created_at": r["item_created_at"],
                "baseline_bucket": base_bucket,
                "with_trends_bucket": with_bucket,
                "baseline_score": r["baseline_score"],
                "with_trends_score": r["with_trends_score"],
                "risk_delta": r["risk_delta"],
                "trend_overlap_terms": r.get("trend_overlap_terms", []),
                "edge_case_flags": r.get("edge_case_flags", []),
                "matched_topic_signals": r.get("matched_topic_signals", []),
            }
        )
    return events


def select_case_studies(events: List[Dict[str, Any]], *, k: int = 3) -> List[Dict[str, Any]]:
    """
    Deterministic selection:
    - for each item_id, keep the earliest event (by snapshot_as_of) that matches
      low->medium/high/critical
    - pick the top-k by highest risk_delta (tie: earliest snapshot, then item_id)
    """
    earliest_by_item: Dict[str, Dict[str, Any]] = {}
    for e in sorted(events, key=lambda x: (x["item_id"], x["snapshot_as_of"])):
        item_id = e["item_id"]
        if item_id not in earliest_by_item:
            earliest_by_item[item_id] = e

    candidates = list(earliest_by_item.values())
    candidates.sort(key=lambda x: (-float(x["risk_delta"]), x["snapshot_as_of"], x["item_id"]))
    return candidates[:k]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", default=DEFAULT_ITEMS_PATH)
    parser.add_argument("--trend-history", default=DEFAULT_TREND_HISTORY_PATH)
    parser.add_argument("--out-csv", default=os.path.join(ROOT_DIR, "reports", "backtest_results.csv"))
    parser.add_argument("--out-json", default=os.path.join(ROOT_DIR, "reports", "backtest_results.json"))
    parser.add_argument("--case-studies-k", type=int, default=3)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)

    items = load_items(args.items)
    snapshots = load_trend_history(args.trend_history)

    all_rows: List[Dict[str, Any]] = []
    all_events: List[Dict[str, Any]] = []
    for as_of, trends in snapshots:
        snapshot_rows = rescore_items_for_snapshot(items, trends, as_of=as_of)
        all_rows.extend(snapshot_rows)
        all_events.extend(compute_bucket_events(snapshot_rows))

    # Final selection for evaluation/reporting.
    case_studies = select_case_studies(all_events, k=args.case_studies_k)

    # Write CSV (full rescoring matrix).
    # JSON/list columns become JSON strings for CSV friendliness.
    csv_columns = [
        "snapshot_as_of",
        "item_id",
        "item_created_at",
        "baseline_bucket",
        "with_trends_bucket",
        "baseline_score",
        "with_trends_score",
        "risk_delta",
        "bucket_transition",
        "trend_overlap_terms",
        "edge_case_flags",
        "matched_topic_signals",
    ]

    def _json_str(v: Any) -> str:
        return json.dumps(v, ensure_ascii=True)

    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for r in all_rows:
            row = dict(r)
            # ensure csv-compatible representation
            row["trend_overlap_terms"] = _json_str(row.get("trend_overlap_terms", []))
            row["edge_case_flags"] = _json_str(row.get("edge_case_flags", []))
            row["matched_topic_signals"] = _json_str(row.get("matched_topic_signals", []))
            writer.writerow({c: row.get(c) for c in csv_columns})

    # Write JSON (full rows + events + selected case studies).
    payload = {
        "snapshots": [s[0].isoformat().replace("+00:00", "Z") for s in snapshots],
        "rows": all_rows,
        "events_low_to_risky": all_events,
        "case_studies": case_studies,
    }
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)

    # Also provide a useful console summary.
    num_case_studies = len(case_studies)
    print(f"[backtest_rescore] Wrote: {args.out_csv}")
    print(f"[backtest_rescore] Wrote: {args.out_json}")
    print(f"[backtest_rescore] Case studies (k={args.case_studies_k}): {num_case_studies}")
    for cs in case_studies:
        print(
            f"- item={cs['item_id']} {cs['baseline_bucket']}->"
            f"{cs['with_trends_bucket']} at {cs['snapshot_as_of']} "
            f"(delta={cs['risk_delta']}), overlaps={cs.get('trend_overlap_terms', [])}"
        )


if __name__ == "__main__":
    main()

