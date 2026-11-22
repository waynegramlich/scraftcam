"""An outline file drawn as a diagram (`T.sfoe~6.4`): no Qt here.

`outline_sheet()` turns what an outline file holds (`Outline`) into a
`diagram.Sheet`: the outline, its dimensions with their letters and
its marks, the same shapes the editor shows (#S2).  The sheet is in
drawing steps, its corners placed by the letters' values as the
editor places them (#148, #299), so each dimension's `offset` and
`along` apply as they are (#292).
"""

import itertools
import math
from collections.abc import Iterator
from dataclasses import dataclass, field, replace

from ..diagram import (
    FONT_STEP,
    TEXT,
    Sheet,
    Stroke,
    Weight,
    angle_dimension,
    center_mark,
    dimension_line,
    edge_mark,
    length_dimension,
    mark_box,
    note,
    on_paper,
    placed,
    radius_dimension,
    right_angle,
    starting_height,
)
from ..geometry import ArcSegment, LineSegment, Point, XYSegment
from ..model import Length
from ..screws import Screw, screw
from .dimensions import (
    ANGLE,
    HORIZONTAL,
    LENGTH,
    ON_AXIS,
    ORIGIN,
    RADIUS,
    VERTICAL,
    X_AXIS,
    Y_AXIS,
    Dimension,
    is_mark,
    mark_edge,
)
from .letters import Letter
from .outline_cuts import cut_strokes
from .outline_file import COUNTERBORED, Hole, Outline
from .values import (
    first_scale,
    letter_values,
    placed_corners,
    real_coordinates,
)

# The note when fillets share the note letter (#116, #118).
NOTE: str = "All undimensioned fillets are radius {}"

# Two edges closer to parallel than this (the sine of the angle
# between them) have no angle (#40).
PARALLEL: float = 1e-6

# A fillet with no scale yet is drawn this share of its shorter edge
# (the editor's `FILLET_SHARE`, #121).
FILLET_SHARE: float = 0.2


# Class `Fillet`:
@dataclass(frozen=True, slots=True)
class Fillet:
    """A rounded corner: its arc, tangent to the corner's two edges.

    Attributes:
    * `arc` (`ArcSegment`): From the edge in to the edge out.
    * `corner` (`Point`): The sharp corner it rounds.

    Constructor:
    * `Fillet(arc, corner)`
    """

    # Constructor arguments:
    arc: ArcSegment = field(init=True)
    corner: Point = field(init=True)


# Function `outline_sheet()`:
def outline_sheet(outline: Outline, text_height: float = 0.0) -> Sheet:
    """Return an outline's diagram.

    Arguments:
    * `outline` (`Outline`): What its file holds.
    * `text_height` (`float`):
      The text height (drawing steps); 0 takes the outline's own, or
      when it has none picks one from its size (#280).

    Returns:
    * (`Sheet`): The diagram, its paper the drawing plus a margin.
    """
    # The corners where the values put them, as the editor places
    # them, so a file saved before its values changed draws right
    # (#299).
    outline = replace(
        outline,
        points=placed_corners(
            outline.points, outline.letters, outline.dimensions
        )[0],
    )

    # The outline itself, and a revolved outline's mirror half.
    fillets: dict[int, Fillet] = fillet_arcs(outline)
    strokes: list[Stroke] = outline_strokes(outline, fillets)
    if text_height <= 0.0:
        text_height = outline.text_height
    if text_height <= 0.0:
        text_height = starting_height((strokes[0],))

    # The holes, each with its center mark (#290).
    scale: float = _scale(outline)
    hole: Hole
    for hole in outline.holes:
        strokes.extend(hole_strokes(outline, hole, scale, text_height))

    # Then each dimension and mark, its letter grown or shrunk by its
    # font steps, and the fillets' note.
    # Each letter's text carries its name, value and help as a title
    # (#267).
    titles: dict[str, str] = {
        letter.letter: letter_title(letter) for letter in outline.letters
    }
    dimension: Dimension
    for dimension in outline.dimensions:
        height: float = text_height * FONT_STEP**dimension.font_step
        found: list[Stroke] = dimension_strokes(
            outline, dimension, fillets, height
        )
        title: str = titles.get(dimension.letter, "")
        strokes.extend(
            (
                replace(stroke, title=title)
                if title and stroke.role == TEXT
                else stroke
            )
            for stroke in found
        )
    if any(
        dimension.kind == RADIUS and dimension.letter == outline.note_radius
        for dimension in outline.dimensions
    ):
        strokes.extend(
            note(
                tuple(strokes),
                NOTE.format(outline.note_radius),
                text_height,
            )
        )
    cut: list[Stroke] = cut_strokes(outline, strokes, text_height)
    _turn: int
    for _turn in range(outline.turns % 4):
        cut = turned_strokes(cut)
    return on_paper(tuple(cut), text_height)


