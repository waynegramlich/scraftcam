"""Solids: parts and assemblies, each of which is a `Solid`.

A `Solid` is anything that can be built into a SolidCraft design and
placed in an assembly (`T.rps~6.6`):

* `SolidStep`: one `.step` file, drawn elsewhere (in SolidCraft, or a
  vendor's).
* `SolidRoundedPolygon`: a tree of planar `RoundedPolygon`s, each
  extruded from its parent's `z` to its own.
* `SolidRevolved`: a half profile turned about its axis (round tools).
* `SolidAssembly`: other solids, each placed by a `Placement` (a
  rotation about the child's own origin, then a translation), so
  assemblies nest.

A `RoundedPolygon` here is immutable and planar: it has no Z, depth
or children, which the solid that uses it supplies.  `flip()` and
`rotate()` make new ones.  It is measured in millimeters, while its
`unit` is the one its user works in.  (The older
`geometry.RoundedPolygon`, with its own heights and children, stays
until `keepout.py` and `demo.py` move to these solids; this class
uses it to round its corners and check its outline.)

Color is not geometry: an `Appearance` on a solid is its default,
and an assembly may override it for one placement.
"""

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING, cast

from . import geometry
from .geometry import Corner, Point, XYSegment
from .model import MM_PER, Angle, Length, Placement

# A zero length, for defaults.
ZERO: Length = Length(Fraction(0), "mm")

if TYPE_CHECKING:
    from .pybind.scraftpybind import JSON, PyBind

# A solid's name, as SolidCraft takes it: letters, digits and `_`,
# a letter first, not ending with `_`, at most 64 characters.
NAME_PATTERN: re.Pattern[str] = re.compile(
    r"[A-Za-z]([A-Za-z0-9_]*[A-Za-z0-9])?"
)
NAME_LIMIT: int = 64

# The suffixes a STEP file may have.
STEP_SUFFIXES: tuple[str, ...] = (".step", ".stp")


# Function `check_name()`:
def check_name(name: str) -> None:
    """Check that a name is one SolidCraft takes.

    Arguments:
    * `name` (`str`): The name.

    Raises:
    * `ValueError`: If it is empty, too long, does not start with a
      letter, ends with `_`, or holds anything but letters, digits
      and `_`.
    """
    if len(name) > NAME_LIMIT or NAME_PATTERN.fullmatch(name) is None:
        raise ValueError(
            f"{name!r} is not a name: use at most {NAME_LIMIT} letters, "
            "digits and `_`, starting with a letter and not ending "
            "with `_`"
        )


# Function `in_unit()`:
# The arguments are the older class's, in its order.
# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def in_unit(
    unit: str,
    name: str,
    corners: Sequence[Corner],
    z_start: float,
    z_end: float,
    children: Sequence[geometry.RoundedPolygon] = (),
) -> geometry.RoundedPolygon:
    """Make an older `geometry.RoundedPolygon`, its numbers in `unit`.

    The older class has no units: its numbers are whatever its caller
    uses.  Here they are always in `unit`, which its messages are then
    marked with.

    Arguments:
    * `unit` (`str`): The unit of every number given.
    * `name` (`str`): Its name.
    * `corners` (`Sequence[Corner]`): Its corners.
    * `z_start` (`float`): Where it starts.
    * `z_end` (`float`): Where it ends.
    * `children` (`Sequence[geometry.RoundedPolygon]`): Its children.

    Returns:
    * (`geometry.RoundedPolygon`): The polygon.

    Raises:
    * `ValueError`: If the older class refuses it, marked
      `(lengths in UNIT)`.
    """
    try:
        return geometry.RoundedPolygon(name, corners, z_start, z_end, children)
    except ValueError as error:
        raise ValueError(f"{error} (lengths in {unit})") from error


# Class `Appearance`:
@dataclass(frozen=True, slots=True)
class Appearance:
    """A color and how see-through it is.

    Attributes:
    * `r` (`float`): Red, 0 to 1.
    * `g` (`float`): Green, 0 to 1.
    * `b` (`float`): Blue, 0 to 1.
    * `t` (`float`): Transparency: 0 opaque, 1 clear.

    Constructor:
    * `Appearance(r, g, b, t)`
    """

    # Constructor arguments:
    r: float = field(init=True)
    g: float = field(init=True)
    b: float = field(init=True)
    t: float = field(init=True, default=0.0)

    # Method `Appearance.__post_init__()`:
    def __post_init__(self) -> None:
        """Check that every part is from 0 to 1.

        Raises:
        * `ValueError`: If a part is outside 0 to 1 (or not a number).
        """
        label: str
        value: float
        for label, value in zip(
            "rgbt", (self.r, self.g, self.b, self.t), strict=True
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{label}={value!r} is not from 0 to 1")

    # Method `Appearance.hex()`:
    def hex(self) -> str:
        """Return the color as `#RRGGBB` (without the transparency).

        Returns:
        * (`str`): The color, for SolidCraft's `appearance.assign`.
        """
        parts: list[int] = [
            round(value * 255) for value in (self.r, self.g, self.b)
        ]
        return "#" + "".join(f"{part:02x}" for part in parts)


# Class `Solid`:
@dataclass(frozen=True, slots=True)
class Solid:
    """Anything that can be built into a design and placed.

    Subclasses build themselves with `build()`.  A solid is immutable,
    so one solid may be placed many times (one SolidCraft component,
    several occurrences).

    Attributes:
    * `name` (`str`): Its name (see `check_name()`).
    * `appearance` (`Appearance | None`):
      Its color, or `None` to take its parent's (keyword only).

    Constructor:
    * `Solid(name, appearance=None)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    appearance: Appearance | None = field(
        init=True, default=None, kw_only=True
    )

    # Method `Solid.__post_init__()`:
    def __post_init__(self) -> None:
        """Check the name.

        Raises:
        * `ValueError`: If the name is not one SolidCraft takes.
        """
        check_name(self.name)

    # Method `Solid.build()`:
    def build(self, solidcraft: "PyBind") -> list[str]:
        """Build this solid into the design, around the origin.

        Arguments:
        * `solidcraft` (`PyBind`): Where to build it.

        Returns:
        * (`list[str]`): The names of the bodies made.

        Raises:
        * `NotImplementedError`: Always; each subclass builds itself.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not say how to build {self.name}"
        )


