"""Tests for `scraftcam.gui.outline_diagram`: outline files drawn."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scraftcam.diagram import TEXT, Sheet, Stroke, Weight, svg
from scraftcam.geometry import ArcSegment, LineSegment, Point
from scraftcam.gui import outline_diagram
from scraftcam.gui.dimensions import (
    ANGLE,
    DIAMETER,
    HORIZONTAL,
    LENGTH,
    ORIGIN,
    RADIUS,
    VERTICAL,
    Y_AXIS,
    Dimension,
    drawn_marks,
)
from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_diagram import dimension_strokes, outline_sheet
from scraftcam.gui.outline_file import (
    COUNTERBORED,
    PLAIN,
    Hole,
    Outline,
    outline_from_text,
)

DRILL: Path = Path("examples/shop/tools/drill.outline.toml")


# Function `plain_drill()`:
def plain_drill() -> Outline:
    """Return the example drill upright and uncut: the example lies on
    its side with strips hiding its middle (#314), which these tests
    of shapes leave off.

    Returns:
    * (`Outline`): The drill, `turns` 0 and no hides.
    """
    # The shape only: no turn, no strips.
    outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
    outline.turns = 0
    outline.hides.clear()
    return outline


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


# One test per kind of stroke: many methods by design.
class TestOutlineDiagram(unittest.TestCase):  # pylint: disable=too-many-public-methods
    """The outline, its dimensions and marks."""

    def test_holes(self) -> None:
        """Holes are thick circles to scale with center marks (#290): a
        plain one its letter's size, a counterbored one its screw's
        clearance and counterbore, a bad one a text height across."""
        # A 6 in long box, 4 steps: 1 in is 2/3 of a step.
        outline: Outline = box()
        outline.letters = [
            Letter("W", default="6 in"),
            Letter("D", default="0.25 in"),
            Letter("E", default="1/2 in"),
        ]
        outline.dimensions = [Dimension("W", HORIZONTAL, ORIGIN, 1, -1.0, 0.5)]
        outline.holes = [
            Hole(PLAIN, (1.0, 1.0), "D"),
            Hole(COUNTERBORED, (3.0, 1.0), "E"),
            Hole(PLAIN, (2.0, 1.0), "Q"),
        ]
        strokes: list[Stroke] = list(outline_sheet(outline, 0.5).strokes[1:])
        circles: list[Stroke] = [
            stroke for stroke in strokes if stroke.weight is Weight.THICK
        ]
        radii: list[float] = [
            circle.segments[0].radius  # type: ignore[union-attr]  # Arcs.
            for circle in circles
        ]
        step: float = 4.0 / 6.0
        expected: list[float] = [0.125, 17 / 64, 13 / 32]
        self.assertEqual(len(radii), 4)
        each: float
        want: float
        for each, want in zip(radii[:3], expected, strict=True):
            self.assertAlmostEqual(each, want * step)
        self.assertAlmostEqual(radii[3], 0.25)
        self.assertTrue(all(len(circle.segments) == 2 for circle in circles))

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

    def test_diameter(self) -> None:
        """A diameter runs from its corner's mirror image across the
        axis to the corner (#437)."""
        drill: Outline = plain_drill()
        corner: Point = drill.points[1]
        strokes: list[Stroke] = drawn(
            drill, Dimension("D", DIAMETER, ORIGIN, 1, -1.0, 0.5)
        )
        horizontal: list[Stroke] = drawn(
            plain_drill(), Dimension("D", HORIZONTAL, ORIGIN, 1, -1.0, 0.5)
        )
        self.assertEqual(len(strokes), len(horizontal))
        self.assertEqual(strokes[2].segments[0].start, (-corner[0], -1.0))

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

    def test_length_along(self) -> None:
        """A length dimension's letter sits where `along` puts it
        (#442: it was always in the middle)."""
        lefts: list[float] = []
        along: float
        for along in (0.2, 0.8):
            strokes: list[Stroke] = drawn(
                box(), Dimension("W", LENGTH, ORIGIN, 2, 1.0, along)
            )
            lefts.append(
                min(
                    point[0]
                    for stroke in strokes
                    if stroke.role == TEXT
                    for segment in stroke.segments
                    for point in (segment.start, segment.end)
                )
            )
        self.assertGreater(lefts[1] - lefts[0], 1.0)

    def test_angle(self) -> None:
        """An angle's arc is about where its edges' lines cross."""
        strokes: list[Stroke] = drawn(
            box(), Dimension("A", ANGLE, 0, 1, 1.0, 0.5, rays=(-1, 1))
        )
        arc = strokes[0].segments[0]
        assert isinstance(arc, ArcSegment)
        self.assertEqual(arc.center, (4.0, 0.0))
        self.assertGreater(arc.sweep, 0.0)

    def test_angle_reach(self) -> None:
        """An arc past an edge's end gets an extension line (#296)."""
        strokes: list[Stroke] = drawn(
            box(), Dimension("A", ANGLE, 0, 1, 3.0, 0.5, rays=(-1, 1))
        )
        lines: list[LineSegment] = [
            segment
            for stroke in strokes
            for segment in stroke.segments
            if isinstance(segment, LineSegment) and segment.start == (4.0, 2.0)
        ]
        self.assertEqual(len(lines), 1)
        self.assertAlmostEqual(lines[0].end[0], 4.0)
        self.assertAlmostEqual(lines[0].end[1], 3.25)
        near: list[Stroke] = drawn(
            box(), Dimension("A", ANGLE, 0, 1, 1.0, 0.5, rays=(-1, 1))
        )
        self.assertFalse(
            any(
                isinstance(segment, LineSegment)
                and segment.start == (4.0, 2.0)
                for stroke in near
                for segment in stroke.segments
            )
        )

    def test_angle_from_axis(self) -> None:
        """An angle from the Y axis crosses at the origin."""
        outline: Outline = plain_drill()
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
        outline: Outline = plain_drill()
        outline.letters.append(Letter("F", default="1/64 in", fillet=True))
        outline.dimensions.append(Dimension("F", RADIUS, 3, 3, 0.0, 0.5))
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
        """Marks are left out of the diagram (#451), but drawn for the
        editor's [Show Marks]: edge marks, a corner on an axis, a
        right angle."""
        for mark in (
            Dimension("", VERTICAL, 0, 1, 0, 0.5),
            Dimension("", HORIZONTAL, ORIGIN, 3, 0, 0.5),
            Dimension("", ANGLE, 0, 1, 0, 0.5),
        ):
            self.assertEqual(drawn(box(), mark), [])
        level: list[Stroke] = dimension_strokes(
            box(), Dimension("", VERTICAL, 0, 1, 0, 0.5), {}, 0.5
        )
        self.assertEqual(len(level), 2)
        self.assertLess(level[0].segments[0].start[1], 0.0)
        corner: list[Stroke] = dimension_strokes(
            box(), Dimension("", HORIZONTAL, ORIGIN, 3, 0, 0.5), {}, 0.5
        )
        self.assertLess(corner[0].segments[0].start[0], 0.0)
        right: list[Stroke] = dimension_strokes(
            box(), Dimension("", ANGLE, 0, 1, 0, 0.5), {}, 0.5
        )
        self.assertEqual(right[0].segments[0].start, (3.5, 0.0))

    def test_revolve(self) -> None:
        """A revolved outline's mirror: dashed, the axis edge left off."""
        outline: Outline = plain_drill()
        outline.dimensions = []
        sheet: Sheet = outline_sheet(outline, 0.5)
        mirror: list[Stroke] = [s for s in sheet.strokes if s.dashed]
        self.assertEqual(len(mirror), 4)  # An edge each side of FL (#434).
        corner: Point = outline.points[1]
        self.assertEqual(mirror[0].segments[0].end, (-corner[0], corner[1]))
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

    def test_stale_corners(self) -> None:
        """Corners saved before the values changed follow them (#299)."""
        outline: Outline = Outline(
            points=list(BOX),
            letters=[Letter("W", default="1 in"), Letter("H", default="1 in")],
            dimensions=drawn_marks(list(BOX))
            + [
                Dimension("W", HORIZONTAL, ORIGIN, 1),
                Dimension("H", VERTICAL, ORIGIN, 2),
            ],
        )
        corner: Point = outline_sheet(outline, 0.5).strokes[0].segments[1].end
        self.assertAlmostEqual(corner[0], corner[1])
        self.assertEqual(outline.points, BOX)

    def test_titles(self) -> None:
        """A letter's text carries its name, value and help (#267)."""
        letter: Letter = Letter("W", "Width", "1 in", "Across the box.")
        self.assertEqual(
            outline_diagram.letter_title(letter),
            "W: Width = 1 in.  Across the box.",
        )
        self.assertEqual(outline_diagram.letter_title(Letter("H")), "H = 1 in")
        outline: Outline = box()
        outline.letters.append(letter)
        strokes: list[Stroke] = drawn(
            outline, Dimension("W", HORIZONTAL, ORIGIN, 1)
        )
        titled: list[Stroke] = [stroke for stroke in strokes if stroke.title]
        self.assertTrue(titled)
        self.assertTrue(all(stroke.role == TEXT for stroke in titled))
        page: ET.Element = ET.fromstring(svg(outline_sheet(outline)))
        found: list[str] = [
            element.text or ""
            for element in page.iter("{http://www.w3.org/2000/svg}title")
        ]
        self.assertEqual(found, ["W: Width = 1 in.  Across the box."])

    def test_turned(self) -> None:
        """A turned diagram lies on its side, letters upright (#300)."""
        outline: Outline = box()
        outline.letters.append(Letter("W", default="1 in"))
        outline.dimensions.append(Dimension("W", HORIZONTAL, ORIGIN, 1))
        flat: Sheet = outline_sheet(outline, 0.5)
        outline.turns = 4
        self.assertEqual(outline_sheet(outline, 0.5), flat)
        outline.turns = 1
        turned: Sheet = outline_sheet(outline, 0.5)

        # The 4 x 2 box is 2 wide and 4 tall: +Y went to +X.
        corners: list[Point] = [
            segment.end for segment in turned.strokes[0].segments
        ]
        self.assertAlmostEqual(corners[0][0], 0.0)
        self.assertAlmostEqual(corners[0][1], -4.0)
        self.assertAlmostEqual(corners[1][0], 2.0)
        self.assertAlmostEqual(corners[1][1], -4.0)

        # The letter keeps its shape, moved with the drawing.
        def letter(sheet: Sheet) -> list[Stroke]:
            return [stroke for stroke in sheet.strokes if stroke.role == TEXT]

        before: list[Stroke] = letter(flat)
        after: list[Stroke] = letter(turned)
        self.assertEqual(len(before), len(after))
        shift: tuple[float, float] = (
            after[0].segments[0].start[0] - before[0].segments[0].start[0],
            after[0].segments[0].start[1] - before[0].segments[0].start[1],
        )
        old: Point
        new: Point
        for old, new in zip(
            (seg.end for stroke in before for seg in stroke.segments),
            (seg.end for stroke in after for seg in stroke.segments),
            strict=True,
        ):
            self.assertAlmostEqual(new[0] - old[0], shift[0])
            self.assertAlmostEqual(new[1] - old[1], shift[1])

    def test_upright_text(self) -> None:
        """Labels turn counterclockwise about their middles, lines stay
        (#300)."""
        line: Stroke = Stroke(
            (LineSegment((0.0, 0.0), (2.0, 0.0)),), Weight.THICK
        )
        label: Stroke = Stroke(
            (LineSegment((0.0, 0.0), (2.0, 0.0)),), Weight.THICK, role=TEXT
        )
        strokes: list[Stroke] = [line, label]
        self.assertEqual(outline_diagram.upright_text(strokes, 0), strokes)
        self.assertEqual(outline_diagram.upright_text(strokes, 4), strokes)
        turned: list[Stroke] = outline_diagram.upright_text(strokes, 1)
        self.assertEqual(turned[0], line)
        segment = turned[1].segments[0]
        self.assertAlmostEqual(segment.start[0], 1.0)
        self.assertAlmostEqual(segment.start[1], -1.0)
        self.assertAlmostEqual(segment.end[0], 1.0)
        self.assertAlmostEqual(segment.end[1], 1.0)

    def test_drill(self) -> None:
        """The example drill (on its side, its middle hidden) draws and
        writes good SVG."""
        outline: Outline = outline_from_text(DRILL.read_text(encoding="utf-8"))
        ET.fromstring(svg(outline_sheet(outline)))


if __name__ == "__main__":
    unittest.main()
