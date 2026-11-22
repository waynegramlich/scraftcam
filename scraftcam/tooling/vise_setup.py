"""A vise setup as a `SolidAssembly` (`T.rps~6.6` #377).

The Kurt DX6 (`kurt_vise.py`) with two parallels standing on its bed,
one against each jaw plate, flat against it (#370, #380); a tooling
plate will lie on top of both (left out until its grid of holes is
settled, #379).  The parallel against the movable
jaw moves with it, so the gap places both.

Each parallel is `Parallel`'s own solid (lying on its side), stood
up by the same turn as the jaw plates.
"""

from ..model import Length, Placement
from ..solid import (
    Placed,
    SolidAssembly,
    SolidRoundedPolygon,
)
from .jaw_plate import JawPlate
from .kurt_vise import (
    BED_HEIGHT,
    FIXED_JAW_LENGTH,
    UPRIGHT,
    kurt_dx6,
)
from .parallel import Parallel


# Function `vise_setup()`:
def vise_setup(gap: Length, name: str = "vise_setup") -> SolidAssembly:
    """Return the vise with two parallels.

    Arguments:
    * `gap` (`Length`): The distance between the jaw plates' faces.
    * `name` (`str`): The assembly's name.

    Returns:
    * (`SolidAssembly`): The vise and the two parallels.

    Raises:
    * `ValueError`: If `gap` does not fit the vise, or leaves no room
      for the two parallels.
    """
    parallel: Parallel = Parallel()
    thickness: float = parallel.thickness.mm()
    if gap.mm() <= 2.0 * thickness:
        raise ValueError(
            f"{name}: a gap of {gap} leaves no room for two parallels"
        )
    vise: SolidAssembly = kurt_dx6(gap)
    side: SolidRoundedPolygon = parallel.solid
    fixed_face: float = FIXED_JAW_LENGTH.mm() + JawPlate().length.mm()
    movable_face: float = fixed_face + gap.mm()
    across: Length = Length.from_mm(-parallel.length.mm() / 2.0, "in")
    return SolidAssembly(
        name,
        (
            Placed(vise),
            Placed(
                side,
                Placement(
                    (Length.from_mm(fixed_face, "in"), across, BED_HEIGHT),
                    UPRIGHT,
                ),
            ),
            Placed(
                side,
                Placement(
                    (
                        Length.from_mm(movable_face - thickness, "in"),
                        across,
                        BED_HEIGHT,
                    ),
                    UPRIGHT,
                ),
            ),
        ),
    )
