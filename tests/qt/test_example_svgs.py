"""The example shop's diagrams are what their files draw now.

An outline's `.svg` is rewritten only when the outline editor saves,
so an outline file changed any other way leaves it stale (found
2026-11-24, `T.toasl~6.8` #739); each tool's `.svg` follows its
file and its kind's outline (#737b).  `shank_drill.outline.toml`, a
drawing in progress, is left out (`IN_PROGRESS`).
"""

import unittest
from pathlib import Path

from scraftcam.diagram import svg
from scraftcam.gui.outline_diagram import outline_sheet
from scraftcam.gui.outline_editor import drawing_from, svg_path, tool_svg
from scraftcam.gui.tool_svgs import kind_tools, tool_values
from scraftcam.shops import EXAMPLE_SHOP, OUTLINE_SUFFIX

# The user's drawings in progress, whose `.svg` may be stale.
IN_PROGRESS: tuple[str, ...] = ("shank_drill.outline.toml",)

# The kinds' outlines, in their directories.
OUTLINES: list[Path] = sorted(
    outline
    for outline in (EXAMPLE_SHOP / "tools").glob(f"*/*{OUTLINE_SUFFIX}")
    if outline.name not in IN_PROGRESS
)


class ExampleSvgsTest(unittest.TestCase):
    """Every outline's and every tool's `.svg` is current."""

    def test_outlines(self) -> None:
        """An outline's `.svg` is what its file draws."""
        self.assertTrue(OUTLINES)
        outline: Path
        for outline in OUTLINES:
            with self.subTest(outline=outline.name):
                self.assertEqual(
                    svg_path(outline).read_text(encoding="utf-8"),
                    svg(outline_sheet(drawing_from(outline))),
                    "run the outline editor on it, or rewrite its .svg",
                )

    def test_tools(self) -> None:
        """A tool's `.svg` is its outline drawn for its values."""
        outline: Path
        for outline in OUTLINES:
            tool: Path
            for tool in kind_tools(outline):
                with self.subTest(tool=tool.name):
                    self.assertEqual(
                        tool.with_suffix(".svg").read_text(encoding="utf-8"),
                        tool_svg(outline, tool_values(tool, outline)),
                        "run python3 -m scraftcam.gui.tool_svgs",
                    )


if __name__ == "__main__":
    unittest.main()
