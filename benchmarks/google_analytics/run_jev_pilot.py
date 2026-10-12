"""Run a small Jev pilot over session-aware Google Analytics decision points."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

OPTIONS = {
    "continue_previous_journey": (
        "Prioritize continuity with the visitor's established journey or returning context."
    ),
    "guide_product_discovery": (
        "Prioritize categories, product exploration, and orientation for the current visit."
    ),
    "reduce_purchase_friction": (
        "Prioritize cart, checkout, shipping, returns, trust, or other purchase-completion help."
    ),
}


def stable_rank(seed: int, decision_id: str) -> bytes:
    return hashlib.sha256(f"{seed}:{decision_id}".encode()).digest()


def select_points(points: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size > len(points):
        raise ValueError(f"sample-size must be <= {len(points)}")
    return sorted(points, key=lambda point: stable_rank(seed, point["decision_id"]))[:sample_size]


def format_point(point: dict[str, Any]) -> str:
    state = point["current_state_at_decision"]
    traffic = state["traffic_source"]
    device = state["device"]
    history = point["history_before_decision"]
    lines = [
        f"Visit number: {point['visit_number']}",
        f"Prior sessions available: {len(history)}",
        f"Channel grouping: {state['channel_grouping']}",
        f"Traffic source: {traffic['source']}",
        f"Traffic medium: {traffic['medium']}",
        f"Campaign: {traffic['campaign']}",
        f"True direct visit: {str(traffic['is_true_direct']).lower()}",
        f"Device category: {device['category']}",
        f"Operating system: {device['operating_system']}",
        f"Browser: {device['browser']}",
        "Early session hits:",
    ]
    for hit in state["early_hits"]:
        lines.append(
            f"- Hit {hit['hit_number']}: {hit['type']} {hit['page_path']} "
            f"at {hit['milliseconds_from_session_start']} ms"
        )
    lines.append("Prior-session summaries, oldest to newest:")
    if history:
        for prior in history:
            lines.append(
                "- "
                f"Visit {prior['visit_number']}; channel {prior['channel_grouping']}; "
                f"source {prior['source']}; medium {prior['medium']}; "
                f"{prior['pageviews']} pageviews; previous purchase "
                f"{str(prior['purchased']).lower()}"
            )
    else:
        lines.append("- None")
    return "\n".join(lines)


def probability_for_choice(answer: dict[str, Any], choice: str) -> float | None:
    probabilities = answer.get("probabilities")
    if isinstance(probabilities, dict):
        value = probabilities.get(choice)
        if isinstance(value, (int, float)):
            return float(value)
    confidence = answer.get("confidence")
    if answer.get("choice") == choice and isinstance(confidence, (int, float)):
        return float(confidence)
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
    points: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
    timeout: float,
    max_attempts: int,
) -> tuple[dict[str, dict[str, Any]], float, float | None, Any]:
    questions = {}
    for point in points:
        decision_id = point["decision_id"]
        questions[decision_id] = {
            "type": "choice",
            "instructions": (
                "Choose which page experience should be prioritized now, immediately after the "
                "listed early-session hits. Use only information available in this state. Do not "
                "predict or assume the hidden outcome. Return exactly one option.\n\n"
                f"Session state:\n{format_point(point)}"
            ),
            "criteria": OPTIONS,
        }

    payload = json.dumps(
        {
            "model": model,
            "state": {
                "experiment": "Session-aware runtime experience selection",
                "decision_timing": "Immediately after the third hit",
                "ground_truth_notice": (
                    "The dataset has no correct component label. Outcomes are withheld."
                ),
            },
            "questions": questions,
        }
    ).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/systemone",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    response = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as raw:
                response = json.loads(raw.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if error.code < 500 or attempt == max_attempts:
                raise RuntimeError(f"Jev returned HTTP {error.code}: {detail}") from error
            time.sleep(attempt)
        except urllib.error.URLError as error:
            if attempt == max_attempts:
                raise RuntimeError(f"Jev request failed: {error.reason}") from error
            time.sleep(attempt)
    if response is None:
        raise RuntimeError("Jev request failed without a response")
    latency_ms = (time.perf_counter() - started) * 1_000
    answers = response.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("Jev response did not contain an answers object")
    return answers, latency_ms, response_cost(response), response.get("usage")


def summarize(
    records: list[dict[str, Any]], points_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["decision_id"]].append(record)

    per_point = []
    modal_choices: dict[str, str] = {}
    flipped = 0
    for decision_id, runs in sorted(grouped.items()):
        choices = [run["choice"] for run in runs]
        counts = Counter(choices)
        modal = counts.most_common(1)[0][0]
        modal_choices[decision_id] = modal
        did_flip = len(counts) > 1
        flipped += int(did_flip)
        selected_probabilities = [
            run["selected_probability"]
            for run in runs
            if run["selected_probability"] is not None
        ]
        per_point.append(
            {
                "decision_id": decision_id,
                "choice_counts": dict(counts),
                "decision_flipped": did_flip,
                "selected_probability_mean": (
                    statistics.fmean(selected_probabilities)
                    if selected_probabilities
                    else "unavailable"
                ),
                "selected_probability_stddev": (
                    statistics.pstdev(selected_probabilities)
                    if len(selected_probabilities) > 1
                    else (0.0 if selected_probabilities else "unavailable")
                ),
                "selected_probability_min": (
                    min(selected_probabilities) if selected_probabilities else "unavailable"
                ),
                "selected_probability_max": (
                    max(selected_probabilities) if selected_probabilities else "unavailable"
                ),
            }
        )

    choice_distribution = Counter(modal_choices.values())
    descriptive_cross_tab: dict[str, dict[str, int]] = {}
    for option in OPTIONS:
        decision_ids = [key for key, choice in modal_choices.items() if choice == option]
        descriptive_cross_tab[option] = {
            "sessions": len(decision_ids),
            "later_purchase": sum(
                bool(
                    points_by_id[key]["outcome_for_scoring_only"][
                        "purchase_after_decision"
                    ]
                )
                for key in decision_ids
            ),
        }

    return {
        "decision_flip_rate": flipped / len(grouped),
        "points_with_a_flip": flipped,
        "points_evaluated": len(grouped),
        "modal_choice_distribution": dict(choice_distribution),
        "descriptive_outcome_cross_tab": descriptive_cross_tab,
        "outcome_warning": (
            "Later purchase is not a correct-choice label and this is not a causal comparison."
        ),
        "per_point": per_point,
    }


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
        default=directory / "local_results" / "jev_pilot_results.json",
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
    points = select_points(source["decision_points"], args.sample_size, args.seed)
    points_by_id = {point["decision_id"]: point for point in points}

    records = []
    latencies = []
    costs = []
    usages = []
    for repeat in range(1, args.repeats + 1):
        answers, latency_ms, cost, usage = call_jev(
            points, api_key, args.base_url, args.model, args.timeout, args.max_attempts
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
        },
        "measurement_scope": {
            "accuracy": "unavailable: no ground-truth component label",
            "business_impact": "unavailable: requires an online randomized experiment",
        },
        "latency": {
            "total_ms": sum(latencies),
            "mean_request_ms": statistics.fmean(latencies),
            "mean_batched_decision_ms": sum(latencies) / len(records),
        },
        "api_cost_usd": sum(costs) if len(costs) == args.repeats else "unavailable",
        "usage": usages if usages else "unavailable",
        "stability_and_distribution": summarize(records, points_by_id),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote local-only output to {args.output}")


if __name__ == "__main__":
    main()