# Function `turned_strokes()`:
def turned_strokes(strokes: list[Stroke]) -> list[Stroke]:
    """Return strokes turned a quarter turn clockwise about the origin
    (#300), each run of text moved with the drawing but kept upright.

    Arguments:
    * `strokes` (`list[Stroke]`): The diagram's strokes.

    Returns:
    * (`list[Stroke]`): Turned.
    """
    # Each run of text strokes (one label) moves by where its middle
    # goes; everything else turns.
    found: list[Stroke] = []
    is_text: bool
    run: Iterator[Stroke]
    for is_text, run in itertools.groupby(strokes, _is_text):
        group: list[Stroke] = list(run)
        if not is_text:
            found.extend(
                replace(
                    stroke,
                    segments=tuple(_turned(seg) for seg in stroke.segments),
                )
                for stroke in group
            )
            continue
        ends: list[Point] = [
            end
            for stroke in group
            for seg in stroke.segments
            for end in (seg.start, seg.end)
        ]
        middle: Point = (
            (min(x for x, _ in ends) + max(x for x, _ in ends)) / 2.0,
            (min(y for _, y in ends) + max(y for _, y in ends)) / 2.0,
        )
        there: Point = _turn(middle)
        move: Point = (there[0] - middle[0], there[1] - middle[1])
        found.extend(
            replace(
                stroke,
                segments=tuple(placed(seg, move) for seg in stroke.segments),
            )
            for stroke in group
        )
    return found


# Function `upright_text()`:
def upright_text(strokes: list[Stroke], turns: int) -> list[Stroke]:
    """Return strokes with each run of text (one label) turned
    `turns` quarter turns counterclockwise about its middle, so that
    it reads upright in a view turned that many quarter turns
    clockwise (the editor's [Rotate Diagram], #300).

    Arguments:
    * `strokes` (`list[Stroke]`): The strokes, in drawing steps.
    * `turns` (`int`): The view's quarter turns clockwise.

    Returns:
    * (`list[Stroke]`): The strokes, their labels counter-turned.
    """
    # Three clockwise quarter turns make one counterclockwise.
    count: int = (-turns) % 4
    if not count:
        return strokes
    found: list[Stroke] = []
    is_text: bool
    run: Iterator[Stroke]
    for is_text, run in itertools.groupby(strokes, _is_text):
        group: list[Stroke] = list(run)
        if not is_text:
            found.extend(group)
            continue

        # Turn about the label's middle: move it to the origin, turn,
        # move it back.
        ends: list[Point] = [
            end
            for stroke in group
            for seg in stroke.segments
            for end in (seg.start, seg.end)
        ]
        middle: Point = (
            (min(x for x, _ in ends) + max(x for x, _ in ends)) / 2.0,
            (min(y for _, y in ends) + max(y for _, y in ends)) / 2.0,
        )
        stroke: Stroke
        for stroke in group:
            segments: tuple[XYSegment, ...] = tuple(
                placed(seg, (-middle[0], -middle[1]))
                for seg in stroke.segments
            )
            _count: int
            for _count in range(count):
                segments = tuple(_turned(seg) for seg in segments)
            found.append(
                replace(
                    stroke,
                    segments=tuple(placed(seg, middle) for seg in segments),
                )
            )
    return found


