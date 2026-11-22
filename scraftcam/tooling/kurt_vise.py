"""The Kurt DX6 vise as a `SolidAssembly` (`T.rps~6.6`).

Its overall sizes are the catalog's (Shars 202-1007,
`SharsMD/page_311/page_311.md:21`): jaw width 6 in, opening 9.08 in,
length 16.86 in, width 7.39 in, bed height 2.875 in.  The jaw blocks'
lengths are guesses (marked below), until the user measures one.

The screw runs along X; the fixed jaw is at the -X end and the
movable jaw opens toward +X.  The vise is symmetric about `y = 0`,
so each outline is drawn as its right half about the Y axis, as
the editor draws one (`RoundedPolygon.mirrored()`), then turned.
Its three parts are its three keep-out zones (#368): the base, bolted
to the table; the fixed jaw with its plate; and the movable jaw with
its plate, placed by the gap between the plates (#359a).
"""

from fractions import Fraction

from ..geometry import Corner
from ..model import Angle, Length, Placement, Rotation
from ..solid import (
    Layer,
    Placed,
    RoundedPolygon,
    SolidAssembly,
    SolidRoundedPolygon,
)
from .jaw_plate import JawPlate

# The catalog's sizes (inches).
JAW_WIDTH: Length = Length(6, "in")
OPENING: Length = Length(Fraction("9.08"), "in")
LENGTH: Length = Length(Fraction("16.86"), "in")
WIDTH: Length = Length(Fraction("7.39"), "in")
BED_HEIGHT: Length = Length(Fraction("2.875"), "in")

# Guesses, to be measured: each jaw block's size along X.
FIXED_JAW_LENGTH: Length = Length(2, "in")
MOVABLE_JAW_LENGTH: Length = Length(Fraction("2.5"), "in")

# A zero length.
ZERO: Length = Length(0, "in")

# Turns a jaw plate drawn face up (width X, height Y, thickness Z)
# upright on a jaw: X to Y, Y to Z, Z to X, so its face looks to +X.
UPRIGHT: Rotation = Rotation.about((1, 1, 1), Angle(Fraction(120)))

# The same, then half a turn about Z, so its face looks to -X.
UPRIGHT_BACK: Rotation = (
    Rotation.about((0, 0, 1), Angle(Fraction(180))) * UPRIGHT
)


# Function `box()`:
def box(length: Length, width: Length, name: str = "") -> RoundedPolygon:
    """Return a rectangle from `x` 0 to `length`, centered on `y` 0.

    It is drawn as the editor would: its right half about the Y axis,
    `length` up Y (#373), then turned a quarter turn clockwise so that
    `length` runs along X, as the vise's screw does.

    Arguments:
    * `length` (`Length`): Its size along X.
    * `width` (`Length`): Its size along Y.
    * `name` (`str`): Its name ("" to be named by its solid).

    Returns:
    * (`RoundedPolygon`): The rectangle.
    """
    x: float = width.mm() / 2.0
    y: float = length.mm()
    return RoundedPolygon.mirrored(
        (Corner(0.0, 0.0), Corner(x, 0.0), Corner(x, y), Corner(0.0, y)),
        name,
        "in",
    ).rotate((0.0, 0.0), Angle(Fraction(-90)))


# Function `block()`:
def block(
    name: str, length: Length, width: Length, height: Length
) -> SolidRoundedPolygon:
    """Return a block from the origin, along X, centered on `y` 0.

    Arguments:
    * `name` (`str`): Its name.
    * `length` (`Length`): Its size along X.
    * `width` (`Length`): Its size along Y.
    * `height` (`Length`): Its size along Z.

    Returns:
    * (`SolidRoundedPolygon`): The block.
    """
    return SolidRoundedPolygon(
        name, Layer(box(length, width), ZERO, ZERO, height)
    )


