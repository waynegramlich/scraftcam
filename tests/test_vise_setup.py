"""Tests for `scraftcam/tooling/vise_setup.py`: vise, parallels, plate."""

import shutil
import unittest

from scraftcam.model import Length
from scraftcam.pybind.scraftpybind import PyBind, connect
from scraftcam.solid import Leaf, SolidAssembly
from scraftcam.tooling.vise_setup import vise_setup

# Whether a headless SolidCraft can be run.
HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None

# Millimeters per inch.
INCH: float = 25.4


# Class `TestViseSetup`:
class TestViseSetup(unittest.TestCase):
    """Parallels flat against the jaws."""

    def test_places(self) -> None:
        """The movable parallel follows the gap."""
        setup: SolidAssembly = vise_setup(Length.parse("4 in"))
        leaves: dict[str, list[Leaf]] = {}
        leaf: Leaf
        for leaf in setup.leaves():
            leaves.setdefault(leaf.path[-1], []).append(leaf)
        fixed: Leaf
        movable: Leaf
        fixed, movable = leaves["parallel"]
        self.assertAlmostEqual(fixed.placement.mm()[0], 2.725 * INCH)
        self.assertAlmostEqual(
            movable.placement.mm()[0], (2.725 + 4 - 0.125) * INCH
        )

    def test_too_small(self) -> None:
        """A gap with no room for two parallels is refused."""
        with self.assertRaises(ValueError):
            vise_setup(Length.parse("1/4 in"))

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_build_live(self) -> None:
        """It builds: one body per solid."""
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            bodies: list[str] = vise_setup(Length.parse("4 in")).build(
                solidcraft
            )
        self.assertEqual(
            bodies,
            [
                "vise_base",
                "fixed_jaw_block",
                "jaw_plate",
                "movable_jaw_block",
                "parallel",
            ],
        )


if __name__ == "__main__":
    unittest.main()
