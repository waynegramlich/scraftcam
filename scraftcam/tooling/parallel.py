#!/usr/bin/env python3
"""A parallel as a parametric `SolidModel` drawn from a `Profile`.

The first model whose sketch is a `scraftcam.outline.Profile`: its
side, a rectangle with round holes through it, is computed by
`update()`, and every point and center becomes a SolidCraft parameter
(`T.sdfm~2.5.2.1`), so a change of size is a few values sent, and a
change in the number of holes is a new sketch, found by
`SolidCraftLink` on its own.  The older `tooling.tools.Parallel` stays
until this one replaces it.  Run as a program, it shows a parallel in
SolidCraft:

```
# Headless (prints the volume):
python3 -m scraftcam.tooling.parallel headless
# A GUI started with `--control 8085`:
python3 -m scraftcam.tooling.parallel 8085
```
"""

import math
import sys
from dataclasses import dataclass, field
from fractions import Fraction

from ..geometry import ArcSegment, LineSegment, Loop, Point
from ..model import Length, SolidModel, meta
from ..outline import Profile, add_parameters
from ..pybind.scraftpybind import JSON, PyBind, connect

# How the parallel looks.
PARALLEL_COLOR: str = "#8f9aa6"


# Function `_unset_side()`:
def _unset_side() -> Profile:
    """Return a stand-in side until `update()` computes the real one.

    Returns:
    * (`Profile`): A small triangle named `unset`.
    """
    corners: list[Point] = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    return Profile(
        "unset",
        Loop(
            "unset",
            tuple(
                LineSegment(corners[index], corners[(index + 1) % 3])
                for index in range(3)
            ),
        ),
    )


