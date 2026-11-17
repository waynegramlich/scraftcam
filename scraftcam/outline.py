"""Profiles: closed outlines with holes, checked, then drawn live.

A `Profile` is an outer `Loop` of lines and arcs with holes in it, in
millimeters; its messages give lengths in its `unit`, the one its
user works in (inches are exactly 25.4 mm).  It is checked by us
before SolidCraft sees it, since SolidCraft takes several bad
outlines without a word (found by the
experiments in `T.sdfm~2.5.2.1`): edges that cross are filled region
by region, and a hole that touches or crosses the outline is dropped.

In SolidCraft every point and arc center is its own parameter
(`PREFIX__l0__p3x`, `PREFIX__l0__c3y`), so a change is a few plain
values sent at once (`send_changes()`), and SolidCraft's solver only
follows: it never has to choose where anything goes.  A change in the
order of lines and arcs (`Profile.structure()`) needs a new sketch.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .geometry import (
    TOUCH,
    ArcSegment,
    LineSegment,
    Loop,
    Point,
    XYSegment,
    check_crossings,
    meet,
)
from .model import MM_PER

if TYPE_CHECKING:
    from .pybind.scraftpybind import JSON, PyBind

# Segments shorter than this (mm) are refused: SolidCraft refuses a
# line of 1e-10 mm and takes one of 1e-7 mm.
MIN_LENGTH: float = 1e-6

# Coordinates are sent rounded to this many decimals of a millimeter,
# far below SolidCraft's tolerance (about 1e-6 mm).
DECIMALS: int = 12

# The most values one `parameters.change` takes (500 are taken, 510
# refused).
CHANGE_LIMIT: int = 500


# Class `Profile`:
@dataclass(slots=True)
class Profile:
    """An outer loop with holes in it, in millimeters.

    Each loop must be closed, with no segment shorter than
    `MIN_LENGTH`, each arc's ends on its circle, and no two segments
    crossing or touching.  Each hole must lie inside the outer loop
    without touching it, and apart from the other holes (an island in a
    hole is not supported yet).

    Attributes:
    * `name` (`str`): The profile's name, for messages.
    * `outer` (`Loop`): The outside of the profile.
    * `holes` (`Sequence[Loop]`):
      The holes in it (stored as a tuple).
    * `unit` (`str`):
      The unit its messages use (one of `model.MM_PER`'s keys).

    Constructor:
    * `Profile(name, outer, holes, unit)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    outer: Loop = field(init=True)
    holes: Sequence[Loop] = field(init=True, default=())
    unit: str = field(init=True, default="mm")

    # Method `Profile.__post_init__()`:
    def __post_init__(self) -> None:
        """Check every loop, and where the holes are.

        Raises:
        * `ValueError`: If a loop is not closed, has a segment too
          short, an arc whose ends are off its circle, or segments that
          cross or touch; or a hole is not inside the outer loop, or
          touches or overlaps another hole; or `unit` is not a unit.
        """
        if self.unit not in MM_PER:
            raise ValueError(f"{self.unit=} is not one of {list(MM_PER)}")
        self.holes = tuple(self.holes)
        loop: Loop
        label: str
        for label, loop in self.labeled():
            _check_loop(f"{self.name} {label}", loop, self.unit)
        self._check_holes()

    # Method `Profile.labeled()`:
    def labeled(self) -> list[tuple[str, Loop]]:
        """Return each loop with its label for messages.

        Returns:
        * (`list[tuple[str, Loop]]`): `("outer", outer)`, then
          `("hole N", hole)` for each hole.
        """
        return [("outer", self.outer)] + [
            (f"hole {index}", hole) for index, hole in enumerate(self.holes)
        ]

    # Method `Profile._check_holes()`:
    def _check_holes(self) -> None:
        """Check that the holes are inside, and apart.

        Raises:
        * `ValueError`: If a hole touches, crosses or is outside the
          outer loop, or touches, crosses or is inside another hole.
        """
        index: int
        hole: Loop
        for index, hole in enumerate(self.holes):
            if _loops_meet(hole, self.outer):
                raise ValueError(
                    f"{self.name}: hole {index} touches or crosses the"
                    " outer loop"
                )
            if not self.outer.contains(hole.segments[0].start):
                raise ValueError(
                    f"{self.name}: hole {index} is outside the outer loop"
                )
            other: int
            for other in range(index + 1, len(self.holes)):
                second: Loop = self.holes[other]
                if (
                    _loops_meet(hole, second)
                    or hole.contains(second.segments[0].start)
                    or second.contains(hole.segments[0].start)
                ):
                    raise ValueError(
                        f"{self.name}: holes {index} and {other} overlap"
                    )

    # Method `Profile.structure()`:
    def structure(self) -> tuple[str, ...]:
        """Return the order of lines and arcs in each loop.

        Two profiles with the same structure have the same parameter
        names, so one can follow the other by `send_changes()`.

        Returns:
        * (`tuple[str, ...]`): For each loop, `l` for each line and `a`
          for each arc, in order (e.g. `("lalala", "aa")`).
        """
        return tuple(
            "".join(
                "l" if isinstance(segment, LineSegment) else "a"
                for segment in loop.segments
            )
            for _label, loop in self.labeled()
        )

    # Method `Profile.values()`:
    def values(self, prefix: str) -> dict[str, str]:
        """Return each point's and center's coordinates by parameter.

        Arguments:
        * `prefix` (`str`): The start of every parameter name, such as
          `jaw_plate_001__outline`.

        Returns:
        * (`dict[str, str]`): SolidCraft expressions in millimeters by
          parameter name (`PREFIX__l0__p3x`: loop 0's point 3, the start
          of its segment 3; `PREFIX__l0__c3x`: that arc's center).
          Every value has its unit, since a bare number in an inch
          design means different things in different places.
        """
        values: dict[str, str] = {}
        number: int
        loop: Loop
        for number, (_label, loop) in enumerate(self.labeled()):
            index: int
            segment: XYSegment
            for index, segment in enumerate(loop.segments):
                name: str = f"{prefix}__l{number}__p{index}"
                values[f"{name}x"] = _mm(segment.start[0])
                values[f"{name}y"] = _mm(segment.start[1])
                if isinstance(segment, ArcSegment):
                    name = f"{prefix}__l{number}__c{index}"
                    values[f"{name}x"] = _mm(segment.center[0])
                    values[f"{name}y"] = _mm(segment.center[1])
        return values

    # Method `Profile.sketch()`:
    def sketch(self, solidcraft: "PyBind", prefix: str) -> None:
        """Draw every loop into the open sketch, by parameter names.

        The parameters (`values()`) must have been added first, and the
        caller creates the sketch (`sketch.create`) and finishes it
        (`sketch.finish`).  A segment ends at the next segment's start
        point, by the same parameters, so the loops close exactly.

        Arguments:
        * `solidcraft` (`PyBind`): Where to draw it.
        * `prefix` (`str`): The prefix given to `values()`.
        """
        number: int
        loop: Loop
        for number, (_label, loop) in enumerate(self.labeled()):
            count: int = len(loop.segments)
            index: int
            segment: XYSegment
            for index, segment in enumerate(loop.segments):
                name: str = f"{prefix}__l{number}__p"
                here: list[str] = [f"{name}{index}x", f"{name}{index}y"]
                after: int = (index + 1) % count
                there: list[str] = [f"{name}{after}x", f"{name}{after}y"]
                if isinstance(segment, LineSegment):
                    solidcraft.sketch.line(points=[here, there])
                    continue

                # SolidCraft's arcs go counter-clockwise from `start` to
                # `end`, so a clockwise arc is drawn from its end.
                ends: tuple[list[str], list[str]] = (here, there)
                if segment.sweep < 0.0:
                    ends = (there, here)
                center: str = f"{prefix}__l{number}__c{index}"
                solidcraft.sketch.arc_center_point(
                    center=[f"{center}x", f"{center}y"],
                    start=ends[0],
                    end=ends[1],
                )


# Function `add_parameters()`:
def add_parameters(solidcraft: "PyBind", values: dict[str, str]) -> None:
    """Add a profile's parameters (`Profile.values()`) to the design.

    Arguments:
    * `solidcraft` (`PyBind`): Where to add them.
    * `values` (`dict[str, str]`): Expressions by parameter name.
    """
    name: str
    value: str
    for name, value in values.items():
        solidcraft.parameters.add(name=name, expression=value)


# Function `send_changes()`:
def send_changes(
    solidcraft: "PyBind",
    old: dict[str, str],
    new: dict[str, str],
    *,
    limit: int = CHANGE_LIMIT,
) -> list["JSON"]:
    """Send the values that changed, at most `limit` to a call.

    More than `limit` values go in several calls, so SolidCraft may
    see a state in between; the experiments found that it recovers
    from one once the last call is in.

    Arguments:
    * `solidcraft` (`PyBind`): Where to send them.
    * `old` (`dict[str, str]`): The values SolidCraft has.
    * `new` (`dict[str, str]`): The values it should have, with the
      same names (the same `Profile.structure()`).
    * `limit` (`int`): The most values in one call.

    Returns:
    * (`list[JSON]`): The errors SolidCraft reported for the last call
      (features that failed), empty when all is well.

    Raises:
    * `KeyError`: If `new` names a parameter `old` does not have.
    """
    # Only the values that moved are sent.
    unknown: list[str] = [name for name in new if name not in old]
    if unknown:
        raise KeyError(f"not parameters yet: {unknown[:3]}")
    changed: list[tuple[str, str]] = [
        (name, value) for name, value in new.items() if old[name] != value
    ]

    # Send them in chunks, keeping the last call's errors.
    errors: list[JSON] = []
    start: int
    for start in range(0, len(changed), limit):
        chunk: dict[str, JSON] = dict(changed[start : start + limit])
        result: JSON = solidcraft.parameters.change(changes=chunk)
        assert isinstance(result, dict)
        reported: JSON = result.get("errors", [])
        assert isinstance(reported, list)
        errors = list(reported)
    return errors


# Function `_mm()`:
def _mm(value: float) -> str:
    """Return a coordinate as a SolidCraft expression in millimeters.

    Rounding to `DECIMALS` drops the noise of the arithmetic (5 can come
    out as 4.999999999999999), so a value that did not move is not
    sent again.

    Arguments:
    * `value` (`float`): The coordinate (mm).

    Returns:
    * (`str`): Such as `12.5 mm`.
    """
    return f"{round(value, DECIMALS) + 0.0!r} mm"


# Function `_shown()`:
def _shown(mm: float, unit: str) -> str:
    """Return a length for a message, in the user's unit.

    Arguments:
    * `mm` (`float`): The length (mm).
    * `unit` (`str`): The unit to show it in.

    Returns:
    * (`str`): Such as `0.0001 in`.
    """
    return f"{mm / float(MM_PER[unit]):g} {unit}"


# Function `_check_loop()`:
def _check_loop(name: str, loop: Loop, unit: str) -> None:
    """Check that a loop is closed, long enough, and does not cross.

    Arguments:
    * `name` (`str`): The loop's name, for messages.
    * `loop` (`Loop`): The loop.
    * `unit` (`str`): The unit the messages use.

    Raises:
    * `ValueError`: If it has no segments, a segment shorter than
      `MIN_LENGTH`, an arc whose ends are off its circle, a gap between
      two segments, or segments that cross or touch.
    """
    segments: tuple[XYSegment, ...] = loop.segments
    if not segments:
        raise ValueError(f"{name}: no segments")
    count: int = len(segments)
    index: int
    segment: XYSegment
    for index, segment in enumerate(segments):
        # Long enough, and an arc's ends on its circle.
        if segment.length() < MIN_LENGTH:
            raise ValueError(
                f"{name}: segment {index} is"
                f" {_shown(segment.length(), unit)} long"
            )
        if isinstance(segment, ArcSegment):
            end: Point
            for end in (segment.start, segment.end):
                off: float = abs(
                    math.dist(end, segment.center) - segment.radius
                )
                if off > TOUCH:
                    raise ValueError(
                        f"{name}: arc {index} has an end"
                        f" {_shown(off, unit)} off its circle"
                    )

        # Each segment starts where the one before it ends.
        following: XYSegment = segments[(index + 1) % count]
        gap: float = math.dist(segment.end, following.start)
        if gap > TOUCH:
            raise ValueError(
                f"{name}: a gap of {_shown(gap, unit)} after segment {index}"
            )
    check_crossings(
        name, segments, per_unit=float(MM_PER[unit]), shown_unit=unit
    )


# Function `_loops_meet()`:
def _loops_meet(first: Loop, second: Loop) -> bool:
    """Return whether two loops cross or touch anywhere.

    Arguments:
    * `first` (`Loop`): One loop.
    * `second` (`Loop`): The other.

    Returns:
    * (`bool`): True when any segment of one meets one of the other.
    """
    return any(
        meet(one, other) for one in first.segments for other in second.segments
    )
