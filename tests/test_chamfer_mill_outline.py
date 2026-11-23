"""The outline chamfer mill against the old model's (`T.tfo~6.5` #463).

Each chamfer mill of the example shop is made twice: from the kind's
outline drawing, `chamfer_mill.outline.toml`, given the mill's letters,
and from `cutter_models.profile()`, the old hand-written model.  Both
half profiles are turned about the axis (no SolidCraft), and their
volumes and boxes must agree.
"""

import unittest
from pathlib import Path

from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_file import Outline, outline_from_text
from scraftcam.gui.outline_polygon import outline_revolved
from scraftcam.gui.values import refresh_formulas
from scraftcam.shops import read
from scraftcam.solid import SolidRevolved
from scraftcam.tooling.cutter_models import (
    EXAMPLE_SHOP,
    profile,
    shop_tools,
)
from tests.test_drill_outline import MM, turned

# The kind's outline drawing.
CHAMFER_MILL: Path = Path(__file__).resolve().parent.parent / (
    "examples/shop/tools/chamfer_mill.outline.toml"
)

# A chamfer mill's shop keys and the outline's letters (the shop
# files are not keyed by the letters yet).
LETTERS: dict[str, str] = {
    "angle": "A",
    "diameter": "D",
    "overall_length": "OAL",
    "shank": "SD",
    "tip_diameter": "TD",
}


# Function `outline_chamfer_mill()`:
def outline_chamfer_mill(tool: dict[str, object]) -> SolidRevolved:
    """Return the outline chamfer mill given a shop one's sizes.

    Arguments:
    * `tool` (`dict[str, object]`): The mill, from `shops.read()`.

    Returns:
    * (`SolidRevolved`): The mill, in millimeters.
    """
    outline: Outline = outline_from_text(
        CHAMFER_MILL.read_text(encoding="utf-8"), CHAMFER_MILL.name
    )
    values: dict[str, str] = {
        letter: str(tool[key])
        for key, letter in LETTERS.items()
        if key in tool
    }
    values.setdefault("SD", values["D"])
    values.setdefault("TD", "0 in")
    each: Letter
    for each in outline.letters:
        if each.letter in values:
            each.default = values[each.letter]
    refresh_formulas(outline.letters)
    return outline_revolved(outline, f"chamfer_mill_{tool['unique_id']}")


# Class `TestChamferMillOutline`:
class TestChamferMillOutline(unittest.TestCase):
    """The outline chamfer mill matches the old model, mill by mill."""

    def test_example_chamfer_mills(self) -> None:
        """Volume, radius and length agree for each chamfer mill."""
        mills: list[dict[str, object]] = [
            tool
            for key, tool in shop_tools(read(EXAMPLE_SHOP))
            if key == "chamfer_mills"
        ]
        self.assertGreaterEqual(len(mills), 1)
        tool: dict[str, object]
        for tool in mills:
            with self.subTest(chamfer_mill=tool["name"]):
                new: tuple[float, float, float] = turned(
                    [
                        (corner.x, corner.y)
                        for corner in outline_chamfer_mill(
                            tool
                        ).profile.corners
                    ]
                )
                old: tuple[float, float, float] = turned(
                    [
                        (r * MM, z * MM)
                        for r, z in profile("chamfer_mills", tool)
                    ]
                )
                for found, expected in zip(new, old, strict=True):
                    self.assertAlmostEqual(
                        found / expected, 1.0, places=6, msg=(new, old)
                    )


if __name__ == "__main__":
    unittest.main()