# Class `Parallel`:
@dataclass(slots=True)
class Parallel(SolidModel):  # pylint: disable=too-many-instance-attributes
    """A parallel: a thin steel bar that work sits on in a vise.

    Parallels come in matched pairs, one under each side of the work.
    Most have round holes through them, which make them lighter and
    easier to pick up.

    Its coordinates: it stands on edge on the XY plane, its `length`
    along Y centered on the origin, its `thickness` along X centered on
    the origin, its `height` up Z.  Its holes go through along X,
    halfway up, spaced evenly about its middle.  Its unit is inches;
    the defaults are a 1 in parallel of `tooling.tools.PARALLELS`.

    Attributes:
    * `height` (`Length`): Its size up.
    * `thickness` (`Length`): Its size across (X).
    * `length` (`Length`): Its size along (Y).
    * `hole_count` (`int`): How many holes (0 for none).
    * `hole_spacing` (`Length`): The distance between neighboring holes.
    * `hole_diameter` (`Length`): The diameter of its holes.
    * `half_thickness` (`Length`):
      From its middle to each side (a result).
    * `side` (`Profile`):
      Its side on the YZ plane (sketch X is Y, sketch Y is Z), in
      millimeters (a result).
    * `volume` (`float`):
      The volume its solid should have, in cubic millimeters (a
      result).

    Constructor:
    * `Parallel(height, thickness, length, hole_count, hole_spacing,
      hole_diameter)`
    """

    UNIT = "in"

    # Constructor arguments:
    height: Length = field(
        default=Length(1, "in"),
        metadata=meta("length", "Height", "Its size up."),
    )
    thickness: Length = field(
        default=Length(Fraction(1, 8), "in"),
        metadata=meta("length", "Thickness", "Its size across."),
    )
    length: Length = field(
        default=Length(6, "in"),
        metadata=meta("length", "Length", "Its size along."),
    )
    hole_count: int = field(
        default=2,
        metadata=meta("count", "Holes", "How many holes (0 for none)."),
    )
    hole_spacing: Length = field(
        default=Length(3, "in"),
        metadata=meta("length", "Hole spacing", "Between neighboring holes."),
    )
    hole_diameter: Length = field(
        default=Length(Fraction(1, 2), "in"),
        metadata=meta("length", "Hole diameter", "Of each hole."),
    )

    # Results (alphabetized):
    half_thickness: Length = field(init=False, default=Length(0, "in"))
    side: Profile = field(init=False, default_factory=_unset_side)
    volume: float = field(init=False, default=0.0)

    # Method `Parallel.update()`:
    def update(self) -> None:
        """Check that the holes fit, and compute the side and volume.

        Raises:
        * `ValueError`: If the parallel has no size, or its holes do not
          fit inside it or apart.
        """
        # It must have a size, and its holes too.
        zero: Length = Length(0, self.UNIT)
        if min(self.height, self.thickness, self.length) <= zero:
            raise ValueError(
                f"{self.height}, {self.thickness}, {self.length}: a size is 0"
            )
        if self.hole_count < 0:
            raise ValueError(f"{self.hole_count} holes")
        holes: int = self.hole_count
        if holes and self.hole_diameter <= zero:
            raise ValueError(f"{self.hole_diameter} holes")

        # The holes must fit between its top and bottom, apart, and
        # inside its ends.
        if holes and self.hole_diameter >= self.height:
            raise ValueError(
                f"{self.hole_diameter} holes do not fit in a"
                f" {self.height} parallel"
            )
        if holes > 1 and self.hole_diameter >= self.hole_spacing:
            raise ValueError(
                f"{self.hole_diameter} holes {self.hole_spacing} apart touch"
            )
        reach: Length = self.hole_spacing * (holes - 1) + self.hole_diameter
        if holes and reach >= self.length:
            raise ValueError(
                f"{holes} holes {self.hole_spacing} apart need {reach}"
                f" of a {self.length} parallel"
            )

        # The side, and what `build()` needs.
        self.half_thickness = (self.thickness / 2).to(self.UNIT)
        self.side = self._side()
        hole_area: float = math.pi * (self.hole_diameter.mm() / 2.0) ** 2
        area: float = self.height.mm() * self.length.mm() - holes * hole_area
        self.volume = area * self.thickness.mm()

    # Method `Parallel._side()`:
    def _side(self) -> Profile:
        """Return the side: a rectangle with its holes.

        Returns:
        * (`Profile`): The side, in millimeters, counter-clockwise.
        """
        # The outside, counter-clockwise from its bottom left corner.
        half: float = self.length.mm() / 2.0
        top: float = self.height.mm()
        corners: list[Point] = [
            (-half, 0.0),
            (half, 0.0),
            (half, top),
            (-half, top),
        ]
        outer: Loop = Loop(
            "outside",
            tuple(
                LineSegment(corners[index], corners[(index + 1) % 4])
                for index in range(4)
            ),
        )

        # Each hole is one arc all the way round, from its right.
        radius: float = self.hole_diameter.mm() / 2.0
        spacing: float = self.hole_spacing.mm()
        holes: list[Loop] = []
        index: int
        for index in range(self.hole_count):
            center: Point = (
                (index - (self.hole_count - 1) / 2.0) * spacing,
                top / 2.0,
            )
            start: Point = (center[0] + radius, center[1])
            holes.append(
                Loop(
                    f"hole {index}",
                    (ArcSegment(start, start, center, radius, 2 * math.pi),),
                )
            )
        return Profile("side", outer, holes, self.UNIT)

    # Method `Parallel.solidcraft_values()`:
    def solidcraft_values(self, name: str) -> dict[str, str]:
        """Return the lengths' parameters, and the side's points.

        Arguments:
        * `name` (`str`): The parallel's name, and its parameters'
          prefix.

        Returns:
        * (`dict[str, str]`): SolidCraft expressions by parameter name.
        """
        values: dict[str, str] = SolidModel.solidcraft_values(self, name)
        values.update(self.side.values(f"{name}__side"))
        return values

    # Method `Parallel.build()`:
    def build(self, solidcraft: PyBind, name: str) -> str:
        """Build the parallel, driven by SolidCraft parameters.

        Arguments:
        * `solidcraft` (`PyBind`): The SolidCraft session.
        * `name` (`str`): The parallel's name, and its parameters'
          prefix.

        Returns:
        * (`str`): The body's name.
        """
        # Every parameter first, then the side, from the -X face across.
        add_parameters(solidcraft, self.solidcraft_values(name))
        solidcraft.sketch.create(
            plane="YZ",
            offset=f"-{name}__half_thickness",
            name=f"{name} side",
        )
        self.side.sketch(solidcraft, f"{name}__side")
        solidcraft.sketch.finish()
        extruded: JSON = solidcraft.solid.extrude(
            distance=f"{name}__thickness", body_name=name
        )
        assert isinstance(extruded, dict)
        bodies: JSON = extruded["bodies"]
        assert isinstance(bodies, list) and isinstance(bodies[0], str)
        body: str = bodies[0]
        solidcraft.appearance.assign(bodies=[body], color=PARALLEL_COLOR)
        return body


# Function `main()`:
def main() -> int:  # pragma: no cover
    """Build a parallel in SolidCraft and print its volume.

    Returns:
    * (`int`): The exit code.
    """
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} headless|PORT", file=sys.stderr)
        return 2
    parallel: Parallel = Parallel()
    with connect(sys.argv[1]) as transport:
        solidcraft: PyBind = PyBind(transport)
        body: str = parallel.build(solidcraft, "parallel")
        print(f"{body}: expected volume {parallel.volume:.3f} mm^3")
        print(solidcraft.component.properties())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