# Class `SolidStep`:
@dataclass(frozen=True, slots=True)
class SolidStep(Solid):
    """A solid that is one `.step` file.

    Attributes:
    * `name` (`str`): Its name (see `check_name()`).
    * `path` (`Path`): The `.step` (or `.stp`) file.
    * `appearance` (`Appearance | None`):
      Its color, or `None` to take its parent's (keyword only).

    Constructor:
    * `SolidStep(name, path, appearance=None)`
    """

    # Constructor arguments:
    path: Path = field(init=True)

    # Method `SolidStep.__post_init__()`:
    def __post_init__(self) -> None:
        """Check the name and the file's suffix.

        The file need not exist yet; `build()` reads it.

        Raises:
        * `ValueError`: If the name is bad, or the suffix is not one
          of `STEP_SUFFIXES`.
        """
        Solid.__post_init__(self)
        if self.path.suffix.lower() not in STEP_SUFFIXES:
            raise ValueError(
                f"{self.name}: {str(self.path)!r} is not a STEP file "
                f"(one of {', '.join(STEP_SUFFIXES)})"
            )

    # Method `SolidStep.insert()`:
    def insert(self, solidcraft: "PyBind") -> "JSON":
        """Insert the file as a new component in the active one.

        SolidCraft makes the component itself, named for this solid,
        so an assembly uses this in place of `component.create`.

        Arguments:
        * `solidcraft` (`PyBind`): Where to insert it.

        Returns:
        * (`JSON`): SolidCraft's answer: `component`, `occurrence`,
          `created_bodies`, ...

        Raises:
        * `FileNotFoundError`: If the file does not exist.
        """
        if not self.path.is_file():
            raise FileNotFoundError(
                f"{self.name}: no STEP file {str(self.path)!r}"
            )
        return solidcraft.file.insert_step(path=str(self.path), name=self.name)

    # Method `SolidStep.build()`:
    def build(self, solidcraft: "PyBind") -> list[str]:
        """Insert the file into the design, around the origin.

        Arguments:
        * `solidcraft` (`PyBind`): Where to insert it.

        Returns:
        * (`list[str]`): The names of the bodies it holds.

        Raises:
        * `FileNotFoundError`: If the file does not exist.
        """
        return step_bodies(self.insert(solidcraft))


# Function `step_bodies()`:
def step_bodies(made: "JSON") -> list[str]:
    """Return the bodies a STEP file's insert made.

    Arguments:
    * `made` (`JSON`): What `file.insert_step` answered.

    Returns:
    * (`list[str]`): The names of its bodies.
    """
    assert isinstance(made, dict)
    bodies: JSON = made["created_bodies"]
    assert isinstance(bodies, list)
    return [str(body) for body in bodies]


