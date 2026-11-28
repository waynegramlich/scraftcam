"""Tests of `scraftcam.gui.dimensions`: chains of dimensions."""

import unittest
from dataclasses import replace

from scraftcam.gui.dimensions import (
    ANGLE,
    DIAMETER,
    HORIZONTAL,
    LENGTH,
    ORIGIN,
    VERTICAL,
    X_AXIS,
    Y_AXIS,
    Dimension,
    Edge,
    Formula,
    Solution,
    _angle_way,
    difference,
    drawn_marks,
    grouped,
    is_mark,
    mark_edge,
    placement_problem,
    product,
    snapped,
    solve,
    tip_on_origin,
    total,
)
from tests.qt.shapes import HOUSE

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


# Function `marked()`:
def marked(
    points: list[tuple[float, float]], dimensions: list[Dimension]
) -> Solution:
    """Solve with the marks the drawing shows put first (as an old
    file is read, #233), the extras given by the dimensions' own
    indices."""
    marks: list[Dimension] = drawn_marks(points)
    solution: Solution = solve(points, marks + dimensions)
    solution.extra[:] = [
        index - len(marks) for index in solution.extra if index >= len(marks)
    ]
    return solution


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
        solution = marked(L_BRACKET, dimensions)
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
        solution = marked(slanted, [Dimension("W", HORIZONTAL, ORIGIN, 1)])
        self.assertEqual(str(solution.y[1]), "0")
        self.assertNotIn(2, solution.x)
        box: list[tuple[float, float]] = [
            (1.0, 1.0),
            (6.0, 1.0),
            (6.0, 4.0),
            (1.0, 4.0),
        ]
        solution = marked(
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
        solution = marked(L_BRACKET, [Dimension("H", VERTICAL, ORIGIN, 5)])
        self.assertEqual(str(solution.x[0]), "0")
        self.assertEqual(str(solution.y[0]), "0")
        self.assertEqual(str(solution.y[1]), "0")
        self.assertEqual(str(solution.x[5]), "0")
        self.assertNotIn(1, solution.x)
        self.assertEqual(solution.extra, [])
        self.assertEqual(str(solution.y[5]), "H")
        solution = marked(L_BRACKET, [Dimension("Z", VERTICAL, ORIGIN, 1)])
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
        solution = marked(triangle, dimensions)
        self.assertEqual(str(solution.x[2]), "P")
        self.assertEqual(str(solution.y[2]), "sqrt(S^2 - (P - W)^2)")
        self.assertEqual(solution.missing(3), [])
        below = [(0.0, 0.0), (4.0, 0.0), (1.0, -3.0)]
        self.assertEqual(
            str(marked(below, dimensions).y[2]), "-sqrt(S^2 - (P - W)^2)"
        )
        # Without P, corner 2 is known in neither coordinate: it waits.
        self.assertNotIn(2, marked(triangle, dimensions[:2]).y)

    def test_polygons(self) -> None:
        """An angle on a second polygon's edge, `V3-V5`, not the next
        corner in `points`, places its far corner (`T.sa~6.11` #797);
        taken as the next in `points` it is one too many instead."""
        # A 4 x 4 box from the origin, a roof on its top edge.
        house: list[tuple[float, float]] = list(HOUSE)
        loops: list[list[int]] = [[0, 1, 2, 3], [3, 2, 4]]
        dimensions: list[Dimension] = [
            Dimension("", VERTICAL, ORIGIN, 0),
            Dimension("", HORIZONTAL, ORIGIN, 0),
            Dimension("W", HORIZONTAL, ORIGIN, 1),
            Dimension("", HORIZONTAL, 1, 2),
            Dimension("H", VERTICAL, ORIGIN, 2),
            Dimension("", VERTICAL, 2, 3),
            Dimension("", VERTICAL, 0, 1),
            Dimension("", HORIZONTAL, 3, 0),
            Dimension("P", HORIZONTAL, ORIGIN, 4),
            Dimension("A", ANGLE, X_AXIS, 2, rays=(-1, 1), end_to=4),
        ]
        solution = solve(house, dimensions, loops)
        self.assertEqual(solution.missing(5), [])
        self.assertIn("tan(", str(solution.y[4]))
        self.assertEqual(solution.extra, [])
        dimensions[-1] = replace(dimensions[-1], end_to=-1)
        self.assertNotIn(4, solve(house, dimensions, loops).y)

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
        solution = marked(half, dimensions)
        self.assertEqual(str(solution.x[1]), "R")
        self.assertIn("tan(90 deg - A)", str(solution.y[1]))
        self.assertIn(1, solution.y)
        self.assertNotIn(1, marked(half, dimensions[1:]).y)

        # The direction carried on to a second angle; a third between
        # edges already directed is one too many (#230).
        ways: dict[Edge, str] = {(Y_AXIS, -1): "90 deg"}
        known: tuple[dict[int, Formula], dict[int, Formula]] = ({}, {})
        extra: list[int] = []

        # Function `way()`:
        def way(dimension: Dimension, index: int) -> bool:
            return _angle_way(half, dimension, ways, known, extra, index)

        self.assertTrue(way(Dimension("B", ANGLE, Y_AXIS, 1, rays=(-1, 1)), 0))
        self.assertEqual(ways[(1, 2)], "90 deg + B + 180 deg")
        self.assertEqual(ways[(2, 1)], "90 deg + B + 180 deg + 180 deg")
        self.assertEqual(extra, [])
        self.assertTrue(way(Dimension("C", ANGLE, Y_AXIS, 1, rays=(1, 1)), 1))
        self.assertEqual(extra, [1])
        self.assertFalse(way(Dimension("D", ANGLE, 2, 3, rays=(1, 1)), 2))

        # In full: an angle repeating what the corners say is extra.
        square: list[tuple[float, float]] = [
            (0.0, 0.0),
            (4.0, 0.0),
            (4.0, 4.0),
            (0.0, 4.0),
        ]
        given: list[Dimension] = [
            Dimension("W", HORIZONTAL, ORIGIN, 1),
            Dimension("H", VERTICAL, ORIGIN, 3),
            Dimension("A", ANGLE, 0, 1, rays=(-1, 1)),
        ]
        self.assertEqual(marked(square, given).extra, [2])

    def test_marks(self) -> None:
        """Nothing is guessed from the drawing; marks lock edges and
        corners, direct edges for angles, and an extra one shows
        (#233)."""
        square: list[tuple[float, float]] = [
            (0.0, 0.0),
            (4.0, 0.0),
            (4.0, 4.0),
            (0.0, 4.0),
        ]
        given: list[Dimension] = [
            Dimension("W", HORIZONTAL, ORIGIN, 1),
            Dimension("H", VERTICAL, ORIGIN, 3),
        ]
        self.assertEqual(
            solve(square, given).missing(4),
            [(0, "x"), (0, "y"), (1, "y"), (2, "x"), (2, "y"), (3, "x")],
        )
        marks: list[Dimension] = drawn_marks(square)
        self.assertTrue(all(is_mark(mark) for mark in marks))
        self.assertEqual(
            [mark_edge(mark, 4) for mark in marks],
            [None] * 4 + [(1, 2), (2, 3)],
        )
        self.assertEqual(solve(square, given + marks).missing(4), [])
        self.assertFalse(is_mark(given[0]))
        self.assertIsNone(mark_edge(given[0], 4))

        # A level edge directs a slanted one through an angle.
        slant: list[tuple[float, float]] = [
            (0.0, 0.0),
            (4.0, 0.0),
            (3.0, 2.0),
            (0.0, 2.0),
        ]
        dimensions: list[Dimension] = [
            Dimension("", VERTICAL, ORIGIN, 0),
            Dimension("", HORIZONTAL, ORIGIN, 0),
            Dimension("", VERTICAL, 0, 1),
            Dimension("W", HORIZONTAL, 0, 1),
            Dimension("A", ANGLE, 1, 0, rays=(1, -1)),
            Dimension("", VERTICAL, 2, 3),
            Dimension("", HORIZONTAL, ORIGIN, 3),
            Dimension("H", VERTICAL, ORIGIN, 3),
        ]
        solution: Solution = solve(slant, dimensions)
        self.assertEqual(solution.missing(4), [])
        self.assertIn("tan", str(solution.x[2]))
        self.assertEqual(solution.extra, [])
        # A second level mark on the bottom edge is one too many.
        twice: Solution = solve(slant, dimensions + [dimensions[2]])
        self.assertEqual(twice.extra, [len(dimensions)])

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
        solution = marked(
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
        solution = marked(L_BRACKET, dimensions)
        self.assertEqual(solution.extra, [2])
        self.assertEqual(str(solution.y[5]), "H")
        self.assertEqual(
            marked([(-2.0, -3.0)], [Dimension("D", VERTICAL, ORIGIN, 0)])
            .y[0]
            .terms,
            ((-1, "D"),),
        )


class TestDiameter(unittest.TestCase):
    """A revolved outline's diameter (`T.tfo~6.5` #437)."""

    def test_half_x(self) -> None:
        """A diameter gives its corner's X as half its letter, once."""
        points: list[tuple[float, float]] = [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 8.0),
            (0.0, 8.0),
        ]
        sizes: list[Dimension] = [
            *drawn_marks(points),
            Dimension("D", DIAMETER, ORIGIN, 1),
            Dimension("L", VERTICAL, ORIGIN, 2),
        ]
        solution: Solution = solve(points, sizes)
        self.assertEqual(str(solution.x[1]), "(D / 2)")
        self.assertEqual(str(solution.x[2]), "(D / 2)")
        self.assertEqual(str(solution.y[2]), "L")
        twice: Solution = solve(
            points, [*sizes, Dimension("E", DIAMETER, ORIGIN, 2)]
        )
        self.assertEqual(twice.extra, [len(sizes)])

    def test_across(self) -> None:
        """A horizontal across the axis, from one corner's mirror image
        to another corner, gives either X from the other (#479)."""
        points: list[tuple[float, float]] = [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 3.0),
            (1.0, 3.0),
            (1.0, 8.0),
            (0.0, 8.0),
        ]
        sizes: list[Dimension] = [
            *drawn_marks(points),
            Dimension("D", DIAMETER, ORIGIN, 1),
            Dimension("W", DIAMETER, 3, 2),
        ]
        solution: Solution = solve(points, sizes)
        self.assertEqual(str(solution.x[3]), "W - (D / 2)")
        self.assertEqual(str(solution.x[4]), "W - (D / 2)")

        # Known at its start instead; a second one is extra.
        sizes[-1] = Dimension("W", DIAMETER, 2, 3)
        self.assertEqual(str(solve(points, sizes).x[3]), "W - (D / 2)")
        twice: Solution = solve(
            points, [*sizes, Dimension("V", DIAMETER, 4, 1)]
        )
        self.assertEqual(twice.extra, [len(sizes)])


