"""Diagrams drawn as on paper: one list of ink shapes, two back ends.

A diagram is a `Sheet`: ink `Stroke`s (lines and arcs) laid out in
the drawing's own millimeters, with Y up.  The same sheet is written
as SVG text (`svg()`, here, no Qt) and painted by the outline editor
(`gui/diagram_qt.py`), so the two never differ.  The shapes carry no
colors, only ink: the back end picks the ink and the paper (black on
white for files, `T.sfoe~6.4` #274, #279).

Every size comes from the sheet's text height `h` (#277, after ASME
Y14.2, kept simple): outlines `THICK` x h wide, everything else
`THIN` x h, a margin of `MARGIN` x h around the drawing.
"""

import itertools
import math
from dataclasses import dataclass, field
from enum import Enum
from html import escape

from . import hershey
from .geometry import ArcSegment, LineSegment, Loop, Point, XYSegment
from .outline import Profile

# Line widths and the margin, as fractions of the text height (#277).
THICK: float = 0.2
THIN: float = 0.1
MARGIN: float = 2.0

# The style of a themed SVG (#287): dark when the viewer prefers it,
# black on white on paper; the print rule comes last, so it wins.
STYLE: str = (
    "<style>"
    "@media (prefers-color-scheme: dark)"
    " { .paper { fill: black } .ink { stroke: white }"
    " .solid { fill: white } }"
    " @media print"
    " { .paper { fill: white } .ink { stroke: black }"
    " .solid { fill: black } }"
    "</style>"
)

# The roles of a dimension line's strokes and of text's
# (`Stroke.role`).
LINE: str = "line"
TEXT: str = "text"

# A dash's length, in text heights; the gaps are half a text height.
DASH: float = 1.0

# Each [Font +] makes a letter this many times bigger (#273).
FONT_STEP: float = 1.25

# How tall letters print (mm), about ASME's 0.12 in (#277, #292).
LETTER_MM: float = 3.0

# The starting text height: this fraction of the drawing's larger
# side (#281); the user grows or shrinks it from there.
TEXT_FRACTION: float = 1.0 / 30.0


# Class `Weight`:
class Weight(Enum):
    """How heavy a stroke's line is.

    Attributes:
    * `THICK`: The outline itself.
    * `THIN`: Dimension, extension and letter lines.
    """

    THICK = "thick"
    THIN = "thin"


# Class `Stroke`:
@dataclass(frozen=True, slots=True)
class Stroke:
    """A run of connected lines and arcs drawn in one pen stroke.

    Attributes:
    * `segments` (`tuple[XYSegment, ...]`):
      The lines and arcs, each starting where the one before it ends.
    * `weight` (`Weight`): How heavy its line is.
    * `filled` (`bool`):
      Whether the closed stroke is also filled with ink (arrowheads).
    * `dashed` (`bool`):
      Whether it is dashed (a revolved outline's mirror half).
    * `role` (`str`):
      What it is, when that matters later (`LINE`: a dimension line,
      which a hide strip ends with an S; `TEXT`: a letter's lines);
      "" otherwise.
    * `title` (`str`):
      What a viewer shows when the pointer rests on it (#267); ""
      for none.

    Constructor:
    * `Stroke(segments, weight, filled, dashed, role, title)`
    """

    # Constructor arguments:
    segments: tuple[XYSegment, ...] = field(init=True)
    weight: Weight = field(init=True)
    filled: bool = field(init=True, default=False)
    dashed: bool = field(init=True, default=False)
    role: str = field(init=True, default="")
    title: str = field(init=True, default="")


# Class `Sheet`:
@dataclass(frozen=True, slots=True)
class Sheet:
    """A diagram: its strokes, the box they fill, and its text height.

    Attributes:
    * `strokes` (`tuple[Stroke, ...]`): Everything inked.
    * `low` (`Point`): The lower left corner of the paper (mm).
    * `high` (`Point`): The upper right corner of the paper (mm).
    * `text_height` (`float`): The text height `h` (mm).

    Constructor:
    * `Sheet(strokes, low, high, text_height)`
    """

    # Constructor arguments:
    strokes: tuple[Stroke, ...] = field(init=True)
    low: Point = field(init=True)
    high: Point = field(init=True)
    text_height: float = field(init=True)


