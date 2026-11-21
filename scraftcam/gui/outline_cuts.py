"""Hide strips cut out of an outline's diagram (`T.sfoe~6.4`): no Qt.

As the editor's working view does (`OutlineView.draw_cut()`, #170),
each strip's stretch is left out and the pieces either side are
closed up to a gap of `GAP` text heights, with a long break line on
each side of the gap where it crosses the part, the two meshing
(#185).  Strokes are clipped to their pieces and moved with them.
"""

import itertools
import math

from ..diagram import LINE, Stroke, placed, polyline
from ..geometry import ArcSegment, LineSegment, Point, XYSegment
from .hides import HIDE_X, HIDE_Y, Hide, inside_spans, minus, strip
from .outline_file import Outline

# Sizes in text heights, as the editor's pixels are to its letters:
# the gap a cut closes to, and a break line's zigzag (half its width,
# and its height).
GAP: float = 2.0
ZIG_HALF: float = 1.0
ZIG_HIGH: float = 0.6

# A small S ending a dimension line at a cut: half its length across
# the line, in text heights, and how many lines draw its curve.
ESS: float = 0.9
ESS_LINES: int = 8

# Beyond everything drawn (drawing steps).
FAR: float = 1e9

# An arc crossing a cut is clipped as this many lines.
ARC_LINES: int = 32

# A piece of the drawing along one axis: its low and high ends, and
# how far it is moved.
Piece = tuple[float, float, float]


# Function `cut_strokes()`:
def cut_strokes(
    outline: Outline, strokes: list[Stroke], height: float
) -> list[Stroke]:
    """Return a diagram's strokes with the outline's hide strips cut
    out, and the break lines at each cut.

    Arguments:
    * `outline` (`Outline`): The outline, with its hides.
    * `strokes` (`list[Stroke]`): The diagram's strokes.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The strokes as the working view shows them.
    """
    # Nothing hidden: nothing changes.
    if not outline.hides:
        return strokes
    across_x: list[Piece] = pieces(outline, HIDE_X, GAP * height)
    across_y: list[Piece] = pieces(outline, HIDE_Y, GAP * height)

    # Each stroke clipped to each piece's box, and moved with it.
    found: list[Stroke] = []
    stroke: Stroke
    for stroke in strokes:
        for left, right, dx in across_x:
            for bottom, top, dy in across_y:
                found.extend(
                    _clipped(stroke, (left, right, bottom, top), (dx, dy))
                )
    found.extend(_breaks(outline, across_x, across_y, height))
    found.extend(_esses(outline, strokes, (across_x, across_y), height))
    return found


# Function `pieces()`:
def pieces(outline: Outline, axis: int, gap: float) -> list[Piece]:
    """Return the drawing's pieces along an axis: each from one cut to
    the next, and how far it is moved to close up (the editor's
    `cut_offsets()`).

    Arguments:
    * `outline` (`Outline`): The outline.
    * `axis` (`int`): `HIDE_X` or `HIDE_Y`.
    * `gap` (`float`): The gap each cut closes to.

    Returns:
    * (`list[Piece]`): The pieces, low to high.
    """
    # Each cut moves everything above it down by what it hides.
    cuts: list[tuple[float, float]] = sorted(
        strip(outline.points, hide)
        for hide in outline.hides
        if hide.axis == axis
    )
    found: list[Piece] = []
    start: float = -FAR
    shift: float = 0.0
    low: float
    high: float
    for low, high in cuts:
        found.append((start, low, shift))
        shift -= high - low - gap
        start = high
    found.append((start, FAR, shift))
    return found


# Function `shift_at()`:
def shift_at(found: list[Piece], at: float) -> float:
    """Return how far a place is moved: by its piece.

    Arguments:
    * `found` (`list[Piece]`): From `pieces()`.
    * `at` (`float`): The place.

    Returns:
    * (`float`): Its piece's shift (0 inside a cut).
    """
    # The piece holding it.
    low: float
    high: float
    shift: float
    for low, high, shift in found:
        if low <= at <= high:
            return shift
    return 0.0


# Function `_clipped()`:
def _clipped(
    stroke: Stroke,
    box: tuple[float, float, float, float],
    move: Point,
) -> list[Stroke]:
    """Return what of a stroke lies in a box, moved.

    Arguments:
    * `stroke` (`Stroke`): The stroke.
    * `box` (`tuple[float, float, float, float]`): Left, right, bottom
      and top.
    * `move` (`Point`): How far to move what is kept.

    Returns:
    * (`list[Stroke]`): One stroke per connected run kept; a filled
      stroke cut in two loses its fill.
    """
    # Clip each segment (an arc reaching out of the box as lines).
    kept: list[XYSegment] = []
    whole: bool = True
    segment: XYSegment
    for segment in stroke.segments:
        if _inside(segment, box):
            kept.append(placed(segment, move))
            continue
        whole = False
        line: LineSegment
        for line in _lines(segment):
            part: LineSegment | None = _clip_line(line, box)
            if part is not None:
                kept.append(placed(part, move))

    # Split into connected runs.
    runs: list[list[XYSegment]] = []
    for segment in kept:
        if runs and math.dist(runs[-1][-1].end, segment.start) < 1e-12:
            runs[-1].append(segment)
        else:
            runs.append([segment])
    return [
        Stroke(
            tuple(run),
            stroke.weight,
            filled=stroke.filled and whole,
            dashed=stroke.dashed,
            role=stroke.role,
            title=stroke.title,
        )
        for run in runs
    ]