# Function `_is_text()`:
def _is_text(stroke: Stroke) -> bool:
    """Return whether a stroke is part of a label (the grouping key).

    Arguments:
    * `stroke` (`Stroke`): The stroke.

    Returns:
    * (`bool`): Whether its role is `TEXT`.
    """
    # Labels keep upright when the drawing turns.
    return stroke.role == TEXT


# Function `_turn()`:
def _turn(point: Point) -> Point:
    """Return a point turned a quarter turn clockwise about the origin.

    Arguments:
    * `point` (`Point`): The point.

    Returns:
    * (`Point`): `(y, -x)`.
    """
    # Clockwise: +Y goes to +X.
    return (point[1], -point[0])


# Function `_turned()`:
def _turned(segment: XYSegment) -> XYSegment:
    """Return a line or arc turned a quarter turn clockwise (its sweep
    keeps its sign: a turn keeps the way round).

    Arguments:
    * `segment` (`XYSegment`): The line or arc.

    Returns:
    * (`XYSegment`): Turned.
    """
    # An arc turns its ends and center.
    if isinstance(segment, ArcSegment):
        return ArcSegment(
            _turn(segment.start),
            _turn(segment.end),
            _turn(segment.center),
            segment.radius,
            segment.sweep,
        )
    return LineSegment(_turn(segment.start), _turn(segment.end))


# Function `letter_title()`:
def letter_title(letter: Letter) -> str:
    """Return what a viewer shows over a letter (#267): the letter,
    its name and value, then its help.

    Arguments:
    * `letter` (`Letter`): The letter.

    Returns:
    * (`str`): E.g. "L: Overall length = 4 in.  From the tip ...".
    """
    # The parts it has, the help as its own sentence.
    head: str = letter.letter + (f": {letter.name}" if letter.name else "")
    if letter.default:
        head += f" = {letter.default}"
    return f"{head}.  {letter.help}" if letter.help else head


# Function `dimension_strokes()`:
def dimension_strokes(
    outline: Outline,
    dimension: Dimension,
    fillets: dict[int, Fillet],
    height: float,
) -> list[Stroke]:
    """Return one dimension's or mark's strokes, shared by the SVG and
    the editor (#S4).

    Arguments:
    * `outline` (`Outline`): The outline.
    * `dimension` (`Dimension`): The dimension or mark.
    * `fillets` (`dict[int, Fillet]`): From `fillet_arcs()`.
    * `height` (`float`): The text height (drawing steps).

    Returns:
    * (`list[Stroke]`): Its strokes.
    """
    # A fillet's radius is drawn about its arc.
    if dimension.kind == RADIUS:
        return _fillet(outline, dimension, fillets, height)
    return _dimension(outline, dimension, height)


# Function `outline_strokes()`:
def outline_strokes(
    outline: Outline, fillets: dict[int, Fillet]
) -> list[Stroke]:
    """Return the outline's own strokes, shared by the SVG and the
    editor (#S4): first one thick closed stroke, corners rounded;
    then, when revolved, the mirror half, thin and dashed, each
    segment not on the axis reflected across it (#294).

    Arguments:
    * `outline` (`Outline`): The outline.
    * `fillets` (`dict[int, Fillet]`): From `fillet_arcs()`.

    Returns:
    * (`list[Stroke]`): The outline, then the mirror half's strokes.
    """
    # The outline, then its mirror image.
    segments: tuple[XYSegment, ...] = _rounded(outline.points, fillets)
    strokes: list[Stroke] = [Stroke(segments, Weight.THICK)]
    if outline.revolve:
        strokes.extend(
            Stroke(
                (placed(segment, (0.0, 0.0), mirror=True),),
                Weight.THIN,
                dashed=True,
            )
            for segment in segments
            if abs(segment.start[0]) > ON_AXIS or abs(segment.end[0]) > ON_AXIS
        )
    return strokes


