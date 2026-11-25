"""The outline editor's dimensions (`T.oe~6.2` #24): no Qt here.

A dimension ties two points, the origin (`ORIGIN`) or corners (by
index), with a letter: horizontal (the letter is their difference in
X) or vertical (in Y).  Every corner's X must be reached from the
origin by a chain of horizontal dimensions, and its Y by a chain of
vertical ones; each step adds or takes away its letter, as the
drawing shows (a corner drawn left of the one it is measured from
takes it away).  So each coordinate is a formula in the letters, with
no solver.  A corner drawn on an axis has that coordinate 0 already,
as the origin does, and an edge drawn level (upright) gives its two
corners the same Y (X).  A coordinate with no chain is not dimensioned
yet, and a dimension between two coordinates already tied another way
is one too many (over-dimensioned).
"""

import math
import re
from dataclasses import dataclass, field
from typing import TypeAlias

# The origin, as a point of a dimension (corners are 0 and up).
ORIGIN: int = -1

# The kinds of dimension, and the coordinate each one measures.
# Closed set: a `StrEnum` with `match`/`assert_never()` would let
# mypy catch a missed value (#762).
HORIZONTAL: str = "horizontal"
VERTICAL: str = "vertical"
AXIS: dict[str, int] = {HORIZONTAL: 0, VERTICAL: 1}

# A slanted dimension: the straight distance between its points.  It
# is not in `AXIS`: alone it gives no X or Y (angles will, #S2).
LENGTH: str = "length"

# The axes, as the edges of an angle (#59, #63): the only lines other
# than edges an angle may measure from.
X_AXIS: int = -2
Y_AXIS: int = -3
AXES: tuple[int, ...] = (X_AXIS, Y_AXIS)

# An edge by the corners it leaves and reaches (`T.sa~6.11` #797);
# an axis is `(X_AXIS, -1)` or `(Y_AXIS, -1)`.
Edge: TypeAlias = tuple[int, int]

# Each polygon's corners in order (`Outline.loops()`); `None` is one
# ring through every corner in order.
Loops: TypeAlias = list[list[int]] | None


# Function `ring_edges()`:
def ring_edges(count: int, loops: Loops) -> list[Edge]:
    """Return every polygon's edges as walked, a shared one once
    (#797).

    Arguments:
    * `count` (`int`): How many corners there are.
    * `loops` (`Loops`): Each polygon's corners, or `None`.

    Returns:
    * (`list[Edge]`): The edges.
    """
    if loops is None:
        loops = [list(range(count))]
    edges: list[Edge] = []
    seen: set[frozenset[int]] = set()
    loop: list[int]
    for loop in loops:
        spot: int
        corner: int
        for spot, corner in enumerate(loop):
            edge: Edge = (corner, loop[(spot + 1) % len(loop)])
            if frozenset(edge) not in seen:
                seen.add(frozenset(edge))
                edges.append(edge)
    return edges


# Function `edges_at()`:
def edges_at(corner: int, count: int, loops: Loops) -> list[Edge]:
    """Return the edges meeting at a corner, each as walked (#797).

    Arguments:
    * `corner` (`int`): The corner.
    * `count` (`int`): How many corners there are.
    * `loops` (`Loops`): Each polygon's corners, or `None`.

    Returns:
    * (`list[Edge]`): Its edges, arriving and leaving.
    """
    return [edge for edge in ring_edges(count, loops) if corner in edge]


# Function `angle_edges()`:
def angle_edges(dimension: "Dimension", count: int) -> tuple[Edge, Edge]:
    """Return an angle's two edges, each by its corners (an axis as
    `(axis, -1)`); -1 reaches the next corner in `points` (#797).

    Arguments:
    * `dimension` (`Dimension`): The angle.
    * `count` (`int`): How many corners there are.

    Returns:
    * (`tuple[Edge, Edge]`): Its first and second edges.
    """
    found: list[Edge] = []
    corner: int
    to: int
    for corner, to in (
        (dimension.start, dimension.start_to),
        (dimension.end, dimension.end_to),
    ):
        if corner in AXES:
            found.append((corner, -1))
        else:
            found.append((corner, to if to >= 0 else (corner + 1) % count))
    return found[0], found[1]


# An angle between two edges (`start`, `end` are the corners each
# edge leaves, or an axis); `offset` is its arc's radius, `along` the letter's
# place along the arc.  Not in `AXIS` either.
ANGLE: str = "angle"

# A fillet: its corner rounded (`start` and `end` the corner); `offset`
# is its radius as drawn.  Fillets sharing the drawing's note letter
# show no dimension of their own (#116).  Not in `AXIS`: the corner
# stays where its edges meet, as in SolidCraft.
RADIUS: str = "radius"

# A revolved outline's diameter (`T.tfo~6.5` #437): from `end`'s mirror
# image across the Y axis to `end` (`start` is `ORIGIN`), so `end`'s X
# is half its letter.  Not in `AXIS`: drawn across the axis.
DIAMETER: str = "diameter"

# What [Dim. Kind] turns each kind into.
NEXT_KIND: dict[str, str] = {
    HORIZONTAL: LENGTH,
    LENGTH: VERTICAL,
    VERTICAL: HORIZONTAL,
}


