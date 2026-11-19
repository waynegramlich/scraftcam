"""Tests of `scraftcam.gui.values`: real sizes and fillet fits."""

import math
import unittest

from scraftcam.gui.dimensions import (
    HORIZONTAL,
    ORIGIN,
    RADIUS,
    VERTICAL,
    Dimension,
)
from scraftcam.gui.letters import Letter
from scraftcam.gui.values import (
    evaluate,
    fillet_problems,
    letter_values,
    real_corners,
)

# A plate W by H from the origin, its top corners rounded.
PLATE: list[tuple[float, float]] = [
    (0.0, 0.0),
    (6.0, 0.0),
    (6.0, 4.0),
    (0.0, 4.0),
]
SIZES: list[Dimension] = [
    Dimension("W", HORIZONTAL, ORIGIN, 1),
    Dimension("H", VERTICAL, ORIGIN, 2),
    Dimension("R", RADIUS, 2, 2),
    Dimension("UDF", RADIUS, 3, 3),
]


def letters(radius: str, note: str = "1/16 in") -> list[Letter]:
    """Return the plate's letters, 1 in by 1/2 in, with two radii."""
    return [
        Letter("W", "", "1 in", ""),
        Letter("H", "", "1/2 in", ""),
        Letter("R", "", radius, ""),
        Letter("UDF", "", note, ""),
    ]


class ValuesTest(unittest.TestCase):
    """Formulas worked out; fillets checked against their edges."""

    def test_evaluate(self) -> None:
        """Numbers, letters, units and functions; nothing else."""
        values: dict[str, float] = {"R": 2.0, "A": math.radians(59)}
        self.assertAlmostEqual(evaluate("R", values), 2.0)
        self.assertAlmostEqual(
            evaluate("0 + ((R) - (0)) * tan(90 deg - A)", values),
            2.0 * math.tan(math.radians(31)),
        )
        self.assertAlmostEqual(evaluate("sqrt(R^2 + 0 mm)", values), 2.0)
        self.assertAlmostEqual(evaluate("-R / 4", values), -0.5)
        for bad in ("Q", "R.real", "__import__('os')", "R +", "R / 0"):
            with self.assertRaises(ValueError):
                evaluate(bad, values)

    def test_values(self) -> None:
        """Lengths in millimeters, angles in radians; bad ones left
        out."""
        values: dict[str, float] = letter_values(
            [
                Letter("W", "", "1 in", ""),
                Letter("A", "", "90 deg", ""),
                Letter("B", "", "oops", ""),
            ]
        )
        self.assertAlmostEqual(values["W"], 25.4)
        self.assertAlmostEqual(values["A"], math.pi / 2)
        self.assertNotIn("B", values)

    def test_fillets(self) -> None:
        """A fillet fits, uses its edge up, or is too big (#127)."""
        corners = real_corners(PLATE, letters("1/8 in"), SIZES)
        assert corners is not None
        self.assertAlmostEqual(corners[2][0], 25.4)
        self.assertAlmostEqual(corners[2][1], 12.7)
        self.assertEqual(fillet_problems(PLATE, letters("1/8 in"), SIZES), {})

        # The side and the top used up exactly: allowed (#114).
        self.assertEqual(
            fillet_problems(PLATE, letters("1/2 in", "1/2 in"), SIZES), {}
        )

        # Too big for the side (1/2 in): both ends named, in inches.
        problems: dict[int, str] = fillet_problems(
            PLATE, letters("5/8 in"), SIZES
        )
        self.assertEqual(sorted(problems), [2])
        self.assertIn("R need 5/8 in of a 1/2 in edge", problems[2])
        problems = fillet_problems(PLATE, letters("1/2 in", "5/8 in"), SIZES)
        self.assertIn("R and UDF need", problems[2])
        self.assertEqual(problems[2], problems[3])

        # Not worked out while a corner floats or a value is bad.
        self.assertEqual(
            fillet_problems(PLATE, letters("2 in"), SIZES[1:]), {}
        )
        self.assertIsNone(real_corners(PLATE, letters("x"), SIZES[1:]))


if __name__ == "__main__":
    unittest.main()
