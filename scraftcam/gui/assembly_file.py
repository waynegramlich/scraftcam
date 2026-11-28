"""Assembly files (`T.sa~6.11` #S6, #783): outlines put together.

An assembly file, `KIND.assembly.toml`, is needed only when parts
move, mix kinds (revolved and flat), repeat, or come from a `.step`
(#783a).  It has its own letters, the ones it exports (#783b), and
its parts, each an outline file with its letters given as formulas
in the assembly's:

```
kind = "assembly"
version = 1

[letters.H]
name = "Height"
default = "2 in"
help = "From the base to the plunger's top."

[[parts]]
name = "block"
outline = "z_setter_block.outline.toml"
letters = { W = "W", BH = "H - PR" }

[[parts]]
name = "plunger"
outline = "z_setter_plunger.outline.toml"
letters = { PR = "PR" }
on = "block"
at = "V5"
face = "body"
```

Parts form a tree of mates, placed in order with no solver (#783c).
A part with `on` stands on that earlier part (#769b): its origin at
the parent's vertex `at` (its real place), lifted to the `z` of the
parent's polygon or circle `face` (absent: 0, its base), its +Z the
parent's (`flip = true`: the parent's -Z), turned `turn` (a formula,
an angle) about it.  An extruded outline's +Z is its extrusion; a
revolved one's is its axis (#783k).  A part with no `on` sits at the
assembly's origin.  `outline` is relative to the assembly file.  No
Qt.
"""

import math
import os
import tomllib
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from ..appearance import Color
from ..model import Angle, Length, Placement, Rotation
from ..model_cache import Cacheable
from ..shops import ASSEMBLY_SUFFIX
from ..solid import Placed, Solid, SolidAssembly
from .letters import Letter
from .outline_file import (
    VERTEX_NAME,
    Outline,
    OutlineError,
    _letter_lines,
    _Reader,
    _string,
    outline_from_text,
)
from .outline_polygon import outline_solid, solid_cacheable
from .values import evaluate, letter_values, real_corners, set_letters

# The assembly file format's version; only it is read.
ASSEMBLY_VERSION: int = 1


