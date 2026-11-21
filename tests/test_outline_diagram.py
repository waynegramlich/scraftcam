"""Tests for `scraftcam.gui.outline_diagram`: outline files drawn."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scraftcam.diagram import Sheet, Stroke, Weight, svg
from scraftcam.geometry import ArcSegment, Point
from scraftcam.gui import outline_diagram
from scraftcam.gui.dimensions import (
    ANGLE,
    HORIZONTAL,
    LENGTH,
    ORIGIN,
    RADIUS,
    VERTICAL,
    Y_AXIS,
    Dimension,
)
from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_diagram import outline_sheet
from scraftcam.gui.outline_file import Outline, outline_from_text

DRILL: Path = Path("examples/shop/tools/drill.outline.toml")

# A counter-clockwise 4 x 2 rectangle with a corner at the origin.
BOX: list[tuple[float, float]] = [
    (0.0, 0.0),
    (4.0, 0.0),
    (4.0, 2.0),
    (0.0, 2.0),
]


def drawn(outline: Outline, dimension: Dimension) -> list[Stroke]:
    """Return what one dimension adds to the outline's sheet."""
    bare: Sheet = outline_sheet(outline, 0.5)
    outline.dimensions.append(dimension)
    full: Sheet = outline_sheet(outline, 0.5)
    return list(full.strokes[len(bare.strokes) :])


def box() -> Outline:
    """Return the rectangle, with no dimensions."""
    return Outline(points=list(BOX))


