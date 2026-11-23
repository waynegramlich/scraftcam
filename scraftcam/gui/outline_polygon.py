"""A `RoundedPolygon` from an outline file (`T.rps~6.6` #384).

An outline file (the editor's letters table and sketch) is the recipe
for a polygon: its letters' values place the corners
(`values.real_corners()`), and its radius dimensions round them.  So
one file gives both the diagram (`.svg`) and, through `solid.py`, the
solid.  No Qt.

A revolved outline (a round tool's half profile) makes a
`SolidRevolved` (`outline_revolved()`, #339).  Holes are not made
yet (`T.sfoe~6.4` #290: their centers are not dimensioned), and are
refused.
"""

import math
from pathlib import Path

from ..geometry import Corner
from ..model import MM_PER
from ..solid import RoundedPolygon, SolidRevolved
from .dimensions import RADIUS, Dimension
from .letters import Letter
from .outline_file import Outline, outline_from_text
from .values import letter_values, real_corners

# A corner whose edges turn by less than this (the sine of the angle)
# is on a straight edge: dropped from the solid (#434).
STRAIGHT: float = 1e-9


# Function `outline_unit()`:
def outline_unit(outline: Outline) -> str:
    """Return the unit of an outline's first length letter.

    Arguments:
    * `outline` (`Outline`): The outline.

    Returns:
    * (`str`): Its first length letter's unit, or `mm` when it has none.
    """
    letter: Letter
    for letter in outline.letters:
        words: list[str] = letter.default.split()
        if words and words[-1] in MM_PER:
            return words[-1]
    return "mm"


# Function `outline_polygon()`:
def outline_polygon(outline: Outline, name: str = "") -> RoundedPolygon:
    """Return the polygon an outline's letters' values make.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `name` (`str`): The polygon's name ("" to be named by its solid).

    Returns:
    * (`RoundedPolygon`): The polygon, in millimeters, its unit that of
      the outline's first length letter.

    Raises:
    * `ValueError`: If it is revolved, has holes, a corner is not
      dimensioned, a letter's value is bad, or the polygon is not a
      good one (`RoundedPolygon`'s checks).
    """
    label: str = name or "outline"
    if outline.revolve:
        raise ValueError(
            f"{label}: a revolved outline is a `SolidRevolved` "
            "(`outline_revolved()`), not a polygon"
        )
    return _polygon(outline, name)


# Function `outline_revolved()`:
def outline_revolved(outline: Outline, name: str) -> SolidRevolved:
    """Return the round solid a revolved outline makes.

    Arguments:
    * `outline` (`Outline`): A revolved outline (a half profile).
    * `name` (`str`): The solid's name.

    Returns:
    * (`SolidRevolved`): The solid, its tip at the origin if the
      outline's is, its axis along Z.

    Raises:
    * `ValueError`: If it is not revolved, or its polygon or profile
      is bad (see `outline_polygon()`, `SolidRevolved`).
    """
    if not outline.revolve:
        raise ValueError(f"{name}: the outline is not revolved")
    return SolidRevolved(name, _polygon(outline, ""))


# Function `_polygon()`:
def _polygon(outline: Outline, name: str) -> RoundedPolygon:
    """Return the polygon an outline makes, revolved or not.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `name` (`str`): The polygon's name.

    Returns:
    * (`RoundedPolygon`): The polygon.

    Raises:
    * `ValueError`: As `outline_polygon()`, revolving aside.
    """
    label: str = name or "outline"
    if outline.holes:
        raise ValueError(f"{label}: holes are not made into solids yet (#290)")
    corners: list[tuple[float, float]] | None = real_corners(
        outline.points, outline.letters, outline.dimensions
    )
    if corners is None:
        raise ValueError(
            f"{label}: a corner is not dimensioned, or a value is bad"
        )
    values: dict[str, float] = letter_values(outline.letters)
    radii: dict[int, float] = {}
    dimension: Dimension
    for dimension in outline.dimensions:
        if dimension.kind != RADIUS:
            continue
        if dimension.letter not in values:
            raise ValueError(
                f"{label}: the fillet {dimension.letter!r} has no value"
            )
        radii[dimension.start] = values[dimension.letter]
    return RoundedPolygon(
        [
            Corner(x, y, radii.get(index, 0.0))
            for index, (x, y) in enumerate(corners)
            if index in radii or not _straight(corners, index)
        ],
        name,
        outline_unit(outline),
    )


# Function `_straight()`:
def _straight(corners: list[tuple[float, float]], index: int) -> bool:
    """Return whether a corner lies on a straight edge, its edges
    going on the same way (`T.tfo~6.5` #434): such a corner is only a
    place to dimension to (a drill's flutes' end), not a corner of the
    solid.

    Arguments:
    * `corners` (`list[tuple[float, float]]`): The real corners (mm).
    * `index` (`int`): The corner.

    Returns:
    * (`bool`): Whether it is straight.
    """
    # Straight when the edges in and out are parallel and the same way.
    before: tuple[float, float] = corners[index - 1]
    here: tuple[float, float] = corners[index]
    after: tuple[float, float] = corners[(index + 1) % len(corners)]
    ins: tuple[float, float] = (here[0] - before[0], here[1] - before[1])
    out: tuple[float, float] = (after[0] - here[0], after[1] - here[1])
    cross: float = ins[0] * out[1] - ins[1] * out[0]
    dot: float = ins[0] * out[0] + ins[1] * out[1]
    scale: float = math.hypot(*ins) * math.hypot(*out)
    return dot > 0.0 and abs(cross) <= STRAIGHT * scale


# Function `polygon_from_file()`:
def polygon_from_file(path: Path, name: str = "") -> RoundedPolygon:
    """Return the polygon an outline file makes.

    Arguments:
    * `path` (`Path`): The `.outline.toml` file.
    * `name` (`str`): The polygon's name ("" to be named by its solid).

    Returns:
    * (`RoundedPolygon`): The polygon.

    Raises:
    * `OSError`: If the file can not be read.
    * `ValueError`: If the file or the polygon is bad.
    """
    return outline_polygon(
        outline_from_text(path.read_text(encoding="utf-8"), str(path)), name
    )
