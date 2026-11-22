"""Tests for `scraftcam.diagram`: sheets of strokes and their SVG."""

import math
import unittest
import xml.etree.ElementTree as ET

from scraftcam.diagram import (
    MARGIN,
    TEXT,
    TEXT_FRACTION,
    THICK,
    Sheet,
    Stroke,
    Weight,
    _n,
    angle_dimension,
    center_mark,
    dimension_line,
    edge_mark,
    length_dimension,
    note,
    on_paper,
    radius_dimension,
    right_angle,
    starting_height,
    svg,
)
from scraftcam.geometry import (
    ArcSegment,
    LineSegment,
    Loop,
    Point,
    XYSegment,
)

SVG: str = "{http://www.w3.org/2000/svg}"


def square(side: float) -> Loop:
    """Return a counter-clockwise square with a corner at the origin."""
    corners: list[tuple[float, float]] = [
        (0.0, 0.0),
        (side, 0.0),
        (side, side),
        (0.0, side),
    ]
    segments: tuple[XYSegment, ...] = tuple(
        LineSegment(corners[index], corners[(index + 1) % 4])
        for index in range(4)
    )
    return Loop("square", segments)


def circle(x: float, y: float, radius: float) -> Loop:
    """Return a whole circle starting due east of its center."""
    start: tuple[float, float] = (x + radius, y)
    arc: ArcSegment = ArcSegment(start, start, (x, y), radius, 2 * math.pi)
    return Loop("circle", (arc,))


# Function `loop_sheet()`:
def loop_sheet(loops: tuple[Loop, ...], text_height: float = 0.0) -> Sheet:
    """Return loops drawn thick on paper, as an outline's sheet is."""
    strokes: tuple[Stroke, ...] = tuple(
        Stroke(loop.segments, Weight.THICK) for loop in loops
    )
    if text_height <= 0.0:
        text_height = starting_height(strokes)
    return on_paper(strokes, text_height)


class TestSheet(unittest.TestCase):
    """The strokes and paper of `on_paper()` and `starting_height()`."""

    def test_square(self) -> None:
        """A square: one thick stroke, paper a margin wider."""
        sheet: Sheet = loop_sheet((square(30.0),))
        height: float = TEXT_FRACTION * 30.0
        self.assertAlmostEqual(sheet.text_height, height)
        self.assertEqual(len(sheet.strokes), 1)
        self.assertIs(sheet.strokes[0].weight, Weight.THICK)
        self.assertAlmostEqual(sheet.low[0], -MARGIN * height)
        self.assertAlmostEqual(sheet.high[1], 30.0 + MARGIN * height)

    def test_given_height(self) -> None:
        """A text height given is kept."""
        sheet: Sheet = loop_sheet((square(30.0),), 2.0)
        self.assertEqual(sheet.text_height, 2.0)
        self.assertAlmostEqual(sheet.low[1], -2.0 * MARGIN)

    def test_arc_bounds(self) -> None:
        """An arc's bounds include the points it bulges through."""
        loop: Loop = circle(0.0, 0.0, 5.0)
        sheet: Sheet = loop_sheet((loop,), 1.0)
        self.assertAlmostEqual(sheet.low[0], -5.0 - MARGIN)
        self.assertAlmostEqual(sheet.high[1], 5.0 + MARGIN)

    def test_holes(self) -> None:
        """Each loop is a stroke of its own."""
        sheet: Sheet = loop_sheet((square(30.0), circle(10.0, 10.0, 3.0)))
        self.assertEqual(len(sheet.strokes), 2)


def ends(stroke: Stroke) -> tuple[Point, Point]:
    """Return where a stroke starts and ends."""
    return stroke.segments[0].start, stroke.segments[-1].end


