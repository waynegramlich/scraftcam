"""An outline file drawn as a diagram (`T.sfoe~6.4`): no Qt here.

`outline_sheet()` turns what an outline file holds (`Outline`) into a
`diagram.Sheet`: the outline, its dimensions with their letters and
its marks, the same shapes the editor shows (#S2).  The sheet is in
drawing steps, as the file keeps its corners (already placed by the
letters' values, #148), so each dimension's `offset` and `along`
apply as they are (#292).
"""

import math
from dataclasses import dataclass, field

from ..diagram import (
    FONT_STEP,
    Sheet,
    Stroke,
    Weight,
    angle_dimension,
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
from .outline_cuts import cut_strokes
from .outline_file import Outline
from .values import letter_values, real_coordinates

# The note when fillets share the note letter (#116, #118).
NOTE: str = "All undimensioned fillets are radius {}"

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
    # The outline itself: one thick closed stroke, corners rounded.
    fillets: dict[int, Fillet] = fillet_arcs(outline)
    segments: tuple[XYSegment, ...] = _rounded(outline.points, fillets)
    strokes: list[Stroke] = [Stroke(segments, Weight.THICK)]
    if text_height <= 0.0:
        text_height = outline.text_height
    if text_height <= 0.0:
        text_height = starting_height(tuple(strokes))

    # A revolved outline's mirror half: thin, dashed, each segment not
    # on the axis reflected across it (#294).
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

    # Then each dimension and mark, its letter grown or shrunk by its
    # font steps, and the fillets' note.
    dimension: Dimension
    for dimension in outline.dimensions:
        height: float = text_height * FONT_STEP**dimension.font_step
        if dimension.kind == RADIUS:
            strokes.extend(_fillet(outline, dimension, fillets, height))
        else:
            strokes.extend(_dimension(outline, dimension, height))
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
    return on_paper(
        tuple(cut_strokes(outline, strokes, text_height)), text_height
    )


# Function `fillet_arcs()`:
# Type hints on every variable inflate its count of locals.
# pylint: disable-next=too-many-locals
def fillet_arcs(outline: Outline) -> dict[int, Fillet]:
    """Return each rounded corner's arc, as the editor draws it: its
    letter's value to scale once the values fix a scale, else a share
    of its shorter edge; never more than its edges allow.

    Arguments:
    * `outline` (`Outline`): The outline.

    Returns:
    * (`dict[int, Fillet]`): By corner; a corner too straight or too
      sharp to round is left out.
    """
    # The scale (drawing steps per mm) and the letters' values.
    points: list[Point] = outline.points
    scale: float = _scale(outline)
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
    (its `first_scale()`, #148): the middle of the drawn-to-real
    ratios of the coordinates the values fix.

    Arguments:
    * `outline` (`Outline`): The outline.

    Returns:
    * (`float`): The scale; 0 when nothing says.
    """
    # Each fixed coordinate's drawn over real value, when positive.
    real: tuple[dict[int, float], dict[int, float]] | None = real_coordinates(
        outline.points, outline.letters, outline.dimensions
    )
    if real is None:
        return 0.0
    ratios: list[float] = sorted(
        outline.points[corner][axis] / value
        for axis in (0, 1)
        for corner, value in real[axis].items()
        if abs(value) > 1e-9 and outline.points[corner][axis] / value > 0.0
    )
    return ratios[len(ratios) // 2] if ratios else 0.0


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
    # Each edge's start and direction (an axis from the origin).
    points: list[Point] = outline.points
    first: Point = _edge_way(points, dimension.start)
    second: Point = _edge_way(points, dimension.end)
    a0: Point = _point(outline, max(dimension.start, ORIGIN))
    b0: Point = _point(outline, max(dimension.end, ORIGIN))

    # Where their lines cross; parallel lines draw nothing.
    cross: float = first[0] * second[1] - first[1] * second[0]
    if abs(cross) <= 1e-12 * math.hypot(*first) * math.hypot(*second):
        return []
    share: float = (
        (b0[0] - a0[0]) * second[1] - (b0[1] - a0[1]) * second[0]
    ) / cross
    vertex: Point = (a0[0] + first[0] * share, a0[1] + first[1] * share)

    # The rays, along or against their edges.
    rays: tuple[float, float] = (
        math.degrees(
            math.atan2(
                first[1] * dimension.rays[0], first[0] * dimension.rays[0]
            )
        ),
        math.degrees(
            math.atan2(
                second[1] * dimension.rays[1], second[0] * dimension.rays[1]
            )
        ),
    )
    return angle_dimension(
        vertex,
        rays,
        dimension.offset,
        letter=dimension.letter,
        height=height,
        along=dimension.along,
    )


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

    # Across an edge: out from its middle; else out from its corner.
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
