"""The outline editor's dimensions (`T.prg~5.1.9.2` #24): no Qt here.

A dimension ties two points, the origin (`ORIGIN`) or corners (by
index), with a letter: horizontal (the letter is their difference in
X) or vertical (in Y).  Every corner's X must be reached from the
origin by a chain of horizontal dimensions, and its Y by a chain of
vertical ones; each step adds or takes away its letter, as the
drawing shows (a corner drawn left of the one it is measured from
takes it away).  So each coordinate is a formula in the letters, with
no solver.  A corner drawn on an axis has that coordinate 0 already,
as the origin does.  A coordinate with no chain is not dimensioned yet, and a
dimension between two coordinates already tied another way is one too
many (over-dimensioned).
"""

from collections import deque
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
@dataclass(slots=True)
class Dimension:
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

    Constructor:
    * `Dimension(letter, kind, start, end, offset, along, places)`
    """

    # Constructor arguments:
    letter: str = field(init=True)
    kind: str = field(init=True)
    start: int = field(init=True)
    end: int = field(init=True)
    offset: float = field(init=True, default=0.0)
    along: float = field(init=True, default=0.5)
    places: tuple[tuple[str, float, float], ...] = field(init=True, default=())

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
    """A coordinate as a sum of letters, each added or taken away.

    Attributes:
    * `terms` (`tuple[tuple[int, str], ...]`):
      Each letter with its sign (`1` or `-1`); none for zero.

    Constructor:
    * `Formula(terms)`
    """

    # Constructor arguments:
    terms: tuple[tuple[int, str], ...] = field(init=True, default=())

    # Method `Formula.plus()`:
    def plus(self, sign: int, letter: str) -> "Formula":
        """Return this formula with one more term.

        Arguments:
        * `sign` (`int`): `1` to add the letter, `-1` to take it away.
        * `letter` (`str`): The letter.

        Returns:
        * (`Formula`): The longer formula.
        """
        return Formula((*self.terms, (sign, letter)))

    # Method `Formula.__str__()`:
    def __str__(self) -> str:
        """Write it as people would: `W - T`, `-W`, `0`."""
        if not self.terms:
            return "0"
        text: str = ""
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
    """Find each corner's coordinates from the chains of dimensions.

    Arguments:
    * `points` (`list[tuple[float, float]]`):
      The corners as drawn, for the signs.
    * `dimensions` (`list[Dimension]`): The dimensions.

    Returns:
    * (`Solution`): The formulas, and the extra dimensions.
    """
    solution: Solution = Solution()
    kind: str
    axis: int
    for kind, axis in AXIS.items():
        known: dict[int, Formula] = solution.x if axis == 0 else solution.y
        _chain(points, dimensions, kind, known, solution.extra)
        known.pop(ORIGIN)
    solution.extra.sort()
    return solution


# Function `_chain()`:
def _chain(
    points: list[tuple[float, float]],
    dimensions: list[Dimension],
    kind: str,
    known: dict[int, Formula],
    extra: list[int],
) -> None:
    """Walk one kind's dimensions out from the origin.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimensions` (`list[Dimension]`): Every dimension.
    * `kind` (`str`): `HORIZONTAL` or `VERTICAL`.
    * `known` (`dict[int, Formula]`): Filled with each point reached.
    * `extra` (`list[int]`): Given each dimension that is one too many.
    """

    axis: int = AXIS[kind]

    # Function `drawn()`:
    def drawn(point: int) -> float:
        """Return a point's coordinate as drawn."""
        return 0.0 if point == ORIGIN else points[point][axis]

    # Breadth first from the origin and every corner drawn on the
    # axis across this kind (#23: a corner on the Y axis has X = 0);
    # a dimension whose two ends are both known when it is reached
    # ties them a second time.
    known[ORIGIN] = Formula()
    queue: deque[int] = deque([ORIGIN])
    corner: int
    for corner in range(len(points)):
        if abs(drawn(corner)) <= ON_AXIS:
            known[corner] = Formula()
            queue.append(corner)
    used: set[int] = set()
    while queue:
        point: int = queue.popleft()
        index: int
        dimension: Dimension
        for index, dimension in enumerate(dimensions):
            if dimension.kind != kind or index in used:
                continue
            if point not in (dimension.start, dimension.end):
                continue
            used.add(index)
            other: int = (
                dimension.end if point == dimension.start else dimension.start
            )
            if other in known:
                extra.append(index)
                continue
            sign: int = 1 if drawn(other) >= drawn(point) else -1
            known[other] = known[point].plus(sign, dimension.letter)
            queue.append(other)
