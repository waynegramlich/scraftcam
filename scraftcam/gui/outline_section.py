"""Sections through a flat outline's cut lines (`T.sa~6.11` #776,
#861).

A cut line crosses the outline's tree of extruded polygons and
circles (#766, #789).  Along the line, each shape is either there or
not; where it is, it adds material from its parent's `z` to its own
(up) or cuts it away (down).  The section is that material, slab by
slab along the line: hatched, outlined thick, and named "SECTION
A-A".  It is worked out as drawn (#861): along the line in drawing
steps, the heights at the drawing's scale.  No Qt.
"""

import itertools
import math
from dataclasses import dataclass, field

from ..appearance import Hatch
from ..diagram import Stroke, Weight, polyline, text
from ..geometry import ArcSegment, LineSegment, Point, XYSegment, point_at

# Lines shorter than this (drawing steps) are left out.
TINY: float = 1e-9

# How many straight pieces stand for a quarter circle of an arc.
ARC_PIECES: int = 16

# How far the section stands right of the outline, in text heights.
GAP: float = 4.0


# Class `Shape`:
@dataclass(frozen=True, slots=True)
class Shape:
    """One polygon or circle of the tree, as drawn.

    Attributes:
    * `name` (`str`): Its name.
    * `parent` (`str`): Its parent's name, "" for a root.
    * `z` (`float`): The height it ends at, in millimeters.
    * `ring` (`tuple[Point, ...]`): Its outline as drawn, arcs in
      short straight pieces.

    Constructor:
    * `Shape(name, parent, z, ring)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    parent: str = field(init=True)
    z: float = field(init=True)
    ring: tuple[Point, ...] = field(init=True)


# Function `ring_of()`:
def ring_of(segments: tuple[XYSegment, ...]) -> tuple[Point, ...]:
    """Return a closed run of lines and arcs as points, each arc in
    short straight pieces.

    Arguments:
    * `segments` (`tuple[XYSegment, ...]`): The run.

    Returns:
    * (`tuple[Point, ...]`): Its points, the first not repeated.
    """
    points: list[Point] = []
    segment: XYSegment
    for segment in segments:
        pieces: int = 1
        if isinstance(segment, ArcSegment):
            pieces = max(
                2, math.ceil(abs(segment.sweep) / (math.pi / 2) * ARC_PIECES)
            )
        points.extend(
            point_at(segment, index / pieces) for index in range(pieces)
        )
    return tuple(points)


# Function `spans()`:
def spans(
    ring: tuple[Point, ...], start: Point, end: Point
) -> list[tuple[float, float]]:
    """Return where a line from `start` to `end` is inside a ring, as
    distances along it.

    Arguments:
    * `ring` (`tuple[Point, ...]`): The ring's points.
    * `start` (`Point`): The line's start.
    * `end` (`Point`): Its end.

    Returns:
    * (`list[tuple[float, float]]`): The stretches inside, in order,
      clipped to the line.
    """
    length: float = math.dist(start, end)
    if length < TINY:
        return []
    crossings: list[float] = sorted(
        along * length for along in _crossings(ring, start, end)
    )
    found: list[tuple[float, float]] = []
    pair: int
    for pair in range(0, len(crossings) - 1, 2):
        low: float = max(crossings[pair], 0.0)
        high: float = min(crossings[pair + 1], length)
        if high - low > TINY:
            found.append((low, high))
    return found


# Function `_crossings()`:
def _crossings(
    ring: tuple[Point, ...], start: Point, end: Point
) -> list[float]:
    """Return where a line crosses a ring's edges, as fractions of
    the line (beyond its ends too).

    Arguments:
    * `ring` (`tuple[Point, ...]`): The ring's points.
    * `start` (`Point`): The line's start.
    * `end` (`Point`): Its end.

    Returns:
    * (`list[float]`): The crossings, unsorted.
    """
    dx: float = end[0] - start[0]
    dy: float = end[1] - start[1]
    found: list[float] = []
    index: int
    here: Point
    for index, here in enumerate(ring):
        there: Point = ring[(index + 1) % len(ring)]
        ex: float = there[0] - here[0]
        ey: float = there[1] - here[1]
        denominator: float = dx * ey - dy * ex
        if abs(denominator) < TINY:
            continue
        wx: float = here[0] - start[0]
        wy: float = here[1] - start[1]
        # Half open on the edge, so a vertex is crossed once.
        if 0.0 <= (wx * dy - wy * dx) / denominator < 1.0:
            found.append((wx * ey - wy * ex) / denominator)
    return found


# Function `_add()`:
def _add(
    intervals: list[tuple[float, float]], low: float, high: float
) -> list[tuple[float, float]]:
    """Return intervals with one more joined in.

    Arguments:
    * `intervals` (`list[tuple[float, float]]`): Apart, in order.
    * `low` (`float`): The new one's bottom.
    * `high` (`float`): Its top.

    Returns:
    * (`list[tuple[float, float]]`): Apart, in order.
    """
    merged: list[tuple[float, float]] = []
    bottom: float
    top: float
    for bottom, top in sorted([*intervals, (low, high)]):
        if merged and bottom <= merged[-1][1] + TINY:
            merged[-1] = (merged[-1][0], max(merged[-1][1], top))
        else:
            merged.append((bottom, top))
    return merged


# Function `_cut()`:
def _cut(
    intervals: list[tuple[float, float]], low: float, high: float
) -> list[tuple[float, float]]:
    """Return intervals with one taken away.

    Arguments:
    * `intervals` (`list[tuple[float, float]]`): Apart, in order.
    * `low` (`float`): The bottom of what goes.
    * `high` (`float`): Its top.

    Returns:
    * (`list[tuple[float, float]]`): What is left, in order.
    """
    left: list[tuple[float, float]] = []
    bottom: float
    top: float
    for bottom, top in intervals:
        if low - bottom > TINY:
            left.append((bottom, min(top, low)))
        if top - high > TINY:
            left.append((max(bottom, high), top))
    return [(bottom, top) for bottom, top in left if top - bottom > TINY]


# Function `material()`:
def material(
    shapes: list[Shape], inside: dict[str, bool]
) -> list[tuple[float, float]]:
    """Return the heights (mm) with material at one place on the line.

    Arguments:
    * `shapes` (`list[Shape]`): The tree's shapes.
    * `inside` (`dict[str, bool]`): Whether the place is inside each,
      by name.

    Returns:
    * (`list[tuple[float, float]]`): The solid stretches, in order.
    """
    heights: dict[str, float] = {shape.name: shape.z for shape in shapes}
    intervals: list[tuple[float, float]] = []

    # Function `walk()`:
    def walk(parent: str) -> None:
        """Apply each shape standing on `parent` here, then its own."""
        nonlocal intervals
        base: float = heights.get(parent, 0.0)
        shape: Shape
        for shape in shapes:
            if shape.parent != parent or not inside.get(shape.name, False):
                continue
            if shape.z > base:
                intervals = _add(intervals, base, shape.z)
            else:
                intervals = _cut(intervals, shape.z, base)
            walk(shape.name)

    walk("")
    return intervals


# Function `section_strokes()`:
# The cut, its shapes and where and how the section is drawn.
# pylint: disable-next=too-many-arguments,too-many-locals
def section_strokes(
    name: str,
    ends: tuple[Point, Point, Point],
    shapes: list[Shape],
    *,
    scale: float,
    corner: Point,
    height: float,
    hatch: Hatch,
) -> list[Stroke]:
    """Return a cut line's section: hatched, outlined, titled.

    Arguments:
    * `name` (`str`): The cut's letter.
    * `ends` (`tuple[Point, Point, Point]`): Its two ends and the
      point on the side it looks toward, as drawn.
    * `shapes` (`list[Shape]`): The tree's shapes, as drawn.
    * `scale` (`float`): Drawing steps per millimeter, for heights.
    * `corner` (`Point`): Where its bottom left goes.
    * `height` (`float`): The text height.
    * `hatch` (`Hatch`): The hatch of its cut faces.

    Returns:
    * (`list[Stroke]`): The hatched areas, the thick outline, then
      the title; none when the line misses every shape.
    """
    start: Point
    end: Point
    toward: Point
    start, end, toward = ends
    length: float = math.dist(start, end)
    inner: dict[str, list[tuple[float, float]]] = {
        shape.name: spans(shape.ring, start, end) for shape in shapes
    }
    stops: list[float] = sorted(
        {0.0, length}
        | {
            value
            for found in inner.values()
            for pair in found
            for value in pair
        }
    )

    # Looking toward `toward`, the line runs left to right when that
    # side is on its left; otherwise the section is turned round.
    turned: bool = (end[0] - start[0]) * (toward[1] - start[1]) - (
        end[1] - start[1]
    ) * (toward[0] - start[0]) < 0.0
    zoom: float = scale if scale > 0.0 else 1.0

    # Function `at()`:
    def at(along: float, up: float) -> Point:
        """Return a section point on the sheet."""
        x: float = length - along if turned else along
        return (corner[0] + x, corner[1] + up * zoom)

    # The material in each slab between stops.
    slabs: list[tuple[float, float, list[tuple[float, float]]]] = []
    low: float
    high: float
    for low, high in itertools.pairwise(stops):
        middle: float = (low + high) / 2.0
        inside: dict[str, bool] = {
            shape: any(a <= middle <= b for a, b in found)
            for shape, found in inner.items()
        }
        slabs.append((low, high, material(shapes, inside)))
    if not any(found for _, _, found in slabs):
        return []

    # Hatched areas, then the outline: each slab's tops and bottoms,
    # and between slabs where the material changes.
    strokes: list[Stroke] = [
        Stroke(
            polyline(
                [at(low, a), at(high, a), at(high, b), at(low, b), at(low, a)]
            ).segments,
            Weight.THIN,
            hatch=hatch,
        )
        for low, high, found in slabs
        for a, b in found
    ]
    edges: list[XYSegment] = [
        LineSegment(at(low, level), at(high, level))
        for low, high, found in slabs
        for pair in found
        for level in pair
    ]
    before: list[tuple[float, float]] = []
    index: int
    for index, stop in enumerate(stops):
        after: list[tuple[float, float]] = (
            slabs[index][2] if index < len(slabs) else []
        )
        edges.extend(
            LineSegment(at(stop, a), at(stop, b))
            for a, b in _changed(before, after)
        )
        before = after
    strokes.extend(Stroke((edge,), Weight.THICK) for edge in edges)
    bottom: float = min(a for _, _, found in slabs for a, _ in found)
    strokes.extend(
        text(
            f"SECTION {name}-{name}",
            (corner[0] + length / 2.0, corner[1] + bottom * zoom - 2 * height),
            height,
        )
    )
    return strokes


# Function `_changed()`:
def _changed(
    one: list[tuple[float, float]], other: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    """Return the heights solid on one side of a stop and not the
    other (where a wall is).

    Arguments:
    * `one` (`list[tuple[float, float]]`): One side's material.
    * `other` (`list[tuple[float, float]]`): The other's.

    Returns:
    * (`list[tuple[float, float]]`): The walls' stretches.
    """
    found: list[tuple[float, float]] = []
    a: float
    b: float
    for a, b in one:
        kept: list[tuple[float, float]] = [(a, b)]
        for low, high in other:
            kept = _cut(kept, low, high)
        found.extend(kept)
    for a, b in other:
        kept = [(a, b)]
        for low, high in one:
            kept = _cut(kept, low, high)
        found.extend(kept)
    return found


# Function `cut_line_strokes()`:
def cut_line_strokes(
    name: str,
    ends: tuple[Point, Point, Point],
    height: float,
    *,
    with_line: bool = True,
) -> list[Stroke]:
    """Return a cut line as drawn on the outline: thin and dashed, a
    thick stroke at each end, an arrow there looking toward its side,
    and its letter beyond each arrow.

    Arguments:
    * `name` (`str`): Its letter.
    * `ends` (`tuple[Point, Point, Point]`): Its two ends and the
      point on the side it looks toward.
    * `height` (`float`): The text height.
    * `with_line` (`bool`): False to leave out the dashed line itself
      (drawn with the outline's own strokes).

    Returns:
    * (`list[Stroke]`): The strokes.
    """
    start: Point
    end: Point
    toward: Point
    start, end, toward = ends
    length: float = math.dist(start, end)
    if length < TINY:
        return []
    along: Point = (
        (end[0] - start[0]) / length,
        (end[1] - start[1]) / length,
    )

    # The side it looks toward: the normal pointing at `toward`.
    normal: Point = (-along[1], along[0])
    if (
        normal[0] * (toward[0] - start[0]) + normal[1] * (toward[1] - start[1])
        < 0.0
    ):
        normal = (along[1], -along[0])
    strokes: list[Stroke] = (
        [Stroke((LineSegment(start, end),), Weight.THIN, dashed=True)]
        if with_line
        else []
    )
    point: Point
    sign: float
    for point, sign in ((start, 1.0), (end, -1.0)):
        inward: Point = (
            point[0] + sign * along[0] * height,
            point[1] + sign * along[1] * height,
        )
        strokes.append(Stroke((LineSegment(point, inward),), Weight.THICK))
        strokes.extend(_arrow(point, along, normal, height))
        strokes.extend(
            text(
                name,
                (
                    point[0] + normal[0] * height * 3,
                    point[1] + normal[1] * height * 3,
                ),
                height,
            )
        )
    return strokes


# Function `_arrow()`:
def _arrow(
    point: Point, along: Point, normal: Point, height: float
) -> list[Stroke]:
    """Return a cut line's arrow at one end: a thin shaft and a filled
    head, pointing the way the section looks.

    Arguments:
    * `point` (`Point`): The end of the line.
    * `along` (`Point`): The line's unit direction.
    * `normal` (`Point`): The unit direction it looks.
    * `height` (`float`): The text height.

    Returns:
    * (`list[Stroke]`): The shaft and the head.
    """
    tip: Point = (
        point[0] + normal[0] * height * 2,
        point[1] + normal[1] * height * 2,
    )
    base: Point = (
        tip[0] - normal[0] * height * 0.8,
        tip[1] - normal[1] * height * 0.8,
    )
    side: Point = (along[0] * height / 4, along[1] * height / 4)
    return [
        Stroke((LineSegment(point, tip),), Weight.THIN),
        Stroke(
            polyline(
                [
                    tip,
                    (base[0] + side[0], base[1] + side[1]),
                    (base[0] - side[0], base[1] - side[1]),
                    tip,
                ]
            ).segments,
            Weight.THIN,
            filled=True,
        ),
    ]