# Function `profile_sheet()`:
def profile_sheet(profile: Profile, text_height: float = 0.0) -> Sheet:
    """Return a sheet with a profile's outline and holes drawn on it.

    Arguments:
    * `profile` (`Profile`): The profile (mm).
    * `text_height` (`float`):
      The text height (mm); 0 picks one from the profile's size.

    Returns:
    * (`Sheet`): The sheet, its paper the drawing plus a margin.
    """
    # Each loop is one thick stroke.
    loops: list[Loop] = [profile.outer, *profile.holes]
    strokes: tuple[Stroke, ...] = tuple(
        Stroke(loop.segments, Weight.THICK) for loop in loops
    )

    # The paper is the drawing's box plus a margin of text heights.
    if text_height <= 0.0:
        text_height = starting_height(strokes)
    return on_paper(strokes, text_height)


# Function `starting_height()`:
def starting_height(strokes: tuple[Stroke, ...]) -> float:
    """Return the starting text height for some strokes (#281).

    Arguments:
    * `strokes` (`tuple[Stroke, ...]`): The outline's strokes.

    Returns:
    * (`float`): `TEXT_FRACTION` of the larger side of their box.
    """
    # Measure the box's larger side.
    low: Point
    high: Point
    low, high = _bounds(strokes)
    return TEXT_FRACTION * max(high[0] - low[0], high[1] - low[1])


# Function `on_paper()`:
def on_paper(strokes: tuple[Stroke, ...], text_height: float) -> Sheet:
    """Return a sheet whose paper is the strokes' box plus a margin.

    Arguments:
    * `strokes` (`tuple[Stroke, ...]`): Everything inked.
    * `text_height` (`float`): The text height (mm).

    Returns:
    * (`Sheet`): The sheet.
    """
    # Widen the box by `MARGIN` text heights all round.
    low: Point
    high: Point
    low, high = _bounds(strokes)
    margin: float = MARGIN * text_height
    return Sheet(
        strokes,
        (low[0] - margin, low[1] - margin),
        (high[0] + margin, high[1] + margin),
        text_height,
    )


# Function `text()`:
def text(label: str, center: Point, height: float) -> list[Stroke]:
    """Return a label's strokes, upright and centered on a point.

    Arguments:
    * `label` (`str`): The text.
    * `center` (`Point`): The middle of its box.
    * `height` (`float`): The height of a capital letter.

    Returns:
    * (`list[Stroke]`): One thin stroke per pen stroke.
    """
    # Start half its width left of, and half its height below, center.
    origin: Point = (
        center[0] - hershey.width(label, height) / 2.0,
        center[1] - height / 2.0,
    )
    return [
        Stroke(polyline(line).segments, Weight.THIN, role=TEXT)
        for line in hershey.strokes(label, origin, height)
        if len(line) > 1
    ]


# Function `length_dimension()`:
def length_dimension(
    start: Point, end: Point, offset: float, letter: str, height: float
) -> list[Stroke]:
    """Return a length dimension, its line parallel to its points.

    The dimension line runs `offset` from the measured points, to the
    left of `start` -> `end` when positive (`dimension_line()`).

    Arguments:
    * `start` (`Point`): One measured point.
    * `end` (`Point`): The other.
    * `offset` (`float`): How far out the dimension line is.
    * `letter` (`str`): Its letter.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): Its thin strokes and filled arrowheads.
    """
    # Out from the measured points, to the left when positive.
    length: float = max(math.dist(start, end), 1e-12)
    out: Point = (
        -(end[1] - start[1]) / length,
        (end[0] - start[0]) / length,
    )
    return dimension_line(
        (start, end),
        (_step(start, out, offset), _step(end, out, offset)),
        letter=letter,
        height=height,
    )


