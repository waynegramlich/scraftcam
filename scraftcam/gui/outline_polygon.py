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
from typing import cast

from .. import solid as solid_module
from ..appearance import Color
from ..geometry import Corner
from ..model import MM_PER
from ..model_cache import Cacheable, source_digest
from ..pybind.scraftpybind import JSON
from ..solid import (
    Appearance,
    Placed,
    RoundedPolygon,
    Solid,
    SolidAssembly,
    SolidRevolved,
)
from .dimensions import RADIUS, Dimension
from .letters import Letter
from .outline_file import Outline, Role, outline_from_text
from .values import letter_values, real_corners

# A corner whose edges turn by less than this (the sine of the angle)
# is on a straight edge: dropped from the solid (#434).
STRAIGHT: float = 1e-9

# A corner closer than this (mm) to the one before it is in the same
# place: dropped from the solid (`T.tfo~6.5` #450).
SAME: float = 1e-9


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


# How see-through a cutting polygon's solid is: light slips through a
# spinning bit's flutes (`T.sa~6.11` #817, #826).
CUTTING_TRANSPARENCY: float = 0.2


# Function `outline_revolved()`:
def outline_revolved(
    outline: Outline, name: str, *, color: Color | None = None
) -> Solid:
    """Return the round solid a revolved outline makes: one
    `SolidRevolved` per polygon, several stacked in a `SolidAssembly`
    where their drawing puts them (`T.sa~6.11` #818, #823).

    Arguments:
    * `outline` (`Outline`): A revolved outline (a half profile).
    * `name` (`str`): The solid's name; a part is `NAME_POLYGON`
      (#827; SolidCraft's names take no `.`).
    * `color` (`Color | None`): Its material's colour (a tool's,
      `appearance.material_look()`), or `None` for SolidCraft's;
      a `cutting` polygon's part is `CUTTING_TRANSPARENCY`
      see-through (#826).

    Returns:
    * (`Solid`): The solid, its tip at the origin if the outline's
      is, its axis along Z.

    Raises:
    * `ValueError`: If it is not revolved, or a polygon or profile is
      bad (see `outline_polygon()`, `SolidRevolved`).
    """
    if not outline.revolve:
        raise ValueError(f"{name}: the outline is not revolved")
    outline.fill_polygons()
    profiles: list[RoundedPolygon] = _polygons(outline, name)
    if len(profiles) == 1:
        return SolidRevolved(
            name, profiles[0], appearance=_appearance(color, Role.OTHER)
        )
    return SolidAssembly(
        name,
        [
            Placed(
                SolidRevolved(
                    f"{name}_{polygon.name}",
                    profile,
                    appearance=_appearance(color, polygon.role),
                )
            )
            for polygon, profile in zip(
                outline.polygons, profiles, strict=True
            )
        ],
    )


# Function `outline_cacheable()`:
def outline_cacheable(
    outline: Outline, name: str, *, color: Color | None = None
) -> Cacheable:
    """Return a revolved outline's solid as a model for the cache
    (`model_cache`, `T.sa~6.11` #819, #831): its `.step` is made
    headless and kept by a hash of only what shapes it (#837).

    Arguments:
    * `outline` (`Outline`): A revolved outline, its letters set.
    * `name` (`str`): The solid's name (a tool's).
    * `color` (`Color | None`): Its material's colour, given each time
      it is put in a design, not hashed.

    Returns:
    * (`Cacheable`): The model.

    Raises:
    * `ValueError`: As `outline_revolved()`.
    """
    solid: Solid = outline_revolved(outline, name, color=color)
    parts: list[Solid] = (
        [part.solid for part in solid.parts]
        if isinstance(solid, SolidAssembly)
        else [solid]
    )
    shape: JSON = {
        "kind": "outline_revolved",
        "source": source_digest(
            [Path(__file__), Path(str(solid_module.__file__))]
        ),
        "parts": [
            {
                "name": part.name,
                "corners": [
                    [corner.x, corner.y, corner.radius]
                    for corner in cast(SolidRevolved, part).profile.corners
                ],
            }
            for part in parts
        ],
    }
    looks: dict[str, Appearance] = {
        part.name: part.appearance
        for part in parts
        if part.appearance is not None
    }

    # Function `look_of()`:
    def look_of(body: str) -> Appearance | None:
        """Return a body's part's appearance, by the part's name."""
        found: list[str] = [part for part in looks if body.startswith(part)]
        return looks[max(found, key=len)] if found else None

    # Function `color_of()`:
    def color_of(body: str) -> str:
        """Return a body's colour, `#RRGGBB`, or "" for none."""
        look: Appearance | None = look_of(body)
        return "" if look is None else look.hex()

    # Function `opacity_of()`:
    def opacity_of(body: str) -> float:
        """Return a body's opacity (1 is solid)."""
        look: Appearance | None = look_of(body)
        return 1.0 if look is None else 1.0 - look.t

    return Cacheable(
        name, shape, solid.build, color_of=color_of, opacity_of=opacity_of
    )