# Function `hole_sizes()`:
def hole_sizes(outline: Outline, hole: Hole) -> tuple[Length, ...]:
    """Return a hole's diameters, the through hole's first.

    A plain hole is its letter's value; a counterbored one is its
    screw's clearance and counterbore (`screws.py`, #328) unless the
    hole gives its own.

    Arguments:
    * `outline` (`Outline`): The outline, for its letters.
    * `hole` (`Hole`): The hole.

    Returns:
    * (`tuple[Length, ...]`): One diameter, or two for a
      counterbored hole; none when its letter or sizes are bad.
    """
    # The letter's value, then the screw's holes from it.
    values: dict[str, str] = {
        letter.letter: letter.default for letter in outline.letters
    }
    try:
        size: Length = Length.parse(values.get(hole.letter, ""))
        if hole.kind != COUNTERBORED:
            return (size,)
        found: Screw = screw(size)
        return (
            (
                Length.parse(hole.clearance)
                if hole.clearance
                else found.clearance
            ),
            (
                Length.parse(hole.counterbore)
                if hole.counterbore
                else found.counterbore
            ),
        )
    except (KeyError, ValueError):
        return ()


# Function `hole_strokes()`:
def hole_strokes(
    outline: Outline, hole: Hole, scale: float, height: float
) -> list[Stroke]:
    """Return a hole's circles, thick, and its center mark, thin.

    Arguments:
    * `outline` (`Outline`): The outline, for its letters.
    * `hole` (`Hole`): The hole.
    * `scale` (`float`): Drawing steps per millimeter (`_scale()`);
      0 when nothing says, and the circles are then drawn one text
      height across, so they still show.
    * `height` (`float`): The text height (drawing steps).

    Returns:
    * (`list[Stroke]`): The circles, then the center mark.
    """
    # The radii, largest last, so the center lines reach past it.
    radii: list[float] = [
        size.mm() * scale / 2.0 for size in hole_sizes(outline, hole)
    ]
    if scale <= 0.0 or not radii:
        radii = [
            height / 2.0 * (index + 1) for index in range(len(radii) or 1)
        ]
    strokes: list[Stroke] = [
        _circle(hole.at, radius) for radius in radii if radius > 0.0
    ]
    return strokes + center_mark(hole.at, max(radii), height)


# Function `_circle()`:
def _circle(center: Point, radius: float) -> Stroke:
    """Return a thick full circle, as two half circles.

    Arguments:
    * `center` (`Point`): Its center.
    * `radius` (`float`): Its radius.

    Returns:
    * (`Stroke`): The circle, counter-clockwise from its right.
    """
    # Right to left over the top, then back under the bottom.
    right: Point = (center[0] + radius, center[1])
    left: Point = (center[0] - radius, center[1])
    return Stroke(
        (
            ArcSegment(right, left, center, radius, math.pi),
            ArcSegment(left, right, center, radius, math.pi),
        ),
        Weight.THICK,
    )


# Function `fillet_arcs()`:
# Type hints on every variable inflate its count of locals.
# pylint: disable-next=too-many-locals
def fillet_arcs(
    outline: Outline, scale: float | None = None
) -> dict[int, Fillet]:
    """Return each rounded corner's arc, as the editor draws it: its
    letter's value to scale once the values fix a scale, else a share
    of its shorter edge; never more than its edges allow.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `scale` (`float | None`):
      Drawing steps per mm (0 for none yet, as the editor keeps it);
      `None` picks it from the outline.

    Returns:
    * (`dict[int, Fillet]`): By corner; a corner too straight or too
      sharp to round is left out.
    """
    # The scale (drawing steps per mm) and the letters' values.
    points: list[Point] = outline.points
    if scale is None:
        scale = _scale(outline)
    values: dict[str, float] = letter_values(outline.letters)
    fillets: dict[int, Fillet] = {}
    dimension: Dimension
    for dimension in outline.dimensions:
        if dimension.kind != RADIUS:
            continue

        # The radius, then where it meets the edges either side.
        corner: int = dimension.start
        here: Point = points[corner]
        back: Point = points[corner - 1]
        ahead: Point = points[(corner + 1) % len(points)]
        value: float = values.get(dimension.letter, 0.0)
        radius: float = (
            value * scale
            if scale > 0.0 and value > 0.0
            else FILLET_SHARE
            * min(math.dist(here, back), math.dist(here, ahead))
        )
        arc: ArcSegment | None = _tangent_arc(here, back, ahead, radius)
        if arc is not None:
            fillets[corner] = Fillet(arc, here)
    return fillets


