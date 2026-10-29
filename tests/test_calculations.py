import unittest

from backend.calculations import (
    attendance_percentage,
    classes_can_skip,
    classes_to_recover,
    summarize,
)


class TestSpecExamples(unittest.TestCase):
    def test_percentage_example(self):
        self.assertEqual(attendance_percentage(24, 30), 80.0)

    def test_percentage_when_no_classes(self):
        self.assertIsNone(attendance_percentage(0, 0))

    def test_skip_example(self):
        self.assertEqual(classes_can_skip(24, 30), 2)

    def test_recover_example(self):
        self.assertEqual(attendance_percentage(24, 40), 60.0)
        self.assertEqual(classes_to_recover(24, 40), 24)

    def test_exactly_75_percent(self):
        self.assertEqual(attendance_percentage(3, 4), 75.0)
        self.assertEqual(classes_can_skip(3, 4), 0)
        self.assertEqual(classes_to_recover(3, 4), 0)

    def test_below_75_cannot_skip(self):
        self.assertEqual(classes_can_skip(24, 40), 0)

    def test_above_75_needs_no_recovery(self):
        self.assertEqual(classes_to_recover(24, 30), 0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            attendance_percentage(5, 3)
        with self.assertRaises(ValueError):
            classes_can_skip(-1, 3)
        with self.assertRaises(ValueError):
            classes_to_recover(1, -1)


class TestBruteForce(unittest.TestCase):
    """Check the formulas against simple counting for every case up to 60 classes."""

    def test_skip_matches_counting(self):
        for conducted in range(0, 61):
            for attended in range(0, conducted + 1):
                k = 0
                if attended * 4 >= conducted * 3:
                    while attended * 4 >= (conducted + k + 1) * 3:
                        k += 1
                self.assertEqual(
                    classes_can_skip(attended, conducted), k,
                    f"skip wrong for {attended}/{conducted}",
                )

    def test_recover_matches_counting(self):
        for conducted in range(0, 61):
            for attended in range(0, conducted + 1):
                x = 0
                while (attended + x) * 4 < (conducted + x) * 3:
                    x += 1
                self.assertEqual(
                    classes_to_recover(attended, conducted), x,
                    f"recover wrong for {attended}/{conducted}",
                )


class TestSummary(unittest.TestCase):
    def test_no_classes(self):
        self.assertEqual(summarize(0, 0)["status"], "no_classes")

    def test_short(self):
        result = summarize(4, 6)
        self.assertEqual(result["status"], "short")
        self.assertEqual(result["classes_to_recover"], 2)

    def test_borderline(self):
        self.assertEqual(summarize(3, 4)["status"], "borderline")

    def test_safe(self):
        result = summarize(24, 30)
        self.assertEqual(result["status"], "safe")
        self.assertEqual(result["can_skip"], 2)


if __name__ == "__main__":
    unittest.main()