# Class `RoundedPolygon`:
@dataclass(frozen=True, slots=True)
class RoundedPolygon:
    """An immutable planar polygon with a radius at each corner.

    Its corners are in millimeters, in order around it, either way
    round; each is rounded by an arc tangent to its two edges.  It is
    checked when made: at least 3 corners, none straight or turning
    back, the arcs fitting their edges, and the outline neither
    crossing nor touching itself.

    Attributes:
    * `name` (`str`): Its name (see `check_name()`), or "" when the
      solid using it names its sketch (`NAME_NNN`).
    * `corners` (`Sequence[Corner]`):
      The corners, in millimeters (stored as a tuple).
    * `unit` (`str`):
      The unit its user works in (one of `model.MM_PER`'s keys).
    * `box` (`tuple[float, float, float, float]`):
      Low X, high X, low Y and high Y of a box around the outline.
    * `segments` (`tuple[XYSegment, ...]`):
      The outline's lines and arcs, starting with the edge that
      leaves the first corner.
    * `signed_area` (`float`):
      The sharp polygon's area: positive counter-clockwise.

    Constructor:
    * `RoundedPolygon(corners, name, unit)`
    """

    # Constructor arguments:
    corners: Sequence[Corner] = field(init=True)
    name: str = field(init=True, default="")
    unit: str = field(init=True, default="mm")

    # Attributes set by `__post_init__()` (alphabetized):
    box: tuple[float, float, float, float] = field(
        init=False, default=(0.0, 0.0, 0.0, 0.0)
    )
    segments: tuple[XYSegment, ...] = field(init=False, default=())
    signed_area: float = field(init=False, default=0.0)

    # Method `RoundedPolygon.__post_init__()`:
    def __post_init__(self) -> None:
        """Check the polygon, and compute its outline.

        Raises:
        * `ValueError`: If the name or unit is bad, or the corners do
          not make a good outline (see the class's docstring).
        """
        if self.name:
            check_name(self.name)
        if self.unit not in MM_PER:
            raise ValueError(
                f"{self.label()}: {self.unit=} is not one of {list(MM_PER)}"
            )
        corners: tuple[Corner, ...] = tuple(self.corners)
        object.__setattr__(self, "corners", corners)

        # The older class rounds the corners and checks the outline
        # (its heights are placeholders): first in the user's unit, so
        # its messages are, then in millimeters, which are kept.
        per: float = float(MM_PER[self.unit])
        if self.unit != "mm":
            in_unit(
                self.unit,
                self.label(),
                [
                    Corner(c.x / per, c.y / per, c.radius / per)
                    for c in corners
                ],
                0.0,
                1.0,
            )
        shape: geometry.RoundedPolygon = in_unit(
            "mm", self.label(), corners, 0.0, 1.0
        )
        object.__setattr__(self, "box", shape.box)
        object.__setattr__(self, "segments", shape.segments)
        object.__setattr__(self, "signed_area", shape.signed_area)

    # Method `RoundedPolygon.circle()`:
    @staticmethod
    def circle(
        diameter: Length, name: str = "", unit: str = ""
    ) -> "RoundedPolygon":
        """Return a circle about the origin.

        It is a square of side `diameter` with every corner rounded to
        half of it, so its outline is four quarter arcs.

        Arguments:
        * `diameter` (`Length`): The circle's diameter.
        * `name` (`str`): Its name ("" to be named by its solid).
        * `unit` (`str`): Its user's unit ("" for the diameter's).

        Returns:
        * (`RoundedPolygon`): The circle.
        """
        r: float = diameter.mm() / 2.0
        return RoundedPolygon(
            (
                Corner(-r, -r, r),
                Corner(r, -r, r),
                Corner(r, r, r),
                Corner(-r, r, r),
            ),
            name,
            unit or diameter.unit,
        )

    # Method `RoundedPolygon.mirrored()`:
    @staticmethod
    def mirrored(
        half: Sequence[Corner], name: str = "", unit: str = "mm"
    ) -> "RoundedPolygon":
        """Return a polygon symmetric about the Y axis, from its right half.

        The half is drawn as the outline editor draws a revolved one
        (#373): it runs counter-clockwise from a corner on the Y axis
        (`x` 0), through corners right of it, to another on the axis;
        the left half is its mirror.  An axis corner where the two
        halves meet in a straight line (the middle of an edge) is left
        out.  This is how a vise is drawn: half of it, the rest the
        mirror image (a drill's half is revolved instead).

        Arguments:
        * `half` (`Sequence[Corner]`): The right half, in millimeters.
        * `name` (`str`): Its name ("" to be named by its solid).
        * `unit` (`str`): Its user's unit.

        Returns:
        * (`RoundedPolygon`): The whole polygon.

        Raises:
        * `ValueError`: If `half` has fewer than 2 corners, does not
          start and end on the axis, or has a corner left of it.
        """
        label: str = name or "polygon"
        corners: list[Corner] = list(half)
        if len(corners) < 2:
            raise ValueError(f"{label}: a half needs 2 corners")
        if corners[0].x != 0.0 or corners[-1].x != 0.0:
            raise ValueError(
                f"{label}: a half must start and end on the Y axis (x = 0)"
            )
        if any(corner.x < 0.0 for corner in corners):
            raise ValueError(f"{label}: a half must not go left of the Y axis")
        left: list[Corner] = [
            Corner(-corner.x, corner.y, corner.radius)
            for corner in reversed(corners[1:-1])
        ]
        whole: list[Corner] = [*corners, *left]

        # Leave out axis corners whose neighbors are mirror images
        # straight across (a level edge through the axis).
        count: int = len(whole)
        kept: list[Corner] = []
        index: int
        corner: Corner
        for index, corner in enumerate(whole):
            before: Corner = whole[index - 1]
            after: Corner = whole[(index + 1) % count]
            straight: bool = (
                corner.x == 0.0
                and before.y == after.y == corner.y
                and before.x == -after.x
            )
            if not straight:
                kept.append(corner)
        return RoundedPolygon(kept, name, unit)

    # Method `RoundedPolygon.label()`:
    def label(self) -> str:
        """Return its name, or "polygon" when it has none, for messages.

        Returns:
        * (`str`): The label.
        """
        return self.name or "polygon"

    # Method `RoundedPolygon.is_ccw()`:
    def is_ccw(self) -> bool:
        """Return whether the corners go counter-clockwise.

        Returns:
        * (`bool`): True when they go counter-clockwise.
        """
        return self.signed_area > 0.0

    # Method `RoundedPolygon.renamed()`:
    def renamed(self, name: str) -> "RoundedPolygon":
        """Return the same polygon with another name.

        Arguments:
        * `name` (`str`): The new name.

        Returns:
        * (`RoundedPolygon`): The renamed polygon.
        """
        return RoundedPolygon(self.corners, name, self.unit)

    # Method `RoundedPolygon.flip()`:
    def flip(
        self, start: Point, end: Point, name: str = ""
    ) -> "RoundedPolygon":
        """Return the polygon mirrored across the line through two points.

        The corners are put back in their old direction (a mirror
        reverses it), the first corner staying first.

        Arguments:
        * `start` (`Point`): A point on the flip line (millimeters).
        * `end` (`Point`): Another point on it.
        * `name` (`str`): The new polygon's name ("" keeps this one's).

        Returns:
        * (`RoundedPolygon`): The mirrored polygon.

        Raises:
        * `ValueError`: If `start` and `end` are the same point.
        """
        # Reflect each corner: p' = 2 (s + ((p - s) . u) u) - p.
        dx: float = end[0] - start[0]
        dy: float = end[1] - start[1]
        size: float = math.hypot(dx, dy)
        if size == 0.0:
            raise ValueError(f"{self.label()}: the flip line has no length")
        ux: float = dx / size
        uy: float = dy / size
        mirrored: list[Corner] = []
        corner: Corner
        for corner in self.corners:
            along: float = (corner.x - start[0]) * ux + (
                corner.y - start[1]
            ) * uy
            foot_x: float = start[0] + along * ux
            foot_y: float = start[1] + along * uy
            mirrored.append(
                Corner(
                    2.0 * foot_x - corner.x,
                    2.0 * foot_y - corner.y,
                    corner.radius,
                )
            )
        return RoundedPolygon(
            (mirrored[0], *mirrored[:0:-1]), name or self.name, self.unit
        )

    # Method `RoundedPolygon.rotate()`:
    def rotate(
        self, center: Point, angle: Angle, name: str = ""
    ) -> "RoundedPolygon":
        """Return the polygon turned about a point (counter-clockwise).

        Arguments:
        * `center` (`Point`): The point turned about (millimeters).
        * `angle` (`Angle`): How far to turn.
        * `name` (`str`): The new polygon's name ("" keeps this one's).

        Returns:
        * (`RoundedPolygon`): The turned polygon.
        """
        radians: float = angle.radians()
        cosine: float = math.cos(radians)
        sine: float = math.sin(radians)
        turned: list[Corner] = []
        corner: Corner
        for corner in self.corners:
            x: float = corner.x - center[0]
            y: float = corner.y - center[1]
            turned.append(
                Corner(
                    center[0] + x * cosine - y * sine,
                    center[1] + x * sine + y * cosine,
                    corner.radius,
                )
            )
        return RoundedPolygon(turned, name or self.name, self.unit)

    # Method `RoundedPolygon.draw()`:
    def draw(self, solidcraft: "PyBind", dx: float, dy: float) -> list[str]:
        """Draw the outline, moved by (dx, dy), into the open sketch.

        The caller creates the sketch (`sketch.create`) and finishes
        it (`sketch.finish`).

        Arguments:
        * `solidcraft` (`PyBind`): Where to draw it.
        * `dx` (`float`): How far to move it in X (millimeters).
        * `dy` (`float`): How far to move it in Y (millimeters).

        Returns:
        * (`list[str]`): The ids of the curves drawn, in order.
        """

        # Function `moved()`:
        def moved(point: Point) -> Point:
            """Return a point moved by (dx, dy).

            Arguments:
            * `point` (`Point`): The point.

            Returns:
            * (`Point`): The moved point.
            """
            return point[0] + dx, point[1] + dy

        curves: list[str] = []
        segment: XYSegment
        for segment in self.segments:
            # SolidCraft's arcs go counter-clockwise from `start` to
            # `end`, so a clockwise arc is drawn from its end.
            result: JSON
            if isinstance(segment, geometry.LineSegment):
                result = solidcraft.sketch.line(
                    points=cast(
                        "JSON", [moved(segment.start), moved(segment.end)]
                    )
                )
            else:
                ends: tuple[Point, Point] = (segment.start, segment.end)
                if segment.sweep < 0.0:
                    ends = (segment.end, segment.start)
                result = solidcraft.sketch.arc_center_point(
                    center=moved(segment.center),
                    start=moved(ends[0]),
                    end=moved(ends[1]),
                )
            assert isinstance(result, dict)
            ids: JSON = result["curves"]
            assert isinstance(ids, list)
            curves += [str(curve) for curve in ids]
        return curves