# Function `jaw_plate_solid()`:
def jaw_plate_solid(
    plate: JawPlate, name: str = "jaw_plate"
) -> SolidRoundedPolygon:
    """Return a jaw plate drawn face up, from its clamping face.

    The face is X (width) by Y (height), from the origin; it is
    extruded by the thickness, and each counterbore is cut from the
    face (the top) with its clearance hole on through.

    Arguments:
    * `plate` (`JawPlate`): The plate's sizes.
    * `name` (`str`): Its name.

    Returns:
    * (`SolidRoundedPolygon`): The plate.
    """
    face: RoundedPolygon = RoundedPolygon(
        (
            Corner(0.0, 0.0),
            Corner(plate.width.mm(), 0.0),
            Corner(plate.width.mm(), plate.height.mm()),
            Corner(0.0, plate.height.mm()),
        ),
        unit="in",
    )
    floor: Length = Length.from_mm(
        plate.length.mm() - plate.counterbore_depth.mm(), "in"
    )
    hole: Layer = Layer(
        RoundedPolygon.circle(plate.hole_diameter), ZERO, ZERO, ZERO
    )
    middle: float = plate.width.mm() / 2.0
    half: float = plate.hole_spacing.mm() / 2.0
    counterbores: list[Layer] = [
        Layer(
            RoundedPolygon.circle(plate.counterbore_diameter),
            Length.from_mm(x, "in"),
            plate.hole_height,
            floor,
            (hole,),
        )
        for x in (middle - half, middle + half)
    ]
    return SolidRoundedPolygon(
        name, Layer(face, ZERO, ZERO, plate.length, counterbores)
    )


# Function `kurt_dx6()`:
def kurt_dx6(gap: Length, name: str = "kurt_dx6") -> SolidAssembly:
    """Return the vise, its jaw plates `gap` apart.

    Arguments:
    * `gap` (`Length`): The distance between the jaw plates' faces.
    * `name` (`str`): The assembly's name.

    Returns:
    * (`SolidAssembly`): The vise: base, fixed jaw, movable jaw.

    Raises:
    * `ValueError`: If `gap` is negative or more than the opening.
    """
    if not ZERO.mm() <= gap.mm() <= OPENING.mm():
        raise ValueError(f"{name}: a gap of {gap} is not 0 to {OPENING}")
    plate: JawPlate = JawPlate()
    plate_solid: SolidRoundedPolygon = jaw_plate_solid(plate)
    jaw_height: Length = plate.height
    half_plate: float = plate.width.mm() / 2.0
    thickness: float = plate.length.mm()

    # The fixed jaw: its block from x 0, its plate on its +X face.
    fixed: SolidAssembly = SolidAssembly(
        "fixed_jaw",
        (
            Placed(
                block("fixed_jaw_block", FIXED_JAW_LENGTH, WIDTH, jaw_height)
            ),
            Placed(
                plate_solid,
                Placement(
                    (
                        FIXED_JAW_LENGTH,
                        Length.from_mm(-half_plate, "in"),
                        ZERO,
                    ),
                    UPRIGHT,
                ),
            ),
        ),
    )

    # The movable jaw, drawn from its plate's face at x 0: the plate
    # facing -X, its block behind it.
    movable: SolidAssembly = SolidAssembly(
        "movable_jaw",
        (
            Placed(
                plate_solid,
                Placement(
                    (
                        Length.from_mm(thickness, "in"),
                        Length.from_mm(half_plate, "in"),
                        ZERO,
                    ),
                    UPRIGHT_BACK,
                ),
            ),
            Placed(
                block(
                    "movable_jaw_block", MOVABLE_JAW_LENGTH, WIDTH, jaw_height
                ),
                Placement((Length.from_mm(thickness, "in"), ZERO, ZERO)),
            ),
        ),
    )
    face: float = FIXED_JAW_LENGTH.mm() + thickness + gap.mm()
    return SolidAssembly(
        name,
        (
            Placed(block("vise_base", LENGTH, WIDTH, BED_HEIGHT)),
            Placed(fixed, Placement((ZERO, ZERO, BED_HEIGHT))),
            Placed(
                movable,
                Placement((Length.from_mm(face, "in"), ZERO, BED_HEIGHT)),
            ),
        ),
    )
