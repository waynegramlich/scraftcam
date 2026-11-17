#!/usr/bin/env python3
"""A vise's jaw plate as a parametric `SolidModel` (`T.cmt~5.3`).

The first model on `scraftcam.model`: its parameters are `Length`s
in the units they were written in, and `build()` makes each one a
SolidCraft parameter, so that a change to one rebuilds the plate in
milliseconds.  The older `tooling.tools.JawPlate` stays until this one
replaces it.  Run as a program, it shows the Kurt plate in SolidCraft:

```
# Headless (prints the volume):
python3 -m scraftcam.tooling.jaw_plate headless
# A GUI started with `--control 8085`:
python3 -m scraftcam.tooling.jaw_plate 8085
```
"""

import math
import sys
from dataclasses import dataclass, field
from fractions import Fraction

from ..model import Length, SolidModel, meta
from ..pybind.scraftpybind import JSON, PyBind, connect

# How the plate looks.
JAW_PLATE_COLOR: str = "#9aa3ad"


# Class `JawPlate`:
@dataclass(slots=True)
class JawPlate(  # pylint: disable=too-many-instance-attributes
    SolidModel
):
    """A jaw plate: the replaceable part of a vise's jaw that clamps.

    Two socket head cap screws hold it to its jaw, each through a
    counterbore in the clamping face, so that its head sits below the
    face.  A 6 in vise's plates have holes on 3-7/8 in centers, for
    1/2-13 screws.

    Its coordinates: the origin is the center of its bottom face; its
    thickness (`length`) is along X, with the clamping face at +X; its
    `width` is along Y, and its `height` up Z.  Its unit is inches.
    The defaults are the Kurt D688's plate (see `tooling.tools`'s
    `KURT_JAW_PLATE` for where the numbers come from).

    Attributes:
    * `screw` (`str`): The screws that hold it on (e.g. `1/2-13 SHCS`).
    * `length` (`Length`): Its thickness, from its clamping face back.
    * `width` (`Length`): Its size across the vise.
    * `height` (`Length`): Its size up.
    * `hole_spacing` (`Length`): The distance between its two holes.
    * `hole_diameter` (`Length`): The diameter of its holes.
    * `hole_height` (`Length`):
      The height of its holes' centers above its bottom.
    * `counterbore_diameter` (`Length`):
      The diameter of the counterbores, for the screws' heads.
    * `counterbore_depth` (`Length`):
      How deep the counterbores reach in from the clamping face.
    * `half_length` (`Length`):
      From its center to its clamping face (a result).
    * `half_spacing` (`Length`):
      From its center to each hole's center (a result).
    * `volume` (`float`):
      The volume its solid should have, in cubic millimeters (a
      result).

    Constructor:
    * `JawPlate(screw, length, width, height, hole_spacing,
      hole_diameter, hole_height, counterbore_diameter,
      counterbore_depth)`
    """

    UNIT = "in"

    # Constructor arguments:
    screw: str = field(
        default="1/2-13 SHCS",
        metadata=meta("text", "Screws", "The screws that hold it on."),
    )
    length: Length = field(
        default=Length(Fraction("0.725"), "in"),
        metadata=meta("length", "Thickness", "From the clamping face back."),
    )
    width: Length = field(
        default=Length(6, "in"),
        metadata=meta("length", "Width", "Its size across the vise."),
    )
    height: Length = field(
        default=Length(Fraction("1.735"), "in"),
        metadata=meta("length", "Height", "Its size up."),
    )
    hole_spacing: Length = field(
        default=Length(Fraction(31, 8), "in"),
        metadata=meta(
            "length", "Hole spacing", "The distance between its holes."
        ),
    )
    hole_diameter: Length = field(
        default=Length(Fraction(17, 32), "in"),
        metadata=meta("length", "Hole diameter", "For the screws."),
    )
    hole_height: Length = field(
        default=Length(Fraction("0.94"), "in"),
        metadata=meta(
            "length", "Hole height", "The holes' centers above its bottom."
        ),
    )
    counterbore_diameter: Length = field(
        default=Length(20, "mm"),
        metadata=meta(
            "length", "Counterbore diameter", "For the screws' heads."
        ),
    )
    counterbore_depth: Length = field(
        default=Length(Fraction(17, 32), "in"),
        metadata=meta(
            "length", "Counterbore depth", "In from the clamping face."
        ),
    )

    # Results (alphabetized):
    half_length: Length = field(init=False, default=Length(0, "in"))
    half_spacing: Length = field(init=False, default=Length(0, "in"))
    volume: float = field(init=False, default=0.0)

    # Method `JawPlate.update()`:
    def update(self) -> None:
        """Check that the holes fit, and compute the results.

        Raises:
        * `ValueError`: If the plate has no size, or they do not fit.
        """
        # The plate must have a size.
        zero: Length = Length(0, self.UNIT)
        if min(self.length, self.width, self.height) <= zero:
            raise ValueError(
                f"{self.length}, {self.width}, {self.height}: a size is 0"
            )

        # The counterbores are the wider part of each hole, so they are
        # what must fit, beside each other and inside the plate.
        hole: Length = self.hole_diameter / 2
        counterbore: Length = self.counterbore_diameter / 2
        if not zero < hole < counterbore or not (
            zero < self.counterbore_depth < self.length
        ):
            raise ValueError(
                f"{self.hole_diameter} holes, {self.counterbore_diameter}"
                f" counterbores {self.counterbore_depth} deep: do not fit"
            )
        self.half_spacing = (self.hole_spacing / 2).to(self.UNIT)
        if (
            self.hole_spacing <= counterbore * 2
            or self.half_spacing + counterbore >= self.width / 2
            or self.hole_height - counterbore <= zero
            or self.hole_height + counterbore >= self.height
        ):
            raise ValueError(
                f"{self.counterbore_diameter} counterbores at"
                f" {self.hole_spacing} and {self.hole_height}: do not fit"
            )

        # What `build()` and its checks need.
        self.half_length = (self.length / 2).to(self.UNIT)
        hole_area: float = math.pi * hole.mm() ** 2
        counterbore_area: float = math.pi * counterbore.mm() ** 2
        deep: float = self.counterbore_depth.mm()
        each: float = hole_area * (self.length.mm() - deep)
        each += counterbore_area * deep
        block: float = self.length.mm() * self.width.mm() * self.height.mm()
        self.volume = block - 2.0 * each

    # Method `JawPlate.build()`:
    def build(self, solidcraft: PyBind, name: str) -> str:
        """Build the plate, driven by SolidCraft parameters.

        Each length parameter and result becomes the SolidCraft
        parameter `NAME__FIELD` (e.g. `jaw__width`), sent as a plain
        value, so that SolidCraft's expressions never refer to one
        another (`T.cmt~5.3` #22).

        Arguments:
        * `solidcraft` (`PyBind`): The SolidCraft session.
        * `name` (`str`): The plate's name, and its parameters' prefix.

        Returns:
        * (`str`): The body's name.
        """
        # One SolidCraft parameter per length.
        path: str
        value: object
        lengths: list[tuple[str, object]] = [
            *self.parameters(),
            *self.results(),
        ]
        for path, value in lengths:
            if isinstance(value, Length):
                solidcraft.parameters.add(
                    name=f"{name}__{path.replace('.', '__')}",
                    expression=value.solidcraft(),
                )

        # The block: a rectangle about the origin, its sides dimensioned
        # by the parameters, extruded up by the height.
        solidcraft.sketch.create(plane="XY", name=f"{name} block")
        outline: JSON = solidcraft.sketch.rectangle_center(
            center=(0.0, 0.0),
            corner=(self.half_length.mm(), self.width.mm() / 2.0),
        )
        assert isinstance(outline, dict)
        sides: JSON = outline["sides"]
        assert isinstance(sides, dict)
        solidcraft.sketch.dimension(
            entities=[sides["bottom"]], type="length", value=f"{name}__length"
        )
        solidcraft.sketch.dimension(
            entities=[sides["left"]], type="length", value=f"{name}__width"
        )
        solidcraft.sketch.finish()
        extruded: JSON = solidcraft.solid.extrude(
            distance=f"{name}__height", body_name=name
        )
        assert isinstance(extruded, dict)
        bodies: JSON = extruded["bodies"]
        assert isinstance(bodies, list) and isinstance(bodies[0], str)
        body: str = bodies[0]

        # The holes through it, then the counterbores, each cut from
        # the clamping face in (the YZ plane, moved out to that face).
        self._cut_holes(
            solidcraft, name, body, ("hole_diameter", "length", "holes")
        )
        self._cut_holes(
            solidcraft,
            name,
            body,
            ("counterbore_diameter", "counterbore_depth", "counterbores"),
        )
        solidcraft.appearance.assign(bodies=[body], color=JAW_PLATE_COLOR)
        return body

    # Method `JawPlate._cut_holes()`:
    def _cut_holes(
        self,
        solidcraft: PyBind,
        name: str,
        body: str,
        cut: tuple[str, str, str],
    ) -> None:
        """Cut the two holes, or the two counterbores, from the face in.

        Arguments:
        * `solidcraft` (`PyBind`): The SolidCraft session.
        * `name` (`str`): The plate's name, and its parameters' prefix.
        * `body` (`str`): The plate's body.
        * `cut` (`tuple[str, str, str]`): The diameter's field, the
          depth's field, and what they are (`holes`).
        """
        # Each circle is held by its diameter, and its center's distances
        # across and up from the sketch's origin.
        diameter, depth, part = cut
        solidcraft.sketch.create(
            plane="YZ",
            offset=f"{name}__half_length",
            name=f"{name} {part}",
        )
        across: float
        for across in (-1.0, 1.0):
            circle: JSON = solidcraft.sketch.circle_center(
                center=(
                    across * self.half_spacing.mm(),
                    self.hole_height.mm(),
                ),
                diameter=getattr(self, diameter).mm(),
            )
            assert isinstance(circle, dict)
            curves: JSON = circle["curves"]
            assert isinstance(curves, list)
            solidcraft.sketch.dimension(
                entities=curves,
                type="diameter",
                value=f"{name}__{diameter}",
            )
            solidcraft.sketch.dimension(
                entities=["origin", f"{curves[0]}.center"],
                type="horizontal",
                value=f"{name}__half_spacing",
            )
            solidcraft.sketch.dimension(
                entities=["origin", f"{curves[0]}.center"],
                type="vertical",
                value=f"{name}__hole_height",
            )
        solidcraft.sketch.finish()

        # Cut into the plate, away from the clamping face.
        solidcraft.solid.extrude(
            distance=f"{name}__{depth}",
            direction="negative",
            operation="cut",
            targets=[body],
        )


# Function `main()`:
def main() -> int:  # pragma: no cover
    """Build the Kurt plate in SolidCraft and print its volume.

    Returns:
    * (`int`): The exit code.
    """
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} headless|PORT", file=sys.stderr)
        return 2
    plate: JawPlate = JawPlate()
    with connect(sys.argv[1]) as transport:
        solidcraft: PyBind = PyBind(transport)
        body: str = plate.build(solidcraft, "jaw")
        print(f"{body}: expected volume {plate.volume:.3f} mm^3")
        print(solidcraft.component.properties())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