# Function `_inside()`:
def _inside(
    segment: XYSegment, box: tuple[float, float, float, float]
) -> bool:
    """Return whether a segment lies wholly in a box.

    Arguments:
    * `segment` (`XYSegment`): A line or an arc.
    * `box` (`tuple[float, float, float, float]`): Left, right, bottom,
      top.

    Returns:
    * (`bool`): True when every point of it is inside.
    """
    # An arc's whole circle must fit (simple, and safe).
    left: float
    right: float
    bottom: float
    top: float
    left, right, bottom, top = box
    if isinstance(segment, ArcSegment):
        x: float = segment.center[0]
        y: float = segment.center[1]
        r: float = segment.radius
        return (
            left <= x - r
            and x + r <= right
            and bottom <= y - r
            and y + r <= top
        )
    return all(
        left <= point[0] <= right and bottom <= point[1] <= top
        for point in (segment.start, segment.end)
    )


# Function `_lines()`:
def _lines(segment: XYSegment) -> list[LineSegment]:
    """Return a segment as lines: itself, or an arc as `ARC_LINES`.

    Arguments:
    * `segment` (`XYSegment`): A line or an arc.

    Returns:
    * (`list[LineSegment]`): The lines.
    """
    # A line is itself; an arc is cut into short chords.
    if isinstance(segment, LineSegment):
        return [segment]
    start: float = math.atan2(
        segment.start[1] - segment.center[1],
        segment.start[0] - segment.center[0],
    )
    points: list[Point] = [
        (
            segment.center[0]
            + segment.radius
            * math.cos(start + segment.sweep * step / ARC_LINES),
            segment.center[1]
            + segment.radius
            * math.sin(start + segment.sweep * step / ARC_LINES),
        )
        for step in range(ARC_LINES + 1)
    ]
    points[0] = segment.start
    points[-1] = segment.end
    return [
        LineSegment(first, second)
        for first, second in itertools.pairwise(points)
    ]


# Function `_clip_line()`:
def _clip_line(
    line: LineSegment, box: tuple[float, float, float, float]
) -> LineSegment | None:
    """Return what of a line lies in a box (Liang-Barsky).

    Arguments:
    * `line` (`LineSegment`): The line.
    * `box` (`tuple[float, float, float, float]`): Left, right, bottom,
      top.

    Returns:
    * (`LineSegment | None`): The part inside; `None` for none.
    """
    # Narrow the line's share, 0 to 1, at each side of the box.
    dx: float = line.end[0] - line.start[0]
    dy: float = line.end[1] - line.start[1]
    low: float = 0.0
    high: float = 1.0
    left: float
    right: float
    bottom: float
    top: float
    left, right, bottom, top = box
    edges: list[tuple[float, float]] = [
        (-dx, line.start[0] - left),
        (dx, right - line.start[0]),
        (-dy, line.start[1] - bottom),
        (dy, top - line.start[1]),
    ]
    p: float
    q: float
    for p, q in edges:
        if p == 0.0:
            if q < 0.0:
                return None
            continue
        share: float = q / p
        if p < 0.0:
            low = max(low, share)
        else:
            high = min(high, share)
    if high - low <= 1e-12:
        return None
    return LineSegment(
        (line.start[0] + dx * low, line.start[1] + dy * low),
        (line.start[0] + dx * high, line.start[1] + dy * high),
    )


# Function `_breaks()`:
def _breaks(
    outline: Outline,
    across_x: list[Piece],
    across_y: list[Piece],
    height: float,
) -> list[Stroke]:
    """Return a long break line on each side of every cut: straight,
    a zigzag in its middle, the two meshing; only where the cut
    crosses the part, stopping at another cut's gap (the editor's
    `draw_breaks()`).

    Arguments:
    * `outline` (`Outline`): The outline.
    * `across_x` (`list[Piece]`): The pieces along X.
    * `across_y` (`list[Piece]`): Along Y.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The break lines, thin.
    """
    # Each side of each cut, where its piece moves it.
    found: list[Stroke] = []
    hide: Hide
    for hide in outline.hides:
        along: list[Piece] = across_y if hide.axis == HIDE_Y else across_x
        others: list[Piece] = across_x if hide.axis == HIDE_Y else across_y
        holes: list[tuple[float, float]] = [
            strip(outline.points, other)
            for other in outline.hides
            if other.axis != hide.axis
        ]
        side: float
        for side in strip(outline.points, hide):
            at: float = side + shift_at(along, side)
            spans: list[tuple[float, float]] = minus(
                inside_spans(outline.points, hide.axis, side, outline.revolve),
                holes,
            )
            start: float
            end: float
            for start, end in spans:
                shift: float = shift_at(others, (start + end) / 2.0)
                found.append(
                    _zigzag(
                        hide.axis, at, (start + shift, end + shift), height
                    )
                )
    return found


