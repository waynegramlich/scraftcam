"""Tests for `scraftcam.outline`: profiles checked, then drawn live.

The SolidCraft test runs a headless `solidcraft-cli`, and is skipped
when there is none.
"""

import math
import shutil
import unittest
from typing import cast

from scraftcam.geometry import (
    ArcSegment,
    Corner,
    LineSegment,
    Loop,
    RoundedPolygon,
)
from scraftcam.outline import (
    Profile,
    add_parameters,
    send_changes,
)
from scraftcam.pybind.scraftpybind import JSON, PyBind, connect

HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None


def rounded_rect(
    x0: float, y0: float, x1: float, y1: float, radius: float
) -> Loop:
    """Return a rectangle with its corners rounded alike.

    Arguments:
    * `x0` (`float`): Low X.
    * `y0` (`float`): Low Y.
    * `x1` (`float`): High X.
    * `y1` (`float`): High Y.
    * `radius` (`float`): Each corner's radius.

    Returns:
    * (`Loop`): The rectangle, counter-clockwise.
    """
    corners: list[Corner] = [
        Corner(x0, y0, radius),
        Corner(x1, y0, radius),
        Corner(x1, y1, radius),
        Corner(x0, y1, radius),
    ]
    return Loop.from_poly(RoundedPolygon("rect", corners, 0.0, 1.0))


def square_hole(x: float, y: float) -> Loop:
    """Return a 10 x 10 hole with corners of radius 2, at `x, y`.

    Arguments:
    * `x` (`float`): Its low X.
    * `y` (`float`): Its low Y.

    Returns:
    * (`Loop`): The hole.
    """
    return rounded_rect(x, y, x + 10.0, y + 10.0, 2.0)


# Class `FakeParameters`:
# It stands in for the one method the code under test calls.
class FakeParameters:  # pylint: disable=too-few-public-methods
    """Records `parameters.change` calls in place of SolidCraft.

    Attributes:
    * `calls` (`list[dict[str, JSON]]`): The changes sent, in order.
    """

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[dict[str, JSON]] = []

    def change(self, *, changes: dict[str, JSON]) -> JSON:
        """Record one change.

        Arguments:
        * `changes` (`dict[str, JSON]`): The values sent.

        Returns:
        * (`JSON`): No errors.
        """
        self.calls.append(changes)
        return {"errors": []}


# Class `FakeSolidCraft`:
# It stands in for `PyBind`'s one namespace the code under test uses.
class FakeSolidCraft:  # pylint: disable=too-few-public-methods
    """Stands in for `PyBind` with only its parameters.

    Attributes:
    * `parameters` (`FakeParameters`): The recorder.
    """

    def __init__(self) -> None:
        """Start a recorder."""
        self.parameters: FakeParameters = FakeParameters()


# Class `TestChecks`:
class TestChecks(unittest.TestCase):
    """The checks SolidCraft does not make for us."""

    outer: Loop = rounded_rect(0.0, 0.0, 60.0, 40.0, 5.0)

    def test_good(self) -> None:
        """A rounded rectangle with two holes is taken."""
        profile: Profile = Profile(
            "plate", self.outer, [square_hole(10, 15), square_hole(40, 15)]
        )
        self.assertEqual(profile.structure(), ("lalalala",) * 3)
        values: dict[str, str] = profile.values("plate")
        self.assertEqual(values["plate__l0__p0x"], "5.0 mm")
        self.assertEqual(values["plate__l0__c1y"], "5.0 mm")
        self.assertEqual(len(values), 3 * (8 + 4) * 2)

    def test_full_circle(self) -> None:
        """One arc all the way round is a loop."""
        circle: ArcSegment = ArcSegment(
            (10.0, 0.0), (10.0, 0.0), (0.0, 0.0), 10.0, 2.0 * math.pi
        )
        profile: Profile = Profile("disk", Loop("disk", (circle,)))
        self.assertEqual(profile.structure(), ("a",))

    def test_crossing(self) -> None:
        """A bow tie is refused (SolidCraft fills it)."""
        points: list[tuple[float, float]] = [
            (0, 0),
            (50, 0),
            (-10, 30),
            (0, 30),
        ]
        lines: tuple[LineSegment, ...] = tuple(
            LineSegment(points[index], points[(index + 1) % 4])
            for index in range(4)
        )
        with self.assertRaisesRegex(ValueError, "cross"):
            Profile("bow", Loop("bow", lines))

    def test_gap_and_short(self) -> None:
        """A gap, a segment too short and an arc off its circle."""
        square: list[tuple[float, float]] = [
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 10),
        ]
        lines: list[LineSegment] = [
            LineSegment(square[index], square[(index + 1) % 4])
            for index in range(4)
        ]
        gap: list[LineSegment] = [*lines[:3], LineSegment((0, 10), (0, 1))]
        with self.assertRaisesRegex(ValueError, "gap"):
            Profile("gap", Loop("gap", tuple(gap)))
        short: list[LineSegment] = [
            *lines[:3],
            LineSegment((0, 10), (0, 1e-7)),
            LineSegment((0, 1e-7), (0, 0)),
        ]
        with self.assertRaisesRegex(ValueError, "long"):
            Profile("short", Loop("short", tuple(short)))
        off: ArcSegment = ArcSegment(
            (10.0, 0.0), (-10.001, 0.0), (0.0, 0.0), 10.0, math.pi
        )
        with self.assertRaisesRegex(ValueError, "off its circle"):
            Profile(
                "off",
                Loop("off", (off, LineSegment((-10.001, 0.0), (10.0, 0.0)))),
            )

    def test_holes(self) -> None:
        """Holes touching, crossing, outside, overlapping are refused."""
        for x, y, message in (
            (50, 15, "touches or crosses"),  # Touches the right edge.
            (55, 15, "touches or crosses"),
            (53, 33, "touches or crosses"),  # The rounded corner.
            (70, 15, "outside"),
        ):
            with (
                self.subTest(x=x, y=y),
                self.assertRaisesRegex(ValueError, message),
            ):
                Profile("plate", self.outer, [square_hole(x, y)])
        for x in (20, 15, 10):  # Touching, half over, on top.
            with (
                self.subTest(x=x),
                self.assertRaisesRegex(ValueError, "overlap"),
            ):
                Profile(
                    "plate",
                    self.outer,
                    [square_hole(10, 15), square_hole(x, 15)],
                )
        inside: Loop = rounded_rect(12.0, 17.0, 18.0, 23.0, 1.0)
        with self.assertRaisesRegex(ValueError, "overlap"):
            Profile("plate", self.outer, [square_hole(10, 15), inside])