# Function `dimension_line()`:
# Type hints on every variable inflate its count of locals.
# pylint: disable-next=too-many-locals
def dimension_line(
    feet: tuple[Point, Point],
    ends: tuple[Point, Point],
    *,
    letter: str,
    height: float,
    along: float = 0.5,
) -> list[Stroke]:
    """Return a dimension: extension lines, its line, arrows, letter.

    An extension line runs from each foot (a measured point), a gap
    of `height` / 2 off it, out to its end of the dimension line and
    `height` / 2 past; the arrows point out to the ends; the letter
    sits upright `along` the line, in a break in it, or past an
    arrowhead (below 0 or above 1) with the line run out to it (#277:
    arrowheads `height` long and a third as wide).

    Arguments:
    * `feet` (`tuple[Point, Point]`): The measured points.
    * `ends` (`tuple[Point, Point]`): The dimension line's ends.
    * `letter` (`str`): Its letter.
    * `height` (`float`): The text height.
    * `along` (`float`): Where the letter sits, as a share of the line
      from its first end.

    Returns:
    * (`list[Stroke]`): Its thin strokes and filled arrowheads.
    """
    # An extension line from each foot, when it is off the line.
    gap: float = height / 2.0
    found: list[Stroke] = []
    foot: Point
    end: Point
    for foot, end in zip(feet, ends, strict=True):
        reach: float = math.dist(foot, end)
        if reach > gap:
            out: Point = (
                (end[0] - foot[0]) / reach,
                (end[1] - foot[1]) / reach,
            )
            found.append(
                polyline(
                    [_step(foot, out, gap), _step(foot, out, reach + gap)]
                )
            )

    # The line's direction, and where the letter sits on it.
    first: Point = ends[0]
    last: Point = ends[1]
    length: float = max(math.dist(first, last), 1e-12)
    way: Point = ((last[0] - first[0]) / length, (last[1] - first[1]) / length)
    spot: Point = _step(first, way, along * length)
    half: float = (
        abs(way[0]) * hershey.width(letter, height) / 2.0
        + abs(way[1]) * height / 2.0
        + gap
    )

    # The line: broken around the letter, or run out past an arrow to it.
    pieces: list[list[Point]]
    if along < 0.0:
        pieces = [[_step(spot, way, half), last]]
    elif along > 1.0:
        pieces = [[first, _step(spot, way, -half)]]
    else:
        pieces = [
            [first, _step(spot, way, -half)],
            [_step(spot, way, half), last],
        ]
    found.extend(
        Stroke(polyline(piece).segments, Weight.THIN, role=LINE)
        for piece in pieces
    )

    # An arrowhead at each end, pointing out to its extension line.
    found.append(_arrowhead(first, way, height))
    found.append(_arrowhead(last, (-way[0], -way[1]), height))
    found.extend(text(letter, spot, height))
    return found


