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

import re
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

# A fillet: its corner rounded (`start` and `end` the corner); `offset`
# is its radius as drawn.  Fillets sharing the drawing's note letter
# show no dimension of their own (#116).  Not in `AXIS`: the corner
# stays where its edges meet, as in SolidCraft.
RADIUS: str = "radius"

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
    points: list[tuple[float, float]],
    dimensions: list[Dimension],
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
    ways: dict[int, str] = {X_AXIS: "0 deg", Y_AXIS: "90 deg"}
    marked: set[int] = set()
    dimension: Dimension
    for dimension in dimensions:
        edge: int = mark_edge(dimension, len(points))
        if edge >= 0:
            marked.add(edge)
            ways[edge] = _drawn_way(points, edge, AXIS[dimension.kind])
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
        for edge, way in ways.items():
            if (
                edge not in AXES
                and edge not in marked
                and _along_edge(points, edge, way, known)
            ):
                found = True
    known[0].pop(ORIGIN)
    known[1].pop(ORIGIN)
    solution.extra.sort()
    return solution


# Function `is_mark()`:
def is_mark(dimension: Dimension) -> bool:
    """Return whether a dimension is a mark (#233): letterless, a
    horizontal or vertical dimension of nothing.  A vertical one
    across an edge marks it level (horizontal, `—`), a horizontal one
    upright (vertical, `|`); from the origin to a corner, it puts the
    corner on the X (Y) axis.

    Arguments:
    * `dimension` (`Dimension`): The dimension.

    Returns:
    * (`bool`): Whether it is a mark.
    """
    return not dimension.letter and dimension.kind in AXIS


# Function `mark_edge()`:
def mark_edge(dimension: Dimension, corners: int) -> int:
    """Return the edge a mark lies along (the corner it leaves), or
    -1 when it is not a mark across an edge.

    Arguments:
    * `dimension` (`Dimension`): The dimension.
    * `corners` (`int`): How many corners the outline has.

    Returns:
    * (`int`): The edge, or -1.
    """
    if not is_mark(dimension) or min(dimension.start, dimension.end) < 0:
        return -1
    start: int = dimension.start
    end: int = dimension.end
    if end == (start + 1) % corners:
        return start
    if start == (end + 1) % corners:
        return end
    return -1


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
def _drawn_way(points: list[tuple[float, float]], edge: int, axis: int) -> str:
    """Return a marked edge's direction, from the corner it leaves:
    along X for a level mark, Y for an upright one, the sign as drawn.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `edge` (`int`): The corner the edge leaves.
    * `axis` (`int`): 1 for a level mark (Y kept), 0 for an upright.

    Returns:
    * (`str`): Its direction, in degrees.
    """
    after: int = (edge + 1) % len(points)
    if axis == 1:
        return "0 deg" if points[after][0] >= points[edge][0] else "180 deg"
    return "90 deg" if points[after][1] >= points[edge][1] else "-90 deg"


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
def _angle_way(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    points: list[tuple[float, float]],
    dimension: Dimension,
    ways: dict[int, str],
    known: tuple[dict[int, Formula], dict[int, Formula]],
    extra: list[int],
    index: int,
) -> bool:
    """An angle from an edge already directed gives the other edge's
    direction (counterclockwise from its first ray to its second).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimension` (`Dimension`): The angle.
    * `ways` (`dict[int, str]`): Each edge's direction (from the
      corner it leaves), an expression in degrees; added to.
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas found so far.
    * `extra` (`list[int]`): Given the angle if one too many (#230).
    * `index` (`int`): The angle's index.

    Returns:
    * (`bool`): Whether it is done with (used or extra).
    """
    start: int = dimension.start
    end: int = dimension.end

    # Both edges directed already, by angles or by both their corners
    # known in full: the angle is one too many (#33, #230).
    if all(
        edge in ways or _edge_known(points, edge, known)
        for edge in (start, end)
    ):
        extra.append(index)
        return True

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


# Function `_edge_known()`:
def _edge_known(
    points: list[tuple[float, float]],
    edge: int,
    known: tuple[dict[int, Formula], dict[int, Formula]],
) -> bool:
    """Return whether both corners of an edge are known in full, so
    its direction is known too.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `edge` (`int`): The corner the edge leaves (an axis: never).
    * `known` (`tuple[dict[int, Formula], dict[int, Formula]]`):
      The X and Y formulas found so far.

    Returns:
    * (`bool`): Whether the edge is known.
    """
    if edge in AXES:
        return False
    ends: tuple[int, int] = (edge, (edge + 1) % len(points))
    return all(end in table for end in ends for table in known)


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
