import unittest

from extract_decision_points import (
    boolean,
    build_candidates,
    choose_decision_points,
    clean_path,
    selected_visitor,
)


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


if __name__ == "__main__":
    unittest.main()
