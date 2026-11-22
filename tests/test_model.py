"""Tests for `scraftcam.model`: lengths, angles, rotations, placements."""

import math
import unittest
from collections.abc import Sequence
from dataclasses import dataclass, field
from fractions import Fraction

from scraftcam.model import (
    ORIGIN,
    Angle,
    Length,
    NotSettledError,
    Placement,
    Rotation,
    SolidModel,
    Vector,
    meta,
    parse_number,
)


# Function `close()`:
def close(
    a: Sequence[float], b: Sequence[float], tolerance: float = 1e-12
) -> bool:
    """Return whether two vectors agree within `tolerance`."""
    return all(abs(p - q) <= tolerance for p, q in zip(a, b, strict=True))


# Class `TestLength`:
class TestLength(unittest.TestCase):
    """Lengths are exact, in their own units."""

    def test_parse_number(self) -> None:
        """Whole numbers, decimals, fractions and mixed fractions."""
        self.assertEqual(parse_number("3"), 3)
        self.assertEqual(parse_number("-3.875"), Fraction(-31, 8))
        self.assertEqual(parse_number("7/8"), Fraction(7, 8))
        self.assertEqual(parse_number("3-7/8"), Fraction(31, 8))
        self.assertEqual(parse_number("3 7/8"), Fraction(31, 8))
        self.assertEqual(parse_number("-1-1/2"), Fraction(-3, 2))
        self.assertEqual(parse_number(".5"), Fraction(1, 2))
        with self.assertRaises(ValueError):
            parse_number("3-")
        with self.assertRaises(ValueError):
            parse_number("abc")

    def test_parse_and_text(self) -> None:
        """Lengths read and write the way people write them."""
        self.assertEqual(str(Length.parse("3-7/8 in")), "3-7/8 in")
        self.assertEqual(str(Length.parse("3.875 in")), "3-7/8 in")
        self.assertEqual(str(Length.parse("20 mm")), "20 mm")
        self.assertEqual(str(Length.parse("0.1 in")), "0.1 in")
        self.assertEqual(str(Length.parse("-1/2 in")), "-1/2 in")
        self.assertEqual(str(Length(Fraction(1, 3), "mm")), "0.333333333 mm")
        with self.assertRaises(ValueError):
            Length.parse("20")
        with self.assertRaises(ValueError):
            Length.parse("20 yd")

    def test_exact_conversion(self) -> None:
        """Inches and millimeters convert both ways exactly."""
        inches: Length = Length.parse("3-7/8 in")
        self.assertEqual(inches.to("mm").value, Fraction("98.425"))
        self.assertEqual(inches.to("mm").to("in").value, Fraction(31, 8))
        self.assertEqual(Length.parse("1 ft"), Length.parse("12 in"))
        self.assertEqual(Length.parse("1 in"), Length.parse("25.4 mm"))
        self.assertLess(Length.parse("1 in"), Length.parse("26 mm"))

    def test_arithmetic(self) -> None:
        """Sums take the left unit; numbers keep it."""
        total: Length = Length.parse("1 in") + Length.parse("25.4 mm")
        self.assertEqual(str(total), "2 in")
        self.assertEqual(str(Length.parse("1 in") * 3), "3 in")
        self.assertEqual(str(Length.parse("3 in") / 4), "3/4 in")
        self.assertEqual(str(-Length.parse("3 in")), "-3 in")

    def test_solidcraft(self) -> None:
        """Mixed fractions are sent with parentheses."""
        self.assertEqual(Length.parse("3-7/8 in").solidcraft(), "(3 + 7/8) in")
        self.assertEqual(
            Length.parse("-3-7/8 in").solidcraft(), "-(3 + 7/8) in"
        )
        self.assertEqual(Length.parse("7/8 in").solidcraft(), "(7/8) in")
        self.assertEqual(Length.parse("20 mm").solidcraft(), "20 mm")


# Class `TestAngle`:
class TestAngle(unittest.TestCase):
    """Angles are in degrees."""

    def test_parse(self) -> None:
        """Degrees by default; radians converted with 9 decimals."""
        self.assertEqual(Angle.parse("30").degrees, 30)
        self.assertEqual(str(Angle.parse("22.5 deg")), "22.5 deg")
        self.assertEqual(
            Angle.parse(f"{math.pi / 2} rad").degrees, Fraction(90)
        )
        self.assertEqual(
            Angle.parse("1 rad").degrees, Fraction("57.295779513")
        )


