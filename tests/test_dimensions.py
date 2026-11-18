"""Tests of `scraftcam.gui.dimensions`: chains of dimensions."""

import unittest

from scraftcam.gui.dimensions import (
    HORIZONTAL,
    ORIGIN,
    VERTICAL,
    Dimension,
    Formula,
    solve,
)

# An L bracket, counterclockwise from the origin: W wide, H high, its
# leg T thick.
L_BRACKET: list[tuple[float, float]] = [
    (0.0, 0.0),
    (6.0, 0.0),
    (6.0, 1.0),
    (1.0, 1.0),
    (1.0, 4.0),
    (0.0, 4.0),
]


class DimensionsTest(unittest.TestCase):
    """Formulas from chains, missing and extra dimensions."""

    def test_formula_text(self) -> None:
        """Formulas read as people write them."""
        self.assertEqual(str(Formula()), "0")
        self.assertEqual(str(Formula().plus(-1, "W")), "-W")
        self.assertEqual(
            str(Formula().plus(1, "W").plus(-1, "T").plus(1, "A")),
            "W - T + A",
        )

    def test_l_bracket(self) -> None:
        """Every corner of the L is reached, with the right signs."""
        dimensions: list[Dimension] = [
            Dimension("W", HORIZONTAL, ORIGIN, 1),
            Dimension("T", HORIZONTAL, 1, 3),
            Dimension("T", VERTICAL, ORIGIN, 2),
            Dimension("H", VERTICAL, 2, 4),
        ]
        solution = solve(L_BRACKET, dimensions)
        self.assertEqual(str(solution.x[1]), "W")
        self.assertEqual(solution.extra, [])
        self.assertEqual(str(solution.x[3]), "W - T")
        self.assertEqual(str(solution.y[2]), "T")
        self.assertEqual(str(solution.y[4]), "T + H")
        missing = solution.missing(len(L_BRACKET))
        self.assertIn((2, "x"), missing)
        self.assertNotIn((3, "x"), missing)

    def test_on_axis(self) -> None:
        """A corner on an axis has that coordinate 0 (the one at the
        origin both), and a dimension to it is one too many."""
        solution = solve(L_BRACKET, [Dimension("H", VERTICAL, ORIGIN, 5)])
        self.assertEqual(str(solution.x[0]), "0")
        self.assertEqual(str(solution.y[0]), "0")
        self.assertEqual(str(solution.y[1]), "0")
        self.assertEqual(str(solution.x[5]), "0")
        self.assertNotIn(1, solution.x)
        self.assertEqual(solution.extra, [])
        self.assertEqual(str(solution.y[5]), "H")
        solution = solve(L_BRACKET, [Dimension("Z", VERTICAL, ORIGIN, 1)])
        self.assertEqual(solution.extra, [0])

    def test_extra(self) -> None:
        """A second way to the same point is one too many."""
        dimensions: list[Dimension] = [
            Dimension("W", HORIZONTAL, ORIGIN, 1),
            Dimension("A", HORIZONTAL, ORIGIN, 3),
            Dimension("B", HORIZONTAL, 3, 1),
            Dimension("H", VERTICAL, 5, ORIGIN),
        ]
        solution = solve(L_BRACKET, dimensions)
        self.assertEqual(solution.extra, [2])
        self.assertEqual(str(solution.y[5]), "H")
        self.assertEqual(
            solve([(-2.0, -3.0)], [Dimension("D", VERTICAL, ORIGIN, 0)])
            .y[0]
            .terms,
            ((-1, "D"),),
        )


if __name__ == "__main__":
    unittest.main()
