"""Tests for `scraftcam.tooling.parallel`: a model drawn from a profile.

The SolidCraft test runs a headless `solidcraft-cli`, and is skipped
when there is none.
"""

import shutil
import unittest
from fractions import Fraction

from scraftcam.model import Length
from scraftcam.pybind.scraftpybind import PyBind, connect
from scraftcam.solidcraft_link import SolidCraftLink
from scraftcam.tooling.parallel import Parallel
from tests.test_jaw_plate import body_facts

HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None


# Class `TestParallel`:
class TestParallel(unittest.TestCase):
    """The parallel's checks and side."""

    def test_side(self) -> None:
        """Two holes by default, none when asked."""
        parallel: Parallel = Parallel()
        self.assertEqual(parallel.side.structure(), ("llll", "a", "a"))
        values: dict[str, str] = parallel.solidcraft_values("p")
        self.assertEqual(values["p__height"], "1 in")
        self.assertEqual(values["p__side__l1__c0x"], "-38.1 mm")
        parallel.hole_count = 0
        parallel.settle()
        self.assertEqual(parallel.side.structure(), ("llll",))

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
        """A longer parallel is sent; more holes rebuild it."""
        parallel: Parallel = Parallel()
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            link: SolidCraftLink = SolidCraftLink(solidcraft)
            name: str = link.add(parallel, "parallel")
            volume: float
            top: list[float]
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume / parallel.volume, 1.0, 4)
            self.assertAlmostEqual(top[1], 76.2, 6)

            # Longer, and the holes further apart: values sent.
            parallel.length = Length(8, "in")
            parallel.hole_spacing = Length(4, "in")
            self.assertEqual(link.send(name), "changed")
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume / parallel.volume, 1.0, 4)
            self.assertAlmostEqual(top[1], 101.6, 6)

            # A third hole changes the side's structure: rebuilt.
            parallel.hole_spacing = Length(2, "in")
            parallel.hole_count = 3
            self.assertEqual(link.send(name), "rebuilt")
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume / parallel.volume, 1.0, 4)
            self.assertAlmostEqual(top[1], 101.6, 6)


if __name__ == "__main__":
    unittest.main()
