"""Tests of `scraftcam.gui.values`: real sizes and fillet fits."""

import math
import unittest

from scraftcam.gui.dimensions import (
    HORIZONTAL,
    ORIGIN,
    RADIUS,
    VERTICAL,
    Dimension,
    drawn_marks,
)
from scraftcam.gui.letters import Letter
from scraftcam.gui.values import (
    evaluate,
    fillet_problems,
    first_scale,
    formula_problem,
    letter_values,
    letters_bad,
    placed_corners,
    real_corners,
    refresh_formulas,
)

# A plate W by H from the origin, its top corners rounded.
PLATE: list[tuple[float, float]] = [
    (0.0, 0.0),
    (6.0, 0.0),
    (6.0, 4.0),
    (0.0, 4.0),
]
# Its marks (#233) first, then its dimensions.
SIZES: list[Dimension] = drawn_marks(PLATE) + [
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

    def test_placed_corners(self) -> None:
        """Corners follow the values, to the middle scale (#299)."""
        placed: list[tuple[float, float]]
        scale: float
        placed, scale = placed_corners(PLATE, letters("1/8 in"), SIZES)
        self.assertAlmostEqual(scale, 4.0 / 12.7)
        self.assertAlmostEqual(placed[2][0], 2.0 * placed[2][1])
        self.assertEqual(placed[0], (0.0, 0.0))
        self.assertIsNot(placed, PLATE)

        # A scale given is kept; none found leaves the corners.
        placed, scale = placed_corners(PLATE, letters("1/8 in"), SIZES, 1.0)
        self.assertEqual(scale, 1.0)
        self.assertAlmostEqual(placed[2][0], 25.4)
        self.assertEqual(placed_corners(PLATE, [], [])[0], PLATE)
        self.assertEqual(first_scale(PLATE, ({}, {})), 0.0)

    def test_letters_bad(self) -> None:
        """A used letter with a bad value keeps the drawing (#154)."""
        bad: list[Letter] = letters("1/8 in")
        self.assertFalse(letters_bad(bad, SIZES))
        bad[0] = Letter("W", "", "30 deg", "")
        self.assertTrue(letters_bad(bad, SIZES))
        self.assertEqual(placed_corners(PLATE, bad, SIZES), (PLATE, 0.0))


# A drill's letters: two given values, two worked out (#430).
def drill() -> list[Letter]:
    """Return a drill's letters, with `HPA` and `R` from formulas."""
    return [
        Letter("D", "Diameter", "1/8 in"),
        Letter("PA", "Point angle", "135 deg"),
        Letter("HPA", "Half point angle", formula="PA / 2"),
        Letter("R", "Radius", formula="D / 2"),
    ]


class TestFormulas(unittest.TestCase):
    """Letters worked out from other letters (`T.tfo~6.5` #430)."""

    def test_values(self) -> None:
        """Formula letters are worked out exactly."""
        values: dict[str, float] = letter_values(drill())
        self.assertAlmostEqual(values["HPA"], math.radians(67.5))
        self.assertAlmostEqual(values["R"], 25.4 / 16.0)

    def test_refresh(self) -> None:
        """Each formula letter's `default` shows its value."""
        found: list[Letter] = drill()
        refresh_formulas(found)
        self.assertEqual(found[2].default, "67.5 deg")
        self.assertEqual(found[3].default, "0.0625 in")

    def test_problems(self) -> None:
        """Unknown names, formula letters and bad values are refused."""
        found: list[Letter] = drill()
        self.assertEqual(formula_problem(found, 0), "")
        self.assertEqual(formula_problem(found, 2), "")
        found[2].formula = "Q / 2"
        self.assertIn("no letter Q", formula_problem(found, 2))
        found[2].formula = "R / 2"
        self.assertIn("formula letter too", formula_problem(found, 2))
        found[2].formula = "2"
        self.assertIn("names no letter", formula_problem(found, 2))
        found[2].formula = "PA / (D - D)"
        self.assertNotEqual(formula_problem(found, 2), "")
        refresh_formulas(found)
        self.assertEqual(found[2].default, "")
        self.assertNotIn("HPA", letter_values(found))


if __name__ == "__main__":
    unittest.main()