# Class `TestRotation`:
class TestRotation(unittest.TestCase):
    """Rotations are unit quaternions."""

    def test_about(self) -> None:
        """A quarter turn about Z takes X to Y."""
        quarter: Rotation = Rotation.about((0, 0, 1), Angle(Fraction(90)))
        self.assertTrue(close(quarter.apply((1, 0, 0)), (0, 1, 0)))
        self.assertTrue(close(quarter.inverse().apply((0, 1, 0)), (1, 0, 0)))

    def test_pointing(self) -> None:
        """`pointing()` turns one direction onto another."""
        cases: tuple[tuple[Vector, Vector], ...] = (
            ((0, 0, 1), (1, 0, 0)),
            ((0, 0, 1), (0, 0, 1)),
            ((0, 0, 1), (0, 0, -1)),
            ((1, 0, 0), (-1, 0, 0)),
            ((1, 2, 3), (-3, 1, 2)),
        )
        axis: Vector
        toward: Vector
        for axis, toward in cases:
            size: float = math.hypot(*toward)
            unit: Vector = (
                toward[0] / size,
                toward[1] / size,
                toward[2] / size,
            )
            size = math.hypot(*axis)
            turned: Vector = Rotation.pointing(axis, toward).apply(
                (axis[0] / size, axis[1] / size, axis[2] / size)
            )
            self.assertTrue(close(turned, unit), (axis, toward))

    def test_xyzw_order(self) -> None:
        """The constructor takes ROS order; both orders come back."""
        half: float = math.sqrt(0.5)
        quarter: Rotation = Rotation(0.0, 0.0, half, half)
        expected: Rotation = Rotation.about((0, 0, 1), Angle(Fraction(90)))
        self.assertTrue(close(quarter.xyzw(), expected.xyzw()))
        self.assertTrue(close(quarter.wxyz(), (half, 0.0, 0.0, half)))
        self.assertEqual(Rotation().xyzw(), (0.0, 0.0, 0.0, 1.0))
        placement: Placement = Placement(ORIGIN, quarter)
        self.assertEqual(placement.xyzw(), quarter.xyzw())
        self.assertEqual(placement.wxyz(), quarter.wxyz())

    def test_long_chain(self) -> None:
        """3600 tenth-degree turns come back to where they started."""
        step: Rotation = Rotation.about((1, 2, 3), Angle(Fraction(1, 10)))
        total: Rotation = Rotation()
        for _ in range(3600):
            total = step * total
        self.assertTrue(close(total.apply((1, 0, 0)), (1, 0, 0), 1e-9))

    def test_rows_are_rigid(self) -> None:
        """The matrix is orthonormal far inside SolidCraft's 1e-9."""
        rotation: Rotation = Rotation.about((1, -2, 5), Angle(Fraction(37)))
        rows: tuple[Vector, Vector, Vector] = rotation.rows()
        i: int
        j: int
        for i in range(3):
            for j in range(3):
                dot: float = sum(rows[k][i] * rows[k][j] for k in range(3))
                self.assertAlmostEqual(dot, 1.0 if i == j else 0.0, 14)


# Class `TestPlacement`:
class TestPlacement(unittest.TestCase):
    """Placements compose, invert, and make SolidCraft's matrix."""

    def test_matrix_matches_solidcraft(self) -> None:
        """The matrix tried in SolidCraft (`T.cmt~5.3` #45)."""
        placement: Placement = Placement(
            (
                Length.parse("100 mm"),
                Length.parse("0 mm"),
                Length.parse("0 mm"),
            ),
            Rotation.about((0, 0, 1), Angle(Fraction(90))),
        )
        expected: tuple[Vector, ...] = ((0, -1, 0), (1, 0, 0), (0, 0, 1))
        row: tuple[float, float, float, float]
        for row, rotation in zip(placement.matrix(), expected, strict=True):
            self.assertTrue(close(row[:3], rotation))
        self.assertEqual(placement.matrix()[0][3], 100.0)

    def test_compose_inverse_delta(self) -> None:
        """`delta()` is the move that takes the old placement to the new."""
        old: Placement = Placement(
            (
                Length.parse("1 in"),
                Length.parse("2 mm"),
                Length.parse("-3 mm"),
            ),
            Rotation.about((1, 1, 0), Angle(Fraction(30))),
        )
        new: Placement = Placement(
            (
                Length.parse("-4 mm"),
                Length.parse("1/2 in"),
                Length.parse("7 mm"),
            ),
            Rotation.about((0, 1, 1), Angle(Fraction(-75))),
        )
        delta: Placement = new.delta(old)
        moved: Placement = delta.compose(old)
        self.assertTrue(close(moved.mm(), new.mm(), 1e-8))
        point: Vector = (3.0, -1.0, 2.0)
        self.assertTrue(
            close(moved.rotation.apply(point), new.rotation.apply(point))
        )
        identity: Placement = old.compose(old.inverse())
        self.assertTrue(close(identity.mm(), (0, 0, 0), 1e-8))


