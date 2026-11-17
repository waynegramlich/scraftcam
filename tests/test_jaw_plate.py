"""Tests for `scraftcam.tooling.jaw_plate`: the parametric jaw plate.

The SolidCraft tests run a headless `solidcraft-cli`, and are skipped
when it is not on the `PATH`.
"""

import shutil
import unittest
from fractions import Fraction

from scraftcam.model import Length
from scraftcam.pybind.scraftpybind import JSON, PyBind, connect
from scraftcam.tooling.jaw_plate import JawPlate
from scraftcam.tooling.tools import KURT_JAW_PLATE

# Whether a headless SolidCraft can be run.
HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None


# Function `body_facts()`:
def body_facts(solidcraft: PyBind) -> tuple[float, list[float]]:
    """Return the design's one body's volume and bounding box maximum.

    Arguments:
    * `solidcraft` (`PyBind`): The SolidCraft session.

    Returns:
    * (`tuple[float, list[float]]`): The volume (mm^3) and the box's
      maximum corner (mm).
    """
    properties: JSON = solidcraft.component.properties()
    assert isinstance(properties, dict)
    total: JSON = properties["total"]
    assert isinstance(total, dict)
    volume: JSON = total["volume_mm3"]
    box: JSON = total["bbox"]
    assert isinstance(volume, float) and isinstance(box, dict)
    top: JSON = box["max"]
    assert isinstance(top, list)
    return volume, [float(each) for each in top if isinstance(each, float)]


# Class `TestJawPlate`:
class TestJawPlate(unittest.TestCase):
    """The plate's parameters, checks and results."""

    def test_matches_old_plate(self) -> None:
        """The defaults are the old Kurt plate's, in inches."""
        plate: JawPlate = JawPlate()
        self.assertEqual(str(plate.length), "0.725 in")
        self.assertEqual(str(plate.hole_spacing), "3-7/8 in")
        self.assertAlmostEqual(plate.length.mm(), KURT_JAW_PLATE.length)
        self.assertAlmostEqual(
            plate.hole_spacing.mm(), KURT_JAW_PLATE.hole_spacing
        )
        self.assertAlmostEqual(plate.volume, KURT_JAW_PLATE.volume())
        self.assertEqual(str(plate.half_spacing), "1-15/16 in")

    def test_edit_and_settle(self) -> None:
        """An edit, settled again, moves the results."""
        plate: JawPlate = JawPlate()
        plate.hole_spacing = Length(100, "mm")
        plate.settle()
        self.assertEqual(plate.half_spacing, Length(50, "mm"))
        self.assertEqual(plate.half_spacing.unit, "in")

    def test_refuses_misfits(self) -> None:
        """Holes that do not fit are refused."""
        with self.assertRaises(ValueError):
            JawPlate(hole_spacing=Length(Fraction(1, 2), "in"))
        with self.assertRaises(ValueError):
            JawPlate(counterbore_depth=Length(1, "in"))
        with self.assertRaises(ValueError):
            JawPlate(height=Length(0, "in"))


# Class `TestJawPlateSolidCraft`:
@unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
class TestJawPlateSolidCraft(unittest.TestCase):
    """The plate built in a headless SolidCraft, then changed live."""

    def test_build_and_change(self) -> None:
        """Built, then two parameters changed in one call."""
        plate: JawPlate = JawPlate()
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            plate.build(solidcraft, "jaw")
            volume: float
            top: list[float]
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume / plate.volume, 1.0, 4)
            self.assertAlmostEqual(top[1], plate.width.mm() / 2.0, 6)

            # A narrower plate with deeper counterbores, sent as plain
            # values the way the link will send them.
            plate.width = Length(5, "in")
            plate.counterbore_depth = Length(Fraction(5, 8), "in")
            plate.settle()
            solidcraft.parameters.change(
                changes={
                    "jaw__width": plate.width.solidcraft(),
                    "jaw__counterbore_depth": (
                        plate.counterbore_depth.solidcraft()
                    ),
                }
            )
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume / plate.volume, 1.0, 4)
            self.assertAlmostEqual(top[1], plate.width.mm() / 2.0, 6)


if __name__ == "__main__":
    unittest.main()
