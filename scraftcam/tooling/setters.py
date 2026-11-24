#!/usr/bin/env python3
"""3D models of the setters that set a machine's zero, for SolidCraft.

So far, a magnetic Z-axis zero setter (Shars 303-3104, page 414 of the
2026 catalog; `T.c~6.3`): a blue block, a silver cylinder out of
its top that the tool pushes down, and a dial on its front whose
pointer is straight up when the cylinder's top is exactly the
setter's height above its base.  Run as a program, it shows one in
SolidCraft:

```
# A GUI started with `--control 8081`:
python3 -m scraftcam.tooling.setters 8081
# The metric one:
python3 -m scraftcam.tooling.setters 8081 metric
```
"""

import sys
from dataclasses import dataclass, field

from ..pybind.scraftpybind import JSON, PyBind, connect
from .cutter_models import MM_PER_INCH

# A point: `(x, y, z)`, in millimeters.
Point = tuple[float, float, float]

# How the setter's parts look (the user's description).
BLOCK_COLOR: str = "#2f5fb3"
SILVER_COLOR: str = "#c8ccd0"
DIAL_COLOR: str = "#f4f4f4"
POINTER_COLOR: str = "#202020"


# Class `ZSetter`:
# Each attribute is one fact it holds; grouping them would not read better.
@dataclass(frozen=True, slots=True)
class ZSetter:  # pylint: disable=too-many-instance-attributes
    """A magnetic Z-axis zero setter.

    A square block stands on the work; a cylinder out of the middle of
    its top, chamfered at its upper edge, is what the tool pushes on.
    On the block's front (its -Y face), dead center, a ring stands out
    around a recessed dial, and the dial's pointer runs from its
    center straight up.  The 8 rounded edges of the block, the dial's
    graduations and the magnet are not modeled.  All lengths are in
    millimeters, and the model goes up from the center of its base.

    Attributes:
    * `name` (`str`): What it is (e.g. "Z setter 2 in").
    * `height` (`float`): From its base to the cylinder's top: the
      height the pointer reads zero at.
    * `width` (`float`): The block's side (it is square).
    * `cylinder_diameter` (`float`): The cylinder's diameter.
    * `cylinder_rise` (`float`): How far the cylinder stands above
      the block.
    * `chamfer` (`float`): The 45 degree chamfer at its upper edge.
    * `ring_diameter` (`float`): The ring's outer diameter.
    * `ring_width` (`float`): From the ring's outer edge to its inner.
    * `ring_rise` (`float`): How far the ring stands out of the front.
    * `dial_recess` (`float`): How far the dial sits back from the
      ring's front.
    * `pointer_width` (`float`): The pointer's width.
    * `pointer_thickness` (`float`): How far it stands off the dial.
    * `pointer_gap` (`float`): From its end to the ring.

    Constructor:
    * `ZSetter(name, height, width, cylinder_diameter, cylinder_rise,
      chamfer, ring_diameter, ring_width, ring_rise, dial_recess,
      pointer_width, pointer_thickness, pointer_gap)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    height: float = field(init=True)
    width: float = field(init=True)
    cylinder_diameter: float = field(init=True)
    cylinder_rise: float = field(init=True)
    chamfer: float = field(init=True)
    ring_diameter: float = field(init=True)
    ring_width: float = field(init=True)
    ring_rise: float = field(init=True)
    dial_recess: float = field(init=True)
    pointer_width: float = field(init=True)
    pointer_thickness: float = field(init=True)
    pointer_gap: float = field(init=True)

    # Method `ZSetter.__post_init__()`:
    def __post_init__(self) -> None:
        """Check that the sizes fit together.

        Raises:
        * `ValueError`: If a part does not fit on or in another.
        """
        if not 0.0 < self.cylinder_rise < self.height:
            raise ValueError(f"{self.name}: the cylinder rises too far")
        if not 0.0 < self.chamfer < self.cylinder_rise:
            raise ValueError(f"{self.name}: the chamfer is too large")
        if self.cylinder_diameter >= self.width:
            raise ValueError(f"{self.name}: the cylinder is too wide")
        if not self.ring_diameter < min(self.width, self.block_height()):
            raise ValueError(f"{self.name}: the ring does not fit")
        if not 0.0 < self.dial_recess < self.ring_rise:
            raise ValueError(f"{self.name}: the dial is recessed too far")
        if self.pointer_thickness >= self.dial_recess:
            raise ValueError(f"{self.name}: the pointer is too thick")
        if not 0.0 < self.pointer_length():
            raise ValueError(f"{self.name}: the pointer has no length")

    # Method `ZSetter.block_height()`:
    def block_height(self) -> float:
        """Return the block's height, under the cylinder.

        Returns:
        * (`float`): Its height (mm).
        """
        return self.height - self.cylinder_rise

    # Method `ZSetter.dial_radius()`:
    def dial_radius(self) -> float:
        """Return the dial's radius: the ring's inner one.

        Returns:
        * (`float`): The radius (mm).
        """
        return self.ring_diameter / 2.0 - self.ring_width

    # Method `ZSetter.pointer_length()`:
    def pointer_length(self) -> float:
        """Return the pointer's length, from the dial's center.

        Returns:
        * (`float`): Its length (mm).
        """
        return self.dial_radius() - self.pointer_gap

    # Method `ZSetter.model()`:
    def model(
        self, solidcraft: PyBind, center: Point = (0.0, 0.0, 0.0)
    ) -> list[str]:
        """Model the setter, up from the center of its base.

        Arguments:
        * `solidcraft` (`PyBind`): The SolidCraft session.
        * `center` (`Point`): The center of its base (mm).

        Returns:
        * (`list[str]`): Its bodies: block, cylinder, ring, dial and
          pointer (SolidCraft may change a name, if it is taken).
        """
        # The block; the cylinder, revolved about the vertical axis
        # from its top; the ring and the dial, about the axis out of
        # its front's center (sketch Y out of the front, -Y); the
        # pointer on the dial's face.
        x, y, z = center
        top: Point = (x, y, z + self.block_height())
        front: Point = (x, y - self.width / 2.0, z + self.block_height() / 2.0)
        up: tuple[Point, Point] = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        out: tuple[Point, Point] = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0))
        face: float = self.ring_rise - self.dial_recess
        return [
            self._block(solidcraft, center),
            self._revolved(
                solidcraft, "cylinder", top, up, self.cylinder_profile()
            ),
            self._revolved(
                solidcraft, "ring", front, out, self.ring_profile()
            ),
            self._revolved(
                solidcraft, "dial", front, out, self.dial_profile()
            ),
            self._pointer(solidcraft, (front[0], front[1] - face, front[2])),
        ]

    # Method `ZSetter.cylinder_profile()`:
    def cylinder_profile(self) -> list[tuple[float, float]]:
        """Return the cylinder's profile, its upper edge chamfered.

        Returns:
        * (`list[tuple[float, float]]`): (radius, up from the block's
          top) points (mm).
        """
        radius: float = self.cylinder_diameter / 2.0
        rise: float = self.cylinder_rise
        return [
            (0.0, 0.0),
            (radius, 0.0),
            (radius, rise - self.chamfer),
            (radius - self.chamfer, rise),
            (0.0, rise),
        ]

    # Method `ZSetter.ring_profile()`:
    def ring_profile(self) -> list[tuple[float, float]]:
        """Return the ring's profile.

        Returns:
        * (`list[tuple[float, float]]`): (radius, out of the front)
          points (mm).
        """
        outer: float = self.ring_diameter / 2.0
        inner: float = self.dial_radius()
        return [
            (inner, 0.0),
            (outer, 0.0),
            (outer, self.ring_rise),
            (inner, self.ring_rise),
        ]

    # Method `ZSetter.dial_profile()`:
    def dial_profile(self) -> list[tuple[float, float]]:
        """Return the dial's profile: a disk inside the ring, recessed.

        Returns:
        * (`list[tuple[float, float]]`): (radius, out of the front)
          points (mm).
        """
        inner: float = self.dial_radius()
        face: float = self.ring_rise - self.dial_recess
        return [(0.0, 0.0), (inner, 0.0), (inner, face), (0.0, face)]

    # Method `ZSetter._block()`:
    def _block(self, solidcraft: PyBind, center: Point) -> str:
        """Model the block, up from the center of its base.

        Arguments:
        * `solidcraft` (`PyBind`): The SolidCraft session.
        * `center` (`Point`): The center of its base (mm).

        Returns:
        * (`str`): The body's name.
        """
        x, y, z = center
        half: float = self.width / 2.0
        solidcraft.sketch.create(
            plane="XY", offset=z, name=f"{self.name} block"
        )
        solidcraft.sketch.rectangle_center(
            center=(x, y), corner=(x + half, y + half)
        )
        solidcraft.sketch.finish()
        block: str = created(
            solidcraft.solid.extrude(
                distance=self.block_height(), body_name=f"{self.name} block"
            )
        )
        solidcraft.appearance.assign(bodies=[block], color=BLOCK_COLOR)
        return block

    # Method `ZSetter._pointer()`:
    def _pointer(self, solidcraft: PyBind, center: Point) -> str:
        """Model the pointer: a prism from the dial's center, straight up.

        Arguments:
        * `solidcraft` (`PyBind`): The SolidCraft session.
        * `center` (`Point`): The dial face's center (mm).

        Returns:
        * (`str`): The body's name.
        """
        # The sketch on the dial's face, facing out of the front.
        across: float = self.pointer_width / 2.0
        solidcraft.sketch.create(
            plane={
                "origin": list(center),
                "x_dir": [1.0, 0.0, 0.0],
                "y_dir": [0.0, 0.0, 1.0],
            },
            name=f"{self.name} pointer",
        )
        solidcraft.sketch.line(
            points=[
                [-across, 0.0],
                [across, 0.0],
                [across, self.pointer_length()],
                [-across, self.pointer_length()],
            ],
            closed=True,
        )
        solidcraft.sketch.finish()
        pointer: str = created(
            solidcraft.solid.extrude(
                distance=self.pointer_thickness,
                body_name=f"{self.name} pointer",
            )
        )
        solidcraft.appearance.assign(bodies=[pointer], color=POINTER_COLOR)
        return pointer

    # Method `ZSetter._revolved()`:
    def _revolved(
        self,
        solidcraft: PyBind,
        part: str,
        origin: Point,
        axes: tuple[Point, Point],
        profile: list[tuple[float, float]],
    ) -> str:
        """Revolve a profile into one of the setter's round parts.

        Arguments:
        * `solidcraft` (`PyBind`): The SolidCraft session.
        * `part` (`str`): Which part (`"cylinder"`, `"ring"`, `"dial"`).
        * `origin` (`Point`): A point on the axis (mm).
        * `axes` (`tuple[Point, Point]`): The sketch's X (the radius)
          and Y (along the axis) directions.
        * `profile` (`list[tuple[float, float]]`): The profile, as
          (radius, along the axis) points (mm).

        Returns:
        * (`str`): The body's name.
        """
        # Sketch the profile, then revolve it about the sketch's Y.
        name: str = f"{self.name} {part}"
        solidcraft.sketch.create(
            plane={
                "origin": list(origin),
                "x_dir": list(axes[0]),
                "y_dir": list(axes[1]),
            },
            name=name,
        )
        drawn: JSON = solidcraft.sketch.line(
            points=[[r, a] for r, a in profile], closed=True
        )
        assert isinstance(drawn, dict)
        solidcraft.sketch.finish()
        body: str = created(
            solidcraft.solid.revolve(
                axis={"origin": list(origin), "dir": list(axes[1])},
                profiles=[{"curves": drawn["curves"]}],
                body_name=name,
            )
        )
        color: str = DIAL_COLOR if part == "dial" else SILVER_COLOR
        solidcraft.appearance.assign(bodies=[body], color=color)
        return body


# Function `created()`:
def created(made: JSON) -> str:
    """Return the body that a SolidCraft command made.

    Arguments:
    * `made` (`JSON`): The command's answer.

    Returns:
    * (`str`): The first body it created.
    """
    assert isinstance(made, dict)
    bodies: JSON = made["created_bodies"]
    assert isinstance(bodies, list) and isinstance(bodies[0], str)
    return bodies[0]


# Function `z_setter()`:
def z_setter(imperial: bool) -> ZSetter:
    """Return the Shars magnetic Z-axis zero setter (303-3104).

    The catalog gives the height and the block's side; the rest is the
    user's description of the imperial one (2026-11-15), and the
    metric one's are the same, scaled by its block's side.

    Arguments:
    * `imperial` (`bool`): True for the 2 in one (303-3104), False for
      the 50 mm one (303-3104M).

    Returns:
    * (`ZSetter`): The setter.
    """
    # The imperial one's sizes, in inches, but its name and height.
    sizes: tuple[float, ...] = (
        2.05,  # The block's side.
        1.0,  # The cylinder's diameter.
        0.25,  # Its rise above the block (a guess).
        0.1,  # Its chamfer.
        1.5,  # The ring's outer diameter.
        0.1,  # Its width (a guess).
        0.25,  # How far it stands out.
        0.1,  # The dial's recess.
        0.04,  # The pointer's width (a guess).
        0.02,  # Its thickness (a guess).
        0.05,  # Its gap to the ring (a guess).
    )
    scale: float = MM_PER_INCH if imperial else 52.0 / sizes[0]
    mm: list[float] = [size * scale for size in sizes]
    return ZSetter(
        "Z setter 2 in" if imperial else "Z setter 50 mm",
        2.0 * MM_PER_INCH if imperial else 50.0,
        *mm,
    )


# Function `main()`:
def main() -> None:
    """Show a Z setter in a new design."""
    target: str = sys.argv[1] if len(sys.argv) > 1 else "8081"
    with connect(target) as transport:
        solidcraft: PyBind = PyBind(transport)
        solidcraft.file.new()
        setter: ZSetter = z_setter(sys.argv[2:] != ["metric"])
        print(setter.model(solidcraft))
        solidcraft.view.apply(view="iso")


if __name__ == "__main__":
    main()