# Function `_tangent_arc()`:
# Type hints on every variable inflate its count of locals.
# pylint: disable-next=too-many-locals
def _tangent_arc(
    here: Point, back: Point, ahead: Point, radius: float
) -> ArcSegment | None:
    """Return the arc rounding a corner, tangent to both its edges.

    Arguments:
    * `here` (`Point`): The corner.
    * `back` (`Point`): The corner before.
    * `ahead` (`Point`): The corner after.
    * `radius` (`float`): The radius wanted.

    Returns:
    * (`ArcSegment | None`): The arc, shrunk to fit its edges; `None`
      for a straight or folded corner, or no radius.
    """
    # The unit vectors along each edge from the corner, and half the
    # angle between them.
    into: Point = _unit(back[0] - here[0], back[1] - here[1])
    out: Point = _unit(ahead[0] - here[0], ahead[1] - here[1])
    cosine: float = max(-1.0, min(1.0, into[0] * out[0] + into[1] * out[1]))
    half: float = math.acos(cosine) / 2.0
    if radius <= 0.0 or half <= 1e-9 or half >= math.pi / 2.0 - 1e-9:
        return None

    # How far along each edge the arc meets it, at most the edge.
    reach: float = min(
        radius / math.tan(half),
        math.dist(here, back),
        math.dist(here, ahead),
    )
    radius = reach * math.tan(half)
    start: Point = (here[0] + into[0] * reach, here[1] + into[1] * reach)
    end: Point = (here[0] + out[0] * reach, here[1] + out[1] * reach)
    middle: Point = _unit(into[0] + out[0], into[1] + out[1])
    away: float = radius / math.sin(half)
    center: Point = (here[0] + middle[0] * away, here[1] + middle[1] * away)

    # Counter-clockwise when the arc turns left from start to end.
    turn: float = (start[0] - center[0]) * (end[1] - center[1]) - (
        start[1] - center[1]
    ) * (end[0] - center[0])
    sweep: float = math.copysign(math.pi - 2.0 * half, turn)
    return ArcSegment(start, end, center, radius, sweep)


# Function `_rounded()`:
def _rounded(
    points: list[Point], fillets: dict[int, Fillet]
) -> tuple[XYSegment, ...]:
    """Return the outline's segments: edges between fillets, and arcs.

    Arguments:
    * `points` (`list[Point]`): The corners.
    * `fillets` (`dict[int, Fillet]`): The rounded corners.

    Returns:
    * (`tuple[XYSegment, ...]`): The closed outline, from corner 0.
    """
    # Each edge runs from its corner's arc's end to the next one's
    # start (or the sharp corners themselves).
    count: int = len(points)
    found: list[XYSegment] = []
    corner: int
    for corner in range(count):
        following: int = (corner + 1) % count
        begin: Point = (
            fillets[corner].arc.end if corner in fillets else points[corner]
        )
        finish: Point = (
            fillets[following].arc.start
            if following in fillets
            else points[following]
        )
        if math.dist(begin, finish) > 1e-12:
            found.append(LineSegment(begin, finish))
        if following in fillets:
            found.append(fillets[following].arc)
    return tuple(found)


