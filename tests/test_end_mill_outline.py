"""The outline end mill against the old model's (`T.tfo~6.5`).

Each square end mill of the example shop (the roughing one too: its
teeth are not modeled) is made twice: from the kind's outline drawing,
`end_mill.outline.toml`, given the mill's letters, and
from `cutter_models.profile()`, the old hand-written model.  Both half
profiles are turned about the axis (no SolidCraft), and their volumes
and boxes must agree.  Ball end mills are drawn separately.
"""

import unittest
from pathlib import Path

from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_file import Outline, outline_from_text
from scraftcam.gui.outline_polygon import outline_revolved
from scraftcam.gui.values import refresh_formulas
from scraftcam.shops import END_MILL_LETTERS, read
from scraftcam.solid import SolidRevolved
from scraftcam.tooling.cutter_models import (
    EXAMPLE_SHOP,
    profile,
    shop_tools,
)
from tests.test_drill_outline import MM, turned

# The kind's outline drawing.
END_MILL: Path = Path(__file__).resolve().parent.parent / (
    "examples/shop/tools/end_mill.outline.toml"
)


# Function `outline_end_mill()`:
def outline_end_mill(tool: dict[str, object]) -> SolidRevolved:
    """Return the outline end mill given a shop end mill's sizes.

    Arguments:
    * `tool` (`dict[str, object]`): The end mill, from `shops.read()`.

    Returns:
    * (`SolidRevolved`): The end mill, in millimeters.
    """
    outline: Outline = outline_from_text(
        END_MILL.read_text(encoding="utf-8"), END_MILL.name
    )
    values: dict[str, str] = {
        letter: str(tool[key])
        for key, letter in END_MILL_LETTERS.items()
        if key in tool
    }
    if "SD" not in values:
        values["SD"] = values["D"]
    each: Letter
    for each in outline.letters:
        if each.letter in values:
            each.default = values[each.letter]
    refresh_formulas(outline.letters)
    return outline_revolved(outline, f"end_mill_{tool['unique_id']}")


# Class `TestEndMillOutline`:
class TestEndMillOutline(unittest.TestCase):
    """The outline end mill matches the old model, mill by mill."""

    def test_example_end_mills(self) -> None:
        """Volume, radius and length agree for each square end mill."""
        mills: list[dict[str, object]] = [
            tool
            for key, tool in shop_tools(read(EXAMPLE_SHOP))
            if key == "end_mills" and tool.get("end", "square") == "square"
        ]
        self.assertGreaterEqual(len(mills), 3)
        tool: dict[str, object]
        for tool in mills:
            with self.subTest(end_mill=tool["name"]):
                new: tuple[float, float, float] = turned(
                    [
                        (corner.x, corner.y)
                        for corner in outline_end_mill(tool).profile.corners
                    ]
                )
                old: tuple[float, float, float] = turned(
                    [(r * MM, z * MM) for r, z in profile("end_mills", tool)]
                )
                for found, expected in zip(new, old, strict=True):
                    self.assertAlmostEqual(
                        found / expected, 1.0, places=6, msg=(new, old)
                    )


if __name__ == "__main__":
    unittest.main()
