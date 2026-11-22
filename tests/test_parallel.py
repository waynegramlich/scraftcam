"""Tests for `scraftcam.tooling.parallel`: a model made of layers.

The SolidCraft test runs a headless `solidcraft-cli`, and is skipped
when there is none.
"""

import shutil
import unittest
from fractions import Fraction

from scraftcam.model import Length
from scraftcam.pybind.scraftpybind import PyBind, connect
from scraftcam.solid import Layer
from scraftcam.solidcraft_link import SolidCraftLink
from scraftcam.tooling.parallel import Parallel
from tests.test_jaw_plate import body_facts

HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None


# Class `TestParallel`:
class TestParallel(unittest.TestCase):
    """The parallel's checks and layers."""

    def test_layers(self) -> None:
        """Two holes by default, 3 in apart about its middle; none."""
        parallel: Parallel = Parallel()
        holes: tuple[Layer, ...] = tuple(parallel.solid.root.children)
        self.assertEqual(
            [round(hole.dx.mm(), 9) for hole in holes], [38.1, 114.3]
        )
        self.assertAlmostEqual(holes[0].dy.mm(), 12.7)
        values: dict[str, str] = parallel.solidcraft_values("p")
        self.assertEqual(values["p__height"], "1 in")
        parallel.hole_count = 0
        parallel.settle()
        self.assertEqual(tuple(parallel.solid.root.children), ())

    def test_refused(self) -> None:
        """Holes that do not fit are refused, in the user's units."""
        parallel: Parallel = Parallel()
        parallel.hole_count = 3
        with self.assertRaisesRegex(ValueError, "need 6-1/2 in of a 6 in"):
            parallel.settle()
        parallel.hole_count = 2
        parallel.hole_diameter = Length(Fraction(5, 4), "in")
        with self.assertRaisesRegex(ValueError, "1-1/4 in holes"):
            parallel.settle()
        parallel.hole_diameter = Length(20, "mm")
        parallel.hole_spacing = Length(15, "mm")
        with self.assertRaisesRegex(ValueError, "20 mm holes 15 mm"):
            parallel.settle()


# Class `TestSolidCraft`:
@unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
class TestSolidCraft(unittest.TestCase):
    """A parallel kept up to date in a headless SolidCraft."""

    def test_link(self) -> None:
        """Every change of size rebuilds it, at the volume it should."""
        parallel: Parallel = Parallel()
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            link: SolidCraftLink = SolidCraftLink(solidcraft)
            name: str = link.add(parallel, "parallel")
            volume: float
            top: list[float]
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume / parallel.volume, 1.0, 4)
            self.assertAlmostEqual(top[0], 152.4, 6)

            # Longer, and the holes further apart.
            parallel.length = Length(8, "in")
            parallel.hole_spacing = Length(4, "in")
            self.assertEqual(link.send(name), "rebuilt")
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume / parallel.volume, 1.0, 4)
            self.assertAlmostEqual(top[0], 203.2, 6)

            # A third hole.
            parallel.hole_spacing = Length(2, "in")
            parallel.hole_count = 3
            self.assertEqual(link.send(name), "rebuilt")
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume / parallel.volume, 1.0, 4)
            self.assertAlmostEqual(top[0], 203.2, 6)


if __name__ == "__main__":
    unittest.main()