class TestDimensions(unittest.TestCase):
    """Length and angle dimensions."""

    def test_length(self) -> None:
        """Extension lines, a broken line, arrows out, the letter."""
        strokes: list[Stroke] = length_dimension(
            (0.0, 0.0), (20.0, 0.0), -5.0, "L", 2.0
        )
        # Extension lines: from a gap below the point to past the line.
        first: Point
        last: Point
        first, last = ends(strokes[0])
        self.assertAlmostEqual(first[1], -1.0)
        self.assertAlmostEqual(last[1], -6.0)
        # The dimension line, broken around the letter in the middle.
        left: Point = ends(strokes[2])[1]
        right: Point = ends(strokes[3])[0]
        self.assertAlmostEqual(left[1], -5.0)
        self.assertLess(left[0], 10.0)
        self.assertGreater(right[0], 10.0)
        self.assertAlmostEqual(10.0 - left[0], right[0] - 10.0)
        # Arrowheads: filled, tips on the extension lines.
        self.assertTrue(strokes[4].filled and strokes[5].filled)
        self.assertEqual(ends(strokes[4])[0], (0.0, -5.0))
        self.assertEqual(ends(strokes[5])[0], (20.0, -5.0))
        self.assertGreater(len(strokes), 6)

    def test_length_vertical(self) -> None:
        """A vertical dimension's break fits an upright letter."""
        strokes: list[Stroke] = length_dimension(
            (0.0, 0.0), (0.0, 20.0), -5.0, "H", 2.0
        )
        self.assertAlmostEqual(ends(strokes[2])[1][0], 5.0)
        self.assertAlmostEqual(ends(strokes[2])[1][1], 10.0 - 2.0)

    def test_feet_apart(self) -> None:
        """Feet at different heights: each extension line its own."""
        strokes: list[Stroke] = dimension_line(
            ((0.0, 0.0), (10.0, 4.0)),
            ((0.0, 8.0), (10.0, 8.0)),
            letter="X",
            height=2.0,
        )
        self.assertEqual(ends(strokes[0]), ((0.0, 1.0), (0.0, 9.0)))
        self.assertEqual(ends(strokes[1]), ((10.0, 5.0), (10.0, 9.0)))

    def test_on_its_line(self) -> None:
        """A foot on the line gets no extension line."""
        strokes: list[Stroke] = dimension_line(
            ((0.0, 0.0), (10.0, 0.0)),
            ((0.0, 0.0), (10.0, 0.0)),
            letter="X",
            height=2.0,
        )
        self.assertFalse(strokes[0].filled)
        self.assertTrue(strokes[2].filled)

    def test_letter_past(self) -> None:
        """A letter past an arrowhead: one line, run out to it and a
        tail past the far end; the arrows outside, pointing in
        (#321)."""
        before: list[Stroke] = dimension_line(
            ((0.0, 0.0), (4.0, 0.0)),
            ((0.0, 0.0), (4.0, 0.0)),
            letter="X",
            height=1.0,
            along=-1.0,
        )
        self.assertLess(ends(before[0])[0][0], 0.0)
        self.assertEqual(ends(before[0])[1], (6.0, 0.0))
        self.assertTrue(before[1].filled)

        # Each arrow lies outside its end, its tip on the end.
        self.assertTrue(all(seg.start[0] <= 0.0 for seg in before[1].segments))
        self.assertTrue(all(seg.start[0] >= 4.0 for seg in before[2].segments))
        after: list[Stroke] = dimension_line(
            ((0.0, 0.0), (4.0, 0.0)),
            ((0.0, 0.0), (4.0, 0.0)),
            letter="X",
            height=1.0,
            along=2.0,
        )
        self.assertGreater(ends(after[0])[1][0], 4.0)
        self.assertEqual(ends(after[0])[0], (-2.0, 0.0))

    def test_letter_clear(self) -> None:
        """A letter just past its end is drawn clear of the arrowhead
        (#323): at least an arrow and half the letter beyond."""
        strokes: list[Stroke] = dimension_line(
            ((0.0, 0.0), (4.0, 0.0)),
            ((0.0, 0.0), (4.0, 0.0)),
            letter="X",
            height=1.0,
            along=-0.01,
        )
        letter: list[float] = [
            x
            for stroke in strokes
            if stroke.role == TEXT
            for seg in stroke.segments
            for x in (seg.start[0], seg.end[0])
        ]
        self.assertLess(max(letter), -1.0)

        # An angle's letter likewise clears its arrow.
        arcs: list[Stroke] = angle_dimension(
            (0.0, 0.0), (0.0, 90.0), 10.0, letter="A", height=1.0, along=1.01
        )
        tops: list[float] = [
            x
            for stroke in arcs
            if stroke.role == TEXT
            for seg in stroke.segments
            for x in (seg.start[0], seg.end[0])
        ]
        self.assertLess(max(tops), -1.0)

    def test_angle_past(self) -> None:
        """An angle's letter past a ray: one arc run on to it and a
        tail past the other ray, the arrows pointing in (#321)."""
        strokes: list[Stroke] = angle_dimension(
            (0.0, 0.0), (0.0, 90.0), 10.0, letter="A", height=1.0, along=1.5
        )
        arcs: list[Stroke] = [
            stroke for stroke in strokes if stroke.role != TEXT
        ]
        self.assertFalse(arcs[0].filled)
        self.assertTrue(arcs[1].filled and arcs[2].filled)

        # The arc starts a tail below the first ray (Y < 0).
        self.assertLess(ends(arcs[0])[0][1], 0.0)

        # The first ray's arrow lies below it, the second's left of it.
        self.assertTrue(all(seg.start[1] <= 1e-9 for seg in arcs[1].segments))
        self.assertTrue(all(seg.start[0] <= 1e-9 for seg in arcs[2].segments))

    def test_angle(self) -> None:
        """Two arcs around the letter, arrows at the rays."""
        strokes: list[Stroke] = angle_dimension(
            (0.0, 0.0), (0.0, 90.0), 10.0, letter="A", height=1.0
        )
        arc: XYSegment = strokes[0].segments[0]
        assert isinstance(arc, ArcSegment)
        self.assertAlmostEqual(arc.start[0], 10.0)
        self.assertGreater(arc.sweep, 0.0)
        tip: Point = ends(strokes[3])[0]
        self.assertAlmostEqual(tip[0], 0.0)
        self.assertAlmostEqual(tip[1], 10.0)
        self.assertTrue(strokes[2].filled)

    def test_angle_wraps(self) -> None:
        """Rays given past 360 degrees still sweep the short way."""
        strokes: list[Stroke] = angle_dimension(
            (0.0, 0.0), (350.0, 10.0), 10.0, letter="A", height=1.0
        )
        arc: XYSegment = strokes[0].segments[0]
        assert isinstance(arc, ArcSegment)
        self.assertLess(arc.sweep, math.radians(10.0))

    def test_radius(self) -> None:
        """A leader from the center, its arrow's tip on the arc."""
        strokes: list[Stroke] = radius_dimension(
            (0.0, 0.0), 5.0, 0.0, letter="R", height=1.0
        )
        self.assertEqual(ends(strokes[0]), ((0.0, 0.0), (7.0, 0.0)))
        self.assertTrue(strokes[1].filled)
        self.assertEqual(ends(strokes[1])[0], (5.0, 0.0))
        self.assertGreater(len(strokes), 2)

    def test_center_mark(self) -> None:
        """A cross and four center lines past the circle."""
        strokes: list[Stroke] = center_mark((0.0, 0.0), 5.0, 2.0)
        self.assertEqual(len(strokes), 8)
        self.assertEqual(ends(strokes[1]), ((1.5, 0.0), (6.0, 0.0)))
        tiny: list[Stroke] = center_mark((0.0, 0.0), 0.1, 2.0)
        self.assertEqual(len(tiny), 4)

    def test_paper(self) -> None:
        """The paper takes in the dimensions."""
        strokes: list[Stroke] = length_dimension(
            (0.0, 0.0), (20.0, 0.0), -5.0, "L", 2.0
        )
        self.assertAlmostEqual(on_paper(tuple(strokes), 2.0).low[1], -10.0)

    def test_filled_svg(self) -> None:
        """A filled stroke is filled with ink in the SVG."""
        strokes: list[Stroke] = length_dimension(
            (0.0, 0.0), (20.0, 0.0), -5.0, "L", 2.0
        )
        self.assertIn(
            'class="ink solid" fill="black"',
            svg(on_paper(tuple(strokes), 2.0)),
        )


