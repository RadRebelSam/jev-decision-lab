"""Stream the 25 GB GA training CSV into local, leakage-aware decision points."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

CSV_FIELD_LIMIT = 2_147_483_647
REQUIRED_COLUMNS = {
    "channelGrouping",
    "date",
    "device",
    "fullVisitorId",
    "hits",
    "totals",
    "trafficSource",
    "visitId",
    "visitNumber",
    "visitStartTime",
}


def parse_nested(value: str) -> Any:
    """Parse Kaggle's JSON-like columns, including legacy Python-literal rows."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return ast.literal_eval(value)


def integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def selected_visitor(visitor_id: str, seed: int, modulus: int, cutoff: int) -> bool:
    digest = hashlib.sha256(f"{seed}:{visitor_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big") % modulus
    return bucket < cutoff


def stable_rank(seed: int, *parts: Any) -> bytes:
    value = ":".join([str(seed), *(str(part) for part in parts)])
    return hashlib.sha256(value.encode()).digest()


def clean_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return ""
    try:
        return urlsplit(value).path[:300]
    except ValueError:
        return value.split("?", 1)[0][:300]


def compact_hit(hit: dict[str, Any]) -> dict[str, Any]:
    page = hit.get("page") if isinstance(hit.get("page"), dict) else {}
    return {
        "hit_number": integer(hit.get("hitNumber")),
        "milliseconds_from_session_start": integer(hit.get("time")),
        "type": str(hit.get("type") or "unknown"),
        "page_path": clean_path(page.get("pagePath")),
    }


def transaction_hit_number(hits: list[dict[str, Any]]) -> int | None:
    for hit in hits:
        action = hit.get("eCommerceAction")
        action_type = action.get("action_type") if isinstance(action, dict) else None
        transaction = hit.get("transaction")
        if action_type == "6" or (
            isinstance(transaction, dict) and transaction.get("transactionRevenue")
        ):
            return integer(hit.get("hitNumber"))
    return None


def parse_session(row: dict[str, str], early_hit_count: int) -> dict[str, Any]:
    totals = parse_nested(row["totals"])
    device = parse_nested(row["device"])
    traffic = parse_nested(row["trafficSource"])
    hits = parse_nested(row["hits"])
    if not isinstance(hits, list):
        hits = []

    first_transaction_hit = transaction_hit_number(hits)
    transactions = integer(totals.get("transactions"))
    revenue_micros = integer(
        totals.get("totalTransactionRevenue") or totals.get("transactionRevenue")
    )
    return {
        "visit_id": row["visitId"],
        "visit_number": integer(row["visitNumber"]),
        "visit_start_time": integer(row["visitStartTime"]),
        "date": row["date"],
        "channel_grouping": row["channelGrouping"],
        "traffic_source": {
            "source": str(traffic.get("source") or ""),
            "medium": str(traffic.get("medium") or ""),
            "campaign": str(traffic.get("campaign") or ""),
            "is_true_direct": boolean(traffic.get("isTrueDirect", False)),
        },
        "device": {
            "category": str(device.get("deviceCategory") or ""),
            "operating_system": str(device.get("operatingSystem") or ""),
            "browser": str(device.get("browser") or ""),
            "is_mobile": boolean(device.get("isMobile", False)),
        },
        "hit_count": len(hits),
        "early_hits": [compact_hit(hit) for hit in hits[:early_hit_count]],
        "first_transaction_hit": first_transaction_hit,
        "purchased": transactions > 0 or revenue_micros > 0,
        "revenue_micros": revenue_micros,
        "pageviews": integer(totals.get("pageviews")),
    }