# Class `Layer`:
@dataclass(frozen=True, slots=True)
class Layer:
    """One node of a `SolidRoundedPolygon`'s tree.

    The polygon is turned by `angle` (counter-clockwise) about
    `center` (in its own coordinates), then moved by (`dx`, `dy`) in
    its parent's coordinates (the root's from the origin); its
    children turn and move with it.  It spans from its parent's `z` (the
    root's from 0) to its own `z`: higher adds material, lower cuts it
    away.  `z` is absolute, so equal `z` means a matching level.  A
    polygon may be used in more than one layer.

    Attributes:
    * `polygon` (`RoundedPolygon`): Its outline.
    * `dx` (`Length`): How far it is moved in X from its parent.
    * `dy` (`Length`): How far it is moved in Y from its parent.
    * `z` (`Length`): The absolute height it ends at.
    * `children` (`Sequence[Layer]`):
      The layers that start on it (stored as a tuple).
    * `angle` (`Angle`): How far it is turned (keyword only).
    * `center` (`tuple[Length, Length]`):
      The point it is turned about (keyword only).

    Constructor:
    * `Layer(polygon, dx, dy, z, children, angle=0, center=(0, 0))`
    """

    # Constructor arguments:
    polygon: RoundedPolygon = field(init=True)
    dx: Length = field(init=True)
    dy: Length = field(init=True)
    z: Length = field(init=True)
    children: Sequence["Layer"] = field(init=True, default=())
    angle: Angle = field(init=True, default=Angle(Fraction(0)), kw_only=True)
    center: tuple[Length, Length] = field(
        init=True, default=(ZERO, ZERO), kw_only=True
    )

    # Method `Layer.__post_init__()`:
    def __post_init__(self) -> None:
        """Store the children as a tuple."""
        object.__setattr__(self, "children", tuple(self.children))