class TestOutlineDiagram(unittest.TestCase):
    """The outline, its dimensions and marks."""

    def test_outline(self) -> None:
        """One thick closed stroke through the corners."""
        sheet: Sheet = outline_sheet(box(), 0.5)
        self.assertEqual(len(sheet.strokes), 1)
        outline: Stroke = sheet.strokes[0]
        self.assertIs(outline.weight, Weight.THICK)
        self.assertEqual(len(outline.segments), 4)
        self.assertEqual(outline.segments[-1].end, (0.0, 0.0))
        self.assertAlmostEqual(outline_sheet(box()).text_height, 4.0 / 30)

    def test_horizontal(self) -> None:
        """A horizontal dimension's line sits at its offset's Y."""
        strokes: list[Stroke] = drawn(
            box(), Dimension("W", HORIZONTAL, ORIGIN, 1, -1.0, 0.5)
        )
        ends: list[Point] = [strokes[2].segments[0].start]
        self.assertEqual(ends, [(0.0, -1.0)])

    def test_vertical(self) -> None:
        """A vertical dimension's line sits at its offset's X."""
        strokes: list[Stroke] = drawn(
            box(), Dimension("H", VERTICAL, 1, 2, 5.0, 0.5)
        )
        self.assertEqual(strokes[2].segments[0].start, (5.0, 0.0))

    def test_length(self) -> None:
        """A length runs parallel to its points."""
        strokes: list[Stroke] = drawn(
            box(), Dimension("D", LENGTH, 0, 2, 1.0, 0.5)
        )
        start: Point = strokes[2].segments[0].start
        self.assertAlmostEqual(start[1] / start[0], -2.0)

    def test_angle(self) -> None:
        """An angle's arc is about where its edges' lines cross."""
        strokes: list[Stroke] = drawn(
            box(), Dimension("A", ANGLE, 0, 1, 1.0, 0.5, rays=(-1, 1))
        )
        arc = strokes[0].segments[0]
        assert isinstance(arc, ArcSegment)
        self.assertEqual(arc.center, (4.0, 0.0))
        self.assertGreater(arc.sweep, 0.0)

    def test_angle_from_axis(self) -> None:
        """An angle from the Y axis crosses at the origin."""
        outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
        outline.dimensions = []
        strokes: list[Stroke] = drawn(
            outline, Dimension("A", ANGLE, 0, Y_AXIS, 0.6, 0.5, rays=(1, 1))
        )
        arc = strokes[0].segments[0]
        assert isinstance(arc, ArcSegment)
        self.assertEqual(arc.center, (0.0, 0.0))

    def test_parallel_angle(self) -> None:
        """An angle between parallel edges draws nothing."""
        self.assertEqual(
            drawn(box(), Dimension("A", ANGLE, 0, 2, 1.0, 0.5)), []
        )

    def test_fillets(self) -> None:
        """Rounded corners: tangent arcs, a letter or the note."""
        outline: Outline = box()
        outline.note_radius = "UDF"
        outline.dimensions = [
            Dimension("F", RADIUS, 2, 2, 0.0, 0.5),
            Dimension("UDF", RADIUS, 1, 1, 0.0, 0.5),
        ]
        sheet: Sheet = outline_sheet(outline, 0.1)
        arcs: list[ArcSegment] = [
            segment
            for segment in sheet.strokes[0].segments
            if isinstance(segment, ArcSegment)
        ]
        self.assertEqual(len(arcs), 2)
        # A fifth of the shorter edge (no scale): 0.4, centered in.
        self.assertAlmostEqual(arcs[0].radius, 0.4)
        self.assertAlmostEqual(arcs[0].center[0], 3.6)
        self.assertAlmostEqual(arcs[0].center[1], 0.4)
        self.assertGreater(arcs[0].sweep, 0.0)
        self.assertEqual(sheet.strokes[0].segments[0].end, arcs[0].start)
        dashed: list[Stroke] = [s for s in sheet.strokes if s.dashed]
        self.assertEqual(len(dashed), 2)
        filled: list[Stroke] = [s for s in sheet.strokes if s.filled]
        self.assertEqual(len(filled), 1)
        self.assertLess(sheet.low[1], -0.1)

    def test_fillet_to_scale(self) -> None:
        """With the values fixing a scale, the letter's value is used."""
        outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
        outline.letters.append(Letter("F", default="1/64 in", fillet=True))
        outline.dimensions.append(Dimension("F", RADIUS, 2, 2, 0.0, 0.5))
        # The scale is private, but the radius must follow it.
        # pylint: disable-next=protected-access
        scale: float = outline_diagram._scale(outline)
        self.assertGreater(scale, 0.0)
        sheet: Sheet = outline_sheet(outline, 0.1)
        arcs: list[ArcSegment] = [
            segment
            for segment in sheet.strokes[0].segments
            if isinstance(segment, ArcSegment)
        ]
        self.assertAlmostEqual(arcs[0].radius, 25.4 / 64 * scale)

    def test_folded(self) -> None:
        """A corner on a straight line is not rounded."""
        outline: Outline = Outline(
            points=[(0.0, 0.0), (2.0, 0.0), (4.0, 0.0), (2.0, 2.0)],
            dimensions=[Dimension("F", RADIUS, 1, 1, 0.0, 0.5)],
        )
        self.assertEqual(len(outline_sheet(outline, 0.1).strokes), 1)

    def test_marks(self) -> None:
        """Edge marks, a corner on an axis, a right angle."""
        level: list[Stroke] = drawn(
            box(), Dimension("", VERTICAL, 0, 1, 0, 0.5)
        )
        self.assertEqual(len(level), 2)
        self.assertLess(level[0].segments[0].start[1], 0.0)
        corner: list[Stroke] = drawn(
            box(), Dimension("", HORIZONTAL, ORIGIN, 3, 0, 0.5)
        )
        self.assertLess(corner[0].segments[0].start[0], 0.0)
        right: list[Stroke] = drawn(box(), Dimension("", ANGLE, 0, 1, 0, 0.5))
        self.assertEqual(right[0].segments[0].start, (3.5, 0.0))

    def test_revolve(self) -> None:
        """A revolved outline's mirror: dashed, the axis edge left off."""
        outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
        outline.dimensions = []
        sheet: Sheet = outline_sheet(outline, 0.5)
        mirror: list[Stroke] = [s for s in sheet.strokes if s.dashed]
        self.assertEqual(len(mirror), 3)
        self.assertEqual(mirror[0].segments[0].end, (-2.0, 1.2))
        self.assertIn("stroke-dasharray", svg(sheet))

    def test_text_sizes(self) -> None:
        """The outline's own text height, and a letter's font steps."""
        outline: Outline = box()
        outline.text_height = 0.3
        self.assertEqual(outline_sheet(outline).text_height, 0.3)
        plain: list[Stroke] = drawn(
            box(), Dimension("W", HORIZONTAL, ORIGIN, 1, -1.0, 0.5)
        )
        bigger: list[Stroke] = drawn(
            box(),
            Dimension("W", HORIZONTAL, ORIGIN, 1, -1.0, 0.5, font_step=2),
        )
        self.assertLess(
            bigger[2].segments[0].end[0], plain[2].segments[0].end[0]
        )

    def test_drill(self) -> None:
        """The example drill draws and writes good SVG."""
        outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
        ET.fromstring(svg(outline_sheet(outline)))


if __name__ == "__main__":
    unittest.main()