class TestPlacement(unittest.TestCase):
    """What keeps an outline from its real sizes (#445, #448)."""

    def test_problems(self) -> None:
        """Floating corners are named; a revolved tip must be on the
        origin."""
        points: list[tuple[float, float]] = [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 8.0),
            (0.0, 8.0),
        ]
        sizes: list[Dimension] = [
            Dimension("D", HORIZONTAL, ORIGIN, 1),
            Dimension("L", VERTICAL, ORIGIN, 2),
        ]
        self.assertIn(
            "Every corner floats", placement_problem(points, [], False)
        )
        self.assertIn(
            "Corners 0, 1, 2, 3 float", placement_problem(points, sizes, False)
        )
        with_marks: list[Dimension] = [*drawn_marks(points), *sizes]
        self.assertEqual(placement_problem(points, with_marks, False), "")
        self.assertTrue(tip_on_origin(with_marks))
        self.assertEqual(placement_problem(points, with_marks, True), "")
        self.assertIn(
            "tip goes on the origin", placement_problem(points, sizes, True)
        )


# Class `TestSnapped`:
class TestSnapped(unittest.TestCase):
    """`snapped()`: a dragged corner's snap and marks (#451)."""

    def marks(self, dimensions: list[Dimension]) -> set[tuple[str, int, int]]:
        """Return the marks, as (kind, start, end)."""
        return {
            (each.kind, each.start, each.end)
            for each in dimensions
            if is_mark(each)
        }

    def test_snaps_level_and_upright(self) -> None:
        """Dragged near its neighbors, corner 2 snaps and is marked."""
        points: list[tuple[float, float]] = list(L_BRACKET)
        points[2] = (6.05, 0.97)
        here: tuple[float, float]
        found: list[Dimension]
        here, found = snapped(points, [], 2, 0.1)
        self.assertEqual(here, (6.0, 1.0))
        self.assertEqual(
            self.marks(found), {(HORIZONTAL, 1, 2), (VERTICAL, 2, 3)}
        )

    def test_dragged_off(self) -> None:
        """Dragged away, the corner's marks go; others stay."""
        points: list[tuple[float, float]] = list(L_BRACKET)
        points[2] = (6.5, 1.5)
        old: list[Dimension] = [
            Dimension("", HORIZONTAL, 1, 2),
            Dimension("", VERTICAL, 2, 3),
            Dimension("", VERTICAL, 4, 5),
        ]
        here: tuple[float, float]
        found: list[Dimension]
        here, found = snapped(points, old, 2, 0.1)
        self.assertEqual(here, (6.5, 1.5))
        self.assertEqual(self.marks(found), {(VERTICAL, 4, 5)})

    def test_axis(self) -> None:
        """A corner dragged near the Y axis goes on it, marked."""
        points: list[tuple[float, float]] = list(L_BRACKET)
        points[3] = (0.03, 1.0)
        here: tuple[float, float]
        found: list[Dimension]
        here, found = snapped(points, [], 3, 0.1)
        self.assertEqual(here, (0.0, 1.0))
        self.assertIn((HORIZONTAL, ORIGIN, 3), self.marks(found))

    def test_not_onto_neighbor(self) -> None:
        """Snapping never puts a corner on a neighbor."""
        points: list[tuple[float, float]] = list(L_BRACKET)
        points[4] = (0.03, 4.0)
        here: tuple[float, float]
        here, _ = snapped(points, [], 4, 0.1)
        self.assertEqual(here, (0.03, 4.0))

    def test_lettered_angle(self) -> None:
        """An edge with a lettered angle is never marked."""
        points: list[tuple[float, float]] = list(L_BRACKET)
        angle: Dimension = Dimension("A", ANGLE, 1, Y_AXIS)
        found: list[Dimension]
        _, found = snapped(points, [angle], 2, 0.1)
        self.assertNotIn((HORIZONTAL, 1, 2), self.marks(found))
        self.assertIn((VERTICAL, 2, 3), self.marks(found))

    def test_one_too_many(self) -> None:
        """A mark the dimensions already give is left off."""
        points: list[tuple[float, float]] = [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 1.0),
        ]
        given: list[Dimension] = [
            Dimension("", VERTICAL, ORIGIN, 0),
            Dimension("", HORIZONTAL, ORIGIN, 0),
            Dimension("", VERTICAL, ORIGIN, 1),
            Dimension("", VERTICAL, 0, 1),
        ]
        found: list[Dimension]
        _, found = snapped(points, given, 1, 0.1)
        level: int = sum(
            1
            for each in found
            if is_mark(each)
            and each.kind == VERTICAL
            and 1 in (each.start, each.end)
        )
        self.assertEqual(level, 1)


if __name__ == "__main__":
    unittest.main()