# Class `Frame`:
@dataclass(frozen=True, slots=True)
class Frame:
    """A turn then a move in the XY plane, in millimeters.

    A point `p` goes to `R p + (x, y)`, `R` turning by `angle`.

    Attributes:
    * `angle` (`float`): The turn, in radians (counter-clockwise).
    * `x` (`float`): The move in X.
    * `y` (`float`): The move in Y.

    Constructor:
    * `Frame(angle, x, y)`
    """

    # Constructor arguments:
    angle: float = field(init=True, default=0.0)
    x: float = field(init=True, default=0.0)
    y: float = field(init=True, default=0.0)

    # Method `Frame.of()`:
    @staticmethod
    def of(layer: Layer) -> "Frame":
        """Return a layer's frame within its parent.

        Turning about `center` is `p -> R (p - c) + c`, then the move.

        Arguments:
        * `layer` (`Layer`): The layer.

        Returns:
        * (`Frame`): Where the layer's coordinates go in its parent's.
        """
        angle: float = layer.angle.radians()
        cx: float = layer.center[0].mm()
        cy: float = layer.center[1].mm()
        turned: Frame = Frame(angle, 0.0, 0.0)
        tx: float
        ty: float
        tx, ty = turned.apply((-cx, -cy))
        return Frame(angle, tx + cx + layer.dx.mm(), ty + cy + layer.dy.mm())

    # Method `Frame.apply()`:
    def apply(self, point: Point) -> Point:
        """Return a point turned, then moved.

        Arguments:
        * `point` (`Point`): The point.

        Returns:
        * (`Point`): Where it goes.
        """
        cosine: float = math.cos(self.angle)
        sine: float = math.sin(self.angle)
        return (
            point[0] * cosine - point[1] * sine + self.x,
            point[0] * sine + point[1] * cosine + self.y,
        )

    # Method `Frame.then()`:
    def then(self, inner: "Frame") -> "Frame":
        """Return `inner` followed by this frame (inner within this).

        Arguments:
        * `inner` (`Frame`): A frame within this one.

        Returns:
        * (`Frame`): The two together.
        """
        x: float
        y: float
        x, y = self.apply((inner.x, inner.y))
        return Frame(self.angle + inner.angle, x, y)