# Function `angle_dimension()`:
# Type hints on every variable inflate its count of locals; the
# letter's settings (`letter`, `height`, `along`) are keyword-only.
# pylint: disable-next=too-many-locals,too-many-arguments
def angle_dimension(
    vertex: Point,
    rays: tuple[float, float],
    radius: float,
    *,
    letter: str,
    height: float,
    along: float = 0.5,
) -> list[Stroke]:
    """Return an angle dimension: an arc with arrows, and its letter.

    The arc runs counter-clockwise from the first ray to the second,
    `radius` from the vertex, broken around the letter `along` it;
    an arc too short for the break is drawn whole, its letter just
    outside it.  The edges themselves serve as extension lines.

    Arguments:
    * `vertex` (`Point`): Where the two rays meet.
    * `rays` (`tuple[float, float]`):
      The two rays' directions (degrees), the second counter-clockwise
      from the first.
    * `radius` (`float`): How far out the arc is.
    * `letter` (`str`): Its letter.
    * `height` (`float`): The text height.
    * `along` (`float`): Where the letter sits, as a share of the arc
      from the first ray.

    Returns:
    * (`list[Stroke]`): Its thin arcs, filled arrowheads and letter.
    """
    # The arc's ends and the letter's place, in radians
    # counter-clockwise.
    start: float = math.radians(rays[0])
    sweep: float = math.radians(rays[1] - rays[0]) % (2.0 * math.pi)
    end: float = start + sweep
    middle: float = start + sweep * along
    center: Point = _step(vertex, (math.cos(middle), math.sin(middle)), radius)

    # Break the arc around the letter: half its box plus a gap.
    tangent: Point = (-math.sin(middle), math.cos(middle))
    half: float = (
        abs(tangent[0]) * hershey.width(letter, height) / 2.0
        + abs(tangent[1]) * height / 2.0
        + height / 2.0
    ) / radius
    found: list[Stroke]
    if start < middle - half and middle + half < end:
        found = [
            _arc(vertex, radius, start, middle - half),
            _arc(vertex, radius, middle + half, end),
        ]
    else:
        found = [_arc(vertex, radius, start, end)]
        center = _step(
            vertex, (math.cos(middle), math.sin(middle)), radius + height
        )

    # An arrowhead at each end, along the arc's tangent there.
    found.append(
        _arrowhead(
            _on_circle(vertex, radius, start),
            (-math.sin(start), math.cos(start)),
            height,
        )
    )
    found.append(
        _arrowhead(
            _on_circle(vertex, radius, end),
            (math.sin(end), -math.cos(end)),
            height,
        )
    )
    found.extend(text(letter, center, height))
    return found


# Function `radius_dimension()`:
def radius_dimension(
    center: Point,
    radius: float,
    angle: float,
    *,
    letter: str,
    height: float,
) -> list[Stroke]:
    """Return a radius dimension: a leader out through the arc.

    The leader runs from the center out through the arc at `angle`
    and `2 * height` past it, an arrowhead on the arc pointing out,
    and the letter just beyond the leader's end.

    Arguments:
    * `center` (`Point`): The arc's center.
    * `radius` (`float`): Its radius.
    * `angle` (`float`): Where the leader crosses it (degrees).
    * `letter` (`str`): Its letter.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The leader, its arrowhead and its letter.
    """
    # The leader from the center to past the arc.
    out: Point = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    tip: Point = _step(center, out, radius)
    end: Point = _step(tip, out, 2.0 * height)
    found: list[Stroke] = [
        polyline([center, end]),
        _arrowhead(tip, (-out[0], -out[1]), height),
    ]

    # The letter beyond the end, its box clear of the leader.
    reach: float = (
        abs(out[0]) * hershey.width(letter, height) / 2.0
        + abs(out[1]) * height / 2.0
        + height / 2.0
    )
    found.extend(text(letter, _step(end, out, reach), height))
    return found


# Function `center_mark()`:
def center_mark(center: Point, radius: float, height: float) -> list[Stroke]:
    """Return a hole's center mark: a small cross and center lines.

    A cross `height` across at the center, then after a gap of
    `height` / 4, center lines out to `height` / 2 past the circle,
    across and up.

    Arguments:
    * `center` (`Point`): The hole's center.
    * `radius` (`float`): Its radius.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): Its thin strokes.
    """
    # In each of the four directions, a dash of the cross and a line.
    cross: float = height / 2.0
    start: float = cross + height / 4.0
    reach: float = radius + height / 2.0
    found: list[Stroke] = []
    direction: Point
    for direction in ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)):
        found.append(polyline([center, _step(center, direction, cross)]))
        if reach > start:
            found.append(
                polyline(
                    [
                        _step(center, direction, start),
                        _step(center, direction, reach),
                    ]
                )
            )
    return found


