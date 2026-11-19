"""Tests of `scraftcam.gui.dimensions`: chains of dimensions."""

import unittest

from scraftcam.gui.dimensions import (
    ANGLE,
    HORIZONTAL,
    LENGTH,
    ORIGIN,
    VERTICAL,
    Y_AXIS,
    Dimension,
    Formula,
    _angle_way,
    difference,
    grouped,
    product,
    solve,
    total,
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
        # Its edges are all level or upright, so they carry the rest
        # (#100): corner 2 has corner 1's X.
        self.assertEqual(solution.missing(len(L_BRACKET)), [])
        self.assertEqual(str(solution.x[2]), "W")

    def test_level_edges(self) -> None:
        """A level edge's corners share Y, an upright one's X; a
        slanted edge carries nothing; a dimension saying again what an
        edge says is one too many (#100)."""
        slanted: list[tuple[float, float]] = [
            (0.0, 0.0),
            (6.0, 0.0),
            (5.0, 3.0),
        ]
        solution = solve(slanted, [Dimension("W", HORIZONTAL, ORIGIN, 1)])
        self.assertEqual(str(solution.y[1]), "0")
        self.assertNotIn(2, solution.x)
        box: list[tuple[float, float]] = [
            (1.0, 1.0),
            (6.0, 1.0),
            (6.0, 4.0),
            (1.0, 4.0),
        ]
        solution = solve(
            box,
            [
                Dimension("X", HORIZONTAL, ORIGIN, 0),
                Dimension("Y", VERTICAL, ORIGIN, 0),
                Dimension("W", HORIZONTAL, 0, 1),
                Dimension("H", VERTICAL, 1, 2),
                Dimension("Z", VERTICAL, ORIGIN, 1),
            ],
        )
        self.assertEqual(solution.missing(4), [])
        self.assertEqual(str(solution.y[3]), "Y + H")
        self.assertEqual(solution.extra, [4])

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

    def test_length(self) -> None:
        """A length from a known point fixes a corner known in one
        coordinate, on the side drawn; until then it waits."""
        triangle: list[tuple[float, float]] = [
            (0.0, 0.0),
            (4.0, 0.0),
            (1.0, 3.0),
        ]
        dimensions: list[Dimension] = [
            Dimension("S", LENGTH, 1, 2),
            Dimension("W", HORIZONTAL, ORIGIN, 1),
            Dimension("P", HORIZONTAL, ORIGIN, 2),
        ]
        solution = solve(triangle, dimensions)
        self.assertEqual(str(solution.x[2]), "P")
        self.assertEqual(str(solution.y[2]), "sqrt(S^2 - (P - W)^2)")
        self.assertEqual(solution.missing(3), [])
        below = [(0.0, 0.0), (4.0, 0.0), (1.0, -3.0)]
        self.assertEqual(
            str(solve(below, dimensions).y[2]), "-sqrt(S^2 - (P - W)^2)"
        )
        # Without P, corner 2 is known in neither coordinate: it waits.
        self.assertNotIn(2, solve(triangle, dimensions[:2]).y)

    def test_angle(self) -> None:
        """Half a drill point: an angle from the Y axis directs the tip
        edge, and the shoulder's X then gives its Y."""
        half: list[tuple[float, float]] = [
            (0.0, 0.0),
            (2.0, 1.2),
            (2.0, 8.0),
            (0.0, 8.0),
        ]
        dimensions: list[Dimension] = [
            Dimension("A", ANGLE, 0, Y_AXIS, rays=(1, 1)),
            Dimension("R", HORIZONTAL, ORIGIN, 1),
        ]
        solution = solve(half, dimensions)
        self.assertEqual(str(solution.x[1]), "R")
        self.assertIn("tan(90 deg - A)", str(solution.y[1]))
        self.assertIn(1, solution.y)
        self.assertNotIn(1, solve(half, dimensions[1:]).y)

        # The direction carried on to a second angle.
        ways: dict[int, str] = {Y_AXIS: "90 deg"}
        self.assertTrue(
            _angle_way(Dimension("B", ANGLE, Y_AXIS, 1, rays=(-1, 1)), ways)
        )
        self.assertEqual(ways[1], "90 deg + B + 180 deg")
        self.assertTrue(
            _angle_way(Dimension("C", ANGLE, Y_AXIS, 1, rays=(1, 1)), ways)
        )
        self.assertFalse(
            _angle_way(Dimension("D", ANGLE, 2, 3, rays=(1, 1)), ways)
        )

    def test_tidy(self) -> None:
        """Formulas are written without `0 +`, `- 0` or needless
        brackets (#81)."""
        self.assertEqual(total("0", "+", "R"), "R")
        self.assertEqual(total("R", "+", "0"), "R")
        self.assertEqual(total("0", "-", "W - T"), "-(W - T)")
        self.assertEqual(total("H", "-", "W - T"), "H - (W - T)")
        self.assertEqual(total("H", "+", "W - T"), "H + W - T")
        self.assertEqual(difference("R", "0"), "R")
        self.assertEqual(difference("W", "W"), "0")
        self.assertEqual(
            product("R", "tan(90 deg - A)"), "R * tan(90 deg - A)"
        )
        self.assertEqual(product("W - T", "2"), "(W - T) * 2")
        self.assertEqual(product("0", "tan(A)"), "0")
        self.assertEqual(grouped("sqrt(a) * b(c)"), "(sqrt(a) * b(c))")

        # The drill's shoulder (half a point from the Y axis).
        half: list[tuple[float, float]] = [
            (0.0, 0.0),
            (2.0, 1.2),
            (2.0, 8.0),
            (0.0, 8.0),
        ]
        solution = solve(
            half,
            [
                Dimension("A", ANGLE, 0, Y_AXIS, rays=(1, 1)),
                Dimension("R", HORIZONTAL, ORIGIN, 1),
            ],
        )
        self.assertEqual(str(solution.y[1]), "R * tan(90 deg - A)")

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
