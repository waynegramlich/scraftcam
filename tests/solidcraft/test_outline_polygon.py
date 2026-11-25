"""Tests for `scraftcam/gui/outline_polygon.py`: outline file to polygon."""

import math
import shutil
import tempfile
import unittest
from pathlib import Path

from scraftcam.geometry import Corner
from scraftcam.gui.dimensions import RADIUS, Dimension
from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_file import (
    Hole,
    Outline,
    Polygon,
    Role,
    outline_from_text,
)
from scraftcam.gui.outline_polygon import (
    outline_polygon,
    outline_revolved,
    outline_unit,
    polygon_from_file,
)
from scraftcam.gui.values import letter_values, real_corners
from scraftcam.model import Length
from scraftcam.pybind.scraftpybind import JSON, PyBind, connect
from scraftcam.shops import EXAMPLE_SHOP
from scraftcam.solid import (
    Layer,
    RoundedPolygon,
    SolidRevolved,
    SolidRoundedPolygon,
)
from tests.solidcraft_checks import totals

# The example drill's outline file.
DRILL: Path = EXAMPLE_SHOP / "tools/drills/drill.outline.toml"

# Whether a headless SolidCraft can be run.
HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None


# Function `flat_drill()`:
def flat_drill() -> Outline:
    """Return the example drill's outline, not revolved."""
    outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
    outline.revolve = False
    return outline


# Function `filleted_drill()`:
def filleted_drill() -> Outline:
    """Return the flat drill with its shank's outer end (corner 3)
    rounded."""
    outline: Outline = flat_drill()
    outline.letters.append(Letter("F", "Fillet", "1/32 in", fillet=True))
    outline.dimensions.append(Dimension("F", RADIUS, 3, 3))
    return outline


# Class `TestOutlinePolygon`:
class TestOutlinePolygon(unittest.TestCase):
    """The letters' values place and round the corners."""

    def test_drill(self) -> None:
        """The corners are where the values put them, rounded by them;
        the flutes' end (corner 2), on a straight edge, is left out
        (#434)."""
        outline: Outline = filleted_drill()
        polygon: RoundedPolygon = outline_polygon(outline, "drill")
        expected: list[tuple[float, float]] | None = real_corners(
            outline.points, outline.letters, outline.dimensions
        )
        assert expected is not None
        del expected[2]
        self.assertEqual(
            [(corner.x, corner.y) for corner in polygon.corners], expected
        )
        values: dict[str, float] = letter_values(outline.letters)
        rounded: dict[int, float] = {
            dimension.start: values[dimension.letter]
            for dimension in outline.dimensions
            if dimension.kind == RADIUS
        }
        self.assertEqual(list(rounded), [3])
        self.assertAlmostEqual(rounded[3], 25.4 / 32)
        self.assertEqual(polygon.corners[2].radius, rounded[3])
        self.assertEqual(polygon.unit, outline_unit(outline))

    def test_from_file(self) -> None:
        """A file is read; a revolved one is refused."""
        with tempfile.TemporaryDirectory() as directory:
            path: Path = Path(directory) / "flat.outline.toml"
            text: str = DRILL.read_text(encoding="utf-8")
            path.write_text(
                text.replace("revolve = true", "revolve = false"),
                encoding="utf-8",
            )
            self.assertEqual(
                polygon_from_file(path).corners,
                outline_polygon(flat_drill()).corners,
            )
        with self.assertRaisesRegex(ValueError, "SolidRevolved"):
            polygon_from_file(DRILL)

    def test_refused(self) -> None:
        """Holes, several polygons, and corners left undimensioned,
        are refused."""
        outline: Outline = flat_drill()
        outline.holes = [Hole("plain", (0.0, 0.0), "A")]
        with self.assertRaisesRegex(ValueError, "holes"):
            outline_polygon(outline)

        # Several polygons wait for `T.sa~6.11` #S4.
        outline = flat_drill()
        outline.polygons.append(
            Polygon("cap", Role.OTHER, list(outline.names[:3]))
        )
        with self.assertRaisesRegex(ValueError, "several polygons"):
            outline_polygon(outline)
        outline = flat_drill()
        outline.dimensions = []
        with self.assertRaisesRegex(ValueError, "not dimensioned"):
            outline_polygon(outline)
        outline = filleted_drill()
        outline.letters[-1].default = "bad"
        with self.assertRaisesRegex(ValueError, "no value"):
            outline_polygon(outline)

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_build_live(self) -> None:
        """The polygon extrudes into a solid."""
        polygon: RoundedPolygon = outline_polygon(filleted_drill())
        zero: Length = Length.parse("0 in")
        solid: SolidRoundedPolygon = SolidRoundedPolygon(
            "drill", Layer(polygon, zero, zero, Length.parse("1/4 in"))
        )
        with connect("headless") as transport:
            self.assertEqual(solid.build(PyBind(transport)), ["drill"])


# Function `turned_volume()`:
def turned_volume(corners: list[Corner]) -> float:
    """Return the volume a sharp half profile makes turned (Pappus)."""
    count: int = len(corners)
    moment: float = 0.0
    index: int
    for index in range(count):
        a: Corner = corners[index]
        b: Corner = corners[(index + 1) % count]
        moment += (a.x + b.x) * (a.x * b.y - b.x * a.y)
    return abs(2.0 * math.pi * moment / 6.0)


# Class `TestOutlineRevolved`:
class TestOutlineRevolved(unittest.TestCase):
    """A revolved outline is a round solid."""

    def test_drill(self) -> None:
        """The drill's tip is cut flat; a flat outline is refused."""
        outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
        drill: SolidRevolved = outline_revolved(outline, "drill")
        self.assertEqual(
            len(drill.flat.corners), len(drill.profile.corners) + 1
        )
        with self.assertRaisesRegex(ValueError, "not revolved"):
            outline_revolved(flat_drill(), "flat")

    def test_bad_profiles(self) -> None:
        """Across the axis, or with no edge on it, is refused."""
        cases: tuple[tuple[Corner, ...], ...] = (
            (Corner(-1.0, 0.0), Corner(1.0, 0.0), Corner(0.0, 1.0)),
            (Corner(1.0, 0.0), Corner(2.0, 0.0), Corner(1.0, 1.0)),
        )
        corners: tuple[Corner, ...]
        for corners in cases:
            with self.assertRaises(ValueError, msg=repr(corners)):
                SolidRevolved("bad", RoundedPolygon(corners))

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_build_live(self) -> None:
        """The drill turns into the volume Pappus gives, along Z."""
        outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
        drill: SolidRevolved = outline_revolved(outline, "drill")
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            self.assertEqual(drill.build(solidcraft), ["drill"])
            properties: JSON = solidcraft.component.properties()
        volume: float
        high: list[float]
        volume, _, high = totals(properties)
        expected: float = turned_volume(list(drill.flat.corners))
        self.assertLess(abs(volume - expected) / expected, 2e-3)
        self.assertAlmostEqual(high[2], 4 * 25.4, 3)


if __name__ == "__main__":
    unittest.main()