# Function `edge_mark()`:
def edge_mark(
    start: Point, end: Point, inside: Point, *, level: bool, height: float
) -> list[Stroke]:
    """Return a level or upright mark: a box holding `—` or `|`.

    The box, `height` on a side, sits out from the edge's middle, away
    from `inside`, a gap of `height` / 2 between them (#233).

    Arguments:
    * `start` (`Point`): The edge's start.
    * `end` (`Point`): Its end.
    * `inside` (`Point`): A point inside the outline (its middle).
    * `level` (`bool`): True for `—` (level), False for `|` (upright).
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The box (thin) and its line (thick).
    """
    # Out from the edge's middle, away from the inside.
    here: Point = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
    out: Point = (start[1] - end[1], end[0] - start[0])
    if out[0] * (here[0] - inside[0]) + out[1] * (here[1] - inside[1]) < 0:
        out = (-out[0], -out[1])
    size: float = math.hypot(out[0], out[1])
    middle: Point = _step(here, (out[0] / size, out[1] / size), height)
    return mark_box(middle, level=level, height=height)


# Function `mark_box()`:
def mark_box(middle: Point, *, level: bool, height: float) -> list[Stroke]:
    """Return a mark's box, `height` on a side, and its line.

    Arguments:
    * `middle` (`Point`): The box's middle.
    * `level` (`bool`): True for `—` (level), False for `|` (upright).
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The box (thin) and its line (thick), inset a
      quarter of the box from its sides.
    """
    # The box, then the line across it.
    half: float = height / 2.0
    x: float = middle[0]
    y: float = middle[1]
    box: Stroke = polyline(
        [
            (x - half, y - half),
            (x + half, y - half),
            (x + half, y + half),
            (x - half, y + half),
            (x - half, y - half),
        ]
    )
    inset: float = half / 2.0
    line: list[Point] = (
        [(x - inset, y), (x + inset, y)]
        if level
        else [(x, y - inset), (x, y + inset)]
    )
    return [box, Stroke(polyline(line).segments, Weight.THICK)]


# Function `right_angle()`:
def right_angle(
    corner: Point, before: Point, after: Point, height: float
) -> list[Stroke]:
    """Return a right angle's square, tucked into its corner (#236).

    Arguments:
    * `corner` (`Point`): The corner.
    * `before` (`Point`): The far end of one of its edges.
    * `after` (`Point`): The far end of the other.
    * `height` (`float`): The text height (the square's side).

    Returns:
    * (`list[Stroke]`): Its two outer sides, one thin stroke.
    """
    # A side's length along each edge from the corner.
    ways: list[Point] = []
    other: Point
    for other in (before, after):
        size: float = max(math.dist(corner, other), 1e-12)
        ways.append(
            (
                (other[0] - corner[0]) / size,
                (other[1] - corner[1]) / size,
            )
        )
    first: Point = _step(corner, ways[0], height)
    return [
        polyline(
            [
                first,
                _step(first, ways[1], height),
                _step(corner, ways[1], height),
            ]
        )
    ]


# Function `note()`:
def note(
    strokes: tuple[Stroke, ...], label: str, height: float
) -> list[Stroke]:
    """Return a note's text, under the strokes' box at its left.

    Arguments:
    * `strokes` (`tuple[Stroke, ...]`): What is drawn so far.
    * `label` (`str`): The note (e.g. "All undimensioned fillets are
      radius UDF").
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The note's strokes, its top `height` below the
      box.
    """
    # Center the text so its left end lines up with the box's.
    low: Point
    low, _ = _bounds(strokes)
    middle: Point = (
        low[0] + hershey.width(label, height) / 2.0,
        low[1] - 1.5 * height,
    )
    return text(label, middle, height)