# Function `_fillet()`:
def _fillet(
    outline: Outline,
    dimension: Dimension,
    fillets: dict[int, Fillet],
    height: float,
) -> list[Stroke]:
    """Return a fillet's marks: dashed lines to its sharp corner, and
    its radius unless it is the note's letter.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `dimension` (`Dimension`): The fillet's radius dimension.
    * `fillets` (`dict[int, Fillet]`): The rounded corners.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): Its strokes (none when the corner is sharp).
    """
    # Dashed from where the arc meets each edge to the sharp corner.
    fillet: Fillet | None = fillets.get(dimension.start)
    if fillet is None:
        return []
    arc: ArcSegment = fillet.arc
    found: list[Stroke] = [
        Stroke(
            (
                LineSegment(arc.start, fillet.corner),
                LineSegment(fillet.corner, arc.end),
            ),
            Weight.THIN,
            dashed=True,
        )
    ]

    # Its own letter: a leader out through the arc's middle.
    if dimension.letter != outline.note_radius:
        middle: Point = _unit(
            fillet.corner[0] - arc.center[0], fillet.corner[1] - arc.center[1]
        )
        found.extend(
            radius_dimension(
                arc.center,
                arc.radius,
                math.degrees(math.atan2(middle[1], middle[0])),
                letter=dimension.letter,
                height=height,
            )
        )
    return found


# Function `_scale()`:
def _scale(outline: Outline) -> float:
    """Return drawing steps per millimeter, as the editor picks it
    (`values.first_scale()`, #148).

    Arguments:
    * `outline` (`Outline`): The outline.

    Returns:
    * (`float`): The scale; 0 when nothing says.
    """
    # The ratios of the coordinates the values fix.
    real: tuple[dict[int, float], dict[int, float]] | None = real_coordinates(
        outline.points, outline.letters, outline.dimensions
    )
    return 0.0 if real is None else first_scale(outline.points, real)


# Function `_unit()`:
def _unit(x: float, y: float) -> Point:
    """Return a vector made one long (`(0, 0)` stays).

    Arguments:
    * `x` (`float`): Its X.
    * `y` (`float`): Its Y.

    Returns:
    * (`Point`): The unit vector.
    """
    # Divide by its length.
    size: float = math.hypot(x, y)
    return (x / size, y / size) if size > 0.0 else (0.0, 0.0)


# Function `_dimension()`:
def _dimension(
    outline: Outline, dimension: Dimension, height: float
) -> list[Stroke]:
    """Return one dimension's or mark's strokes (none for a kind not
    drawn yet).

    Arguments:
    * `outline` (`Outline`): The outline.
    * `dimension` (`Dimension`): The dimension.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): Its strokes.
    """
    # Marks first: they have no letter.
    if is_mark(dimension):
        return _mark(outline, dimension, height)

    # A length runs parallel to its points; horizontal and vertical
    # lines sit at their `offset` (a Y or an X).
    first: Point = _point(outline, dimension.start)
    second: Point = _point(outline, dimension.end)
    if dimension.kind == LENGTH:
        return length_dimension(
            first, second, dimension.offset, dimension.letter, height
        )
    if dimension.kind == ANGLE:
        return _angle(outline, dimension, height)
    ends: tuple[Point, Point]
    if dimension.kind == HORIZONTAL:
        ends = ((first[0], dimension.offset), (second[0], dimension.offset))
    elif dimension.kind == VERTICAL:
        ends = ((dimension.offset, first[1]), (dimension.offset, second[1]))
    else:
        return []
    return dimension_line(
        (first, second),
        ends,
        letter=dimension.letter,
        height=height,
        along=dimension.along,
    )


# Function `_angle()`:
def _angle(
    outline: Outline, dimension: Dimension, height: float
) -> list[Stroke]:
    """Return an angle's strokes: its arc about where its edges' lines
    cross, from the first ray counter-clockwise to the second (as the
    editor's `edge_arc()`).

    Arguments:
    * `outline` (`Outline`): The outline.
    * `dimension` (`Dimension`): The angle.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): Its strokes; none for parallel edges.
    """
    # The arc about where the edges' lines cross; parallel lines draw
    # nothing.
    points: list[Point] = outline.points
    arc: tuple[Point, float, float] | None = edge_arc(
        points, dimension.start, dimension.end, dimension.rays
    )
    if arc is None:
        return []
    vertex: Point = arc[0]
    rays: tuple[float, float] = (arc[1], arc[1] + arc[2])
    found: list[Stroke] = angle_dimension(
        vertex,
        rays,
        dimension.offset,
        letter=dimension.letter,
        height=height,
        along=dimension.along,
    )

    found.extend(_reaches(points, dimension, (vertex, rays), height))
    return found


