import unittest

import numpy as np
import pandas as pd

from benchmark import SELECTED_FEATURES, expected_calibration_error
from run_jev import format_session, probability_from_answer


class BenchmarkTests(unittest.TestCase):
    def test_selected_features_do_not_include_target_or_page_values(self) -> None:
        self.assertNotIn("Revenue", SELECTED_FEATURES)
        self.assertNotIn("PageValues", SELECTED_FEATURES)

    def test_session_text_preserves_codes_and_excludes_labels(self) -> None:
        row = pd.Series(
            {
                "Administrative": 1,
                "Administrative_Duration": 2,
                "Informational": 3,
                "Informational_Duration": 4,
                "ProductRelated": 5,
                "ProductRelated_Duration": 6,
                "BounceRates": 0.01,
                "ExitRates": 0.02,
                "SpecialDay": 0,
                "Month": "Nov",
                "OperatingSystems": 2,
                "Browser": 3,
                "Region": 4,
                "TrafficType": 7,
                "VisitorType": "Returning_Visitor",
                "Weekend": False,
                "PageValues": 99,
                "Revenue": True,
            }
        )
        text = format_session(row)
        self.assertIn("Traffic type category: 7", text)
        self.assertNotIn("PageValues", text)
        self.assertNotIn("Revenue", text)
        self.assertNotIn("99", text)

    def test_probability_uses_choice_confidence_when_needed(self) -> None:
        self.assertAlmostEqual(
            probability_from_answer({"choice": "No purchase", "confidence": 0.8}), 0.2
        )

    def test_perfect_calibration_has_zero_error(self) -> None:
        labels = np.array([0, 0, 1, 1])
        probabilities = np.array([0.0, 0.0, 1.0, 1.0])
        self.assertEqual(expected_calibration_error(labels, probabilities), 0.0)


if __name__ == "__main__":
    unittest.main()
