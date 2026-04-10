from __future__ import annotations

import unittest

from vibe_check.scoring import score_to_grade, compute_overall
from vibe_check._types import CategoryScore


class TestScoreToGrade(unittest.TestCase):
    def test_grade_a_plus(self):
        self.assertEqual(score_to_grade(97), "A+")
        self.assertEqual(score_to_grade(100), "A+")

    def test_grade_a(self):
        self.assertEqual(score_to_grade(93), "A")
        self.assertEqual(score_to_grade(96.9), "A")

    def test_grade_a_minus(self):
        self.assertEqual(score_to_grade(90), "A-")
        self.assertEqual(score_to_grade(92.9), "A-")

    def test_grade_b_plus(self):
        self.assertEqual(score_to_grade(87), "B+")
        self.assertEqual(score_to_grade(89.9), "B+")

    def test_grade_b(self):
        self.assertEqual(score_to_grade(83), "B")
        self.assertEqual(score_to_grade(86.9), "B")

    def test_grade_b_minus(self):
        self.assertEqual(score_to_grade(80), "B-")
        self.assertEqual(score_to_grade(82.9), "B-")

    def test_grade_c_plus(self):
        self.assertEqual(score_to_grade(77), "C+")
        self.assertEqual(score_to_grade(79.9), "C+")

    def test_grade_c(self):
        self.assertEqual(score_to_grade(73), "C")
        self.assertEqual(score_to_grade(76.9), "C")

    def test_grade_c_minus(self):
        self.assertEqual(score_to_grade(70), "C-")
        self.assertEqual(score_to_grade(72.9), "C-")

    def test_grade_d_plus(self):
        self.assertEqual(score_to_grade(67), "D+")
        self.assertEqual(score_to_grade(69.9), "D+")

    def test_grade_d(self):
        self.assertEqual(score_to_grade(63), "D")
        self.assertEqual(score_to_grade(66.9), "D")

    def test_grade_d_minus(self):
        self.assertEqual(score_to_grade(60), "D-")
        self.assertEqual(score_to_grade(62.9), "D-")

    def test_grade_f(self):
        self.assertEqual(score_to_grade(59.9), "F")
        self.assertEqual(score_to_grade(0), "F")

    def test_edge_zero(self):
        self.assertEqual(score_to_grade(0), "F")

    def test_edge_100(self):
        self.assertEqual(score_to_grade(100), "A+")

    def test_edge_50(self):
        self.assertEqual(score_to_grade(50), "F")

    def test_negative(self):
        self.assertEqual(score_to_grade(-10), "F")


class TestComputeOverall(unittest.TestCase):
    def _make_cats(self, **kwargs: float) -> list[CategoryScore]:
        name_map = {
            "quality": "Code Quality",
            "security": "Security",
            "dependencies": "Dependencies",
            "testing": "Testing",
        }
        cats = []
        for key, score in kwargs.items():
            cats.append(CategoryScore(name=name_map.get(key, key), score=score, grade=score_to_grade(score)))
        return cats

    def test_all_perfect(self):
        cats = self._make_cats(quality=100, security=100, dependencies=100, testing=100)
        score, grade = compute_overall(cats)
        self.assertEqual(score, 100.0)
        self.assertEqual(grade, "A+")

    def test_all_zero(self):
        cats = self._make_cats(quality=0, security=0, dependencies=0, testing=0)
        score, grade = compute_overall(cats)
        self.assertEqual(score, 0.0)
        self.assertEqual(grade, "F")

    def test_weighted_average(self):
        # Default weights: security=0.30, quality=0.25, deps=0.20, testing=0.25
        cats = self._make_cats(quality=80, security=90, dependencies=70, testing=60)
        score, grade = compute_overall(cats)
        expected = (80 * 0.25 + 90 * 0.30 + 70 * 0.20 + 60 * 0.25)
        self.assertAlmostEqual(score, round(expected, 1), places=1)

    def test_custom_weights(self):
        cats = self._make_cats(quality=100, security=0, dependencies=100, testing=100)
        weights = {"quality": 1.0, "security": 0.0, "dependencies": 0.0, "testing": 0.0}
        score, grade = compute_overall(cats, weights=weights)
        self.assertEqual(score, 100.0)

    def test_empty_categories(self):
        score, grade = compute_overall([])
        self.assertEqual(score, 0.0)
        self.assertEqual(grade, "F")


if __name__ == "__main__":
    unittest.main()