# Function `next_kind()`:
def next_kind(dimension: "Dimension", revolve: bool) -> str:
    """Return the kind [Dim. Kind] turns a dimension into: on a
    revolved outline, one from the origin goes horizontal, diameter
    (#437), length, vertical.

    Arguments:
    * `dimension` (`Dimension`): The dimension (not an angle, fillet
      or mark).
    * `revolve` (`bool`): Whether the outline is revolved.

    Returns:
    * (`str`): The next kind.
    """
    if is_across(dimension):
        return VERTICAL  # Its corners' rise (#479).
    if dimension.kind == DIAMETER:
        return LENGTH
    if revolve and dimension.start == ORIGIN and dimension.kind == HORIZONTAL:
        return DIAMETER
    return NEXT_KIND[dimension.kind]


# A corner drawn this close to an axis is on it (snapped corners are
# exactly on it), so that coordinate is 0 (#23).
ON_AXIS: float = 1e-9

# A mark the drawing is off by more than this (drawing steps) is
# broken (#241).
BROKEN: float = 1e-6


# Class `Dimension`:
# A record of everything a dimension is; each kind needs its fields.
@dataclass(slots=True)
class Dimension:  # pylint: disable=too-many-instance-attributes
    """A letter measuring two points along X, along Y, or straight.

    Attributes:
    * `letter` (`str`): The letter (`W`).
    * `kind` (`str`): `HORIZONTAL`, `VERTICAL` or `LENGTH`.
    * `start` (`int`): The first point (`ORIGIN` or a corner index).
    * `end` (`int`): The second point.
    * `offset` (`float`): Where its line sits, in drawing steps: for a
      horizontal one its Y, for a vertical one its X, for a length its
      distance from the line between its points (left of `start` to
      `end` is positive).
    * `along` (`float`): Where its letter sits along the line, as a
      share of it from the `start` end (below 0 or above 1: past the
      arrowheads, for a short dimension).
    * `places` (`tuple[tuple[str, float, float], ...]`): Where the
      line and letter were (`offset`, `along`) for each other kind
      it has been, so [Dim. Kind] brings them back (#29).
    * `rays` (`tuple[int, int]`): For an angle, each ray from the
      edges' crossing along (`1`) or against (`-1`) its edge's
      direction, fixed when it is made (#53); the angle is measured
      counterclockwise from the first ray to the second.
    * `font_step` (`int`): How many [Font +] presses its letter has
      had (less [Font -]): each 1.25 times bigger (`T.sfoe~6.4`
      #273, #280).
    * `moved` (`tuple[float, float]`): How far the user has dragged a
      `—` or `|` mark's box from where it is first drawn (drawing
      steps, #317); (0, 0) for everything else.
    * `start_to` (`int`): For an angle, the corner its first edge
      reaches (`T.sa~6.11` #797); -1 for an axis, or the corner after
      `start` in the outline's `points`.
    * `end_to` (`int`): The same for its second edge.

    Constructor:
    * `Dimension(letter, kind, start, end, offset, along, places,
      rays, font_step, moved, start_to, end_to)`
    """

    # Constructor arguments:
    letter: str = field(init=True)
    kind: str = field(init=True)
    start: int = field(init=True)
    end: int = field(init=True)
    offset: float = field(init=True, default=0.0)
    along: float = field(init=True, default=0.5)
    places: tuple[tuple[str, float, float], ...] = field(init=True, default=())
    rays: tuple[int, int] = field(init=True, default=(1, 1))
    font_step: int = field(init=True, default=0)
    moved: tuple[float, float] = field(init=True, default=(0.0, 0.0))
    start_to: int = field(init=True, default=-1)
    end_to: int = field(init=True, default=-1)

    # Method `Dimension.place_of()`:
    def place_of(self, kind: str) -> tuple[float, float] | None:
        """Return where the line and letter were for a kind, if it
        has been that kind.

        Arguments:
        * `kind` (`str`): `HORIZONTAL`, `VERTICAL` or `LENGTH`.

        Returns:
        * (`tuple[float, float] | None`): `offset` and `along`.
        """
        was: str
        offset: float
        along: float
        for was, offset, along in self.places:
            if was == kind:
                return offset, along
        return None

    # Method `Dimension.become()`:
    def become(self, kind: str, offset: float) -> None:
        """Turn into another kind, keeping this kind's place; the new
        kind goes back to its own place, or to `offset` the first
        time.

        Arguments:
        * `kind` (`str`): The new kind.
        * `offset` (`float`): Where the line goes the first time.
        """
        self.places = (
            *(place for place in self.places if place[0] != self.kind),
            (self.kind, self.offset, self.along),
        )
        place: tuple[float, float] | None = self.place_of(kind)
        self.kind = kind
        if place is None:
            self.offset = offset
        else:
            self.offset, self.along = place


