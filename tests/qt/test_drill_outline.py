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
from typing import cast

from scraftcam.appearance import Color
from scraftcam.gui.outline_file import Outline, outline_from_text
from scraftcam.gui.outline_polygon import (
    CUTTING_TRANSPARENCY,
    outline_revolved,
)
from scraftcam.gui.values import set_letters
from scraftcam.shops import (
    DRILL_LETTERS,
    EXAMPLE_SHOP,
    EXAMPLE_SHOP_FILE,
    read,
)
from scraftcam.solid import Appearance, Solid, SolidAssembly, SolidRevolved
from scraftcam.tooling.cutter_models import (
    profile,
    shop_tools,
)

# The kind's outline drawing.
DRILL: Path = Path(__file__).resolve().parents[2] / (
    EXAMPLE_SHOP / "tools/drills/drill.outline.toml"
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


# Function `turned_parts()`:
def turned_parts(solid: Solid) -> tuple[float, float, float]:
    """Return a revolved solid's volume, radius and height, its parts
    (flutes and shank, `T.sa~6.11` #817) added up.

    Arguments:
    * `solid` (`Solid`): A `SolidRevolved`, or an assembly of them.

    Returns:
    * (`tuple[float, float, float]`): Volume, radius, height.
    """
    parts: list[SolidRevolved] = (
        [cast(SolidRevolved, part.solid) for part in solid.parts]
        if isinstance(solid, SolidAssembly)
        else [cast(SolidRevolved, solid)]
    )
    points: list[list[tuple[float, float]]] = [
        [(corner.x, corner.y) for corner in part.profile.corners]
        for part in parts
    ]
    each: list[tuple[float, float, float]] = [turned(part) for part in points]
    zs: list[float] = [z for part in points for _, z in part]
    return (
        sum(volume for volume, _, _ in each),
        max(radius for _, radius, _ in each),
        max(zs) - min(zs),
    )


# Function `outline_drill()`:
def outline_drill(tool: dict[str, object]) -> Solid:
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


# Class `TestDrillParts`:
class TestDrillParts(unittest.TestCase):
    """The drill is flutes and a shank (`T.sa~6.11` #817, #826)."""

    def test_parts(self) -> None:
        """Two stacked parts, named after the drill; the flutes are
        see-through, both the material's colour."""
        outline: Outline = outline_from_text(
            DRILL.read_text(encoding="utf-8"), DRILL.name
        )
        drill: Solid = outline_revolved(
            outline, "drill", color=Color(16.0, 17.0, 19.0)
        )
        assert isinstance(drill, SolidAssembly)
        self.assertEqual(
            [part.solid.name for part in drill.parts],
            ["drill_flutes", "drill_shank"],
        )
        flutes: Appearance | None = drill.parts[0].solid.appearance
        shank: Appearance | None = drill.parts[1].solid.appearance
        assert flutes is not None and shank is not None
        self.assertAlmostEqual(flutes.t, CUTTING_TRANSPARENCY)
        self.assertEqual(shank.t, 0.0)
        self.assertAlmostEqual(shank.r, 0.16)
        self.assertIsNone(
            cast(SolidAssembly, outline_revolved(outline, "bare"))
            .parts[0]
            .solid.appearance
        )


# Class `TestDrillOutline`:
class TestDrillOutline(unittest.TestCase):
    """The outline drill matches the old model, drill by drill."""

    def test_example_drills(self) -> None:
        """Volume, radius and length agree for each example drill."""
        drills: list[dict[str, object]] = [
            tool
            for key, tool in shop_tools(read(EXAMPLE_SHOP_FILE))
            if key == "drills"
        ]
        self.assertGreaterEqual(len(drills), 2)
        tool: dict[str, object]
        for tool in drills:
            with self.subTest(drill=tool["name"]):
                new: tuple[float, float, float] = turned_parts(
                    outline_drill(tool)
                )
                old_points: list[tuple[float, float]] = [
                    (r * MM, z * MM) for r, z in profile("drills", tool)
                ]
                old: tuple[float, float, float] = turned(old_points)
                assert_same(self, new, old)


if __name__ == "__main__":
    unittest.main()