# Class `Halver`:
# Test models are settled, never built, so `build()` is not given.
@dataclass(slots=True)
# pylint: disable-next=abstract-method
class Halver(SolidModel):
    """A child whose result moves half way to its target each pass.

    Attributes:
    * `target` (`Length`): Where `reach` heads.
    * `reach` (`Length`): A result: half way from itself to `target`.

    Constructor:
    * `Halver(target)`
    """

    # Constructor arguments:
    target: Length = field(
        default=Length(2, "in"),
        metadata=meta("length", "Target", "Where the result heads."),
    )

    # Results (alphabetized):
    reach: Length = field(init=False, default=Length(0, "in"))

    def update(self) -> None:
        """Move `reach` half way to `target`."""
        self.reach = Length.from_mm(
            (self.reach.mm() + self.target.mm()) / 2.0, "in"
        )


# Class `Pair`:
# Test models are settled, never built, so `build()` is not given.
@dataclass(slots=True)
# pylint: disable-next=abstract-method
class Pair(SolidModel):
    """A parent that sets its child's target and reads its result.

    Attributes:
    * `gap` (`Length`): Added to the child's result.
    * `child` (`Halver`): The child.
    * `total` (`Length`): A result: the child's reach plus `gap`.

    Constructor:
    * `Pair(gap, child)`
    """

    # Constructor arguments:
    gap: Length = field(
        default=Length(1, "in"),
        metadata=meta("length", "Gap", "Added to the child's reach."),
    )
    child: Halver = field(default_factory=Halver)

    # Results (alphabetized):
    total: Length = field(init=False, default=Length(0, "in"))

    def update(self) -> None:
        """Set the child, update it, and read its result."""
        self.child.target = self.gap * 3
        self.child.update()
        self.total = self.child.reach + self.gap


# Class `Runaway`:
# Test models are settled, never built, so `build()` is not given.
@dataclass(slots=True)
# pylint: disable-next=abstract-method
class Runaway(SolidModel):
    """A model that never settles: its result doubles each pass.

    Attributes:
    * `size` (`float`): A result that doubles.

    Constructor:
    * `Runaway()`
    """

    # Results (alphabetized):
    size: float = field(init=False, default=1.0)

    def __post_init__(self) -> None:
        """Do not settle when made, so the test can."""

    def update(self) -> None:
        """Double `size`."""
        self.size *= 2.0


# Class `TestSolidModel`:
class TestSolidModel(unittest.TestCase):
    """Models settle by passes, parents setting their children."""

    def test_settles(self) -> None:
        """Made or edited, the results settle."""
        pair: Pair = Pair()
        self.assertTrue(abs(pair.total.mm() - 4 * 25.4) < 1e-6)
        pair.gap = Length(10, "mm")
        passes: int = pair.settle()
        self.assertGreater(passes, 2)
        self.assertTrue(abs(pair.total.mm() - 40.0) < 1e-6)

    def test_paths(self) -> None:
        """Parameters and results are named by dotted paths."""
        pair: Pair = Pair()
        self.assertEqual(
            [path for path, _ in pair.parameters()], ["gap", "child.target"]
        )
        self.assertEqual(
            sorted(path for path, _ in pair.results()),
            ["child.reach", "total"],
        )
        names: list[str] = [each.name for each in pair.parameter_fields()]
        self.assertEqual(names, ["gap", "child"])

    def test_wall_clock_limit(self) -> None:
        """A model that never settles is stopped and reported."""
        with self.assertRaises(NotSettledError) as caught:
            Runaway().settle(seconds=0.05)
        self.assertIn("size", caught.exception.moving)
        self.assertGreater(caught.exception.passes, 1)

    def test_meta(self) -> None:
        """Unknown kinds of value are refused."""
        self.assertFalse(meta("count", "Holes", "How many.")["shape"])
        with self.assertRaises(ValueError):
            meta("weight", "Mass", "How heavy.")


if __name__ == "__main__":
    unittest.main()