def scan_sessions(
    input_path: Path,
    seed: int,
    hash_modulus: int,
    hash_cutoff: int,
    early_hit_count: int,
    progress_every: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int | float]]:
    csv.field_size_limit(CSV_FIELD_LIMIT)
    selected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows_scanned = 0
    selected_rows = 0
    malformed_selected_rows = 0
    started = time.perf_counter()

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Input is missing required columns: {sorted(missing)}")

        for rows_scanned, row in enumerate(reader, 1):
            visitor_id = row["fullVisitorId"]
            if selected_visitor(visitor_id, seed, hash_modulus, hash_cutoff):
                try:
                    selected[visitor_id].append(parse_session(row, early_hit_count))
                    selected_rows += 1
                except (SyntaxError, ValueError, TypeError):
                    malformed_selected_rows += 1
            if progress_every and rows_scanned % progress_every == 0:
                elapsed = time.perf_counter() - started
                print(
                    f"Scanned {rows_scanned:,} rows; selected {selected_rows:,}; "
                    f"elapsed {elapsed:.1f}s",
                    flush=True,
                )

    elapsed = time.perf_counter() - started
    return selected, {
        "rows_scanned": rows_scanned,
        "selected_rows": selected_rows,
        "selected_visitors": len(selected),
        "malformed_selected_rows": malformed_selected_rows,
        "scan_seconds": elapsed,
    }


def historical_summary(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "visit_number": session["visit_number"],
        "visit_start_time": session["visit_start_time"],
        "channel_grouping": session["channel_grouping"],
        "source": session["traffic_source"].get("source", ""),
        "medium": session["traffic_source"].get("medium", ""),
        "hit_count": session["hit_count"],
        "pageviews": session["pageviews"],
        "purchased": session["purchased"],
        "revenue_micros": session["revenue_micros"],
    }