class TestMarks(unittest.TestCase):
    """Level and upright marks, right angles and notes."""

    def test_level(self) -> None:
        """A level mark sits outside its edge, its line across."""
        strokes: list[Stroke] = edge_mark(
            (0.0, 0.0), (10.0, 0.0), (5.0, 5.0), level=True, height=2.0
        )
        box: Stroke = strokes[0]
        self.assertEqual(len(box.segments), 4)
        self.assertEqual(box.segments[0].start, (4.0, -3.0))
        line: Stroke = strokes[1]
        self.assertIs(line.weight, Weight.THICK)
        self.assertEqual(ends(line), ((4.5, -2.0), (5.5, -2.0)))

    def test_upright(self) -> None:
        """An upright mark's line runs up, out from a vertical edge."""
        strokes: list[Stroke] = edge_mark(
            (0.0, 10.0), (0.0, 0.0), (5.0, 5.0), level=False, height=2.0
        )
        self.assertEqual(ends(strokes[1]), ((-2.0, 4.5), (-2.0, 5.5)))

    def test_right_angle(self) -> None:
        """The square's two outer sides, along both edges."""
        strokes: list[Stroke] = right_angle(
            (0.0, 0.0), (10.0, 0.0), (0.0, 10.0), 2.0
        )
        self.assertEqual(ends(strokes[0]), ((2.0, 0.0), (0.0, 2.0)))
        self.assertEqual(strokes[0].segments[0].end, (2.0, 2.0))

    def test_note(self) -> None:
        """A note starts at the box's left, below it."""
        outline: tuple[Stroke, ...] = (
            Stroke(square(30.0).segments, Weight.THICK),
        )
        strokes: list[Stroke] = note(outline, "UDF", 1.0)
        xs: list[float] = [
            point
            for stroke in strokes
            for segment in stroke.segments
            for point in (segment.start[0], segment.end[0])
        ]
        ys: list[float] = [
            point
            for stroke in strokes
            for segment in stroke.segments
            for point in (segment.start[1], segment.end[1])
        ]
        self.assertGreaterEqual(min(xs), 0.0)
        self.assertLess(min(xs), 1.0)
        self.assertAlmostEqual(max(ys), -1.0)