# Function `_arc()`:
def _arc(center: Point, radius: float, start: float, end: float) -> Stroke:
    """Return a thin counter-clockwise arc between two angles.

    Arguments:
    * `center` (`Point`): The arc's center.
    * `radius` (`float`): Its radius.
    * `start` (`float`): Where it starts (radians).
    * `end` (`float`): Where it ends (radians), past `start`.

    Returns:
    * (`Stroke`): The arc.
    """
    # One arc segment, swept counter-clockwise.
    return Stroke(
        (
            ArcSegment(
                _on_circle(center, radius, start),
                _on_circle(center, radius, end),
                center,
                radius,
                end - start,
            ),
        ),
        Weight.THIN,
    )


# Function `_on_circle()`:
def _on_circle(center: Point, radius: float, angle: float) -> Point:
    """Return the point at an angle on a circle.

    Arguments:
    * `center` (`Point`): The circle's center.
    * `radius` (`float`): Its radius.
    * `angle` (`float`): The angle (radians).

    Returns:
    * (`Point`): The point.
    """
    # Out from the center along the angle.
    return _step(center, (math.cos(angle), math.sin(angle)), radius)


# Function `_arrowhead()`:
def _arrowhead(tip: Point, back: Point, height: float) -> Stroke:
    """Return a filled arrowhead, `height` long and a third as wide.

    Arguments:
    * `tip` (`Point`): Its point.
    * `back` (`Point`): The unit vector from its tip to its base.
    * `height` (`float`): The text height.

    Returns:
    * (`Stroke`): The closed, filled triangle.
    """
    # The base corners lie either side of the line through the tip.
    base: Point = _step(tip, back, height)
    across: Point = (-back[1], back[0])
    return Stroke(
        polyline(
            [
                tip,
                _step(base, across, height / 6.0),
                _step(base, across, -height / 6.0),
                tip,
            ]
        ).segments,
        Weight.THIN,
        filled=True,
    )


# Function `_step()`:
def _step(point: Point, direction: Point, distance: float) -> Point:
    """Return a point moved some distance along a unit vector.

    Arguments:
    * `point` (`Point`): Where to start.
    * `direction` (`Point`): The unit vector.
    * `distance` (`float`): How far.

    Returns:
    * (`Point`): The moved point.
    """
    # Move each coordinate by its share.
    return (
        point[0] + direction[0] * distance,
        point[1] + direction[1] * distance,
    )


# Function `polyline()`:
def polyline(points: list[Point]) -> Stroke:
    """Return a thin stroke through some points.

    Arguments:
    * `points` (`list[Point]`): At least two points.

    Returns:
    * (`Stroke`): Lines from each point to the next.
    """
    # Join each point to the next.
    return Stroke(
        tuple(
            LineSegment(first, second)
            for first, second in itertools.pairwise(points)
        ),
        Weight.THIN,
    )


# Function `placed()`:
def placed(
    segment: XYSegment, move: Point, *, mirror: bool = False
) -> XYSegment:
    """Return a segment moved, after reflecting it across the Y axis
    when asked.

    Arguments:
    * `segment` (`XYSegment`): A line or an arc.
    * `move` (`Point`): How far to move it.
    * `mirror` (`bool`): Whether to negate each X first (an arc's
      sweep turns around).

    Returns:
    * (`XYSegment`): The new segment.
    """
    # The same change to every point of it.
    flip: float = -1.0 if mirror else 1.0

    # Function `change()`:
    def change(point: Point) -> Point:
        """Return a point reflected and moved."""
        return (flip * point[0] + move[0], point[1] + move[1])

    if isinstance(segment, LineSegment):
        return LineSegment(change(segment.start), change(segment.end))
    return ArcSegment(
        change(segment.start),
        change(segment.end),
        change(segment.center),
        segment.radius,
        flip * segment.sweep,
    )


