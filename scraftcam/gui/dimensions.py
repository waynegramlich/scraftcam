"""The outline editor's dimensions (`T.prg~5.1.9.2` #24): no Qt here.

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

from dataclasses import dataclass, field

# The origin, as a point of a dimension (corners are 0 and up).
ORIGIN: int = -1

# The kinds of dimension, and the coordinate each one measures.
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

# An angle between two edges (`start`, `end` are the corners each
# edge leaves, or an axis); `offset` is its arc's radius, `along` the letter's
# place along the arc.  Not in `AXIS` either.
ANGLE: str = "angle"

# What [Dim. Kind] turns each kind into.
NEXT_KIND: dict[str, str] = {
    HORIZONTAL: LENGTH,
    LENGTH: VERTICAL,
    VERTICAL: HORIZONTAL,
}

# A corner drawn this close to an axis is on it (snapped corners are
# exactly on it), so that coordinate is 0 (#23).
ON_AXIS: float = 1e-9


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

    Constructor:
    * `Dimension(letter, kind, start, end, offset, along, places,
      rays)`
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
    points: list[tuple[float, float]], dimensions: list[Dimension]
) -> Solution:
    """Find each corner's coordinates from the dimensions.

    Angles give edges' directions (from an axis, or an edge already
    directed); an edge directed and known at one end gives its other
    end from one coordinate there.

    Starting from the origin and the corners drawn on an axis, each
    pass takes every dimension that can tell something new, until
    none can: a horizontal (vertical) one from a point whose X (Y)
    is known, a length from a point known in full to a corner known
    in one coordinate (#37: the drawing picks the side).  A
    horizontal or vertical dimension between two points already known
    that way is one too many.

    Arguments:
    * `points` (`list[tuple[float, float]]`):
      The corners as drawn, for the signs.
    * `dimensions` (`list[Dimension]`): The dimensions.

    Returns:
    * (`Solution`): The formulas, and the extra dimensions.
    """
    solution: Solution = Solution()
    known: tuple[dict[int, Formula], dict[int, Formula]] = (
        solution.x,
        solution.y,
    )
    _seed(points, known)

    # Pass after pass, until nothing more is found: the dimensions,
    # then the edges whose directions angles gave.
    ways: dict[int, str] = {X_AXIS: "0 deg", Y_AXIS: "90 deg"}
    used: set[int] = set()
    # Level and upright edges first: a dimension saying again what
    # one says is the one too many.
    level: list[Dimension] = _level_edges(points)
    every: list[Dimension] = level + dimensions
    found: bool = True
    while found:
        found = False
        index: int
        dimension: Dimension
        for index, dimension in enumerate(every):
            if index in used:
                continue
            if dimension.kind == ANGLE:
                done: bool = _angle_way(dimension, ways)
            else:
                done = _apply(points, dimension, known, solution.extra, index)
            if done:
                # Start over, so the level edges go first again.
                used.add(index)
                found = True
                break
        edge: int
        way: str
        for edge, way in ways.items():
            if edge not in AXES and _along_edge(points, edge, way, known):
                found = True
    known[0].pop(ORIGIN)
    known[1].pop(ORIGIN)

    # The extras by the dimensions' own indices.
    solution.extra[:] = sorted(
        index - len(level) for index in solution.extra if index >= len(level)
    )
    return solution


# Function `_seed()`:
def _seed(
    points: list[tuple[float, float]],
    known: tuple[dict[int, Formula], dict[int, Formula]],
) -> None:
    """Start from what is known before any dimension: the origin, and
    each corner drawn on an axis (#23).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas, filled in.
    """
    axis: int
    for axis in (0, 1):
        known[axis][ORIGIN] = Formula()
        corner: int
        point: tuple[float, float]
        for corner, point in enumerate(points):
            if abs(point[axis]) <= ON_AXIS:
                known[axis][corner] = Formula()


# Function `_level_edges()`:
def _level_edges(points: list[tuple[float, float]]) -> list[Dimension]:
    """Return an edge drawn level (upright) as a vertical (horizontal)
    dimension of nothing between its corners (#100): they share Y (X),
    as a corner drawn on an axis is on it (#23).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.

    Returns:
    * (`list[Dimension]`): One per level or upright edge, letter "".
    """
    edges: list[Dimension] = []
    corner: int
    here: tuple[float, float]
    for corner, here in enumerate(points):
        after: int = (corner + 1) % len(points)
        apart: tuple[float, float] = (
            abs(points[after][0] - here[0]),
            abs(points[after][1] - here[1]),
        )
        if apart[1] <= ON_AXIS < apart[0]:
            edges.append(Dimension("", VERTICAL, corner, after))
        elif apart[0] <= ON_AXIS < apart[1]:
            edges.append(Dimension("", HORIZONTAL, corner, after))
    return edges


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
            across: str = f"({known[have][start]}) - ({known[have][end]})"
            known[want][start] = Formula(
                text=f"{known[want][end]} {side} "
                f"sqrt({dimension.letter}^2 - ({across})^2)"
            )
            return True
    return all(start in table for table in known)


# Function `_angle_way()`:
def _angle_way(dimension: Dimension, ways: dict[int, str]) -> bool:
    """An angle from an edge already directed gives the other edge's
    direction (counterclockwise from its first ray to its second).

    Arguments:
    * `dimension` (`Dimension`): The angle.
    * `ways` (`dict[int, str]`): Each edge's direction (from the
      corner it leaves), an expression in degrees; added to.

    Returns:
    * (`bool`): Whether it is done with.
    """
    start: int = dimension.start
    end: int = dimension.end
    if start in ways and end in ways:
        return True  # One too many: not marked yet (#33).

    # A ray against its edge is half a turn from the edge's direction.
    flips: int = (dimension.rays[0] != 1) - (dimension.rays[1] != 1)
    if start in ways:
        half: str = {1: " + 180 deg", -1: " - 180 deg", 0: ""}[flips]
        ways[end] = f"{ways[start]} + {dimension.letter}{half}"
        return True
    if end in ways:
        back: str = {1: " - 180 deg", -1: " + 180 deg", 0: ""}[flips]
        ways[start] = f"{ways[end]} - {dimension.letter}{back}"
        return True
    return False


# Function `_along_edge()`:
def _along_edge(
    points: list[tuple[float, float]],
    edge: int,
    way: str,
    known: tuple[dict[int, Formula], dict[int, Formula]],
) -> bool:
    """A directed edge known in full at one end gives its other end
    from one known coordinate there.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `edge` (`int`): The corner the edge leaves.
    * `way` (`str`): Its direction, an expression in degrees.
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas found so far, added to.

    Returns:
    * (`bool`): Whether it gave something.
    """
    ends: tuple[int, int] = (edge, (edge + 1) % len(points))
    full: int
    other: int
    for full, other in (ends, ends[::-1]):
        if not all(full in table for table in known):
            continue
        x0: Formula = known[0][full]
        y0: Formula = known[1][full]
        if other in known[0] and other not in known[1]:
            known[1][other] = Formula(
                text=f"{y0} + (({known[0][other]}) - ({x0})) * tan({way})"
            )
            return True
        if other in known[1] and other not in known[0]:
            known[0][other] = Formula(
                text=f"{x0} + (({known[1][other]}) - ({y0})) / tan({way})"
            )
            return True
    return False
