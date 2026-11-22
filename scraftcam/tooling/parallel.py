#!/usr/bin/env python3
"""A parallel as a parametric `SolidModel` made of `solid.py` layers.

Its side, a rectangle with round holes through it, is a
`SolidRoundedPolygon` (`T.rps~6.6` #346): the rectangle extruded by
the thickness, each hole a layer cut through.  Every size changes the
shape, so a change rebuilds it (a few milliseconds headless; parallels
are only changed during setup).  The older `tooling.tools.Parallel`
stays until this one replaces it.  Run as a program, it shows a
parallel in SolidCraft:

```
# Headless (prints the volume):
python3 -m scraftcam.tooling.parallel headless
# A GUI started with `--control 8085`:
python3 -m scraftcam.tooling.parallel 8085
```
"""

import math
import sys
from dataclasses import dataclass, field, replace
from fractions import Fraction

from ..geometry import Corner
from ..model import Length, SolidModel, meta
from ..pybind.scraftpybind import PyBind, connect
from ..solid import Layer, RoundedPolygon, SolidRoundedPolygon

# How the parallel looks.
PARALLEL_COLOR: str = "#8f9aa6"


# A zero length, for the layers' moves and the holes' depth.
ZERO: Length = Length(0, "in")

# A stand-in solid until `update()` makes the real one.
UNSET: SolidRoundedPolygon = SolidRoundedPolygon(
    "unset",
    Layer(
        RoundedPolygon((Corner(0.0, 0.0), Corner(1.0, 0.0), Corner(0.0, 1.0))),
        ZERO,
        ZERO,
        Length(1, "mm"),
    ),
)


# Class `Parallel`:
@dataclass(slots=True)
class Parallel(SolidModel):  # pylint: disable=too-many-instance-attributes
    """A parallel: a thin steel bar that work sits on in a vise.

    Parallels come in matched pairs, one under each side of the work.
    Most have round holes through them, which make them lighter and
    easier to pick up.

    Its coordinates: it lies on its side, from the origin: its
    `length` along X, its `height` along Y, its `thickness` up Z (an
    assembly stands it up, as `vise_setup.py` does).  Its holes go
    through along Z, halfway up its height, spaced evenly about its
    middle.  Its unit is inches;
    the defaults are a 1 in parallel of `tooling.tools.PARALLELS`.

    Attributes:
    * `height` (`Length`): Its size up.
    * `thickness` (`Length`): Its size across (Z).
    * `length` (`Length`): Its size along (X).
    * `hole_count` (`int`): How many holes (0 for none).
    * `hole_spacing` (`Length`): The distance between neighboring holes.
    * `hole_diameter` (`Length`): The diameter of its holes.
    * `solid` (`SolidRoundedPolygon`):
      Its layers, named `parallel` (a result).
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
        metadata=meta("length", "Height", "Its size up.", shape=True),
    )
    thickness: Length = field(
        default=Length(Fraction(1, 8), "in"),
        metadata=meta("length", "Thickness", "Its size across.", shape=True),
    )
    length: Length = field(
        default=Length(6, "in"),
        metadata=meta("length", "Length", "Its size along.", shape=True),
    )
    hole_count: int = field(
        default=2,
        metadata=meta(
            "count", "Holes", "How many holes (0 for none).", shape=True
        ),
    )
    hole_spacing: Length = field(
        default=Length(3, "in"),
        metadata=meta(
            "length", "Hole spacing", "Between neighboring holes.", shape=True
        ),
    )
    hole_diameter: Length = field(
        default=Length(Fraction(1, 2), "in"),
        metadata=meta("length", "Hole diameter", "Of each hole.", shape=True),
    )

    # Results (alphabetized):
    solid: SolidRoundedPolygon = field(init=False, default=UNSET)
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

        # The layers, and the volume they should have.
        self.solid = self._solid()
        hole_area: float = math.pi * (self.hole_diameter.mm() / 2.0) ** 2
        area: float = self.height.mm() * self.length.mm() - holes * hole_area
        self.volume = area * self.thickness.mm()

    # Method `Parallel._solid()`:
    def _solid(self) -> SolidRoundedPolygon:
        """Return the layers: the side, with each hole cut through.

        Returns:
        * (`SolidRoundedPolygon`): The parallel, named `parallel`.
        """
        side: RoundedPolygon = RoundedPolygon(
            (
                Corner(0.0, 0.0),
                Corner(self.length.mm(), 0.0),
                Corner(self.length.mm(), self.height.mm()),
                Corner(0.0, self.height.mm()),
            ),
            unit=self.UNIT,
        )
        middle: float = self.length.mm() / 2.0
        spacing: float = self.hole_spacing.mm()
        count: int = self.hole_count
        holes: list[Layer] = []
        if count:
            hole: RoundedPolygon = RoundedPolygon.circle(
                self.hole_diameter, unit=self.UNIT
            )
            index: int
            for index in range(count):
                x: float = middle + (index - (count - 1) / 2.0) * spacing
                holes.append(
                    Layer(
                        hole,
                        Length.from_mm(x, self.UNIT),
                        Length.from_mm(self.height.mm() / 2.0, self.UNIT),
                        ZERO,
                    )
                )
        return SolidRoundedPolygon(
            "parallel", Layer(side, ZERO, ZERO, self.thickness, holes)
        )

    # Method `Parallel.build()`:
    def build(self, solidcraft: PyBind, name: str) -> str:
        """Build the parallel as one body named `name`.

        Arguments:
        * `solidcraft` (`PyBind`): The SolidCraft session.
        * `name` (`str`): The parallel's name.

        Returns:
        * (`str`): The body's name.
        """
        body: str = replace(self.solid, name=name).build(solidcraft)[0]
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
