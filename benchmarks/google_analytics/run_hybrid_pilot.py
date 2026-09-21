"""Route clear GA sessions with rules and sample ambiguous sessions for Jev."""

from __future__ import annotations

import argparse
import json
import os
import statistics
from pathlib import Path

from hybrid_router import route_point, route_summary
from run_jev_pilot import OPTIONS, call_jev, probability_for_choice, select_points, summarize


def select_ambiguous_points(
    points: list[dict], sample_size: int, seed: int
) -> list[dict]:
    """Balance prior-history and no-history contexts without using outcomes."""
    with_history = [point for point in points if point["history_before_decision"]]
    without_history = [point for point in points if not point["history_before_decision"]]
    history_target = min(len(with_history), sample_size // 2)
    no_history_target = min(len(without_history), sample_size - history_target)
    remaining = sample_size - history_target - no_history_target
    if remaining:
        history_target += min(len(with_history) - history_target, remaining)
        remaining = sample_size - history_target - no_history_target
    if remaining:
        no_history_target += min(len(without_history) - no_history_target, remaining)
    selected = select_points(with_history, history_target, seed)
    selected += select_points(without_history, no_history_target, seed)
    return sorted(selected, key=lambda point: point["decision_id"])


def parse_args() -> argparse.Namespace:
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=directory / "local_results" / "decision_points.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=directory / "local_results" / "hybrid_pilot_results.json",
    )
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument(
        "--base-url", default=os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai")
    )
    parser.add_argument(
        "--model", default=os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.sample_size < 1 or args.repeats < 1 or args.max_attempts < 1:
        raise ValueError("sample-size, repeats, and max-attempts must be positive")
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY is required and must remain local/server-side")

    source = json.loads(args.input.read_text(encoding="utf-8"))
    all_points = source["decision_points"]
    ambiguous = [point for point in all_points if route_point(point)["needs_jev"]]
    points = select_ambiguous_points(ambiguous, args.sample_size, args.seed)
    points_by_id = {point["decision_id"]: point for point in points}

    records = []
    latencies = []
    costs = []
    usages = []
    for repeat in range(1, args.repeats + 1):
        answers, latency_ms, cost, usage = call_jev(
            points,
            api_key,
            args.base_url,
            args.model,
            args.timeout,
            args.max_attempts,
        )
        latencies.append(latency_ms)
        if cost is not None:
            costs.append(cost)
        if usage is not None:
            usages.append(usage)
        for point in points:
            decision_id = point["decision_id"]
            answer = answers.get(decision_id)
            if not isinstance(answer, dict):
                raise ValueError(f"Missing answer for {decision_id}")
            choice = answer.get("choice")
            if choice not in OPTIONS:
                raise ValueError(f"Invalid choice for {decision_id}: {choice!r}")
            records.append(
                {
                    "decision_id": decision_id,
                    "repeat": repeat,
                    "choice": choice,
                    "selected_probability": probability_for_choice(answer, choice),
                }
            )

    result = {
        "configuration": {
            "sample_size": args.sample_size,
            "repeats": args.repeats,
            "seed": args.seed,
            "model": args.model,
            "options": OPTIONS,
            "sampling": "Balanced by presence of prior-session history; outcomes were not used.",
        },
        "full_local_route_summary": route_summary(all_points),
        "jev_ambiguous_sample": {
            "available_ambiguous_points": len(ambiguous),
            "sampled_points": len(points),
            "latency": {
                "total_ms": sum(latencies),
                "mean_request_ms": statistics.fmean(latencies),
                "mean_batched_decision_ms": sum(latencies) / len(records),
            },
            "api_cost_usd": (
                sum(costs) if len(costs) == args.repeats else "unavailable"
            ),
            "usage": usages if usages else "unavailable",
            "stability_and_distribution": summarize(records, points_by_id),
        },
        "measurement_scope": {
            "accuracy": "unavailable: no ground-truth component label",
            "business_impact": "unavailable: requires an online randomized experiment",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote local-only output to {args.output}")


if __name__ == "__main__":
    main()