# Function `_zigzag()`:
def _zigzag(
    axis: int, at: float, reach: tuple[float, float], height: float
) -> Stroke:
    """Return a long break line: straight, a zigzag in its middle that
    goes the same way on both sides of a cut, so the two mesh.

    Arguments:
    * `axis` (`int`): The cut's axis (`HIDE_Y`: a line along X).
    * `at` (`float`): Where the line is, along the axis.
    * `reach` (`tuple[float, float]`): Where it starts and ends,
      across.
    * `height` (`float`): The text height.

    Returns:
    * (`Stroke`): The line.
    """
    # Along the line, with the zigzag's offsets from it.
    half: float = ZIG_HALF * height
    high: float = ZIG_HIGH * height
    middle: float = (reach[0] + reach[1]) / 2.0
    steps: list[tuple[float, float]] = [
        (reach[0], 0.0),
        (middle - half, 0.0),
        (middle - half / 3.0, high),
        (middle + half / 3.0, -high),
        (middle + half, 0.0),
        (reach[1], 0.0),
    ]
    points: list[Point] = [
        (along, at + off) if axis == HIDE_Y else (at + off, along)
        for along, off in steps
    ]
    return polyline(points)


# Function `_esses()`:
def _esses(
    outline: Outline,
    strokes: list[Stroke],
    both: tuple[list[Piece], list[Piece]],
    height: float,
) -> list[Stroke]:
    """Return a small S on each side of a cut, where it chops a
    dimension line (the editor's `draw_esses()`, #185).

    Arguments:
    * `outline` (`Outline`): The outline.
    * `strokes` (`list[Stroke]`): The strokes before cutting.
    * `both` (`tuple[list[Piece], list[Piece]]`): The pieces along X,
      then along Y.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The S's.
    """
    # Each dimension line's segments crossing each side of each cut.
    found: list[Stroke] = []
    hide: Hide
    for hide in outline.hides:
        along: list[Piece] = both[hide.axis]
        others: list[Piece] = both[1 - hide.axis]
        side: float
        for side in strip(outline.points, hide):
            stroke: Stroke
            for stroke in strokes:
                if stroke.role != LINE:
                    continue
                segment: XYSegment
                for segment in stroke.segments:
                    first: float = segment.start[hide.axis]
                    last: float = segment.end[hide.axis]
                    if (first - side) * (last - side) >= 0.0:
                        continue
                    share: float = (side - first) / (last - first)
                    meets: float = segment.start[1 - hide.axis] + share * (
                        segment.end[1 - hide.axis]
                        - segment.start[1 - hide.axis]
                    )
                    found.append(
                        _ess(
                            hide.axis,
                            side + shift_at(along, side),
                            meets + shift_at(others, meets),
                            height,
                        )
                    )
    return found


# Function `_ess()`:
def _ess(axis: int, at: float, across_at: float, height: float) -> Stroke:
    """Return a small S lying across a dimension line at a cut's side,
    its middle at the line's end; the same way round on both sides,
    so the hump of one faces the valley of the other.

    Arguments:
    * `axis` (`int`): The cut's axis (`HIDE_Y`: the line runs along
      Y, the S lies along X).
    * `at` (`float`): The cut's side, along the axis.
    * `across_at` (`float`): The dimension line, across it.
    * `height` (`float`): The text height.

    Returns:
    * (`Stroke`): The S, as short lines.
    """
    # A cubic curve (along, off): from (0, -long) to (0, long), its
    # controls at (wide, -long / 3) and (-wide, long / 3).
    long: float = ESS * height
    wide: float = long / 2.0
    controls: list[tuple[float, float]] = [
        (0.0, -long),
        (wide, -long / 3.0),
        (-wide, long / 3.0),
        (0.0, long),
    ]
    points: list[Point] = []
    step: int
    for step in range(ESS_LINES + 1):
        t: float = step / ESS_LINES
        weights: tuple[float, float, float, float] = (
            (1 - t) ** 3,
            3 * (1 - t) ** 2 * t,
            3 * (1 - t) * t**2,
            t**3,
        )
        along: float = sum(
            w * c[0] for w, c in zip(weights, controls, strict=True)
        )
        off: float = sum(
            w * c[1] for w, c in zip(weights, controls, strict=True)
        )
        points.append(
            (across_at + off, at + along)
            if axis == HIDE_Y
            else (at + along, across_at + off)
        )
    return polyline(points)