# Function `_appearance()`:
def _appearance(color: Color | None, role: Role) -> Appearance | None:
    """Return a part's appearance: its material's colour, a cutting
    part see-through (#826).

    Arguments:
    * `color` (`Color | None`): The material's colour, if any.
    * `role` (`Role`): The part's polygon's role.

    Returns:
    * (`Appearance | None`): Its appearance; `None` with no colour.
    """
    if color is None:
        return None
    clear: float = color.transparency / 100.0
    if role is Role.CUTTING:
        clear = max(clear, CUTTING_TRANSPARENCY)
    return Appearance(
        color.red / 100.0, color.green / 100.0, color.blue / 100.0, clear
    )


# Function `_polygon()`:
def _polygon(outline: Outline, name: str) -> RoundedPolygon:
    """Return the polygon an outline of one polygon makes.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `name` (`str`): The polygon's name.

    Returns:
    * (`RoundedPolygon`): The polygon.

    Raises:
    * `ValueError`: As `outline_polygon()`, revolving aside, or when it
      has several polygons (extruded trees are #S5).
    """
    label: str = name or "outline"
    if len(outline.polygons) > 1:
        raise ValueError(
            f"{label}: several flat polygons are not made into solids"
            " yet (`T.sa~6.11` #S5)"
        )
    return _polygons(outline, name)[0]


# Function `_polygons()`:
def _polygons(outline: Outline, name: str) -> list[RoundedPolygon]:
    """Return the polygon each of an outline's polygons makes.

    Arguments:
    * `outline` (`Outline`): The outline.
    * `name` (`str`): The polygons' name ("" to be named by a solid).

    Returns:
    * (`list[RoundedPolygon]`): A polygon per outline polygon, in order.

    Raises:
    * `ValueError`: As `outline_polygon()`, revolving aside.
    """
    label: str = name or "outline"
    if outline.holes:
        raise ValueError(f"{label}: holes are not made into solids yet (#290)")
    loops: list[list[int]] = outline.loops()
    corners: list[tuple[float, float]] | None = real_corners(
        outline.points, outline.letters, outline.dimensions, loops
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
    return [
        _loop_polygon(
            [(index, corners[index]) for index in loop],
            radii,
            name,
            outline_unit(outline),
        )
        for loop in loops
    ]


# Function `_loop_polygon()`:
def _loop_polygon(
    loop: list[tuple[int, tuple[float, float]]],
    radii: dict[int, float],
    name: str,
    unit: str,
) -> RoundedPolygon:
    """Return the polygon one loop of real corners makes.

    Arguments:
    * `loop` (`list[tuple[int, tuple[float, float]]]`): Each corner's
      index and place (mm), in order.
    * `radii` (`dict[int, float]`): The fillets' radii, by corner.
    * `name` (`str`): The polygon's name.
    * `unit` (`str`): The outline's unit.

    Returns:
    * (`RoundedPolygon`): The polygon.
    """
    # Drop a corner in the same place as the one before it (a step
    # whose two sizes are equal, as an end mill's shank as big as its
    # cutter, #450), then the corners on straight edges.
    kept: list[tuple[int, tuple[float, float]]] = [
        (index, here)
        for spot, (index, here) in enumerate(loop)
        if index in radii or math.dist(here, loop[spot - 1][1]) > SAME
    ]
    places: list[tuple[float, float]] = [here for _, here in kept]
    return RoundedPolygon(
        [
            Corner(x, y, radii.get(index, 0.0))
            for place, (index, (x, y)) in enumerate(kept)
            if index in radii or not _straight(places, place)
        ],
        name,
        unit,
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