# Class `SolidRoundedPolygon`:
@dataclass(frozen=True, slots=True)
class SolidRoundedPolygon(Solid):
    """A solid made of a tree of extruded planar polygons.

    The root `Layer` is extruded from 0 up to its `z`; each child from
    its parent's `z` to its own (see `Layer`).  It is checked when
    made: the root must go up, no layer may end where its parent does,
    each child must stay inside its parent's outline (touching is
    fine), and children of one parent must not overlap.  Layers whose
    polygon has no name are named `NAME_NNN` in tree order.

    Attributes:
    * `name` (`str`): Its name (see `check_name()`), also its body's.
    * `root` (`Layer`): The bottom layer.
    * `appearance` (`Appearance | None`):
      Its color, or `None` to take its parent's (keyword only).
    * `shape` (`geometry.RoundedPolygon`):
      The same tree, absolute, in the root polygon's unit (so that
      messages are in it), which checks and builds it.

    Constructor:
    * `SolidRoundedPolygon(name, root, appearance=None)`
    """

    # Constructor arguments:
    root: Layer = field(init=True)

    # Remaining attributes (alphabetized):
    shape: geometry.RoundedPolygon = field(
        init=False, repr=False, compare=False
    )

    # Method `SolidRoundedPolygon.__post_init__()`:
    def __post_init__(self) -> None:
        """Check the tree, and make its shape in the root's unit.

        Raises:
        * `ValueError`: If the name is bad, the root does not go up, a
          layer ends where its parent does, a child leaves its
          parent's outline, or two children of one parent overlap.
        """
        Solid.__post_init__(self)
        unit: str = self.root.polygon.unit
        per: float = float(MM_PER[unit])
        if self.root.z.mm() <= 0.0:
            raise ValueError(
                f"{self.name}: the root must go up from 0, not to "
                f"{self.root.z}"
            )
        count: list[int] = [0]

        # Function `shaped()`:
        def shaped(
            layer: Layer, parent: Frame, z_start: float
        ) -> geometry.RoundedPolygon:
            """Return a layer and its children, absolute, in `unit`.

            Arguments:
            * `layer` (`Layer`): The layer.
            * `parent` (`Frame`): Its parent's place (millimeters).
            * `z_start` (`float`): Its parent's `z` (in `unit`).

            Returns:
            * (`geometry.RoundedPolygon`): The layer's shape.
            """
            name: str = layer.polygon.name or self.name
            if layer is not self.root:
                count[0] += 1
                name = layer.polygon.name or f"{self.name}_{count[0]:03d}"
            here: Frame = parent.then(Frame.of(layer))
            z_end: float = float(layer.z.to(unit).value)
            corners: list[Corner] = []
            corner: Corner
            for corner in layer.polygon.corners:
                x: float
                y: float
                x, y = here.apply((corner.x, corner.y))
                corners.append(Corner(x / per, y / per, corner.radius / per))
            children: list[geometry.RoundedPolygon] = [
                shaped(child, here, z_end) for child in layer.children
            ]
            return in_unit(unit, name, corners, z_start, z_end, children)

        object.__setattr__(self, "shape", shaped(self.root, Frame(), 0.0))

    # Method `SolidRoundedPolygon.build()`:
    def build(self, solidcraft: "PyBind") -> list[str]:
        """Build it as one body: the root's extrude, then joins and cuts.

        Arguments:
        * `solidcraft` (`PyBind`): Where to build it.

        Returns:
        * (`list[str]`): The name of its one body.
        """
        unit: str = self.root.polygon.unit
        return [self.shape.model(solidcraft, float(MM_PER[unit]))]


# How far along its slanted edge a tip on the axis is cut flat (#106,
# from `T.oe~6.2`): a point on the axis revolves into an ill-defined
# solid.
TIP_FLAT: float = 0.05


# Function `flat_tips()`:
def flat_tips(corners: Sequence[Corner]) -> list[Corner]:
    """Return the corners with each tip on the axis cut flat (#106).

    A sharp corner at X = 0 between an edge on the axis and a slanted
    one becomes two: `TIP_FLAT` of the way along the slanted edge, and
    on the axis at that height.  A corner beside a level edge is no
    tip.

    Arguments:
    * `corners` (`Sequence[Corner]`): The half profile's corners.

    Returns:
    * (`list[Corner]`): The corners, tips cut.
    """
    flat: list[Corner] = []
    index: int
    corner: Corner
    for index, corner in enumerate(corners):
        before: Corner = corners[index - 1]
        after: Corner = corners[(index + 1) % len(corners)]
        other: Corner = after if before.x == 0.0 else before
        if (
            corner.x != 0.0
            or (before.x == 0.0) == (after.x == 0.0)
            or other.y == corner.y
        ):
            flat.append(corner)
            continue
        height: float = corner.y + TIP_FLAT * (other.y - corner.y)
        pair: list[Corner] = [
            Corner(0.0, height),
            Corner(TIP_FLAT * other.x, height),
        ]
        flat += pair if before.x == 0.0 else pair[::-1]
    return flat


# Class `SolidRevolved`:
@dataclass(frozen=True, slots=True)
class SolidRevolved(Solid):
    """A round solid: a half profile turned about its axis (#339).

    The profile is drawn as the outline editor draws a revolved
    outline: X out from the axis (never below 0), Y along it.  It is
    built with the profile's Y along Z, so a tool's tip at the
    profile's origin sits at the origin with its shank up +Z (as
    `T.tm~2.5` has it: "tip up the shank").  Tips on the axis are cut
    flat (`flat_tips()`).

    Attributes:
    * `name` (`str`): Its name (see `check_name()`), also its body's.
    * `profile` (`RoundedPolygon`): The half profile (millimeters).
    * `appearance` (`Appearance | None`):
      Its color, or `None` to take its parent's (keyword only).
    * `flat` (`RoundedPolygon`): The profile with its tips cut flat.

    Constructor:
    * `SolidRevolved(name, profile, appearance=None)`
    """

    # Constructor arguments:
    profile: RoundedPolygon = field(init=True)

    # Remaining attributes (alphabetized):
    flat: RoundedPolygon = field(init=False, repr=False, compare=False)

    # Method `SolidRevolved.__post_init__()`:
    def __post_init__(self) -> None:
        """Check the profile, and cut its tips flat.

        Raises:
        * `ValueError`: If the name is bad, a corner is left of the
          axis, or no edge lies on the axis.
        """
        Solid.__post_init__(self)
        corners: tuple[Corner, ...] = tuple(self.profile.corners)
        if any(corner.x < 0.0 for corner in corners):
            raise ValueError(
                f"{self.name}: a revolved profile must not cross the axis "
                "(x < 0)"
            )
        if not any(
            corner.x == 0.0 and corners[index - 1].x == 0.0
            for index, corner in enumerate(corners)
        ):
            raise ValueError(
                f"{self.name}: a revolved profile needs an edge on the axis"
            )
        object.__setattr__(
            self,
            "flat",
            RoundedPolygon(
                flat_tips(corners), self.profile.name, self.profile.unit
            ),
        )

    # Method `SolidRevolved.build()`:
    def build(self, solidcraft: "PyBind") -> list[str]:
        """Draw the profile on the XZ plane and revolve it about Z.

        Arguments:
        * `solidcraft` (`PyBind`): Where to build it.

        Returns:
        * (`list[str]`): The name of its one body.
        """
        solidcraft.sketch.create(
            plane=cast(
                "JSON",
                {
                    "origin": [0.0, 0.0, 0.0],
                    "x_dir": [1.0, 0.0, 0.0],
                    "y_dir": [0.0, 0.0, 1.0],
                },
            ),
            name=f"{self.name} profile",
        )
        curves: list[str] = self.flat.draw(solidcraft, 0.0, 0.0)
        solidcraft.sketch.finish()
        made: JSON = solidcraft.solid.revolve(
            axis=cast(
                "JSON", {"origin": [0.0, 0.0, 0.0], "dir": [0.0, 0.0, 1.0]}
            ),
            profiles=cast("JSON", [{"curves": curves}]),
            body_name=self.name,
        )
        assert isinstance(made, dict)
        bodies: JSON = made["created_bodies"]
        assert isinstance(bodies, list)
        return [str(body) for body in bodies]


