"""The outline drill against the old model's drill (`T.tfo~6.5` #436).

Each drill of the example shop is made twice: from the kind's outline
drawing, `drill.outline.toml`, given the drill's letters, and from
`cutter_models.profile()`, the old hand-written model.  Both half
profiles are turned about the axis here (no SolidCraft), and their
volumes and boxes must agree.
"""

import math
import unittest
from pathlib import Path

from scraftcam.gui.outline_file import Outline, outline_from_text
from scraftcam.gui.outline_polygon import outline_revolved
from scraftcam.gui.values import set_letters
from scraftcam.shops import DRILL_LETTERS, read
from scraftcam.solid import SolidRevolved
from scraftcam.tooling.cutter_models import (
    EXAMPLE_SHOP,
    profile,
    shop_tools,
)

# The kind's outline drawing.
DRILL: Path = Path(__file__).resolve().parents[2] / (
    "examples/shop/tools/drill.outline.toml"
)

# Millimeters per inch: `cutter_models` works in inches.
MM: float = 25.4


# Function `assert_same()`:
def assert_same(
    case: unittest.TestCase,
    new: tuple[float, float, float],
    old: tuple[float, float, float],
) -> None:
    """Check that two turned profiles agree to 6 places, as ratios.

    Arguments:
    * `case` (`unittest.TestCase`): The test that checks.
    * `new` (`tuple[float, float, float]`): The outline's volume,
      radius and height.
    * `old` (`tuple[float, float, float]`): The old model's.
    """
    found: float
    expected: float
    for found, expected in zip(new, old, strict=True):
        case.assertAlmostEqual(found / expected, 1.0, places=6, msg=(new, old))


# Function `turned()`:
def turned(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Return a half profile's volume turned about its Y axis, its
    largest radius and its height.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The profile, (r, z), in
      order around it.

    Returns:
    * (`tuple[float, float, float]`): Volume, radius, height.
    """
    # Each edge sweeps a cone's frustum (Pappus, edge by edge).
    volume: float = 0.0
    index: int
    for index, (r0, z0) in enumerate(points):
        r1: float
        z1: float
        r1, z1 = points[(index + 1) % len(points)]
        volume += (r0 * r0 + r0 * r1 + r1 * r1) * (z1 - z0)
    zs: list[float] = [z for _, z in points]
    return (
        abs(volume) * math.pi / 3.0,
        max(r for r, _ in points),
        max(zs) - min(zs),
    )


# Function `outline_drill()`:
def outline_drill(tool: dict[str, object]) -> SolidRevolved:
    """Return the outline drill given a shop drill's letters.

    Arguments:
    * `tool` (`dict[str, object]`): The drill, from `shops.read()`.

    Returns:
    * (`SolidRevolved`): The drill, in millimeters.
    """
    outline: Outline = outline_from_text(
        DRILL.read_text(encoding="utf-8"), DRILL.name
    )
    values: dict[str, str] = {
        letter: str(tool[key])
        for key, letter in DRILL_LETTERS.items()
        if key in tool
    }
    set_letters(outline.letters, values)
    return outline_revolved(outline, f"drill_{tool['unique_id']}")


# Class `TestDrillOutline`:
class TestDrillOutline(unittest.TestCase):
    """The outline drill matches the old model, drill by drill."""

    def test_example_drills(self) -> None:
        """Volume, radius and length agree for each example drill."""
        drills: list[dict[str, object]] = [
            tool
            for key, tool in shop_tools(read(EXAMPLE_SHOP))
            if key == "drills"
        ]
        self.assertGreaterEqual(len(drills), 2)
        tool: dict[str, object]
        for tool in drills:
            with self.subTest(drill=tool["name"]):
                new: tuple[float, float, float] = turned(
                    [
                        (corner.x, corner.y)
                        for corner in outline_drill(tool).profile.corners
                    ]
                )
                old_points: list[tuple[float, float]] = [
                    (r * MM, z * MM) for r, z in profile("drills", tool)
                ]
                old: tuple[float, float, float] = turned(old_points)
                assert_same(self, new, old)


if __name__ == "__main__":
    unittest.main()
