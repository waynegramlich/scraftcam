"""Socket head cap screws and the holes they need (`T.sfoe~6.4` #328).

A catalog often gives only a screw's size (Shars's vise jaws, page
116: "E, screw size"), so the clearance hole and the counterbore for
its head come from here.  The numbers are the usual normal fit ones
for inch socket head cap screws (ASME B18.3 heads): a clearance drill
a little over the screw, a counterbore a little over the head, and a
counterbore depth equal to the head's height, so the head sits flush.
A part that wants its heads below the face adds its own margin.
Metric sizes come later.
"""

from dataclasses import dataclass, field
from fractions import Fraction

from .model import Length


# Class `Screw`:
@dataclass(frozen=True, slots=True)
class Screw:
    """One socket head cap screw size and its holes.

    Attributes:
    * `name` (`str`): Its usual name (`#10`, `1/2`).
    * `diameter` (`Length`): Its nominal (major) diameter.
    * `clearance` (`Length`): The clearance hole's diameter.
    * `counterbore` (`Length`): The counterbore's diameter.
    * `depth` (`Length`): The counterbore's depth, the head's height.

    Constructor:
    * `Screw(name, diameter, clearance, counterbore, depth)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    diameter: Length = field(init=True)
    clearance: Length = field(init=True)
    counterbore: Length = field(init=True)
    depth: Length = field(init=True)


# Function `_inch()`:
def _inch(text: str) -> Length:
    """Return a length in inches from a number's text.

    Arguments:
    * `text` (`str`): A number such as `17/32` or `0.112`.

    Returns:
    * (`Length`): The length, in inches.
    """
    return Length(Fraction(text), "in")


# The inch sizes: name, diameter, clearance, counterbore, depth.
SCREWS: tuple[Screw, ...] = tuple(
    Screw(name, _inch(diameter), _inch(clear), _inch(bore), _inch(depth))
    for name, diameter, clear, bore, depth in (
        ("#4", "0.112", "1/8", "7/32", "0.112"),
        ("#5", "0.125", "9/64", "1/4", "0.125"),
        ("#6", "0.138", "5/32", "9/32", "0.138"),
        ("#8", "0.164", "3/16", "5/16", "0.164"),
        ("#10", "0.190", "7/32", "3/8", "0.190"),
        ("1/4", "1/4", "9/32", "7/16", "1/4"),
        ("5/16", "5/16", "11/32", "17/32", "5/16"),
        ("3/8", "3/8", "13/32", "5/8", "3/8"),
        ("7/16", "7/16", "15/32", "23/32", "7/16"),
        ("1/2", "1/2", "17/32", "13/16", "1/2"),
    )
)


# Function `screw()`:
def screw(diameter: Length) -> Screw:
    """Return the screw of a nominal diameter.

    Arguments:
    * `diameter` (`Length`): Its nominal diameter, in any unit
      (`1/2 in`, `0.19 in` for a #10).

    Returns:
    * (`Screw`): The screw.

    Raises:
    * `KeyError`: If no screw in `SCREWS` has that diameter (within
      0.001 mm, so `12.7 mm` finds `1/2`).
    """
    found: Screw
    for found in SCREWS:
        if abs(found.diameter.mm() - diameter.mm()) < 0.001:
            return found
    names: str = ", ".join(each.name for each in SCREWS)
    raise KeyError(f"no socket head cap screw of {diameter} ({names})")
