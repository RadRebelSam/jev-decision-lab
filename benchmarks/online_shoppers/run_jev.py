"""Run a reproducible Jev sample and repeated-run stability experiment."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from benchmark import (
    DATASET_URL,
    SELECTED_FEATURES,
    TARGET,
    classification_metrics,
    load_dataset,
    split_dataset,
)


def clean_number(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.6g}"


def format_session(row: pd.Series) -> str:
    """Render only selected, non-target fields as compact natural language."""
    return "\n".join(
        [
            f"Administrative pages viewed: {clean_number(row['Administrative'])}",
            f"Administrative duration: {clean_number(row['Administrative_Duration'])} seconds",
            f"Informational pages viewed: {clean_number(row['Informational'])}",
            f"Informational duration: {clean_number(row['Informational_Duration'])} seconds",
            f"Product-related pages viewed: {clean_number(row['ProductRelated'])}",
            f"Product-related duration: {clean_number(row['ProductRelated_Duration'])} seconds",
            f"Bounce rate: {clean_number(row['BounceRates'])}",
            f"Exit rate: {clean_number(row['ExitRates'])}",
            f"Special-day proximity: {clean_number(row['SpecialDay'])}",
            f"Month: {row['Month']}",
            f"Operating system category: {row['OperatingSystems']}",
            f"Browser category: {row['Browser']}",
            f"Region category: {row['Region']}",
            f"Traffic type category: {row['TrafficType']}",
            f"Visitor type: {row['VisitorType']}",
            f"Weekend: {str(bool(row['Weekend'])).lower()}",
        ]
    )


def reproducible_sample(
    test_x: pd.DataFrame, test_y: pd.Series, sample_size: int, seed: int
) -> tuple[pd.DataFrame, pd.Series]:
    if sample_size > len(test_x):
        raise ValueError(f"sample-size must be <= {len(test_x)}")
    if sample_size == len(test_x):
        return test_x.copy(), test_y.copy()
    sample_x, _, sample_y, _ = train_test_split(
        test_x,
        test_y,
        train_size=sample_size,
        random_state=seed,
        stratify=test_y,
    )
    return sample_x.sort_index(), sample_y.sort_index()


def probability_from_answer(answer: dict[str, Any]) -> float | None:
    probabilities = answer.get("probabilities")
    if isinstance(probabilities, dict):
        for key in ("Purchase", "purchase"):
            value = probabilities.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    confidence = answer.get("confidence")
    choice = answer.get("choice")
    if isinstance(confidence, (int, float)) and choice in {"Purchase", "No purchase"}:
        return float(confidence) if choice == "Purchase" else 1.0 - float(confidence)
    return None


def response_cost(response: dict[str, Any]) -> float | None:
    containers = [response]
    if isinstance(response.get("usage"), dict):
        containers.insert(0, response["usage"])
    for container in containers:
        for key in ("total_cost_usd", "cost_usd", "cost"):
            value = container.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def call_jev(
    sample_x: pd.DataFrame,
    api_key: str,
    base_url: str,
    model: str,
    timeout: float,
) -> tuple[dict[str, dict[str, Any]], float, float | None, Any]:
    ids = [f"session-{index}" for index in sample_x.index]
    state = [
        {"id": session_id, "description": format_session(sample_x.loc[index])}
        for session_id, index in zip(ids, sample_x.index)
    ]
    questions = {
        session_id: {
            "type": "choice",
            "instructions": (
                "Use only this session description. Is this completed session likely to result "
                "in a purchase? Return one of the two exact options. Coded categories are labels, "
                "not invented semantic meanings."
            ),
            "criteria": {
                "Purchase": "The session is likely to end with a purchase.",
                "No purchase": "The session is unlikely to end with a purchase.",
            },
        }
        for session_id in ids
    }
    payload = json.dumps({"model": model, "state": state, "questions": questions}).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/systemone",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as raw:
            response = json.loads(raw.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jev returned HTTP {error.code}: {detail}") from error
    latency_ms = (time.perf_counter() - started) * 1_000
    answers = response.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("Jev response did not contain an answers object")
    return answers, latency_ms, response_cost(response), response.get("usage")


def summarize_stability(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_session[record["session_id"]].append(record)

    per_session = []
    flipped = 0
    for session_id, runs in sorted(by_session.items()):
        decisions = [run["prediction"] for run in runs]
        probabilities = [run["purchase_probability"] for run in runs]
        numeric = [value for value in probabilities if value is not None]
        did_flip = len(set(decisions)) > 1
        flipped += int(did_flip)
        per_session.append(
            {
                "session_id": session_id,
                "decision_counts": dict(Counter(decisions)),
                "decision_flipped": did_flip,
                "probability_mean": statistics.fmean(numeric) if numeric else "unavailable",
                "probability_stddev": statistics.pstdev(numeric) if len(numeric) > 1 else (
                    0.0 if numeric else "unavailable"
                ),
                "probability_min": min(numeric) if numeric else "unavailable",
                "probability_max": max(numeric) if numeric else "unavailable",
            }
        )
    return {
        "decision_flip_rate": flipped / len(by_session),
        "sessions_with_a_flip": flipped,
        "sessions_evaluated": len(by_session),
        "definition": "Share of sampled sessions whose decision changed across repeated runs.",
        "per_session": per_session,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY is required and must remain server-side/local")

    frame = load_dataset(args.data, allow_download=not args.no_download)
    _, test_x, _, test_y = split_dataset(frame, test_size=args.test_size, seed=args.seed)
    sample_x, sample_y = reproducible_sample(test_x, test_y, args.sample_size, args.seed)

    records: list[dict[str, Any]] = []
    latencies: list[float] = []
    costs: list[float] = []
    usages: list[Any] = []
    for repeat in range(args.repeats):
        answers, latency_ms, cost, usage = call_jev(
            sample_x, api_key, args.base_url, args.model, args.timeout
        )
        latencies.append(latency_ms)
        if cost is not None:
            costs.append(cost)
        if usage is not None:
            usages.append(usage)
        for index in sample_x.index:
            session_id = f"session-{index}"
            answer = answers.get(session_id)
            if not isinstance(answer, dict):
                raise ValueError(f"Missing answer for {session_id}")
            choice = answer.get("choice")
            if choice not in {"Purchase", "No purchase"}:
                raise ValueError(f"Invalid choice for {session_id}: {choice!r}")
            records.append(
                {
                    "session_id": session_id,
                    "repeat": repeat + 1,
                    "actual": int(sample_y.loc[index]),
                    "prediction": choice,
                    "purchase_probability": probability_from_answer(answer),
                }
            )

    labels = np.array([record["actual"] for record in records])
    predictions = np.array([record["prediction"] == "Purchase" for record in records], dtype=int)
    raw_probabilities = [record["purchase_probability"] for record in records]
    probabilities = (
        np.array(raw_probabilities, dtype=float)
        if all(value is not None for value in raw_probabilities)
        else None
    )

    return {
        "dataset": {"source": DATASET_URL, "rows": len(frame)},
        "configuration": {
            "seed": args.seed,
            "test_size": args.test_size,
            "sample_size": args.sample_size,
            "repeats": args.repeats,
            "model": args.model,
            "selected_features": SELECTED_FEATURES,
        },
        "metrics_across_all_repeats": classification_metrics(
            labels, predictions, probabilities
        ),
        "latency": {
            "total_ms": sum(latencies),
            "mean_request_ms": statistics.fmean(latencies),
            "mean_decision_ms": sum(latencies) / len(records),
        },
        "api_cost_usd": sum(costs) if len(costs) == args.repeats else "unavailable",
        "usage": usages if usages else "unavailable",
        "stability": summarize_stability(records),
        "predictions": records,
        "limitations": [
            "This is a small held-out sample, not the full test set.",
            "Rows summarize completed sessions and are not timestamped early-session snapshots.",
            "The dataset provides purchase outcomes, not personalization-component labels.",
        ],
    }


def parse_args() -> argparse.Namespace:
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=directory / "data" / "online_shoppers_intention.csv"
    )
    parser.add_argument(
        "--output", type=Path, default=directory / "results" / "jev_results.json"
    )
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--base-url", default=os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai")
    )
    parser.add_argument(
        "--model", default=os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest")
    )
    parser.add_argument("--no-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.sample_size < 2:
        raise ValueError("sample-size must be at least 2")
    if args.repeats < 1:
        raise ValueError("repeats must be at least 1")
    results = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
