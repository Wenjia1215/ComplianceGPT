#!/usr/bin/env python3

from __future__ import annotations

import math
import unittest

from score_retest import cohens_kappa, jaccard, normalize_control, parse_id_set, summarize


class ScoreRetestTests(unittest.TestCase):
    def test_control_normalization(self) -> None:
        self.assertEqual(normalize_control("ac-02"), "AC-2")
        self.assertEqual(normalize_control("AC-2.03"), "AC-2(3)")
        self.assertEqual(normalize_control("AC-2(3)"), "AC-2(3)")

    def test_id_set_parsing(self) -> None:
        self.assertEqual(parse_id_set("NONE"), frozenset())
        self.assertEqual(parse_id_set("A\nb\nA"), frozenset({"a", "b"}))

    def test_empty_set_jaccard_is_one(self) -> None:
        self.assertEqual(jaccard(frozenset(), frozenset()), 1.0)

    def test_jaccard(self) -> None:
        self.assertEqual(
            jaccard(frozenset({"a", "b"}), frozenset({"b", "c"})),
            1 / 3,
        )

    def test_cohens_kappa(self) -> None:
        self.assertEqual(cohens_kappa(["A", "B"], ["A", "B"]), 1.0)
        self.assertTrue(
            math.isclose(
                cohens_kappa(["A", "A", "B", "B"], ["A", "B", "B", "B"]),
                0.5,
            )
        )

    def test_summary(self) -> None:
        rows = [
            {
                "original_control": "AC-1",
                "retest_control": "AC-1",
                "control_exact": True,
                "clause_set_exact": True,
                "clause_jaccard": 1.0,
                "odp_set_exact": True,
                "odp_jaccard": 1.0,
                "all_components_exact": True,
            },
            {
                "original_control": "AC-2",
                "retest_control": "AC-3",
                "control_exact": False,
                "clause_set_exact": False,
                "clause_jaccard": 0.5,
                "odp_set_exact": True,
                "odp_jaccard": 1.0,
                "all_components_exact": False,
            },
        ]
        result = summarize(rows)
        self.assertEqual(result["control_exact_count"], 1)
        self.assertEqual(result["clause_mean_jaccard"], 0.75)
        self.assertEqual(result["rows_with_any_disagreement"], 1)


if __name__ == "__main__":
    unittest.main()