# Function `_reaches()`:
def _reaches(
    points: list[Point],
    dimension: Dimension,
    arc: tuple[Point, tuple[float, float]],
    height: float,
) -> list[Stroke]:
    """Return an angle's extension lines (#296): where its arc lies
    past an edge's far end, the edge carried on to it, a little past;
    none for the axes (drawn across the window already).

    Arguments:
    * `points` (`list[Point]`): The corners.
    * `dimension` (`Dimension`): The angle.
    * `arc` (`tuple[Point, tuple[float, float]]`):
      Its vertex and its two rays' directions (degrees).
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The lines, thin.
    """
    # Each edge's far end, measured along its ray.
    vertex: Point = arc[0]
    found: list[Stroke] = []
    edge: int
    ray: float
    for edge, ray in zip(
        (dimension.start, dimension.end), arc[1], strict=True
    ):
        if edge in (X_AXIS, Y_AXIS):
            continue
        way: Point = (math.cos(math.radians(ray)), math.sin(math.radians(ray)))
        reach: float = max(
            (end[0] - vertex[0]) * way[0] + (end[1] - vertex[1]) * way[1]
            for end in (points[edge], points[(edge + 1) % len(points)])
        )
        if reach < dimension.offset:
            found.append(
                Stroke(
                    (
                        LineSegment(
                            _along(vertex, way, max(reach, 0.0)),
                            _along(vertex, way, dimension.offset + height / 2),
                        ),
                    ),
                    Weight.THIN,
                )
            )
    return found


# Function `_along()`:
def _along(start: Point, way: Point, distance: float) -> Point:
    """Return a point some distance from another along a unit vector.

    Arguments:
    * `start` (`Point`): Where it starts.
    * `way` (`Point`): The unit vector.
    * `distance` (`float`): How far.

    Returns:
    * (`Point`): The point.
    """
    # A step along the vector.
    return (start[0] + way[0] * distance, start[1] + way[1] * distance)


# Function `edge_arc()`:
def edge_arc(
    points: list[Point],
    first: int,
    second: int,
    rays: tuple[int, int],
) -> tuple[Point, float, float] | None:
    """Return an angle's arc, for the SVG and the editor alike (#295):
    where two edges' lines cross, and the turn counterclockwise from
    the first ray to the second.

    Arguments:
    * `points` (`list[Point]`): The corners.
    * `first` (`int`): The corner the first edge leaves, or an axis.
    * `second` (`int`): The corner the second edge leaves, or an axis.
    * `rays` (`tuple[int, int]`): Each ray along (`1`) or against
      (`-1`) its edge's direction.

    Returns:
    * (`tuple[Point, float, float] | None`): The crossing, the first
      ray's direction and the turn to the second ray (degrees, 0 to
      360, counterclockwise); `None` for parallel edges.
    """
    # Each edge's start and direction (an axis from the origin).
    way_a: Point = _edge_way(points, first)
    way_b: Point = _edge_way(points, second)
    a0: Point = _edge_start(points, first)
    b0: Point = _edge_start(points, second)

    # Where their lines cross, unless (nearly) parallel.
    cross: float = way_a[0] * way_b[1] - way_a[1] * way_b[0]
    if abs(cross) <= PARALLEL * max(
        math.hypot(*way_a) * math.hypot(*way_b), 1e-300
    ):
        return None
    share: float = (
        (b0[0] - a0[0]) * way_b[1] - (b0[1] - a0[1]) * way_b[0]
    ) / cross
    vertex: Point = (a0[0] + way_a[0] * share, a0[1] + way_a[1] * share)

    # The rays, along or against their edges.
    start: float = math.degrees(
        math.atan2(way_a[1] * rays[0], way_a[0] * rays[0])
    )
    end: float = math.degrees(
        math.atan2(way_b[1] * rays[1], way_b[0] * rays[1])
    )
    return vertex, start, (end - start) % 360.0


