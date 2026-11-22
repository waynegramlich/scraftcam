"""Tests for `scraftcam/tooling/kurt_vise.py`: the DX6 as an assembly."""

import shutil
import unittest

from scraftcam.model import Length
from scraftcam.pybind.scraftpybind import JSON, PyBind, connect
from scraftcam.solid import Leaf, SolidAssembly
from scraftcam.tooling.kurt_vise import kurt_dx6

# Whether a headless SolidCraft can be run.
HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None


# Class `TestKurtDX6`:
class TestKurtDX6(unittest.TestCase):
    """The vise's parts and where the gap puts the movable jaw."""

    def test_parts(self) -> None:
        """Base, fixed jaw and movable jaw; one plate solid, twice."""
        vise: SolidAssembly = kurt_dx6(Length.parse("1 in"))
        self.assertEqual(
            [part.solid.name for part in vise.parts],
            ["vise_base", "fixed_jaw", "movable_jaw"],
        )
        leaves: list[Leaf] = vise.leaves()
        self.assertEqual(
            [leaf.path[-1] for leaf in leaves],
            [
                "vise_base",
                "fixed_jaw_block",
                "jaw_plate",
                "jaw_plate",
                "movable_jaw_block",
            ],
        )

    def test_gap(self) -> None:
        """The gap moves the movable jaw; too big a gap is refused."""
        near: SolidAssembly = kurt_dx6(Length.parse("1 in"))
        far: SolidAssembly = kurt_dx6(Length.parse("3 in"))
        moved: float = (
            far.leaves()[3].placement.mm()[0]
            - near.leaves()[3].placement.mm()[0]
        )
        self.assertAlmostEqual(moved, 2 * 25.4)
        with self.assertRaises(ValueError):
            kurt_dx6(Length.parse("10 in"))

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_build_live(self) -> None:
        """Opened all the way, it fills the catalog's box."""
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            kurt_dx6(Length.parse("9.08 in")).build(solidcraft)
            properties: JSON = solidcraft.component.properties(
                component="root"
            )
        assert isinstance(properties, dict)
        total: JSON = properties["total"]
        assert isinstance(total, dict)
        box: JSON = total["bbox"]
        assert isinstance(box, dict)
        low: JSON = box["min"]
        high: JSON = box["max"]
        assert isinstance(low, list) and isinstance(high, list)
        self.assertEqual(
            [round(float(str(v)) / 25.4, 4) for v in (*low, *high)],
            [0.0, -3.695, 0.0, 16.86, 3.695, 4.61],
        )


if __name__ == "__main__":
    unittest.main()