class TestSvg(unittest.TestCase):
    """The SVG text of `svg()`."""

    def test_document(self) -> None:
        """Paper painted, sizes in mm, Y negated, widths from `h`."""
        sheet: Sheet = loop_sheet((square(30.0),), 1.0)
        root: ET.Element = ET.fromstring(svg(sheet))
        self.assertEqual(root.get("width"), "102mm")
        self.assertEqual(
            ET.fromstring(svg(sheet, letter_mm=1.0)).get("width"), "34mm"
        )
        self.assertEqual(root.get("viewBox"), "-2 -32 34 34")
        rect: ET.Element | None = root.find(f"{SVG}rect")
        assert rect is not None
        self.assertEqual(rect.get("fill"), "white")
        path: ET.Element | None = root.find(f"{SVG}path")
        assert path is not None
        self.assertEqual(path.get("d"), "M 0 0 L 30 0 L 30 -30 L 0 -30 L 0 0")
        self.assertEqual(path.get("stroke-width"), _n(THICK))
        self.assertEqual(path.get("stroke"), "black")

    def test_inks(self) -> None:
        """The ink and paper are the caller's."""
        sheet: Sheet = loop_sheet((square(1.0),))
        text: str = svg(sheet, ink="white", paper="black")
        self.assertIn('fill="black"', text)
        self.assertIn('stroke="white"', text)

    def test_unthemed(self) -> None:
        """Files are black on white whatever the viewer's theme
        (#285)."""
        sheet: Sheet = loop_sheet((square(1.0),))
        text: str = svg(sheet)
        self.assertNotIn("<style>", text)
        self.assertIn('fill="white"', text)
        self.assertIn('stroke="black"', text)

    def test_circle(self) -> None:
        """A whole circle is two half arcs, counter-clockwise as flag 0."""
        sheet: Sheet = Sheet(
            (Stroke(circle(0.0, 0.0, 5.0).segments, Weight.THIN),),
            (-6.0, -6.0),
            (6.0, 6.0),
            1.0,
        )
        path: ET.Element | None = ET.fromstring(svg(sheet)).find(f"{SVG}path")
        assert path is not None
        self.assertEqual(
            path.get("d"), "M 5 0 A 5 5 0 0 0 -5 0 A 5 5 0 0 0 5 0"
        )

    def test_clockwise(self) -> None:
        """A clockwise quarter arc has sweep flag 1."""
        arc: ArcSegment = ArcSegment(
            (0.0, 5.0), (5.0, 0.0), (0.0, 0.0), 5.0, -math.pi / 2
        )
        sheet: Sheet = Sheet(
            (Stroke((arc,), Weight.THIN),), (0.0, 0.0), (6.0, 6.0), 1.0
        )
        self.assertIn("A 5 5 0 0 1 5 0", svg(sheet))

    def test_numbers(self) -> None:
        """Numbers have at most 4 decimals and never `-0`."""
        self.assertEqual(_n(1.23456), "1.2346")
        self.assertEqual(_n(2.0), "2")
        self.assertEqual(_n(-0.00001), "0")


if __name__ == "__main__":
    unittest.main()