# Class `Placed`:
@dataclass(frozen=True, slots=True)
class Placed:
    """One entry of a `SolidAssembly`: a solid, where it goes, its color.

    The solid is turned about its own origin, then its origin is moved
    to the placement's translation, in the assembly's coordinates.

    Attributes:
    * `solid` (`Solid`): What is placed.
    * `placement` (`Placement`): Where it goes.
    * `appearance` (`Appearance | None`):
      Its color here, or `None` for the solid's own (or its parent's).

    Constructor:
    * `Placed(solid, placement, appearance)`
    """

    # Constructor arguments:
    solid: Solid = field(init=True)
    placement: Placement = field(init=True, default_factory=Placement)
    appearance: Appearance | None = field(init=True, default=None)


# Class `Leaf`:
@dataclass(frozen=True, slots=True)
class Leaf:
    """A part of an assembly, flattened: where it is and its color.

    Attributes:
    * `solid` (`Solid`): The part (never an assembly).
    * `placement` (`Placement`): Where it is in the top assembly.
    * `appearance` (`Appearance | None`):
      Its color, or `None` for SolidCraft's default.
    * `path` (`tuple[str, ...]`):
      The names of the assemblies it is in, from the top, then its own.

    Constructor:
    * `Leaf(solid, placement, appearance, path)`
    """

    # Constructor arguments:
    solid: Solid = field(init=True)
    placement: Placement = field(init=True)
    appearance: Appearance | None = field(init=True)
    path: tuple[str, ...] = field(init=True)