# Class `Part`:
# One attribute per key of its table, which has eight.
@dataclass(slots=True)
class Part:  # pylint: disable=too-many-instance-attributes
    """One part of an assembly: an outline, its letters and its mate.

    Attributes:
    * `name` (`str`): Its name, unique in the assembly (#783e).
    * `outline` (`str`): Its outline file, relative to the assembly's.
    * `letters` (`dict[str, str]`): Its letters' formulas in the
      assembly's letters, by its letter; others keep their defaults.
    * `on` (`str`): The part it stands on, "" for the origin.
    * `at` (`str`): The vertex of `on`'s outline its origin goes to.
    * `face` (`str`): The polygon or circle of `on` whose `z` it
      stands at ("" for 0).
    * `turn` (`str`): How far it is turned about its +Z, a formula
      ("" for none).
    * `flip` (`bool`): True to stand it upside down (+Z down).

    Constructor:
    * `Part(name, outline, letters, on, at, face, turn, flip)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    outline: str = field(init=True)
    letters: dict[str, str] = field(init=True, default_factory=dict)
    on: str = field(init=True, default="")
    at: str = field(init=True, default="")
    face: str = field(init=True, default="")
    turn: str = field(init=True, default="")
    flip: bool = field(init=True, default=False)


# Class `Assembly`:
@dataclass(slots=True)
class Assembly:
    """What an assembly file holds.

    Attributes:
    * `letters` (`list[Letter]`): Its own letters, which it exports.
    * `parts` (`list[Part]`): Its parts, each after the one it
      stands on.

    Constructor:
    * `Assembly(letters, parts)`
    """

    # Constructor arguments:
    letters: list[Letter] = field(init=True, default_factory=list)
    parts: list[Part] = field(init=True, default_factory=list)


# Function `assembly_from_text()`:
def assembly_from_text(text: str, source: str = "") -> Assembly:
    """Read an assembly from TOML text, checking its parts' names and
    mates (not yet their outlines).

    Arguments:
    * `text` (`str`): The file's text.
    * `source` (`str`): The file's name, for messages.

    Returns:
    * (`Assembly`): The assembly.

    Raises:
    * `OutlineError`: Every problem found, a line each.
    """
    try:
        data: dict[str, object] = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise OutlineError(f"{source}: {error}") from error
    reader: _Reader = _Reader(source)
    if data.get("kind") != "assembly":
        reader.note("kind", 'is not "assembly"')
    if data.get("version") != ASSEMBLY_VERSION:
        reader.note(
            "version",
            f"is {data.get('version')!r}; only {ASSEMBLY_VERSION} is read",
        )
    assembly: Assembly = Assembly(reader.letters(data.get("letters", {})))
    found: object = data.get("parts")
    if not isinstance(found, list) or not found:
        reader.note("parts", "needs at least one [[parts]] table")
        found = []
    index: int
    table: object
    for index, table in enumerate(found):
        part: Part | None = _part(reader, f"parts[{index}]", table, assembly)
        if part is not None:
            assembly.parts.append(part)
    if reader.problems:
        raise OutlineError("\n".join(reader.problems))
    return assembly


# Function `assembly_text()`:
def assembly_text(assembly: Assembly) -> str:
    """Return an assembly as TOML text, its fields in a fixed order
    (for [Move] and [Rename], #783h).

    Arguments:
    * `assembly` (`Assembly`): The assembly.

    Returns:
    * (`str`): The file's text.
    """
    lines: list[str] = ['kind = "assembly"', f"version = {ASSEMBLY_VERSION}"]
    letter: Letter
    for letter in assembly.letters:
        lines += _letter_lines(letter)
    part: Part
    for part in assembly.parts:
        lines += [
            "",
            "[[parts]]",
            f"name = {_string(part.name)}",
            f"outline = {_string(part.outline)}",
        ]
        if part.letters:
            lines.append(
                "letters = { "
                + ", ".join(
                    f"{letter} = {_string(formula)}"
                    for letter, formula in part.letters.items()
                )
                + " }"
            )
        key: str
        value: str
        for key, value in (
            ("on", part.on),
            ("at", part.at),
            ("face", part.face),
            ("turn", part.turn),
        ):
            if value:
                lines.append(f"{key} = {_string(value)}")
        if part.flip:
            lines.append("flip = true")
    return "\n".join(lines) + "\n"


# Function `used_by()`:
def used_by(outline: Path, shop: Path) -> list[Path]:
    """Return the assembly files of a shop that use an outline file
    (`T.sa~6.11` #783h, "used by").

    Arguments:
    * `outline` (`Path`): The outline file.
    * `shop` (`Path`): The shop's directory.

    Returns:
    * (`list[Path]`): The assemblies, in name order; one that can not
      be read is left out.
    """
    found: list[Path] = []
    path: Path
    for path in sorted(shop.rglob(f"*{ASSEMBLY_SUFFIX}")):
        try:
            assembly: Assembly = assembly_from_text(
                path.read_text(encoding="utf-8"), str(path)
            )
        except (OSError, OutlineError):
            continue
        if any(
            (path.parent / part.outline).resolve() == outline.resolve()
            for part in assembly.parts
        ):
            found.append(path)
    return found


# Function `move_outline()`:
def move_outline(old: Path, new: Path, shop: Path) -> list[Path]:
    """Move (or rename) an outline file and its `.svg`, rewriting each
    assembly that uses it (`T.sa~6.11` #783h, [Move] and [Rename]).

    Arguments:
    * `old` (`Path`): The outline file.
    * `new` (`Path`): Where it goes (`NAME.outline.toml`).
    * `shop` (`Path`): The shop's directory, searched for assemblies.

    Returns:
    * (`list[Path]`): The assemblies rewritten.

    Raises:
    * `FileExistsError`: If `new` is there already.
    * `OSError`: If a file can not be moved or written.
    """
    if new.exists():
        raise FileExistsError(f"{new} is there already")
    users: list[Path] = used_by(old, shop)
    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)
    picture: Path = old.with_suffix(".svg")
    if picture.exists():
        picture.rename(new.with_suffix(".svg"))
    path: Path
    for path in users:
        assembly: Assembly = assembly_from_text(
            path.read_text(encoding="utf-8"), str(path)
        )
        part: Part
        for part in assembly.parts:
            if (path.parent / part.outline).resolve() == old.resolve():
                part.outline = os.path.relpath(new, path.parent)
        path.write_text(assembly_text(assembly), encoding="utf-8")
    return users


# Function `_part()`:
def _part(
    reader: _Reader, where: str, table: object, assembly: Assembly
) -> Part | None:
    """Read one part, noting its problems.

    Arguments:
    * `reader` (`_Reader`): Notes the problems.
    * `where` (`str`): The entry, for messages.
    * `table` (`object`): Its table.
    * `assembly` (`Assembly`): The parts read so far.

    Returns:
    * (`Part | None`): The part; `None` when it is bad.
    """
    if not isinstance(table, dict):
        reader.note(where, "is not a table")
        return None
    strings: dict[str, str] = {}
    key: str
    for key in ("name", "outline", "on", "at", "face", "turn"):
        value: object = table.get(key, "")
        if not isinstance(value, str):
            reader.note(where, f"{key} = {value!r}: is not a string")
            return None
        strings[key] = value
    letters: object = table.get("letters", {})
    flip: object = table.get("flip", False)
    names: list[str] = [part.name for part in assembly.parts]
    problem: str = ""
    if not VERTEX_NAME.fullmatch(strings["name"]):
        problem = f"name = {strings['name']!r}: not a letter, then letters"
    elif strings["name"] in names:
        problem = f"name = {strings['name']!r}: is used twice"
    elif not strings["outline"]:
        problem = "needs outline, the part's outline file"
    elif not isinstance(letters, dict) or not all(
        isinstance(value, str) for value in letters.values()
    ):
        problem = "letters is not a table of formulas"
    elif not isinstance(flip, bool):
        problem = "flip is not true or false"
    elif strings["on"] and strings["on"] not in names:
        problem = f"on = {strings['on']!r}: is not an earlier part"
    elif strings["on"] and not strings["at"]:
        problem = "needs at, the vertex of its parent it stands on"
    if problem:
        reader.note(where, problem)
        return None
    formulas: dict[str, str] = {}
    if isinstance(letters, dict):
        formulas = {
            str(letter): str(value) for letter, value in letters.items()
        }
    return Part(
        strings["name"],
        strings["outline"],
        formulas,
        strings["on"],
        strings["at"],
        strings["face"],
        strings["turn"],
        bool(flip),
    )


# Function `part_outline()`:
def part_outline(assembly: Assembly, part: Part, directory: Path) -> Outline:
    """Return a part's outline, its letters given the part's values.

    Arguments:
    * `assembly` (`Assembly`): The assembly, for its letters.
    * `part` (`Part`): The part.
    * `directory` (`Path`): The assembly file's directory.

    Returns:
    * (`Outline`): The outline, its letters set.

    Raises:
    * `OutlineError`: If the outline file can not be read.
    * `ValueError`: If a formula can not be worked out, or names a
      letter the outline does not have.
    """
    path: Path = directory / part.outline
    try:
        text: str = path.read_text(encoding="utf-8")
    except OSError as error:
        raise OutlineError(f"{part.name}: {error}") from error
    outline: Outline = outline_from_text(text, str(path))
    values: dict[str, float] = letter_values(assembly.letters)
    known: set[str] = {letter.letter for letter in outline.letters}
    given: dict[str, str] = {}
    letter: str
    formula: str
    for letter, formula in part.letters.items():
        if letter not in known:
            raise ValueError(
                f"{part.name}: {part.outline} has no letter {letter}"
            )
        given[letter] = _as_value(evaluate(formula, values), outline, letter)
    set_letters(outline.letters, given)
    return outline


# Function `_as_value()`:
def _as_value(value: float, outline: Outline, letter: str) -> str:
    """Return a worked-out formula as a letter's value with its unit.

    Arguments:
    * `value` (`float`): Millimeters, or radians for an angle.
    * `outline` (`Outline`): The part's outline.
    * `letter` (`str`): Which letter it is for.

    Returns:
    * (`str`): `N mm`, or `N deg` for an angle letter.
    """
    default: str = next(
        each.default for each in outline.letters if each.letter == letter
    )
    if default.split()[-1:] == ["deg"]:
        return f"{math.degrees(value):.9g} deg"
    return f"{value:.9g} mm"


# Function `assembly_solid()`:
def assembly_solid(
    assembly: Assembly,
    name: str,
    directory: Path,
    *,
    color: Color | None = None,
) -> SolidAssembly:
    """Return an assembly's solid: each part's outline's solid, placed
    by its mate (`T.sa~6.11` #769b, #783c).

    Arguments:
    * `assembly` (`Assembly`): The assembly.
    * `name` (`str`): The solid's name; a part is `NAME_PART`.
    * `directory` (`Path`): The assembly file's directory.
    * `color` (`Color | None`): Its material's colour, if any.

    Returns:
    * (`SolidAssembly`): The parts, placed.

    Raises:
    * `OutlineError`: If a part's outline can not be read.
    * `ValueError`: If a part makes no solid, or its mate can not be
      worked out.
    """
    outlines: dict[str, Outline] = {}
    places: dict[str, Placement] = {}
    placed: list[Placed] = []
    part: Part
    for part in assembly.parts:
        outline: Outline = part_outline(assembly, part, directory)
        outlines[part.name] = outline
        here: Placement = Placement()
        if part.on:
            here = places[part.on].compose(
                _mate(assembly, part, outlines[part.on])
            )
        places[part.name] = here
        solid: Solid = outline_solid(
            outline, f"{name}_{part.name}", color=color
        )
        placed.append(Placed(solid, here))
    return SolidAssembly(name, placed)


# Function `assembly_cacheable()`:
def assembly_cacheable(
    assembly: Assembly,
    name: str,
    directory: Path,
    *,
    color: Color | None = None,
) -> Cacheable:
    """Return an assembly's solid as a model for the cache: its
    `.step` made headless, kept by what shapes and places each part.

    Arguments:
    * `assembly` (`Assembly`): The assembly.
    * `name` (`str`): The solid's name.
    * `directory` (`Path`): The assembly file's directory.
    * `color` (`Color | None`): Its material's colour, if any.

    Returns:
    * (`Cacheable`): The model.

    Raises:
    * `OutlineError`: As `assembly_solid()`.
    * `ValueError`: As `assembly_solid()`.
    """
    return solid_cacheable(
        assembly_solid(assembly, name, directory, color=color), "assembly"
    )


# Function `_mate()`:
def _mate(assembly: Assembly, part: Part, parent: Outline) -> Placement:
    """Return where a part sits on its parent, in the parent's frame.

    Arguments:
    * `assembly` (`Assembly`): The assembly, for its letters.
    * `part` (`Part`): The part.
    * `parent` (`Outline`): Its parent's outline, letters set.

    Returns:
    * (`Placement`): Its origin at the vertex and face's height, its
      +Z the parent's (or down), turned.

    Raises:
    * `ValueError`: If the vertex or face is not the parent's, or a
      value can not be worked out.
    """
    if part.at not in parent.names:
        raise ValueError(f"{part.name}: at = {part.at!r}: no such vertex")
    corners: list[tuple[float, float]] | None = real_corners(
        parent.points,
        parent.letters,
        parent.dimensions,
        parent.loops(),
        needed=parent.solid_corners() | {parent.names.index(part.at)},
    )
    if corners is None:
        raise ValueError(f"{part.name}: {part.at} is not dimensioned")
    x: float
    y: float
    x, y = corners[parent.names.index(part.at)]
    z: float = _face_height(part, parent)
    if parent.revolve:
        # A revolved parent's drawing Y is its axis, Z (#783k).
        y, z = 0.0, y
    values: dict[str, float] = letter_values(assembly.letters)
    turn: float = evaluate(part.turn, values) if part.turn else 0.0
    rotation: Rotation = Rotation.about(
        (0.0, 0.0, 1.0), Angle(Fraction(math.degrees(turn)))
    )
    if part.flip:
        rotation = Rotation.about((1.0, 0.0, 0.0), Angle(Fraction(180))) * (
            rotation
        )
    return Placement(
        (_mm(x), _mm(y), _mm(z)),
        rotation,
    )


# Function `_face_height()`:
def _face_height(part: Part, parent: Outline) -> float:
    """Return the `z` (mm) of the parent's face a part stands at.

    Arguments:
    * `part` (`Part`): The part.
    * `parent` (`Outline`): Its parent's outline, letters set.

    Returns:
    * (`float`): The height; 0 with no face.

    Raises:
    * `ValueError`: If the face is not the parent's, or has no `z`.
    """
    if not part.face:
        return 0.0
    heights: dict[str, str] = {
        polygon.name: polygon.z for polygon in parent.polygons
    }
    heights.update({circle.name: circle.z for circle in parent.circles})
    if part.face not in heights:
        raise ValueError(f"{part.name}: face = {part.face!r}: no such shape")
    return evaluate(heights[part.face], letter_values(parent.letters))


# Function `_mm()`:
def _mm(value: float) -> Length:
    """Return millimeters as a length, rounded to a millionth.

    Arguments:
    * `value` (`float`): Millimeters.

    Returns:
    * (`Length`): The length.
    """
    return Length(Fraction(value).limit_denominator(1_000_000), "mm")