# Class `Formula`:
@dataclass(frozen=True, slots=True)
class Formula:
    """A coordinate as an expression in the letters: a start (empty
    for zero), then letters each added or taken away.

    Attributes:
    * `terms` (`tuple[tuple[int, str], ...]`):
      Each letter with its sign (`1` or `-1`); none for zero.
    * `text` (`str`): The start, an expression (`sqrt(L^2 - W^2)`);
      empty when it is zero.

    Constructor:
    * `Formula(terms, text)`
    """

    # Constructor arguments:
    terms: tuple[tuple[int, str], ...] = field(init=True, default=())
    text: str = field(init=True, default="")

    # Method `Formula.plus()`:
    def plus(self, sign: int, letter: str) -> "Formula":
        """Return this formula with one more term.

        Arguments:
        * `sign` (`int`): `1` to add the letter, `-1` to take it away.
        * `letter` (`str`): The letter.

        Returns:
        * (`Formula`): The longer formula.
        """
        return Formula((*self.terms, (sign, letter)), self.text)

    # Method `Formula.__str__()`:
    def __str__(self) -> str:
        """Write it as people would: `W - T`, `-W`, `0`."""
        if not self.terms:
            return self.text or "0"
        text: str = self.text
        sign: int
        letter: str
        for sign, letter in self.terms:
            if not text:
                text = letter if sign > 0 else f"-{letter}"
            else:
                text += f" + {letter}" if sign > 0 else f" - {letter}"
        return text


# Class `Solution`:
@dataclass(slots=True)
class Solution:
    """Each corner's coordinates as formulas, and what is amiss.

    Attributes:
    * `x` (`dict[int, Formula]`): The X of each corner reached.
    * `y` (`dict[int, Formula]`): The Y of each corner reached.
    * `extra` (`list[int]`):
      The dimensions that are one too many (by index).

    Constructor:
    * `Solution()`
    """

    # Remaining attributes (alphabetized):
    extra: list[int] = field(init=False, default_factory=list)
    x: dict[int, Formula] = field(init=False, default_factory=dict)
    y: dict[int, Formula] = field(init=False, default_factory=dict)

    # Method `Solution.missing()`:
    def missing(self, count: int) -> list[tuple[int, str]]:
        """Return each corner coordinate not dimensioned yet.

        Arguments:
        * `count` (`int`): How many corners there are.

        Returns:
        * (`list[tuple[int, str]]`): The corner and `"x"` or `"y"`.
        """
        found: list[tuple[int, str]] = []
        corner: int
        for corner in range(count):
            if corner not in self.x:
                found.append((corner, "x"))
            if corner not in self.y:
                found.append((corner, "y"))
        return found


# Function `solve()`:
def solve(
    points: list[tuple[float, float]],
    dimensions: list[Dimension],
    loops: Loops = None,
) -> Solution:
    """Find each corner's coordinates from the dimensions.

    Angles give edges' directions (from an axis, or an edge already
    directed); an edge directed and known at one end gives its other
    end from one coordinate there.

    Nothing is guessed from the drawing (#233): an edge is level or
    upright, or a corner on an axis, only by a mark (`is_mark()`), a
    letterless dimension the user placed, so values that land an
    edge level lock nothing.  Starting from the origin, each pass
    takes every dimension that can tell something new, until none
    can: a horizontal (vertical) one from a point whose X (Y)
    is known, a length from a point known in full to a corner known
    in one coordinate (#37: the drawing picks the side).  A
    horizontal or vertical dimension between two points already known
    that way is one too many.

    Arguments:
    * `points` (`list[tuple[float, float]]`):
      The corners as drawn, for the signs.
    * `dimensions` (`list[Dimension]`): The dimensions.
    * `loops` (`Loops`): Each polygon's corners (#765), or `None`
      for one ring through them all.

    Returns:
    * (`Solution`): The formulas, and the extra dimensions.
    """
    solution: Solution = Solution()
    known: tuple[dict[int, Formula], dict[int, Formula]] = (
        solution.x,
        solution.y,
    )
    known[0][ORIGIN] = Formula()
    known[1][ORIGIN] = Formula()

    # Pass after pass, until nothing more is found: the dimensions,
    # then the edges whose directions angles gave.  A marked edge is
    # directed from the start, as the axes are (#233); the mark itself
    # gives its far end, so it is not followed as a directed edge.
    ways: dict[Edge, str]
    marked: set[frozenset[int]]
    ways, marked = _marked_ways(points, dimensions, loops)
    used: set[int] = set()
    every: list[Dimension] = dimensions
    found: bool = True
    while found:
        found = False
        index: int
        for index, dimension in enumerate(every):
            if index in used:
                continue
            if dimension.kind == ANGLE:
                done: bool = _angle_way(
                    points, dimension, ways, known, solution.extra, index
                )
            else:
                done = _apply(points, dimension, known, solution.extra, index)
            if done:
                # Start over, so the level edges go first again.
                used.add(index)
                found = True
                break
        way: str
        directed: Edge
        for directed, way in list(ways.items()):
            if (
                directed[0] not in AXES
                and frozenset(directed) not in marked
                and _along_edge(directed, way, known)
            ):
                found = True
    known[0].pop(ORIGIN)
    known[1].pop(ORIGIN)
    solution.extra.sort()
    return solution


