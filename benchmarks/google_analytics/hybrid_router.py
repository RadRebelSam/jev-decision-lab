"""Deterministic routing for clear Google Analytics decision points."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

FRICTION_PATH = re.compile(r"/(basket|cart|checkout|payment|order)", re.IGNORECASE)


def route_point(point: dict[str, Any]) -> dict[str, Any]:
    """Route only explicit policy cases; leave everything else to Jev."""
    state = point["current_state_at_decision"]
    paths = [str(hit.get("page_path", "")) for hit in state["early_hits"]]
    first_path = paths[0].lower() if paths else ""
    history = point["history_before_decision"]

    if any(FRICTION_PATH.search(path) for path in paths):
        return {
            "needs_jev": False,
            "choice": "reduce_purchase_friction",
            "reason": "An early hit explicitly entered a basket or purchase-completion path.",
        }
    if history and state["traffic_source"]["is_true_direct"]:
        return {
            "needs_jev": False,
            "choice": "continue_previous_journey",
            "reason": "A direct return has prior session history available.",
        }
    if (
        not history
        and point["visit_number"] <= 1
        and first_path == "/home"
    ):
        return {
            "needs_jev": False,
            "choice": "guide_product_discovery",
            "reason": "A first visit began at the home page without prior history.",
        }
    return {
        "needs_jev": True,
        "reason": "No explicit deterministic policy matched the mixed session context.",
    }


def route_summary(points: list[dict[str, Any]]) -> dict[str, Any]:
    routes = [(point, route_point(point)) for point in points]
    function_routes = [route for _, route in routes if not route["needs_jev"]]
    ambiguous = [point for point, route in routes if route["needs_jev"]]
    counts = Counter(route["choice"] for route in function_routes)
    return {
        "total_points": len(points),
        "function_points": len(function_routes),
        "jev_points": len(ambiguous),
        "function_fraction": len(function_routes) / len(points),
        "jev_fraction": len(ambiguous) / len(points),
        "function_choice_distribution": dict(counts),
        "warning": "These are policy routes, not ground-truth component labels.",
    }
