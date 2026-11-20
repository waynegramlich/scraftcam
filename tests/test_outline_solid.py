"""Tests of `scraftcam.gui.outline_solid`: outlines in SolidCraft.

The SolidCraft test runs a headless `solidcraft-cli`, and is skipped
without one.
"""

import shutil
import unittest
from pathlib import Path

from scraftcam.gui.outline_file import Outline, outline_from_text
from scraftcam.gui.outline_solid import (
    ZERO,
    build,
    corner_expressions,
    flatten_tips,
    letter_value,
)
from scraftcam.pybind.scraftpybind import JSON, PyBind, connect

HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None

# Half a 1/4 in drill (`T.oe~6.2` #S4).
DRILL: Path = Path("examples/shop/tools/drill.outline.toml")


def drill() -> Outline:
    """Return the example drill's outline."""
    return outline_from_text(DRILL.read_text(encoding="utf-8"), str(DRILL))


class OutlineSolidTest(unittest.TestCase):
    """Corners as expressions, tips cut, and a build."""

    def test_corners(self) -> None:
        """Each corner is its formula; a floating one is refused."""
        corners: list[tuple[str, str]] = corner_expressions(drill())
        self.assertEqual(corners[0], (ZERO, ZERO))
        self.assertEqual(corners[2], ("(R)", "(L)"))
        self.assertIn("tan(90 deg - A)", corners[1][1])
        loose: Outline = drill()
        loose.dimensions.pop()
        with self.assertRaises(ValueError):
            corner_expressions(loose)

    def test_flatten_tips(self) -> None:
        """The tip on the axis becomes two corners; the shank's top
        beside a level edge stays (#106)."""
        corners: list[tuple[str, str]] = corner_expressions(drill())
        flat: list[tuple[str, str]] = flatten_tips(corners)
        self.assertEqual(len(flat), len(corners) + 1)
        self.assertEqual(flat[0][0], ZERO)
        self.assertEqual(flat[0][1], flat[1][1])
        self.assertIn("0.05", flat[1][0])
        self.assertEqual(flat[-1], corners[-1])

        # The tip drawn the other way round: the pair reversed.
        backward: list[tuple[str, str]] = [
            corners[0],
            corners[3],
            corners[2],
            corners[1],
        ]
        cut: list[tuple[str, str]] = flatten_tips(backward)
        self.assertIn("0.05", cut[0][0])
        self.assertEqual(cut[1][0], ZERO)
        self.assertEqual(cut[0][1], cut[1][1])

    def test_letter_value(self) -> None:
        """Lengths are sent so mixed numbers read right."""
        self.assertEqual(letter_value("59 deg"), "59 deg")
        self.assertIn("in", letter_value("3-7/8 in"))
        self.assertNotIn("3-7/8", letter_value("3-7/8 in"))

    def test_flat_only(self) -> None:
        """Only revolved outlines are built so far."""
        flat: Outline = drill()
        flat.revolve = False
        with self.assertRaises(ValueError):
            build(PyBind(connect("headless")), flat, "drill")

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_build(self) -> None:
        """The drill builds headless, and a letter changes it live."""
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            solidcraft.file.new()
            self.assertEqual(build(solidcraft, drill(), "drill"), "drill")
            changed: JSON = solidcraft.parameters.change(
                changes={"A": "45 deg"}
            )
            self.assertIsInstance(changed, dict)
            assert isinstance(changed, dict)
            self.assertFalse(changed.get("errors"))


if __name__ == "__main__":
    unittest.main()
