"""Colours and hatches: how a material or polygon looks.

A colour is written as percentages, `R13% G32% B78% T0%` (the spaces
are optional; `T`, the transparency, is optional and 0% is opaque),
and a hatch as an angle, a spacing and a thickness, `A45 S2mm
T0.25mm` (degrees; the spacing and thickness are on the page, with
units), a crosshatch joining two with `+` (`T.sa~6.11` #803, #804).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A hatch's lengths are on the page: these are its units, in inches.
PAGE_LENGTH: dict[str, float] = {"mm": 1.0 / 25.4, "in": 1.0, "pt": 1.0 / 72}

# A length on the page: a number and one of `PAGE_LENGTH`.
LENGTH_TEXT: re.Pattern[str] = re.compile(
    r"\s*(\d+(?:\.\d*)?|\.\d+)\s*([a-z]+)\s*", re.IGNORECASE
)

# A colour's text: red, green, blue and an optional transparency.
COLOR: re.Pattern[str] = re.compile(
    r"\s*[Rr]\s*(\d+(?:\.\d*)?)\s*%\s*[Gg]\s*(\d+(?:\.\d*)?)\s*%"
    r"\s*[Bb]\s*(\d+(?:\.\d*)?)\s*%\s*(?:[Tt]\s*(\d+(?:\.\d*)?)\s*%)?\s*"
)

# One set of hatch lines: an angle, a spacing and a thickness.
HATCH: re.Pattern[str] = re.compile(
    r"\s*[Aa]\s*([-+]?\d+(?:\.\d*)?)"
    r"\s*[Ss]\s*(\d*\.?\d+\s*[A-Za-z]+)\s*[Tt]\s*(\d*\.?\d+\s*[A-Za-z]+)\s*"
)


# Function `page_length()`:
def page_length(text: str) -> float:
    """Return a length on the page, in inches.

    Arguments:
    * `text` (`str`): Such as `"2mm"`, `"0.01 in"` or `"0.5pt"`.

    Returns:
    * (`float`): Its length in inches.

    Raises:
    * `ValueError`: When it is not a number and a unit.
    """
    found: re.Match[str] | None = LENGTH_TEXT.fullmatch(text)
    if found is None or found.group(2).lower() not in PAGE_LENGTH:
        units: str = ", ".join(PAGE_LENGTH)
        raise ValueError(f"{text!r} is not a length in {units}")
    return float(found.group(1)) * PAGE_LENGTH[found.group(2).lower()]


# Function `color_problem()`:
def color_problem(value: object) -> str:
    """Return what is wrong with a colour from a file, if anything.

    Arguments:
    * `value` (`object`): The value, from TOML.

    Returns:
    * (`str`): The problem, or `""` if there is none.
    """
    if not isinstance(value, str):
        return f"{value!r} is not a colour such as 'R13% G32% B78%'"
    try:
        Color.parse(value)
    except ValueError as error:
        return str(error)
    return ""


# Function `hatch_problem()`:
def hatch_problem(value: object) -> str:
    """Return what is wrong with a hatch from a file, if anything.

    Arguments:
    * `value` (`object`): The value, from TOML.

    Returns:
    * (`str`): The problem, or `""` if there is none.
    """
    if not isinstance(value, str):
        return f"{value!r} is not a hatch such as 'A45 S2mm T0.25mm'"
    try:
        Hatch.parse(value)
    except ValueError as error:
        return str(error)
    return ""


# Class `Color`:
@dataclass(slots=True, frozen=True)
class Color:
    """A colour, each part a percentage from 0 to 100.

    Attributes:
    * `red` (`float`): Its red.
    * `green` (`float`): Its green.
    * `blue` (`float`): Its blue.
    * `transparency` (`float`): How see-through it is (0 is opaque).

    Constructor:
    * `Color(red, green, blue, transparency)`
    """

    # Constructor arguments:
    red: float = field(init=True)
    green: float = field(init=True)
    blue: float = field(init=True)
    transparency: float = field(init=True, default=0.0)

    def __post_init__(self) -> None:
        """Refuse a part outside 0% to 100%.

        Raises:
        * `ValueError`: When a part is out of range.
        """
        part: float
        for part in (self.red, self.green, self.blue, self.transparency):
            if not 0.0 <= part <= 100.0:
                raise ValueError(f"{part:g}% is not from 0% to 100%")

    @staticmethod
    def parse(text: str) -> Color:
        """Return the colour a text names.

        Arguments:
        * `text` (`str`): Such as `"R13% G32% B78% T0%"`.

        Returns:
        * (`Color`): Its colour.

        Raises:
        * `ValueError`: When it is not a colour, saying why.
        """
        found: re.Match[str] | None = COLOR.fullmatch(text)
        if found is None:
            raise ValueError(
                f"{text!r} is not a colour such as 'R13% G32% B78% T0%'"
            )
        red, green, blue, transparency = found.groups()
        return Color(
            float(red),
            float(green),
            float(blue),
            float(transparency or "0"),
        )

    @staticmethod
    def from_rgba(red: int, green: int, blue: int, alpha: int) -> Color:
        """Return the colour of 0 to 255 parts (as Qt's).

        Arguments:
        * `red` (`int`): Its red, 0 to 255.
        * `green` (`int`): Its green, 0 to 255.
        * `blue` (`int`): Its blue, 0 to 255.
        * `alpha` (`int`): Its opacity, 0 to 255 (255 is opaque).

        Returns:
        * (`Color`): The colour, each part rounded to a whole percent.
        """

        # Function `percent()`:
        def percent(part: int) -> float:
            """Return a 0 to 255 part as a whole percentage."""
            return float(round(part * 100 / 255))

        return Color(
            percent(red), percent(green), percent(blue), percent(255 - alpha)
        )

    def rgba(self) -> tuple[int, int, int, int]:
        """Return its parts from 0 to 255, opacity last (as Qt's).

        Returns:
        * (`tuple[int, int, int, int]`): Red, green, blue, alpha.
        """

        # Function `byte()`:
        def byte(percent: float) -> int:
            """Return a percentage as 0 to 255."""
            return round(percent * 255 / 100)

        return (
            byte(self.red),
            byte(self.green),
            byte(self.blue),
            byte(100.0 - self.transparency),
        )

    def text(self) -> str:
        """Return it as written in a file.

        Returns:
        * (`str`): Such as `"R13% G32% B78%"` (`T` only when not 0).
        """
        written: str = f"R{self.red:g}% G{self.green:g}% B{self.blue:g}%"
        if self.transparency:
            written += f" T{self.transparency:g}%"
        return written


# Class `HatchLines`:
@dataclass(slots=True, frozen=True)
class HatchLines:
    """One set of parallel hatch lines.

    Attributes:
    * `angle` (`float`): Their angle, in degrees from the X axis.
    * `spacing` (`float`): Their spacing on the page, in inches.
    * `thickness` (`float`): Their thickness on the page, in inches.

    Constructor:
    * `HatchLines(angle, spacing, thickness)`
    """

    # Constructor arguments:
    angle: float = field(init=True)
    spacing: float = field(init=True)
    thickness: float = field(init=True)

    def __post_init__(self) -> None:
        """Refuse a spacing or thickness that is not positive.

        Raises:
        * `ValueError`: When one is not positive.
        """
        if self.spacing <= 0.0 or self.thickness <= 0.0:
            raise ValueError("a hatch's spacing and thickness must be > 0")


# Class `Hatch`:
@dataclass(slots=True, frozen=True)
class Hatch:
    """A hatch: one or more sets of lines (two make a crosshatch).

    Attributes:
    * `lines` (`tuple[HatchLines, ...]`): Its sets of lines.
    * `written` (`str`): Its text, as written in the file.

    Constructor:
    * `Hatch(lines, written)`
    """

    # Constructor arguments:
    lines: tuple[HatchLines, ...] = field(init=True)
    written: str = field(init=True)

    @staticmethod
    def parse(text: str) -> Hatch:
        """Return the hatch a text names.

        Arguments:
        * `text` (`str`): Such as `"A45 S2mm T0.25mm"`, or two such
          joined with `+`.

        Returns:
        * (`Hatch`): Its hatch.

        Raises:
        * `ValueError`: When it is not a hatch, saying why.
        """
        lines: list[HatchLines] = []
        part: str
        for part in text.split("+"):
            found: re.Match[str] | None = HATCH.fullmatch(part)
            if found is None:
                raise ValueError(
                    f"{part.strip()!r} is not a hatch such as "
                    "'A45 S2mm T0.25mm'"
                )
            angle, spacing, thickness = found.groups()
            lines.append(
                HatchLines(
                    float(angle),
                    page_length(spacing),
                    page_length(thickness),
                )
            )
        written: str = " + ".join(part.strip() for part in text.split("+"))
        return Hatch(tuple(lines), written)


# The hatches given, in order, to materials that name none (#781).
STANDARD_HATCHES: tuple[Hatch, ...] = tuple(
    Hatch.parse(written)
    for written in (
        "A45 S2mm T0.25mm",
        "A135 S2mm T0.25mm",
        "A45 S2mm T0.25mm + A135 S2mm T0.25mm",
        "A0 S2mm T0.25mm",
        "A90 S2mm T0.25mm",
        "A45 S1mm T0.18mm",
        "A135 S1mm T0.18mm",
        "A0 S2mm T0.25mm + A90 S2mm T0.25mm",
    )
)


# Class `Look`:
@dataclass(slots=True, frozen=True)
class Look:
    """How one polygon is drawn: its fill colour and its hatch.

    Attributes:
    * `color` (`Color | None`): Its fill (`None`: not filled).
    * `hatch` (`Hatch | None`): Its hatch (`None`: no material, so
      not hatched).

    Constructor:
    * `Look(color, hatch)`
    """

    # Constructor arguments:
    color: Color | None = field(init=True)
    hatch: Hatch | None = field(init=True)


# Function `looks()`:
def looks(
    polygons: list[tuple[str, str]],
    materials: dict[str, tuple[str, str]],
) -> list[Look]:
    """Return how each polygon of a drawing is drawn (#781, #805).

    A polygon's own colour wins over its material's.  A polygon with
    a material is hatched by the material's hatch, or else by the
    first standard hatch that no other material of the drawing has,
    so no two materials share one; one with no material is not.

    Arguments:
    * `polygons` (`list[tuple[str, str]]`): Each polygon's material
      ("" for none) and own colour text ("" for none).
    * `materials` (`dict[str, tuple[str, str]]`): Each known
      material's colour and hatch texts ("" for none), by its name in
      lower case (a polygon's material is matched in any capitals).

    Returns:
    * (`list[Look]`): Each polygon's look, in order.

    Raises:
    * `ValueError`: When a colour or hatch text is bad.
    """
    # Materials in any capitals (as the shop matches them).
    polygons = [(material.lower(), own) for material, own in polygons]

    # Each material's hatch: its own, then the standard ones unused.
    taken: set[tuple[HatchLines, ...]] = {
        Hatch.parse(hatch).lines
        for material, _ in polygons
        if material in materials
        for hatch in (materials[material][1],)
        if hatch
    }
    spare: list[Hatch] = [
        hatch for hatch in STANDARD_HATCHES if hatch.lines not in taken
    ]
    hatches: dict[str, Hatch] = {}
    material: str
    own: str
    for material, _ in polygons:
        if material and material not in hatches:
            own = materials.get(material, ("", ""))[1]
            hatches[material] = (
                Hatch.parse(own)
                if own
                else spare.pop(0)
                if spare
                else STANDARD_HATCHES[0]
            )

    # Each polygon's colour: its own, else its material's.
    found: list[Look] = []
    for material, own in polygons:
        text: str = own or materials.get(material, ("", ""))[0]
        found.append(
            Look(
                Color.parse(text) if text else None,
                hatches.get(material),
            )
        )
    return found