# Function `_bounds()`:
def _bounds(strokes: tuple[Stroke, ...]) -> tuple[Point, Point]:
    """Return the box around some strokes.

    Arguments:
    * `strokes` (`tuple[Stroke, ...]`): The strokes.

    Returns:
    * (`tuple[Point, Point]`): Its lower left and upper right corners.
    """
    # Gather the end points, and each arc's extremes that it passes.
    points: list[Point] = []
    segment: XYSegment
    for stroke in strokes:
        for segment in stroke.segments:
            points.append(segment.start)
            points.append(segment.end)
            if isinstance(segment, ArcSegment):
                points.extend(_arc_extremes(segment))
    xs: list[float] = [point[0] for point in points]
    ys: list[float] = [point[1] for point in points]
    return (min(xs), min(ys)), (max(xs), max(ys))


# Function `_arc_extremes()`:
def _arc_extremes(arc: ArcSegment) -> list[Point]:
    """Return the points due east, north, west, south on an arc.

    Arguments:
    * `arc` (`ArcSegment`): The arc.

    Returns:
    * (`list[Point]`): Those of the four that the arc passes through.
    """
    # Try each of the four compass points of the circle.
    found: list[Point] = []
    quarter: int
    for quarter in range(4):
        angle: float = quarter * math.pi / 2.0
        point: Point = (
            arc.center[0] + arc.radius * math.cos(angle),
            arc.center[1] + arc.radius * math.sin(angle),
        )
        if abs(arc.sweep) >= 2.0 * math.pi or arc.contains(point):
            found.append(point)
    return found