# Class `TestSendChanges`:
class TestSendChanges(unittest.TestCase):
    """Only what moved is sent, in chunks."""

    def test_chunks(self) -> None:
        """Seven changed values at most three a call: 3, 3, 1."""
        old: dict[str, str] = {f"v{index}": "1 mm" for index in range(9)}
        new: dict[str, str] = dict(old)
        index: int
        for index in range(7):
            new[f"v{index}"] = "2 mm"
        fake: FakeSolidCraft = FakeSolidCraft()
        errors: list[JSON] = send_changes(
            cast(PyBind, fake), old, new, limit=3
        )
        self.assertEqual(errors, [])
        self.assertEqual([len(c) for c in fake.parameters.calls], [3, 3, 1])
        self.assertNotIn("v8", fake.parameters.calls[-1])

    def test_unknown(self) -> None:
        """A name SolidCraft does not have is refused."""
        fake: FakeSolidCraft = FakeSolidCraft()
        with self.assertRaises(KeyError):
            send_changes(cast(PyBind, fake), {}, {"v0": "1 mm"})


def body_box(solidcraft: PyBind) -> list[float]:
    """Return the design's box as low X, high X, low Y, high Y.

    Arguments:
    * `solidcraft` (`PyBind`): The SolidCraft session.

    Returns:
    * (`list[float]`): The box, or empty when there is no solid.
    """
    properties: JSON = solidcraft.component.properties()
    assert isinstance(properties, dict)
    total: JSON = properties["total"]
    assert isinstance(total, dict)
    box: JSON = total["bbox"]
    if not isinstance(box, dict):
        return []
    low: JSON = box["min"]
    high: JSON = box["max"]
    assert isinstance(low, list) and isinstance(high, list)
    return [
        float(cast(float, low[0])),
        float(cast(float, high[0])),
        float(cast(float, low[1])),
        float(cast(float, high[1])),
    ]


# Class `TestSolidCraft`:
@unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
class TestSolidCraft(unittest.TestCase):
    """A profile with a hole, built headless, then moved live."""

    def test_build_and_change(self) -> None:
        """The hole moves and the plate grows, by parameter changes."""
        profile: Profile = Profile(
            "plate",
            rounded_rect(0.0, 0.0, 60.0, 40.0, 5.0),
            [square_hole(20, 15)],
        )
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            values: dict[str, str] = profile.values("plate")
            add_parameters(solidcraft, values)
            solidcraft.sketch.create(plane="XY", name="plate")
            profile.sketch(solidcraft, "plate")
            solidcraft.sketch.finish()
            solidcraft.solid.extrude(distance="1 mm", body_name="plate")
            box: list[float] = body_box(solidcraft)
            self.assertEqual([round(v, 9) for v in box], [0, 60, 0, 40])

            # Wider, the hole moved, the same structure.
            changed: Profile = Profile(
                "plate",
                rounded_rect(0.0, 0.0, 80.0, 40.0, 5.0),
                [square_hole(60, 15)],
            )
            self.assertEqual(changed.structure(), profile.structure())
            errors: list[JSON] = send_changes(
                solidcraft, values, changed.values("plate")
            )
            self.assertEqual(errors, [])
            box = body_box(solidcraft)
            self.assertEqual([round(v, 9) for v in box], [0, 80, 0, 40])
            properties: JSON = solidcraft.component.properties()
            assert isinstance(properties, dict)
            total: JSON = properties["total"]
            assert isinstance(total, dict)
            volume: float = float(cast(float, total["volume_mm3"]))
            area: float = changed.outer.signed_area() + sum(
                -abs(hole.signed_area()) for hole in changed.holes
            )
            self.assertAlmostEqual(volume / area, 1.0, 4)


if __name__ == "__main__":
    unittest.main()