# Function `tip_on_origin()`:
def tip_on_origin(dimensions: list[Dimension]) -> bool:
    """Return whether a corner is marked onto both axes, so it sits on
    the origin, as a revolved tool's tip must (`T.tfo~6.5` #448).

    Arguments:
    * `dimensions` (`list[Dimension]`): The dimensions and marks.

    Returns:
    * (`bool`): Whether one corner has both marks from the origin.
    """
    found: dict[int, set[str]] = {}
    dimension: Dimension
    for dimension in dimensions:
        if is_mark(dimension) and ORIGIN in (dimension.start, dimension.end):
            corner: int = max(dimension.start, dimension.end)
            found.setdefault(corner, set()).add(dimension.kind)
    return any({HORIZONTAL, VERTICAL} <= kinds for kinds in found.values())


# Function `placement_problem()`:
def placement_problem(
    points: list[tuple[float, float]],
    dimensions: list[Dimension],
    revolve: bool,
) -> str:
    """Return what keeps the outline from its real sizes ("" if
    nothing): a revolved tool's tip off the origin (#448), or corners
    no marks and dimensions tie to the origin (#445).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimensions` (`list[Dimension]`): The dimensions and marks.
    * `revolve` (`bool`): Whether the outline is revolved.

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    # A round tool is measured from its tip.
    if revolve and not tip_on_origin(dimensions):
        return (
            "A revolved tool's tip goes on the origin: drag its corner "
            "onto the origin."
        )

    # Then every corner must be reached from the origin.
    solution: Solution = solve(points, dimensions)
    floating: list[int] = [
        corner
        for corner in range(len(points))
        if corner not in solution.x or corner not in solution.y
    ]
    if not floating:
        return ""
    if not any(
        ORIGIN in (dimension.start, dimension.end) for dimension in dimensions
    ):
        return (
            "Every corner floats: nothing ties the outline to the origin "
            "(drag a corner onto it, or dimension one from it)."
        )
    named: str = ", ".join(str(corner) for corner in floating)
    return (
        f"Corners {named} float: no dimensions, or edges drawn level or "
        "upright, tie them to the origin (a corner's tooltip says which "
        "way)."
    )


# Function `is_across()`:
def is_across(dimension: Dimension) -> bool:
    """Return whether a dimension is a horizontal across a revolved
    outline's axis (#479): a `DIAMETER` from `start`'s mirror image to
    `end`, where `start` is a corner, not `ORIGIN`.

    Arguments:
    * `dimension` (`Dimension`): The dimension.

    Returns:
    * (`bool`): `True` when it is across the axis.
    """
    return dimension.kind == DIAMETER and dimension.start != ORIGIN


# Function `is_mark()`:
def is_mark(dimension: Dimension) -> bool:
    """Return whether a dimension is a mark (#233): letterless, a
    horizontal or vertical dimension of nothing, or an angle of 90
    degrees (#236).  A vertical one across an edge marks it level
    (horizontal, `—`), a horizontal one upright (vertical, `|`); from
    the origin to a corner, it puts the corner on the X (Y) axis; an
    angle between a corner's edges makes it a right angle (`└`).

    Arguments:
    * `dimension` (`Dimension`): The dimension.

    Returns:
    * (`bool`): Whether it is a mark.
    """
    return not dimension.letter and dimension.kind in (*AXIS, ANGLE)


# Function `mark_edge()`:
def mark_edge(
    dimension: Dimension, corners: int, loops: Loops = None
) -> Edge | None:
    """Return the edge a mark lies along, as walked, or `None` when it
    is not a mark across an edge (#797).

    Arguments:
    * `dimension` (`Dimension`): The dimension.
    * `corners` (`int`): How many corners the outline has.
    * `loops` (`Loops`): Each polygon's corners, or `None`.

    Returns:
    * (`Edge | None`): The edge, or `None`.
    """
    if (
        not is_mark(dimension)
        or dimension.kind not in AXIS
        or min(dimension.start, dimension.end) < 0
    ):
        return None
    pair: frozenset[int] = frozenset((dimension.start, dimension.end))
    edge: Edge
    for edge in ring_edges(corners, loops):
        if frozenset(edge) == pair:
            return edge
    return None


# Function `mark_broken()`:
def mark_broken(
    points: list[tuple[float, float]], dimension: Dimension
) -> bool:
    """Return whether the drawing breaks a mark (#241): its edge no
    longer level (upright), or its corner off its axis, after a drag
    no dimension pinned.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimension` (`Dimension`): The mark (any other: `False`).

    Returns:
    * (`bool`): Whether it is broken.
    """
    if not is_mark(dimension):
        return False
    if dimension.kind == ANGLE:
        # A right angle: its edges' directions square to each other.
        ways: list[tuple[float, float]] = [
            (
                points[edge[1]][0] - points[edge[0]][0],
                points[edge[1]][1] - points[edge[0]][1],
            )
            for edge in angle_edges(dimension, len(points))
        ]
        size: float = math.hypot(*ways[0]) * math.hypot(*ways[1])
        dot: float = ways[0][0] * ways[1][0] + ways[0][1] * ways[1][1]
        return size <= 0.0 or abs(dot) / size > BROKEN
    axis: int = AXIS[dimension.kind]  # The coordinate it keeps.
    ends: list[float] = [
        0.0 if end == ORIGIN else points[end][axis]
        for end in (dimension.start, dimension.end)
    ]
    return abs(ends[0] - ends[1]) > BROKEN


# Function `snapped()`:
def snapped(
    points: list[tuple[float, float]],
    dimensions: list[Dimension],
    corner: int,
    tolerance: float,
    loops: Loops = None,
) -> tuple[tuple[float, float], list[Dimension]]:
    """Return where a dragged corner snaps to, and the dimensions with
    its marks remade (`T.tfo~6.5` #451).

    Along each axis, the corner snaps to its neighbors' coordinate or
    the axis, when within `tolerance` (the closest wins).  Then the
    marks on its two edges and from the origin to it are taken off,
    and made again where the snapped drawing has them: an edge level
    or upright, the corner on an axis.  Only this corner's marks
    change, from where it is drawn (never from solved values: no grid
    lock, #233).  An edge with a lettered angle gets none, and a mark
    one too many for the other dimensions (`solve().extra`) is left
    off.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn,
      the dragged one where the drag put it.
    * `dimensions` (`list[Dimension]`): The dimensions.
    * `corner` (`int`): The dragged corner.
    * `tolerance` (`float`): How near snaps, in drawing units (a few
      pixels at the current zoom).
    * `loops` (`Loops`): Each polygon's corners (#765), or `None`.

    Returns:
    * (`tuple[tuple[float, float], list[Dimension]]`): The corner's
      snapped place, and the new dimensions (the old ones kept, in
      order, the remade marks after them).
    """
    # Snap the corner, then take off its marks.
    count: int = len(points)
    here: tuple[float, float] = _snap_place(points, corner, tolerance, loops)
    moved: list[tuple[float, float]] = list(points)
    moved[corner] = here
    kept: list[Dimension] = without_marks(dimensions, corner, count, loops)

    # Add the marks it shows one at a time, leaving off any one too
    # many.
    mark: Dimension
    for mark in _shown_marks(moved, kept, corner, loops):
        trial: list[Dimension] = [*kept, mark]
        if len(trial) - 1 not in solve(moved, trial, loops).extra:
            kept = trial
    return here, kept


# Function `without_marks()`:
def without_marks(
    dimensions: list[Dimension],
    corner: int,
    count: int,
    loops: Loops = None,
) -> list[Dimension]:
    """Return the dimensions without a corner's marks: those on its
    two edges and from the origin to it (#451).

    Arguments:
    * `dimensions` (`list[Dimension]`): The dimensions.
    * `corner` (`int`): The corner.
    * `count` (`int`): How many corners there are.
    * `loops` (`Loops`): Each polygon's corners (#765), or `None`.

    Returns:
    * (`list[Dimension]`): The others, in order.
    """
    mine: list[set[int]] = [
        set(edge) for edge in edges_at(corner, count, loops)
    ] + [{ORIGIN, corner}]
    return [
        dimension
        for dimension in dimensions
        if not (
            is_mark(dimension)
            and dimension.kind in AXIS
            and {dimension.start, dimension.end} in mine
        )
    ]


# Function `_snap_place()`:
def _snap_place(
    points: list[tuple[float, float]],
    corner: int,
    tolerance: float,
    loops: Loops = None,
) -> tuple[float, float]:
    """Return where a dragged corner snaps to: along each axis, the
    closest of the axis and its neighbors' coordinates, when within
    `tolerance` (#451).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `corner` (`int`): The dragged corner.
    * `tolerance` (`float`): How near snaps, in drawing units.
    * `loops` (`Loops`): Each polygon's corners (#765), or `None`.

    Returns:
    * (`tuple[float, float]`): Its snapped place.
    """
    others: list[tuple[float, float]] = [
        points[edge[0] if edge[1] == corner else edge[1]]
        for edge in edges_at(corner, len(points), loops)
    ]
    raw: tuple[float, float] = points[corner]
    place: list[float] = list(raw)
    gaps: list[float] = [0.0, 0.0]
    axis: int
    for axis in (0, 1):
        best: float = place[axis]
        gap: float = math.inf
        target: float
        for target in (0.0, *(other[axis] for other in others)):
            if abs(target - place[axis]) < gap:
                best = target
                gap = abs(target - place[axis])
        if gap <= tolerance:
            place[axis] = best
            gaps[axis] = gap

    # Never onto a neighbor (an edge of no length): the axis snapped
    # further stays where it was dragged.
    neighbors: set[tuple[float, float]] = set(others)
    if (place[0], place[1]) in neighbors:
        axis = 0 if gaps[0] >= gaps[1] else 1
        place[axis] = raw[axis]
    return place[0], place[1]


# Function `_shown_marks()`:
def _shown_marks(
    points: list[tuple[float, float]],
    dimensions: list[Dimension],
    corner: int,
    loops: Loops = None,
) -> list[Dimension]:
    """Return the marks a drawing shows at one corner (#451): on its
    edges drawn exactly level or upright (not one with a lettered
    angle), and from the origin when it is on an axis.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimensions` (`list[Dimension]`): The dimensions, for angles.
    * `corner` (`int`): The corner.
    * `loops` (`Loops`): Each polygon's corners (#765), or `None`.

    Returns:
    * (`list[Dimension]`): The marks, on axes first.
    """
    count: int = len(points)
    here: tuple[float, float] = points[corner]
    shown: list[Dimension] = []
    if here[1] == 0.0:
        shown.append(Dimension("", VERTICAL, ORIGIN, corner))
    if here[0] == 0.0:
        shown.append(Dimension("", HORIZONTAL, ORIGIN, corner))
    angled: set[frozenset[int]] = {
        frozenset(edge)
        for dimension in dimensions
        if dimension.kind == ANGLE and dimension.letter
        for edge in angle_edges(dimension, count)
    }
    edge: int
    after: int
    for edge, after in edges_at(corner, count, loops):
        if frozenset((edge, after)) in angled or after == edge:
            continue
        start: tuple[float, float] = points[edge]
        end: tuple[float, float] = points[after]
        if start[1] == end[1] and start[0] != end[0]:
            shown.append(Dimension("", VERTICAL, edge, after))
        elif start[0] == end[0] and start[1] != end[1]:
            shown.append(Dimension("", HORIZONTAL, edge, after))
    return shown


# Function `drawn_marks()`:
def drawn_marks(points: list[tuple[float, float]]) -> list[Dimension]:
    """Return the marks the drawing itself shows: a mark across each
    edge drawn exactly level or upright (#100), and from the origin
    to each corner drawn on an axis (#23).  Only for files from before
    marks (#233), whose solving took these from the drawing.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.

    Returns:
    * (`list[Dimension]`): The marks, corners on an axis first, none
      repeating another (as the old solving took them).
    """
    marks: list[Dimension] = []
    corner: int
    here: tuple[float, float]
    for corner, here in enumerate(points):
        if abs(here[1]) <= ON_AXIS:
            marks.append(Dimension("", VERTICAL, ORIGIN, corner))
        if abs(here[0]) <= ON_AXIS:
            marks.append(Dimension("", HORIZONTAL, ORIGIN, corner))
    for corner, here in enumerate(points):
        after: int = (corner + 1) % len(points)
        apart: tuple[float, float] = (
            abs(points[after][0] - here[0]),
            abs(points[after][1] - here[1]),
        )
        if apart[1] <= ON_AXIS < apart[0]:
            marks.append(Dimension("", VERTICAL, corner, after))
        elif apart[0] <= ON_AXIS < apart[1]:
            marks.append(Dimension("", HORIZONTAL, corner, after))
    extra: list[int] = solve(points, marks).extra
    return [mark for index, mark in enumerate(marks) if index not in extra]


# Function `_drawn_way()`:
def _drawn_way(
    points: list[tuple[float, float]], edge: Edge, axis: int
) -> str:
    """Return a marked edge's direction, from the corner it leaves:
    along X for a level mark, Y for an upright one, the sign as drawn.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `edge` (`Edge`): The corners it leaves and reaches.
    * `axis` (`int`): 1 for a level mark (Y kept), 0 for an upright.

    Returns:
    * (`str`): Its direction, in degrees.
    """
    here: tuple[float, float] = points[edge[0]]
    there: tuple[float, float] = points[edge[1]]
    if axis == 1:
        return "0 deg" if there[0] >= here[0] else "180 deg"
    return "90 deg" if there[1] >= here[1] else "-90 deg"


# Function `_marked_ways()`:
def _marked_ways(
    points: list[tuple[float, float]],
    dimensions: list[Dimension],
    loops: Loops,
) -> tuple[dict[Edge, str], set[frozenset[int]]]:
    """Return the directions the axes and the marked edges start with
    (#233, #797), and the marked edges.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimensions` (`list[Dimension]`): The dimensions.
    * `loops` (`Loops`): Each polygon's corners, or `None`.

    Returns:
    * (`tuple[dict[Edge, str], set[frozenset[int]]]`): Each directed
      edge's direction, and each marked edge's corners.
    """
    ways: dict[Edge, str] = {(X_AXIS, -1): "0 deg", (Y_AXIS, -1): "90 deg"}
    marked: set[frozenset[int]] = set()
    dimension: Dimension
    for dimension in dimensions:
        edge: Edge | None = mark_edge(dimension, len(points), loops)
        if edge is not None:
            marked.add(frozenset(edge))
            _set_way(
                ways, edge, _drawn_way(points, edge, AXIS[dimension.kind])
            )
    return ways, marked


# Function `_set_way()`:
def _set_way(ways: dict[Edge, str], edge: Edge, way: str) -> None:
    """Give an edge its direction, and the edge walked the other way
    the opposite one (#797).

    Arguments:
    * `ways` (`dict[Edge, str]`): Each directed edge's direction.
    * `edge` (`Edge`): The edge, as walked.
    * `way` (`str`): Its direction, an expression in degrees.
    """
    ways[edge] = way
    if edge[1] >= 0:
        ways[(edge[1], edge[0])] = f"{way} + 180 deg"


# Function `_apply()`:
def _apply(
    points: list[tuple[float, float]],
    dimension: Dimension,
    known: tuple[dict[int, Formula], dict[int, Formula]],
    extra: list[int],
    index: int,
) -> bool:
    """Learn what one dimension tells, if it can tell it yet.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimension` (`Dimension`): The dimension.
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas found so far, added to.
    * `extra` (`list[int]`): Given the dimension if one too many.
    * `index` (`int`): The dimension's index.

    Returns:
    * (`bool`): Whether it is done with (used or extra).
    """
    if dimension.kind in AXIS:
        axis: int = AXIS[dimension.kind]
        if dimension.start in known[axis] and dimension.end in known[axis]:
            extra.append(index)
            return True
        return _along_axis(points, dimension, known[axis], axis)
    if dimension.kind == LENGTH:
        return _along_length(points, dimension, known)
    if dimension.kind == DIAMETER and dimension.start != ORIGIN:
        return _across(points, dimension, known[0], extra, index)
    if dimension.kind == DIAMETER:
        if dimension.end in known[0]:
            extra.append(index)
        else:
            sign: int = -1 if _drawn(points, dimension.end, 0) < 0 else 1
            known[0][dimension.end] = Formula().plus(
                sign, f"({dimension.letter} / 2)"
            )
        return True
    return False


# Function `_drawn()`:
def _drawn(points: list[tuple[float, float]], point: int, axis: int) -> float:
    """Return a point's coordinate as drawn.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `point` (`int`): `ORIGIN` or a corner.
    * `axis` (`int`): 0 for X, 1 for Y.

    Returns:
    * (`float`): The coordinate.
    """
    return 0.0 if point == ORIGIN else points[point][axis]


# Function `_across()`:
def _across(
    points: list[tuple[float, float]],
    dimension: Dimension,
    known: dict[int, Formula],
    extra: list[int],
    index: int,
) -> bool:
    """A revolved outline's horizontal across the axis (#479), from
    `start`'s mirror image to `end`: the letter is their X's added
    (signs as drawn), so either X gives the other.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimension` (`Dimension`): The dimension (a `DIAMETER` whose
      `start` is a corner).
    * `known` (`dict[int, Formula]`): The X formulas, added to.
    * `extra` (`list[int]`): Given the dimension if one too many.
    * `index` (`int`): The dimension's index.

    Returns:
    * (`bool`): Whether it is done with (used or extra).
    """
    start: int = dimension.start
    end: int = dimension.end
    if start in known and end in known:
        extra.append(index)
        return True
    if end in known:
        start, end = end, start
    if start not in known:
        return False

    # `x_end + x_start` is `+-letter`, the sign as drawn.
    wide: float = _drawn(points, end, 0) + _drawn(points, start, 0)
    letter: str = dimension.letter if wide >= 0.0 else f"-{dimension.letter}"
    known[end] = Formula(text=total(letter, "-", str(known[start])))
    return True


# Function `_along_axis()`:
def _along_axis(
    points: list[tuple[float, float]],
    dimension: Dimension,
    known: dict[int, Formula],
    axis: int,
) -> bool:
    """A horizontal or vertical dimension from a point known along
    its axis gives the other point there, the sign as drawn.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimension` (`Dimension`): The dimension.
    * `known` (`dict[int, Formula]`): The formulas along its axis.
    * `axis` (`int`): 0 for X, 1 for Y.

    Returns:
    * (`bool`): Whether it gave something.
    """
    start: int = dimension.start
    end: int = dimension.end
    if end in known:
        start, end = end, start
    if start not in known:
        return False
    sign: int = (
        1 if _drawn(points, end, axis) >= _drawn(points, start, axis) else -1
    )
    known[end] = (
        known[start].plus(sign, dimension.letter)
        if dimension.letter
        else known[start]  # A level or upright edge: the same.
    )
    return True


# Function `_along_length()`:
def _along_length(
    points: list[tuple[float, float]],
    dimension: Dimension,
    known: tuple[dict[int, Formula], dict[int, Formula]],
) -> bool:
    """A length from a point known in full to a corner known in one
    coordinate gives the other, on the side drawn (#37).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimension` (`Dimension`): The length.
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas found so far, added to.

    Returns:
    * (`bool`): Whether it is done with.
    """
    start: int = dimension.start
    end: int = dimension.end
    if not all(end in table for table in known):
        start, end = end, start
    if not all(end in table for table in known):
        return False
    have: int
    for have in (0, 1):
        want: int = 1 - have
        if start in known[have] and start not in known[want]:
            side: str = (
                "+"
                if _drawn(points, start, want) >= _drawn(points, end, want)
                else "-"
            )
            across: str = difference(
                str(known[have][start]), str(known[have][end])
            )
            reach: str = (
                dimension.letter
                if across == "0"
                else f"sqrt({dimension.letter}^2 - {grouped(across)}^2)"
            )
            known[want][start] = Formula(
                text=total(str(known[want][end]), side, reach)
            )
            return True
    return all(start in table for table in known)


# Function `_angle_way()`:
# Each argument is one thing the angle's side depends on.
def _angle_way(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    points: list[tuple[float, float]],
    dimension: Dimension,
    ways: dict[Edge, str],
    known: tuple[dict[int, Formula], dict[int, Formula]],
    extra: list[int],
    index: int,
) -> bool:
    """An angle from an edge already directed gives the other edge's
    direction (counterclockwise from its first ray to its second).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimension` (`Dimension`): The angle.
    * `ways` (`dict[Edge, str]`): Each directed edge's direction
      (#797), an expression in degrees; added to.
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas found so far.
    * `extra` (`list[int]`): Given the angle if one too many (#230).
    * `index` (`int`): The angle's index.

    Returns:
    * (`bool`): Whether it is done with (used or extra).
    """
    start: Edge
    end: Edge
    start, end = angle_edges(dimension, len(points))
    turn: str = dimension.letter or "90 deg"  # A right angle (#236).

    # Both edges directed already, by angles or by both their corners
    # known in full: the angle is one too many (#33, #230).
    if all(edge in ways or _edge_known(edge, known) for edge in (start, end)):
        extra.append(index)
        return True

    # A ray against its edge is half a turn from the edge's direction.
    flips: int = (dimension.rays[0] != 1) - (dimension.rays[1] != 1)
    if start in ways:
        half: str = {1: " + 180 deg", -1: " - 180 deg", 0: ""}[flips]
        _set_way(ways, end, f"{ways[start]} + {turn}{half}")
        return True
    if end in ways:
        back: str = {1: " - 180 deg", -1: " + 180 deg", 0: ""}[flips]
        _set_way(ways, start, f"{ways[end]} - {turn}{back}")
        return True
    return False


# Function `_edge_known()`:
def _edge_known(
    edge: Edge,
    known: tuple[dict[int, Formula], dict[int, Formula]],
) -> bool:
    """Return whether both corners of an edge are known in full, so
    its direction is known too.

    Arguments:
    * `edge` (`Edge`): Its corners (an axis: never).
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas found so far.

    Returns:
    * (`bool`): Whether the edge is known.
    """
    if edge[0] in AXES:
        return False
    return all(end in table for end in edge for table in known)


# Function `_along_edge()`:
def _along_edge(
    edge: Edge,
    way: str,
    known: tuple[dict[int, Formula], dict[int, Formula]],
) -> bool:
    """A directed edge known in full at one end gives its other end
    from one known coordinate there.

    Arguments:
    * `edge` (`Edge`): Its corners, as walked.
    * `way` (`str`): Its direction, an expression in degrees.
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas found so far, added to.

    Returns:
    * (`bool`): Whether it gave something.
    """
    ends: Edge = edge
    full: int
    other: int
    for full, other in (ends, ends[::-1]):
        if not all(full in table for table in known):
            continue
        x0: Formula = known[0][full]
        y0: Formula = known[1][full]
        if other in known[0] and other not in known[1]:
            rise: str = product(
                difference(str(known[0][other]), str(x0)), f"tan({way})"
            )
            known[1][other] = Formula(text=total(str(y0), "+", rise))
            return True
        if other in known[1] and other not in known[0]:
            run: str = difference(str(known[1][other]), str(y0))
            over: str = "0" if run == "0" else f"{grouped(run)} / tan({way})"
            known[0][other] = Formula(text=total(str(x0), "+", over))
            return True
    return False


# Tidy formulas (#81): no `0 +`, no `- 0`, and brackets only where
# they change the meaning, so `R * tan(90 deg - A)` and not
# `0 + ((R) - (0)) * tan(90 deg - A)`.
TOKEN: re.Pattern[str] = re.compile(r"[A-Za-z0-9_.]+")
CALL: re.Pattern[str] = re.compile(r"[A-Za-z_]\w*\(")


# Function `grouped()`:
def grouped(text: str) -> str:
    """Return a formula ready to be multiplied, divided or squared:
    in brackets unless it is a letter, a number or one call.

    Arguments:
    * `text` (`str`): The formula.

    Returns:
    * (`str`): It, bracketed if need be.
    """
    if TOKEN.fullmatch(text) or _one_call(text):
        return text
    return f"({text})"


# Function `_one_call()`:
def _one_call(text: str) -> bool:
    """Return whether a formula is one call, `name(...)`, its brackets
    closing only at the end.

    Arguments:
    * `text` (`str`): The formula.

    Returns:
    * (`bool`): Whether it is.
    """
    opening: re.Match[str] | None = CALL.match(text)
    if opening is None or not text.endswith(")"):
        return False
    depth: int = 0
    index: int
    mark: str
    for index, mark in enumerate(text[opening.end() - 1 :]):
        depth += {"(": 1, ")": -1}.get(mark, 0)
        if depth == 0:
            return opening.end() + index == len(text)
    return False


# Function `total()`:
def total(left: str, sign: str, right: str) -> str:
    """Return `left + right` or `left - right`, tidily.

    Arguments:
    * `left` (`str`): A formula.
    * `sign` (`str`): `"+"` or `"-"`.
    * `right` (`str`): A formula.

    Returns:
    * (`str`): The sum or difference.
    """
    if right == "0":
        return left
    if left == "0":
        return right if sign == "+" else f"-{grouped(right)}"
    if sign == "-" and any(mark in right for mark in "+-"):
        right = f"({right})"
    return f"{left} {sign} {right}"


# Function `difference()`:
def difference(left: str, right: str) -> str:
    """Return `left - right`, tidily (`0` when they are the same).

    Arguments:
    * `left` (`str`): A formula.
    * `right` (`str`): A formula.

    Returns:
    * (`str`): The difference.
    """
    if left == right:
        return "0"
    return total(left, "-", right)


# Function `product()`:
def product(left: str, right: str) -> str:
    """Return `left * right`, tidily (`0` when either is).

    Arguments:
    * `left` (`str`): A formula.
    * `right` (`str`): A formula.

    Returns:
    * (`str`): The product.
    """
    if "0" in (left, right):
        return "0"
    return f"{grouped(left)} * {grouped(right)}"