# Function `svg()`:
def svg(
    sheet: Sheet,
    ink: str = "black",
    paper: str = "white",
    *,
    themed: bool = True,
    letter_mm: float = LETTER_MM,
) -> str:
    """Return a sheet as SVG text, its size in millimeters.

    A themed SVG follows the viewer (#287): white ink on black paper
    when it prefers dark, black on white when printed; a viewer that
    ignores the style gets `ink` on `paper`.

    Arguments:
    * `sheet` (`Sheet`): The sheet.
    * `ink` (`str`): The ink's SVG color.
    * `paper` (`str`): The paper's SVG color (painted, #284).
    * `themed` (`bool`): Whether to add the dark and print style.
    * `letter_mm` (`float`):
      How tall its letters print (mm, #292); the sheet's own units
      (drawing steps or mm) are scaled to it.

    Returns:
    * (`str`): The SVG document.
    """
    # SVG's Y runs down, so each Y is negated; the view box is the
    # paper.
    print_scale: float = letter_mm / sheet.text_height
    dashes: str = f"{_n(DASH * sheet.text_height)} {_n(sheet.text_height / 2)}"
    width: float = sheet.high[0] - sheet.low[0]
    height: float = sheet.high[1] - sheet.low[1]
    box: str = (
        f"{_n(sheet.low[0])} {_n(-sheet.high[1])} {_n(width)} {_n(height)}"
    )
    lines: list[str] = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg"'
            f' width="{_n(width * print_scale)}mm"'
            f' height="{_n(height * print_scale)}mm"'
            f' viewBox="{box}">'
        ),
        (
            f'<rect x="{_n(sheet.low[0])}" y="{_n(-sheet.high[1])}"'
            f' width="{_n(width)}" height="{_n(height)}" class="paper"'
            f' fill="{paper}"/>'
        ),
    ]
    if themed:
        lines.insert(1, STYLE)

    # One path per stroke, its width from its weight; strokes with a
    # title grouped under it, over an unseen box the pointer can rest
    # on (#267).
    title: str
    group: list[Stroke]
    for title, group in (
        (key, list(run))
        for key, run in itertools.groupby(sheet.strokes, _title)
    ):
        if title:
            lines.extend(("<g>", f"<title>{escape(title)}</title>"))
            lines.append(_hover_box(group, sheet.text_height))
        stroke: Stroke
        for stroke in group:
            share: float = THICK if stroke.weight is Weight.THICK else THIN
            lines.append(
                f'<path d="{_path(stroke)}"'
                + (
                    f' class="ink solid" fill="{ink}"'
                    if stroke.filled
                    else ' class="ink" fill="none"'
                )
                + f' stroke="{ink}"'
                + (f' stroke-dasharray="{dashes}"' if stroke.dashed else "")
                + f' stroke-width="{_n(share * sheet.text_height)}"'
                ' stroke-linecap="round" stroke-linejoin="round"/>'
            )
        if title:
            lines.append("</g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


# Function `_title()`:
def _title(stroke: Stroke) -> str:
    """Return a stroke's title (the key its group is made by).

    Arguments:
    * `stroke` (`Stroke`): The stroke.

    Returns:
    * (`str`): Its title, "" for none.
    """
    # Only the title matters for grouping.
    return stroke.title


# Function `_hover_box()`:
def _hover_box(strokes: list[Stroke], margin: float) -> str:
    """Return an unseen box around some strokes, which the pointer
    can rest on to show their group's title (#267).

    Arguments:
    * `strokes` (`list[Stroke]`): The titled strokes.
    * `margin` (`float`): How far the box reaches past them.

    Returns:
    * (`str`): The SVG `<rect>`, Y negated.
    """
    # The strokes' ends, a margin around them.
    points: list[Point] = [
        end
        for stroke in strokes
        for segment in stroke.segments
        for end in (segment.start, segment.end)
    ]
    low_x: float = min(x for x, _ in points) - margin
    high_x: float = max(x for x, _ in points) + margin
    low_y: float = min(y for _, y in points) - margin
    high_y: float = max(y for _, y in points) + margin
    return (
        f'<rect x="{_n(low_x)}" y="{_n(-high_y)}"'
        f' width="{_n(high_x - low_x)}" height="{_n(high_y - low_y)}"'
        ' fill="none" pointer-events="all"/>'
    )


# Function `_path()`:
def _path(stroke: Stroke) -> str:
    """Return a stroke as SVG path commands, Y negated.

    Arguments:
    * `stroke` (`Stroke`): The stroke.

    Returns:
    * (`str`): Its `d` attribute.
    """
    # Move to the start, then a command for each segment.
    first: Point = stroke.segments[0].start
    words: list[str] = [f"M {_n(first[0])} {_n(-first[1])}"]
    segment: XYSegment
    for segment in stroke.segments:
        if isinstance(segment, LineSegment):
            words.append(f"L {_n(segment.end[0])} {_n(-segment.end[1])}")
        else:
            words.extend(_arc_words(segment))
    return " ".join(words)


# Function `_arc_words()`:
def _arc_words(arc: ArcSegment) -> list[str]:
    """Return an arc as SVG arc commands, Y negated.

    An arc of more than half a turn (a whole circle has the same start
    and end, which SVG cannot draw) is split in two halves.

    Arguments:
    * `arc` (`ArcSegment`): The arc.

    Returns:
    * (`list[str]`): One or two `A` commands.
    """
    # Counter-clockwise with Y up is SVG's sweep flag 0 with Y down.
    flag: int = 0 if arc.sweep > 0.0 else 1
    radius: str = _n(arc.radius)
    ends: list[Point] = [arc.end]
    if abs(arc.sweep) > math.pi:
        start: float = math.atan2(
            arc.start[1] - arc.center[1], arc.start[0] - arc.center[0]
        )
        middle: float = start + arc.sweep / 2.0
        ends.insert(
            0,
            (
                arc.center[0] + arc.radius * math.cos(middle),
                arc.center[1] + arc.radius * math.sin(middle),
            ),
        )
    return [
        f"A {radius} {radius} 0 0 {flag} {_n(end[0])} {_n(-end[1])}"
        for end in ends
    ]


# Function `_n()`:
def _n(value: float) -> str:
    """Return a number for SVG: at most 4 decimals, no trailing zeros.

    Arguments:
    * `value` (`float`): The number.

    Returns:
    * (`str`): Its text (`-0` written as `0`).
    """
    # Round, then drop the zeros and a lone point.
    shown: str = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if shown in ("", "-0") else shown
