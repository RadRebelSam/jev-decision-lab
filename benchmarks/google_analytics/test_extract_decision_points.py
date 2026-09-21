import unittest

from extract_decision_points import (
    boolean,
    build_candidates,
    choose_decision_points,
    clean_path,
    selected_visitor,
)
from hybrid_router import route_point, route_summary
from run_hybrid_pilot import select_ambiguous_points
from run_jev_pilot import format_point, select_points


class ExtractorTests(unittest.TestCase):
    def test_string_false_is_false(self) -> None:
        self.assertFalse(boolean("False"))
        self.assertTrue(boolean("true"))

    def test_hash_sampling_is_reproducible(self) -> None:
        first = selected_visitor("123", 42, 10_000, 100)
        self.assertEqual(first, selected_visitor("123", 42, 10_000, 100))

    def test_query_strings_are_removed(self) -> None:
        self.assertEqual(clean_path("/search?q=private"), "/search")

    def test_early_transaction_is_excluded(self) -> None:
        sessions = {
            "raw-id": [
                {
                    "visit_id": "visit",
                    "visit_number": 1,
                    "visit_start_time": 1_500_000_000,
                    "date": "20170714",
                    "channel_grouping": "Direct",
                    "traffic_source": {},
                    "device": {},
                    "hit_count": 5,
                    "early_hits": [],
                    "first_transaction_hit": 2,
                    "purchased": True,
                    "revenue_micros": 100,
                    "pageviews": 5,
                }
            ]
        }
        self.assertEqual(build_candidates(sessions, 3, 5, 42), [])

    def test_selection_oversamples_positives_and_removes_private_rank(self) -> None:
        candidates = []
        for index in range(20):
            candidates.append(
                {
                    "_rank": bytes([index]),
                    "outcome_for_scoring_only": {"purchase_after_decision": index < 5},
                }
            )
        selected, metadata = choose_decision_points(candidates, 10, 0.2)
        self.assertEqual(metadata["exported_positive_points"], 2)
        self.assertEqual(len(selected), 10)
        self.assertTrue(all("_rank" not in item for item in selected))

    def test_pilot_state_excludes_scoring_outcome(self) -> None:
        point = {
            "decision_id": "decision-1",
            "visit_number": 2,
            "history_before_decision": [],
            "current_state_at_decision": {
                "channel_grouping": "Direct",
                "traffic_source": {
                    "source": "direct",
                    "medium": "none",
                    "campaign": "",
                    "is_true_direct": True,
                },
                "device": {
                    "category": "desktop",
                    "operating_system": "Windows",
                    "browser": "Chrome",
                },
                "early_hits": [
                    {
                        "hit_number": 1,
                        "type": "PAGE",
                        "page_path": "/home",
                        "milliseconds_from_session_start": 0,
                    }
                ],
            },
            "outcome_for_scoring_only": {
                "purchase_after_decision": True,
                "revenue_micros": 123,
            },
        }
        text = format_point(point)
        self.assertNotIn("purchase_after_decision", text)
        self.assertNotIn("revenue_micros", text)
        self.assertNotIn("123", text)

    def test_pilot_sample_is_reproducible(self) -> None:
        points = [{"decision_id": f"decision-{index}"} for index in range(10)]
        self.assertEqual(select_points(points, 5, 42), select_points(points, 5, 42))

    def test_hybrid_routes_basket_without_jev(self) -> None:
        point = {
            "visit_number": 1,
            "history_before_decision": [],
            "current_state_at_decision": {
                "traffic_source": {"is_true_direct": False},
                "early_hits": [{"page_path": "/basket.html"}],
            },
        }
        route = route_point(point)
        self.assertFalse(route["needs_jev"])
        self.assertEqual(route["choice"], "reduce_purchase_friction")

    def test_hybrid_leaves_mixed_context_for_jev(self) -> None:
        point = {
            "visit_number": 1,
            "history_before_decision": [],
            "current_state_at_decision": {
                "traffic_source": {"is_true_direct": False},
                "early_hits": [{"page_path": "/google+redesign/bags"}],
            },
        }
        self.assertTrue(route_point(point)["needs_jev"])

    def test_hybrid_sample_balances_history_without_outcomes(self) -> None:
        points = []
        for index in range(20):
            points.append(
                {
                    "decision_id": f"decision-{index}",
                    "history_before_decision": [{}] if index < 6 else [],
                }
            )
        selected = select_ambiguous_points(points, 10, 42)
        self.assertEqual(sum(bool(point["history_before_decision"]) for point in selected), 5)


if __name__ == "__main__":
    unittest.main()
