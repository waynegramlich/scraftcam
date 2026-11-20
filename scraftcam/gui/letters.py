"""The outline editor's letters (`T.prg~5.1.9.2` #27): no Qt here.

Each letter names a size of the outline (`W`, `T1`, `OAL`): one to
three letters or digits, a letter first, with a long name, a default value
with its unit (`6 in`, `3-7/8 in`, `20 mm`, or an angle, `59 deg`),
and one line of help.  The letters become SolidCraft parameters, so a
letter may not be a name SolidCraft keeps for itself (a unit, a
constant), and two letters may not differ only in case (`W`, `w`),
to spare the reader.
"""

import re
from dataclasses import dataclass, field

from ..model import MM_PER, Angle, Length

# One to three letters or digits, a letter first (`OAL`).
LETTER_PATTERN: re.Pattern[str] = re.compile(r"[A-Za-z][A-Za-z0-9]{0,2}")

# Names SolidCraft keeps for itself (`T.cmt~5.3` #17: unit names,
# constants and functions are refused), compared without case.  The
# constants are `pi` and `e` only (the user, #50).
RESERVED: frozenset[str] = frozenset(
    {"in", "ft", "mm", "m", "cm", "um", "deg", "rad", "pi", "e"}
    | {"sin", "cos", "tan", "abs", "min", "max", "log", "exp", "ln"}
)

# The angle units, for telling an angle from a length.
ANGLE_UNITS: tuple[str, ...] = ("deg", "rad")

# An angle dimension's value must be inside these, in degrees (#58).
ANGLE_LIMITS: tuple[float, float] = (0.1, 179.9)


# Class `Letter`:
@dataclass(slots=True)
class Letter:
    """One letter of an outline, and what it means.

    Attributes:
    * `letter` (`str`): The letter, as on the diagram (`W`, `T1`).
    * `name` (`str`): Its long name ("Overall width").
    * `default` (`str`): Its default value, with a unit (`6 in`).
    * `help` (`str`): One line of help, for tooltips and documents.
    * `fillet` (`bool`): Listed in the [Fillets] tab as a fillet
      radius (#213; only a length letter).

    Constructor:
    * `Letter(letter, name, default, help, fillet)`
    """

    # Constructor arguments:
    letter: str = field(init=True)
    name: str = field(init=True, default="")
    default: str = field(init=True, default="1 in")
    help: str = field(init=True, default="")
    fillet: bool = field(init=True, default=False)


# Function `value_problem()`:
def value_problem(text: str) -> str:
    """Return what is wrong with a default value ("" if nothing).

    Arguments:
    * `text` (`str`): A length (`3-7/8 in`) or an angle (`59 deg`).

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    words: list[str] = text.split()
    try:
        if words and words[-1] in ANGLE_UNITS:
            Angle.parse(text)
        else:
            Length.parse(text)
    except ValueError:
        return (
            f"{text!r} is not a value with a unit "
            f"(e.g. 6 in, 3-7/8 in, 20 mm, 59 deg; units: "
            f"{', '.join([*MM_PER, *ANGLE_UNITS])})."
        )
    return ""


# Function `use_problem()`:
def use_problem(letter: str, text: str, kinds: set[str]) -> str:
    """Return what is wrong with a default value for the dimensions
    that use its letter ("" if nothing, or if the value itself is bad,
    which `value_problem()` reports).

    Arguments:
    * `letter` (`str`): The letter.
    * `text` (`str`): Its default value.
    * `kinds` (`set[str]`): What its dimensions measure: `"length"`
      (horizontal, vertical and slanted ones) and `"angle"`.

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    if value_problem(text):
        return ""
    if {"length", "angle"} <= kinds:
        return f"{letter} is used for both a length and an angle."
    words: list[str] = text.split()
    angle: bool = words[-1] in ANGLE_UNITS
    if "length" in kinds and angle:
        return f"{letter} measures a length: {text} is an angle."
    if "angle" in kinds and not angle:
        return f"{letter} measures an angle: {text} is a length."
    if not kinds:
        return ""
    return _range_problem(letter, text, angle)


# Function `fillet_kind_problem()`:
def fillet_kind_problem(letter: Letter, kinds: set[str]) -> str:
    """Return what is wrong with a letter checked "Fillet" ("" if
    nothing): a fillet radius is a length (#213).

    Arguments:
    * `letter` (`Letter`): The letter.
    * `kinds` (`set[str]`): What its dimensions measure (see
      `use_problem()`).

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    words: list[str] = letter.default.split()
    angle: bool = bool(words) and words[-1] in ANGLE_UNITS
    if letter.fillet and (angle or "angle" in kinds):
        return f"{letter.letter} is an angle: a fillet radius is a length."
    return ""


# Function `_range_problem()`:
def _range_problem(letter: str, text: str, angle: bool) -> str:
    """Return what is wrong with a good value for its use ("" if
    nothing): an angle near 0 or 180 degrees, whose edges are parallel
    (#58), or a length not more than 0, as a dimension measures a
    distance (#154).

    Arguments:
    * `letter` (`str`): The letter.
    * `text` (`str`): Its value, of the kind its use needs.
    * `angle` (`bool`): Whether it is an angle.

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    if angle:
        degrees: float = float(Angle.parse(text).degrees)
        if not ANGLE_LIMITS[0] < degrees < ANGLE_LIMITS[1]:
            return (
                f"{letter}: angles must be between {ANGLE_LIMITS[0]} and "
                f"{ANGLE_LIMITS[1]} deg, not {text}."
            )
    elif Length.parse(text).value <= 0:
        return f"{letter} must be more than 0, not {text}."
    return ""


# Function `letter_problem()`:
def letter_problem(letters: list[Letter], index: int) -> str:
    """Return what is wrong with one letter's name ("" if nothing).

    Arguments:
    * `letters` (`list[Letter]`): All of the outline's letters.
    * `index` (`int`): The one to check.

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    letter: str = letters[index].letter
    if not LETTER_PATTERN.fullmatch(letter):
        return (
            f"{letter!r} is not one to three letters or digits, "
            "a letter first."
        )
    if letter.lower() in RESERVED:
        return (
            f"{letter!r} is kept by SolidCraft (a unit, a constant or a "
            "function)."
        )
    other: Letter
    for other in letters[:index]:
        if other.letter == letter:
            return f"{letter!r} is used twice."
        if other.letter.lower() == letter.lower():
            return f"{letter!r} and {other.letter!r} differ only in case."
    return ""


# Function `next_letter()`:
def next_letter(letters: list[Letter]) -> Letter:
    """Return a new letter, the first of `A` to `Z` not in use.

    Its default takes the unit of the last length default, so that a
    drawing in millimeters stays in millimeters.

    Arguments:
    * `letters` (`list[Letter]`): The outline's letters.

    Returns:
    * (`Letter`): The new letter (`A1` and on, once `A` to `Z` are
      taken).
    """
    used: set[str] = {letter.letter.lower() for letter in letters}
    candidates: list[str] = [chr(code) for code in range(65, 91)]
    candidates += [
        f"{first}{digit}" for first in candidates for digit in "123456789"
    ]
    candidate: str = next(
        name
        for name in candidates
        if name.lower() not in used and name.lower() not in RESERVED
    )
    unit: str = "in"
    letter: Letter
    for letter in reversed(letters):
        words: list[str] = letter.default.split()
        if words and words[-1] in MM_PER and not value_problem(letter.default):
            unit = words[-1]
            break
    return Letter(candidate, default=f"1 {unit}")