# Function `_edge_start()`:
def _edge_start(points: list[Point], edge: int) -> Point:
    """Return the corner an edge leaves (the origin, for an axis).

    Arguments:
    * `points` (`list[Point]`): The corners.
    * `edge` (`int`): The corner the edge leaves, or an axis.

    Returns:
    * (`Point`): The point.
    """
    # The axes run from the origin.
    return (0.0, 0.0) if edge in (X_AXIS, Y_AXIS) else points[edge]


# Function `_edge_way()`:
def _edge_way(points: list[Point], edge: int) -> Point:
    """Return an edge's direction from the corner it leaves (+X or +Y
    for an axis).

    Arguments:
    * `points` (`list[Point]`): The corners.
    * `edge` (`int`): The corner the edge leaves, or an axis.

    Returns:
    * (`Point`): The next corner less this one.
    """
    # The axes run from the origin.
    if edge == X_AXIS:
        return (1.0, 0.0)
    if edge == Y_AXIS:
        return (0.0, 1.0)
    here: Point = points[edge]
    there: Point = points[(edge + 1) % len(points)]
    return (there[0] - here[0], there[1] - here[1])


# Function `_mark()`:
def _mark(
    outline: Outline, dimension: Dimension, height: float
) -> list[Stroke]:
    """Return a mark's strokes: `—` or `|` by its edge or corner, or a
    right angle's square.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `dimension` (`Dimension`): The mark.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): Its strokes.
    """
    # A right angle: the corner the two edges share.
    points: list[Point] = outline.points
    count: int = len(points)
    if dimension.kind == ANGLE:
        corner: int = (
            dimension.end
            if (dimension.start + 1) % count == dimension.end
            else dimension.start
        )
        return right_angle(
            points[corner],
            points[(corner - 1) % count],
            points[(corner + 1) % count],
            height,
        )

    # Across an edge: out from its middle; else out from its corner;
    # then wherever the user dragged it (#317).
    return [
        replace(
            stroke,
            segments=tuple(
                placed(segment, dimension.moved) for segment in stroke.segments
            ),
        )
        for stroke in _mark_box(outline, dimension, height)
    ]


# Function `_mark_box()`:
def _mark_box(
    outline: Outline, dimension: Dimension, height: float
) -> list[Stroke]:
    """Return a `—` or `|` mark's box where it is first drawn: out
    from its edge's middle, or from its corner.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `dimension` (`Dimension`): The mark.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): Its box and line.
    """
    # Across an edge: out from its middle; else out from its corner.
    points: list[Point] = outline.points
    count: int = len(points)
    level: bool = dimension.kind == VERTICAL
    inside: Point = _middle(points)
    edge: int = mark_edge(dimension, count)
    if edge >= 0:
        return edge_mark(
            points[edge],
            points[(edge + 1) % count],
            inside,
            level=level,
            height=height,
        )
    here: Point = points[max(dimension.start, dimension.end)]
    out: Point = (here[0] - inside[0], here[1] - inside[1])
    size: float = max((out[0] ** 2 + out[1] ** 2) ** 0.5, 1e-12)
    return mark_box(
        (
            here[0] + out[0] / size * height,
            here[1] + out[1] / size * height,
        ),
        level=level,
        height=height,
    )


# Function `_point()`:
def _point(outline: Outline, point: int) -> Point:
    """Return a dimension's point: the origin or a corner.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `point` (`int`): `ORIGIN` or a corner's index.

    Returns:
    * (`Point`): Where it is (drawing steps).
    """
    # The origin is not a corner.
    return (0.0, 0.0) if point == ORIGIN else outline.points[point]


# Function `_middle()`:
def _middle(points: list[Point]) -> Point:
    """Return the average of some points (the outline's middle).

    Arguments:
    * `points` (`list[Point]`): The corners.

    Returns:
    * (`Point`): Their average.
    """
    # Add up each coordinate.
    return (
        sum(x for x, _ in points) / len(points),
        sum(y for _, y in points) / len(points),
    )