def build_candidates(
    sessions_by_visitor: dict[str, list[dict[str, Any]]],
    early_hit_count: int,
    max_history: int,
    seed: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    visitor_order = sorted(
        sessions_by_visitor,
        key=lambda visitor_id: stable_rank(seed, "visitor-alias", visitor_id),
    )
    aliases = {visitor_id: f"visitor-{index:05d}" for index, visitor_id in enumerate(visitor_order, 1)}

    for visitor_id, sessions in sessions_by_visitor.items():
        sessions.sort(key=lambda item: (item["visit_start_time"], item["visit_id"]))
        history: list[dict[str, Any]] = []
        for session in sessions:
            transaction_hit = session["first_transaction_hit"]
            outcome_known_early = transaction_hit is not None and transaction_hit <= early_hit_count
            has_post_decision_activity = session["hit_count"] > early_hit_count
            if has_post_decision_activity and not outcome_known_early:
                candidates.append(
                    {
                        "_rank": stable_rank(seed, visitor_id, session["visit_id"]),
                        "visitor_alias": aliases[visitor_id],
                        "visit_number": session["visit_number"],
                        "visit_start_time": session["visit_start_time"],
                        "visit_start_iso": datetime.fromtimestamp(
                            session["visit_start_time"], tz=timezone.utc
                        ).isoformat(),
                        "history_before_decision": history[-max_history:],
                        "current_state_at_decision": {
                            "decision_after_hit": early_hit_count,
                            "channel_grouping": session["channel_grouping"],
                            "traffic_source": session["traffic_source"],
                            "device": session["device"],
                            "early_hits": session["early_hits"],
                        },
                        "outcome_for_scoring_only": {
                            "purchase_after_decision": session["purchased"],
                            "revenue_micros": session["revenue_micros"],
                            "first_transaction_hit": transaction_hit,
                        },
                    }
                )
            history.append(historical_summary(session))
    return candidates


def choose_decision_points(
    candidates: list[dict[str, Any]],
    max_points: int,
    target_positive_fraction: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    positives = sorted(
        (
            item
            for item in candidates
            if item["outcome_for_scoring_only"]["purchase_after_decision"]
        ),
        key=lambda item: item["_rank"],
    )
    negatives = sorted(
        (
            item
            for item in candidates
            if not item["outcome_for_scoring_only"]["purchase_after_decision"]
        ),
        key=lambda item: item["_rank"],
    )
    positive_target = min(len(positives), math.floor(max_points * target_positive_fraction))
    negative_target = min(len(negatives), max_points - positive_target)
    remaining = max_points - positive_target - negative_target
    if remaining:
        extra_positives = min(len(positives) - positive_target, remaining)
        positive_target += extra_positives
        remaining -= extra_positives
    if remaining:
        negative_target += min(len(negatives) - negative_target, remaining)

    selected = positives[:positive_target] + negatives[:negative_target]
    selected.sort(key=lambda item: item["_rank"])
    for index, item in enumerate(selected, 1):
        item.pop("_rank", None)
        item["decision_id"] = f"decision-{index:04d}"

    return selected, {
        "candidate_points": len(candidates),
        "candidate_positive_points": len(positives),
        "candidate_negative_points": len(negatives),
        "exported_points": len(selected),
        "exported_positive_points": positive_target,
        "exported_negative_points": negative_target,
        "target_positive_fraction": target_positive_fraction,
        "sampling_note": (
            "Positive outcomes are intentionally oversampled for evaluation. "
            "Do not interpret exported accuracy as population performance."
        ),
    }


def write_output(
    output_path: Path,
    input_path: Path,
    args: argparse.Namespace,
    scan: dict[str, int | float],
    selection: dict[str, Any],
    decision_points: Iterable[dict[str, Any]],
) -> None:
    payload = {
        "metadata": {
            "source_file": input_path.name,
            "source_size_bytes": input_path.stat().st_size,
            "seed": args.seed,
            "visitor_hash_sampling": {
                "modulus": args.hash_modulus,
                "cutoff": args.hash_cutoff,
                "expected_fraction": args.hash_cutoff / args.hash_modulus,
            },
            "decision_after_hit": args.early_hits,
            "max_prior_sessions": args.max_history,
            "scan": scan,
            "selection": selection,
            "leakage_policy": [
                "Current-session totals are excluded from decision state.",
                "Transaction and revenue fields are scoring-only outcomes.",
                "Sessions with a transaction at or before the decision hit are excluded.",
                "Only path components are kept; URL query strings are removed.",
                "Raw fullVisitorId and visitId values are not exported.",
            ],
            "limitations": [
                "The dataset has no ground-truth personalization-component label.",
                "The exported cohort is intentionally enriched for positive outcomes.",
                "Competition rules may restrict redistribution, so output stays local and ignored.",
            ],
        },
        "decision_points": list(decision_points),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=repository / "data" / "ga-customer-revenue-prediction" / "train_v2.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "local_results" / "decision_points.json",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hash-modulus", type=int, default=10_000)
    parser.add_argument("--hash-cutoff", type=int, default=100)
    parser.add_argument("--early-hits", type=int, default=3)
    parser.add_argument("--max-history", type=int, default=5)
    parser.add_argument("--max-points", type=int, default=300)
    parser.add_argument("--target-positive-fraction", type=float, default=0.2)
    parser.add_argument("--progress-every", type=int, default=100_000)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input.exists():
        raise FileNotFoundError(args.input)
    if args.hash_modulus < 1 or not 0 < args.hash_cutoff <= args.hash_modulus:
        raise ValueError("hash-cutoff must be between 1 and hash-modulus")
    if args.early_hits < 1 or args.max_history < 0 or args.max_points < 1:
        raise ValueError("early-hits and max-points must be positive; max-history cannot be negative")
    if not 0.0 <= args.target_positive_fraction <= 1.0:
        raise ValueError("target-positive-fraction must be between 0 and 1")


def main() -> None:
    args = parse_args()
    validate_args(args)
    sessions, scan = scan_sessions(
        args.input,
        args.seed,
        args.hash_modulus,
        args.hash_cutoff,
        args.early_hits,
        args.progress_every,
    )
    candidates = build_candidates(sessions, args.early_hits, args.max_history, args.seed)
    points, selection = choose_decision_points(
        candidates, args.max_points, args.target_positive_fraction
    )
    write_output(args.output, args.input, args, scan, selection, points)
    print(json.dumps({"scan": scan, "selection": selection}, indent=2))
    print(f"Wrote local-only output to {args.output}")


if __name__ == "__main__":
    main()