# Class `SolidAssembly`:
@dataclass(frozen=True, slots=True)
class SolidAssembly(Solid):
    """Solids placed together; an assembly is a solid, so they nest.

    One solid may be placed many times.  Two different solids in one
    assembly (at any depth) may not share a name, since each becomes a
    SolidCraft component named for it.

    Attributes:
    * `name` (`str`): Its name (see `check_name()`).
    * `parts` (`Sequence[Placed]`):
      What it holds, in order (stored as a tuple).
    * `appearance` (`Appearance | None`):
      The color of parts that have none, or `None` to take its
      parent's (keyword only).

    Constructor:
    * `SolidAssembly(name, parts, appearance=None)`
    """

    # Constructor arguments:
    parts: Sequence[Placed] = field(init=True)

    # Method `SolidAssembly.__post_init__()`:
    def __post_init__(self) -> None:
        """Check the name, that it holds something, and its names.

        Raises:
        * `ValueError`: If the name is bad, it holds nothing, or two
          different solids in it share a name.
        """
        Solid.__post_init__(self)
        object.__setattr__(self, "parts", tuple(self.parts))
        if not self.parts:
            raise ValueError(f"{self.name}: an assembly must hold a solid")
        self.solids()

    # Method `SolidAssembly.solids()`:
    def solids(self) -> dict[str, Solid]:
        """Return every solid in it, at any depth, by name (itself too).

        Returns:
        * (`dict[str, Solid]`): The solids, in the order first met.

        Raises:
        * `ValueError`: If two different solids share a name.
        """
        found: dict[str, Solid] = {}

        # Function `visit()`:
        def visit(solid: Solid) -> None:
            """Add a solid and, for an assembly, what it holds.

            Arguments:
            * `solid` (`Solid`): The solid.

            Raises:
            * `ValueError`: If another solid already has its name.
            """
            seen: Solid | None = found.get(solid.name)
            if seen is not None:
                if seen is not solid and seen != solid:
                    raise ValueError(
                        f"{self.name}: two different solids are named "
                        f"{solid.name}"
                    )
                return
            found[solid.name] = solid
            if isinstance(solid, SolidAssembly):
                part: Placed
                for part in solid.parts:
                    visit(part.solid)

        visit(self)
        return found

    # Method `SolidAssembly.leaves()`:
    def leaves(self) -> list[Leaf]:
        """Return every part, flattened, placed in this assembly.

        A part's color is its entry's, else its own, else that of the
        nearest assembly (or entry) around it that has one.

        Returns:
        * (`list[Leaf]`): The parts, in order.
        """
        found: list[Leaf] = []

        # Function `visit()`:
        def visit(
            assembly: "SolidAssembly",
            where: Placement,
            color: Appearance | None,
            path: tuple[str, ...],
        ) -> None:
            """Add an assembly's parts.

            Arguments:
            * `assembly` (`SolidAssembly`): The assembly.
            * `where` (`Placement`): Where it is in the top one.
            * `color` (`Appearance | None`): Its color.
            * `path` (`tuple[str, ...]`): The names down to it.
            """
            part: Placed
            for part in assembly.parts:
                here: Placement = where.compose(part.placement)
                shown: Appearance | None = (
                    part.appearance or part.solid.appearance or color
                )
                inner: tuple[str, ...] = (*path, part.solid.name)
                if isinstance(part.solid, SolidAssembly):
                    visit(part.solid, here, shown, inner)
                else:
                    found.append(Leaf(part.solid, here, shown, inner))

        visit(self, Placement(), self.appearance, (self.name,))
        return found

    # Method `SolidAssembly.colors()`:
    def colors(self) -> dict[str, Appearance]:
        """Return the color of each solid that has one, by name.

        SolidCraft colors a whole component, every occurrence alike, so
        a solid gets its own color or its entries' (which must agree);
        one without either follows the component around it.

        Returns:
        * (`dict[str, Appearance]`): The colors, by solid name.

        Raises:
        * `ValueError`: If one solid is given two different colors.
        """
        found: dict[str, Appearance] = {}
        if self.appearance is not None:
            found[self.name] = self.appearance
        solid: Solid
        for solid in self.solids().values():
            if isinstance(solid, SolidAssembly):
                part: Placed
                for part in solid.parts:
                    color: Appearance | None = (
                        part.appearance or part.solid.appearance
                    )
                    if color is None:
                        continue
                    seen: Appearance = found.setdefault(part.solid.name, color)
                    if seen != color:
                        raise ValueError(
                            f"{self.name}: {part.solid.name} is given two "
                            "colors, but SolidCraft colors every "
                            "placement of a solid alike"
                        )
        return found

    # Method `SolidAssembly.build()`:
    def build(self, solidcraft: "PyBind") -> list[str]:
        """Build it as nested SolidCraft components, one per solid.

        Each solid is built once, in a component named for it inside
        the component of the first assembly that places it; each later
        placement is another occurrence of it (`occurrence.copy`).
        Each occurrence is then moved to its placement.

        Arguments:
        * `solidcraft` (`PyBind`): Where to build it.

        Returns:
        * (`list[str]`): The names of the bodies made, in order.

        Raises:
        * `ValueError`: If one solid is given two different colors.
        """
        colors: dict[str, Appearance] = self.colors()
        bodies: list[str] = []
        first: dict[str, Placement] = {}

        # Function `made()`:
        def made(reply: "JSON") -> int:
            """Return a new occurrence's id, free to move.

            Arguments:
            * `reply` (`JSON`): What `component.create` or
              `occurrence.copy` answered.

            Returns:
            * (`int`): The occurrence's id.
            """
            assert isinstance(reply, dict)
            occurrence: JSON = reply["occurrence"]
            assert isinstance(occurrence, int)
            if reply.get("grounded"):
                solidcraft.occurrence.ground(
                    occurrence=occurrence, grounded=False
                )
            return occurrence

        # Function `fill()`:
        def fill(assembly: SolidAssembly) -> None:
            """Build an assembly's parts into its (active) component.

            Arguments:
            * `assembly` (`SolidAssembly`): The assembly.
            """
            part: Placed
            for part in assembly.parts:
                name: str = part.solid.name
                old: Placement | None = first.get(name)
                occurrence: int
                move: Placement = part.placement
                if old is None and isinstance(part.solid, SolidStep):
                    # The insert is the component (in the active one).
                    reply: JSON = part.solid.insert(solidcraft)
                    occurrence = made(reply)
                    bodies.extend(step_bodies(reply))
                    first[name] = part.placement
                elif old is None:
                    occurrence = made(
                        solidcraft.component.create(
                            name=name, parent=assembly.name
                        )
                    )
                    if isinstance(part.solid, SolidAssembly):
                        fill(part.solid)
                    else:
                        bodies.extend(part.solid.build(solidcraft))
                    solidcraft.component.activate(component=assembly.name)
                    first[name] = part.placement
                else:
                    # A copy starts where the first placement is.
                    occurrence = made(
                        solidcraft.occurrence.copy(
                            component=name, parent=assembly.name
                        )
                    )
                    move = part.placement.delta(old)
                if move != Placement():
                    solidcraft.occurrence.move(
                        occurrence=occurrence,
                        matrix=cast("JSON", move.matrix()),
                    )

        solidcraft.component.create(name=self.name)
        fill(self)
        solidcraft.component.activate(component="root")
        name: str
        color: Appearance
        for name, color in colors.items():
            solidcraft.appearance.assign(
                components=[name], color=color.hex(), opacity=1.0 - color.t
            )
        return bodies
