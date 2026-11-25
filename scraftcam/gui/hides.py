"""Hide strips (`T.oe~6.2` #157, #164-#168), no Qt.

Long, boring stretches of a drawing (a drill's shank) are hidden by a
strip across the whole drawing, as the grid plate's sketch hides its
middle: the working view leaves out what a strip covers and draws long
break lines where it cuts; the overview shows the whole drawing, each
strip shaded.  A strip hides a stretch of Y (a strip across, laid by
dragging a wide rectangle) or of X (a strip top to bottom).

A strip may cover straight stretches only: no corner and no fillet's
arc (#162, #165).  It is tied to the corners just outside it, at fixed
distances from them, so when values move those corners apart the
strip hides more and the working view stays the same (#160).
"""

from dataclasses import dataclass, field

# The axes a strip hides a stretch of.
# Closed set: a `StrEnum` with `match`/`assert_never()` would let
# mypy catch a missed value (#762).
HIDE_X: int = 0
HIDE_Y: int = 1


# Class `Hide`:
@dataclass(slots=True)
class Hide:
    """A hide strip, tied to the corners on either side of it.

    Attributes:
    * `axis` (`int`): `HIDE_Y` (a strip across, hiding a stretch of
      height) or `HIDE_X` (top to bottom, hiding width).
    * `below` (`int`): The corner on its low side.
    * `above` (`int`): The corner on its high side.
    * `low` (`float`): Its low side, this far past `below` (steps).
    * `high` (`float`): Its high side, this far short of `above`.
    * `under` (`float`): How far it reaches past the outline across
      the axis, on the low side (steps, never less than 0: it cuts
      right through the part, #180).
    * `over` (`float`): How far on the high side.

    Constructor:
    * `Hide(axis, below, above, low, high, under, over)`
    """

    # Constructor arguments:
    axis: int = field(init=True)
    below: int = field(init=True)
    above: int = field(init=True)
    low: float = field(init=True)
    high: float = field(init=True)
    under: float = field(init=True, default=1.0)
    over: float = field(init=True, default=1.0)


# Function `strip()`:
def strip(
    points: list[tuple[float, float]], hide: Hide
) -> tuple[float, float]:
    """Return where a strip is, along its axis (drawing steps).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `hide` (`Hide`): The strip.

    Returns:
    * (`tuple[float, float]`): Its low and high sides.
    """
    return (
        points[hide.below][hide.axis] + hide.low,
        points[hide.above][hide.axis] - hide.high,
    )


# Function `across()`:
def across(
    points: list[tuple[float, float]], hide: Hide
) -> tuple[float, float]:
    """Return where a strip reaches across its axis (drawing steps):
    past the outline by its `under` and `over`.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `hide` (`Hide`): The strip.

    Returns:
    * (`tuple[float, float]`): Its low and high ends across.
    """
    other: list[float] = [point[1 - hide.axis] for point in points]
    return min(other) - hide.under, max(other) + hide.over


# Function `lay()`:
def lay(
    points: list[tuple[float, float]],
    axis: int,
    low: float,
    high: float,
    arcs: list[tuple[float, float]] | None = None,
) -> Hide | str:
    """Lay a strip over a stretch, tied to the corners outside it.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `axis` (`int`): `HIDE_X` or `HIDE_Y`.
    * `low` (`float`): One side of the stretch (drawing steps).
    * `high` (`float`): The other side.
    * `arcs` (`list[tuple[float, float]] | None`): Where along the
      axis each fillet's arc runs, from one end to the other.

    Returns:
    * (`Hide | str`): The strip, or why it cannot be laid there.
    """
    low, high = min(low, high), max(low, high)
    if high - low <= 0.0:
        return "Drag across the stretch to hide."
    along: list[float] = [point[axis] for point in points]
    inside: list[int] = [
        corner for corner, at in enumerate(along) if low < at < high
    ]
    if inside:
        return "A hide strip may not cover a corner."
    if any(min(arc) < high and max(arc) > low for arc in arcs or []):
        return "A hide strip may not cover a fillet."
    under: list[int] = [corner for corner, at in enumerate(along) if at <= low]
    over: list[int] = [corner for corner, at in enumerate(along) if at >= high]
    if not under or not over:
        return "A hide strip must lie between corners of the outline."

    # Function `coordinate()`:
    def coordinate(corner: int) -> float:
        """Return a corner's place along the axis."""
        return along[corner]

    below: int = max(under, key=coordinate)
    above: int = min(over, key=coordinate)
    return Hide(axis, below, above, low - along[below], along[above] - high)


# Function `inside_spans()`:
def inside_spans(
    points: list[tuple[float, float]],
    axis: int,
    at: float,
    mirror: bool = False,
    loops: list[list[int]] | None = None,
) -> list[tuple[float, float]]:
    """Return where a line across the part is inside the outline: a
    long break line runs only there, edge to edge (#185); inside any
    of its polygons (`T.sa~6.11` #765).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `axis` (`int`): The cut's axis (`HIDE_Y`: the line runs along X
      at Y = `at`).
    * `at` (`float`): Where the line is, along the axis.
    * `mirror` (`bool`): Whether the outline is revolved, its mirror
      half counted too.
    * `loops` (`list[list[int]] | None`): Each polygon's corners;
      `None` for one through them all, in order.

    Returns:
    * (`list[tuple[float, float]]`): The stretches inside, across the
      axis, in order, joined where they touch.
    """
    if loops is None:
        loops = [list(range(len(points)))]
    outlines: list[list[tuple[float, float]]] = [
        [points[corner] for corner in loop] for loop in loops
    ]
    if mirror:
        outlines += [[(-x, y) for x, y in each] for each in outlines]
    spans: list[tuple[float, float]] = []
    outline: list[tuple[float, float]]
    for outline in outlines:
        crossings: list[float] = []
        index: int
        for index, here in enumerate(outline):
            there: tuple[float, float] = outline[(index + 1) % len(outline)]
            a: float = here[axis]
            b: float = there[axis]
            if (a < at) != (b < at):
                share: float = (at - a) / (b - a)
                crossings.append(
                    here[1 - axis] + share * (there[1 - axis] - here[1 - axis])
                )
        crossings.sort()
        spans += list(zip(crossings[::2], crossings[1::2], strict=False))
    return _joined(spans)


# Function `minus()`:
def minus(
    spans: list[tuple[float, float]], holes: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    """Return stretches less other stretches (another hide's): a long
    break line stops at another hide's gap (#185).

    Arguments:
    * `spans` (`list[tuple[float, float]]`): The stretches.
    * `holes` (`list[tuple[float, float]]`): What to take out.

    Returns:
    * (`list[tuple[float, float]]`): What is left, in order.
    """
    left: list[tuple[float, float]] = list(spans)
    low: float
    high: float
    for low, high in holes:
        kept: list[tuple[float, float]] = []
        start: float
        end: float
        for start, end in left:
            if start < low:
                kept.append((start, min(end, low)))
            if end > high:
                kept.append((max(start, high), end))
        left = [(start, end) for start, end in kept if end > start]
    return left


# Function `_joined()`:
def _joined(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return stretches sorted, those that touch or overlap joined.

    Arguments:
    * `spans` (`list[tuple[float, float]]`): The stretches.

    Returns:
    * (`list[tuple[float, float]]`): Joined.
    """
    joined: list[tuple[float, float]] = []
    start: float
    end: float
    for start, end in sorted(spans):
        if joined and start <= joined[-1][1]:
            joined[-1] = (joined[-1][0], max(joined[-1][1], end))
        else:
            joined.append((start, end))
    return joined
