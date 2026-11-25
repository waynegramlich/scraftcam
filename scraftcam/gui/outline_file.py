"""Outline files (`T.oe~6.2` #S4): an outline as TOML, no Qt.

An outline drawn in the editor is kept in the shop as
`tools/NAME.outline.toml` (#31), under version control, so each field
always comes out in the same order and a `git diff` shows only what
changed (#92).  The layout (#91):

```toml
kind = "outline"
revolve = true

[letters.A]
name = "Half point angle"
default = "59 deg"
help = ""

[[vertices]]
name = "V1"
at = [0.0, 0.0]

[[dimensions]]
letter = "A"
kind = "angle"
from = "V1"
to = "y_axis"
offset = 0.6
along = 0.5
rays = [1, 1]
```

Positions (`at`, `offset`, `along`) are as drawn, in unitless grid
steps; sizes come from the letters.  Since version 3 (`T.sfoe~6.4`
#280) a `text_height` (grid steps) sets the diagram's lettering,
written once [All Fonts +] or [All Fonts -] sets it (absent: picked
from the outline's size), and a dimension's `font_step` its own
letter's ([Font +], [Font -]; absent: 0).  A mark's `moved`
(`[dx, dy]`, #317; absent: `[0, 0]`) is how far the user dragged
its box.  `turns` (#300, 1 to 3;
absent: 0) shows the drawing turned that many quarter turns
clockwise, its letters upright; the file keeps the tool's axis
along Y.  Since version 4 (#290) `[[holes]]` hold round holes:
`kind` `"plain"` (`letter` its diameter) or `"counterbored"`
(`letter` its socket head cap screw's size, the holes from
`screws.py`, #328), `at` its center as drawn, and, written only
when they differ from the table, `clearance`, `counterbore` and
`depth` (lengths with units).  Since version 5 (`T.sa~6.11`
#787) the corners are `[[vertices]]`, each with a `name` (earlier
files had `[[points]]`, by index).  A dimension's `from` and `to`
are a corner's name or `"origin"`, and for an angle an edge (by the
corner it leaves) or `"x_axis"` / `"y_axis"`; a hide strip's `below`
and `above` are corners' names.
"""

import json
import re
import tomllib
from dataclasses import dataclass, field

from .dimensions import (
    ANGLE,
    DIAMETER,
    HORIZONTAL,
    LENGTH,
    ORIGIN,
    RADIUS,
    VERTICAL,
    X_AXIS,
    Y_AXIS,
    Dimension,
)
from .hides import Hide
from .letters import Letter
from .values import refresh_formulas

# The words a file uses for the points that are not corners.
ENDS: dict[int, str] = {
    ORIGIN: "origin",
    X_AXIS: "x_axis",
    Y_AXIS: "y_axis",
}


# A hide strip's axis, as written (`HIDE_X`, `HIDE_Y`).
AXES: tuple[str, ...] = ("x", "y")

# The file format's version: 2 since marks (#233), 3 since text sizes
# (`T.sfoe~6.4` #280), 4 since holes (#290), 5 since named vertices
# (`T.sa~6.11` #787).  Only version 5 is read: the shipped outlines
# were converted once (#773).
VERSION: int = 5

# A vertex's name (#787): a letter, then letters, digits or `_`.
VERTEX_NAME: re.Pattern[str] = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

# The kinds of hole (#290): a plain one is sized by its letter, a
# counterbored one by its screw's.
# Closed set: a `StrEnum` with `match`/`assert_never()` would let
# mypy catch a missed value (#762).
PLAIN: str = "plain"
COUNTERBORED: str = "counterbored"
HOLE_KINDS: tuple[str, ...] = (PLAIN, COUNTERBORED)

# A counterbored hole's sizes that may differ from `screws.py`'s.
HOLE_SIZES: tuple[str, ...] = ("clearance", "counterbore", "depth")

# The kinds of dimension a file may hold.
KINDS: tuple[str, ...] = (
    HORIZONTAL,
    VERTICAL,
    LENGTH,
    ANGLE,
    RADIUS,
    DIAMETER,
)


# Class `OutlineError`:
class OutlineError(ValueError):
    """An outline file that cannot be read, with every problem found."""


# Class `Hole`:
@dataclass(slots=True)
class Hole:
    """A round hole through the outline (#290).

    Attributes:
    * `kind` (`str`): `PLAIN` or `COUNTERBORED`.
    * `at` (`tuple[float, float]`): Its center, as drawn.
    * `letter` (`str`): A plain hole's diameter, or a counterbored
      one's screw size (Shars's E).
    * `clearance` (`str`): The clearance hole's diameter, a length
      with its unit; "" takes the screw's.
    * `counterbore` (`str`): The counterbore's diameter; "" takes the
      screw's.
    * `depth` (`str`): The counterbore's depth; "" takes the screw's
      head height.

    Constructor:
    * `Hole(kind, at, letter, clearance, counterbore, depth)`
    """

    # Constructor arguments:
    kind: str = field(init=True)
    at: tuple[float, float] = field(init=True)
    letter: str = field(init=True)
    clearance: str = field(init=True, default="")
    counterbore: str = field(init=True, default="")
    depth: str = field(init=True, default="")


# Class `Outline`:
# One attribute per field of the file, which has nine.
@dataclass(slots=True)
class Outline:  # pylint: disable=too-many-instance-attributes
    """What an outline file holds.

    Attributes:
    * `points` (`list[tuple[float, float]]`): The corners, as drawn.
    * `letters` (`list[Letter]`): The letters, in table order.
    * `dimensions` (`list[Dimension]`): The dimensions.
    * `revolve` (`bool`): Whether it is revolved about the Y axis.
    * `note_radius` (`str`): The letter of every fillet without a
      radius of its own ("" for none, #116).
    * `hides` (`list[Hide]`): The hide strips (#157).
    * `holes` (`list[Hole]`): The holes (#290).
    * `text_height` (`float`): The diagram's letter height (drawing
      steps); 0 picks one from the outline's size (`T.sfoe~6.4`
      #280).
    * `turns` (`int`): How many quarter turns clockwise its diagram
      is shown turned, 0 to 3, letters upright (#300).
    * `names` (`list[str]`): Each corner's name, beside `points`
      (#787); missing ones are given `V1`, `V2`, ... unused.

    Constructor:
    * `Outline(points, letters, dimensions, revolve, note_radius,
      hides, text_height, turns, holes, names)`
    """

    # Constructor arguments:
    points: list[tuple[float, float]] = field(init=True, default_factory=list)
    letters: list[Letter] = field(init=True, default_factory=list)
    dimensions: list[Dimension] = field(init=True, default_factory=list)
    revolve: bool = field(init=True, default=False)
    note_radius: str = field(init=True, default="")
    hides: list[Hide] = field(init=True, default_factory=list)
    text_height: float = field(init=True, default=0.0)
    turns: int = field(init=True, default=0)
    holes: list[Hole] = field(init=True, default_factory=list)
    names: list[str] = field(init=True, default_factory=list)

    # Method `Outline.__post_init__()`:
    def __post_init__(self) -> None:
        """Name the corners that have no name yet."""
        self.fill_names()

    # Method `Outline.fill_names()`:
    def fill_names(self) -> None:
        """Make `names` as long as `points`: extra names go, and each
        corner without one gets the next `V` number above every name
        used (#787), so a deleted corner's name is not given again.
        """
        del self.names[len(self.points) :]
        while len(self.names) < len(self.points):
            self.names.append(self.new_name())

    # Method `Outline.new_name()`:
    def new_name(self) -> str:
        """Return a name for a new corner (#787).

        Returns:
        * (`str`): The next `V` number above every name used.
        """
        number: int = max(
            (
                int(name[1:])
                for name in self.names
                if name[:1] == "V" and name[1:].isdigit()
            ),
            default=0,
        )
        return f"V{number + 1}"

    # Method `Outline.name()`:
    def name(self, index: int) -> str:
        """Return a dimension end's or corner's name in file form.

        Arguments:
        * `index` (`int`): A corner's index, or `ORIGIN`, `X_AXIS`,
          `Y_AXIS`.

        Returns:
        * (`str`): Its name.
        """
        return ENDS[index] if index in ENDS else self.names[index]


# Function `outline_text()`:
def outline_text(outline: Outline) -> str:
    """Return an outline as TOML text, its fields in a fixed order.

    Arguments:
    * `outline` (`Outline`): The outline.

    Returns:
    * (`str`): The file's text.
    """
    lines: list[str] = [
        'kind = "outline"',
        f"version = {VERSION}",
        f"revolve = {'true' if outline.revolve else 'false'}",
    ]
    if outline.note_radius:
        lines.append(f"note_radius = {_string(outline.note_radius)}")
    if outline.text_height > 0.0:
        lines.append(f"text_height = {_number(outline.text_height)}")
    if outline.turns:
        lines.append(f"turns = {outline.turns}")

    # The letters, a table each, in the order of the table.
    letter: Letter
    for letter in outline.letters:
        lines += ["", f"[letters.{letter.letter}]"]
        if letter.key:
            lines.append(f"key = {_string(letter.key)}")
        lines += [
            f"name = {_string(letter.name)}",
            (
                f"formula = {_string(letter.formula)}"
                if letter.formula
                else f"default = {_string(letter.default)}"
            ),
            f"help = {_string(letter.help)}",
        ]
        if letter.fillet:
            lines.append("fillet = true")

    # The corners, named (#787), then the dimensions.
    outline.fill_names()
    name: str
    x: float
    y: float
    for name, (x, y) in zip(outline.names, outline.points, strict=True):
        lines += [
            "",
            "[[vertices]]",
            f"name = {_string(name)}",
            f"at = [{_number(x)}, {_number(y)}]",
        ]
    dimension: Dimension
    for dimension in outline.dimensions:
        lines += _dimension_lines(dimension, outline)
    hide: Hide
    for hide in outline.hides:
        lines += _hide_lines(hide, outline)
    hole: Hole
    for hole in outline.holes:
        lines += _hole_lines(hole)
    return "\n".join(lines) + "\n"


# Function `_dimension_lines()`:
def _dimension_lines(dimension: Dimension, outline: Outline) -> list[str]:
    """Return a dimension's table, its optional fields only when set.

    Arguments:
    * `dimension` (`Dimension`): The dimension.
    * `outline` (`Outline`): Its outline, for the corners' names.

    Returns:
    * (`list[str]`): Its lines, a blank one first.
    """
    lines: list[str] = [
        "",
        "[[dimensions]]",
        f"letter = {_string(dimension.letter)}",
        f"kind = {_string(dimension.kind)}",
        f"from = {_string(outline.name(dimension.start))}",
        f"to = {_string(outline.name(dimension.end))}",
        f"offset = {_number(dimension.offset)}",
        f"along = {_number(dimension.along)}",
    ]
    if dimension.kind == ANGLE:
        lines.append(f"rays = [{dimension.rays[0]}, {dimension.rays[1]}]")
    if dimension.font_step:
        lines.append(f"font_step = {dimension.font_step}")
    if dimension.moved != (0.0, 0.0):
        lines.append(
            f"moved = [{_number(dimension.moved[0])},"
            f" {_number(dimension.moved[1])}]"
        )
    if dimension.places:
        places: str = ", ".join(
            f"[{_string(kind)}, {_number(offset)}, {_number(along)}]"
            for kind, offset, along in dimension.places
        )
        lines.append(f"places = [{places}]")
    return lines


# Function `_hide_lines()`:
def _hide_lines(hide: Hide, outline: Outline) -> list[str]:
    """Return a hide strip's table.

    Arguments:
    * `hide` (`Hide`): The strip.
    * `outline` (`Outline`): Its outline, for the corners' names.

    Returns:
    * (`list[str]`): Its lines, a blank one first.
    """
    return [
        "",
        "[[hides]]",
        f"axis = {_string(AXES[hide.axis])}",
        f"below = {_string(outline.name(hide.below))}",
        f"above = {_string(outline.name(hide.above))}",
        f"low = {_number(hide.low)}",
        f"high = {_number(hide.high)}",
        f"under = {_number(hide.under)}",
        f"over = {_number(hide.over)}",
    ]


# Function `_hole_lines()`:
def _hole_lines(hole: Hole) -> list[str]:
    """Return a hole's table, its sizes only when set.

    Arguments:
    * `hole` (`Hole`): The hole.

    Returns:
    * (`list[str]`): Its lines, a blank one first.
    """
    return [
        "",
        "[[holes]]",
        f"kind = {_string(hole.kind)}",
        f"at = [{_number(hole.at[0])}, {_number(hole.at[1])}]",
        f"letter = {_string(hole.letter)}",
    ] + [
        f"{size} = {_string(getattr(hole, size))}"
        for size in HOLE_SIZES
        if getattr(hole, size)
    ]


# Function `outline_from_text()`:
def outline_from_text(text: str, source: str = "") -> Outline:
    """Read an outline from TOML text, checking that it can be drawn
    (#93); the letters' names and values are left to the editor's
    table, which marks them (#96).

    Arguments:
    * `text` (`str`): The file's text.
    * `source` (`str`): The file's name, for messages.

    Returns:
    * (`Outline`): The outline.

    Raises:
    * `OutlineError`: Every problem found, a line each, naming the
      file and the entry.
    """
    try:
        data: dict[str, object] = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise OutlineError(f"{source}: {error}") from error
    reader: _Reader = _Reader(source)
    outline: Outline = reader.outline(data)
    if reader.problems:
        raise OutlineError("\n".join(reader.problems))
    return outline


# Class `_Reader`:
@dataclass(slots=True)
class _Reader:
    """Reads a file's tables into an `Outline`, noting each problem.

    Attributes:
    * `source` (`str`): The file's name, for messages.
    * `corners` (`dict[str, int]`): Each corner's index by its name
      (#787).
    * `problems` (`list[str]`): What is wrong, a line each.

    Constructor:
    * `_Reader(source)`
    """

    # Constructor arguments:
    source: str = field(init=True)

    # Remaining attributes (alphabetized):
    corners: dict[str, int] = field(init=False, default_factory=dict)
    problems: list[str] = field(init=False, default_factory=list)

    # Method `_Reader.note()`:
    def note(self, where: str, problem: str) -> None:
        """Note one problem.

        Arguments:
        * `where` (`str`): The entry (`dimensions[2]`).
        * `problem` (`str`): What is wrong with it.
        """
        self.problems.append(f"{self.source}: {where}: {problem}")

    # Method `_Reader.outline()`:
    def outline(self, data: dict[str, object]) -> Outline:
        """Read the whole file.

        Arguments:
        * `data` (`dict[str, object]`): What `tomllib` read.

        Returns:
        * (`Outline`): As much as could be read.
        """
        if data.get("kind") != "outline":
            self.note("kind", 'is not "outline"')
        revolve: object = data.get("revolve", False)
        if not isinstance(revolve, bool):
            self.note("revolve", "is not true or false")
            revolve = False
        note: object = data.get("note_radius", "")
        if not isinstance(note, str):
            self.note("note_radius", "is not a letter")
            note = ""
        turns: object = data.get("turns", 0)
        if isinstance(turns, bool) or turns not in (0, 1, 2, 3):
            self.note("turns", "is not 0, 1, 2 or 3")
            turns = 0
        height: object = data.get("text_height", 0.0)
        if not _is_number(height) or float(height) < 0.0:  # type: ignore[arg-type]  # Checked.
            self.note("text_height", "is not a number, 0 or more")
            height = 0.0
        version: object = data.get("version")
        if version != VERSION:
            self.note(
                "version",
                f"is {version!r}; only {VERSION} is read (#773)",
            )
        names: list[str] = []
        points: list[tuple[float, float]] = self.vertices(
            data.get("vertices", []), names
        )
        outline: Outline = Outline(
            points,
            self.letters(data.get("letters", {})),
            [],
            revolve,
            note,
            text_height=float(height),  # type: ignore[arg-type]  # Checked.
            turns=turns,
            names=names,
        )
        if revolve and any(x < 0.0 for x, _ in outline.points):
            self.note("points", "a revolved outline has a corner at X < 0")
        found: object = data.get("dimensions", [])
        if not isinstance(found, list):
            self.note("dimensions", "is not a list of tables")
            found = []
        index: int
        table: object
        for index, table in enumerate(found):
            dimension: Dimension | None = self.dimension(
                f"dimensions[{index}]", table, outline
            )
            if dimension is not None:
                outline.dimensions.append(dimension)
        self.hides(data.get("hides", []), outline)
        self.holes(data.get("holes", []), outline)

        return outline

    # Method `_Reader.hides()`:
    def hides(self, found: object, outline: Outline) -> None:
        """Read the hide strips, their corners checked.

        Arguments:
        * `found` (`object`): The file's `hides`.
        * `outline` (`Outline`): Given the good ones.
        """
        if not isinstance(found, list):
            self.note("hides", "is not a list of tables")
            return
        index: int
        table: object
        for index, table in enumerate(found):
            where: str = f"hides[{index}]"
            if not isinstance(table, dict) or table.get("axis") not in AXES:
                self.note(where, 'needs axis = "x" or "y"')
                continue
            corners: list[int | None] = [
                self.corner(table.get("below")),
                self.corner(table.get("above")),
            ]
            sides: list[object] = [
                table.get(key, 1.0) for key in ("low", "high", "under", "over")
            ]
            sides[:2] = [table.get("low"), table.get("high")]
            below: int | None = corners[0]
            above: int | None = corners[1]
            if (
                below is None
                or above is None
                or not all(_is_number(side) for side in sides)
            ):
                self.note(where, "needs corners below, above and numbers")
                continue
            outline.hides.append(
                Hide(
                    AXES.index(str(table["axis"])),
                    below,
                    above,
                    float(table["low"]),
                    float(table["high"]),
                    float(table.get("under", 1.0)),
                    float(table.get("over", 1.0)),
                )
            )

    # Method `_Reader.holes()`:
    def holes(self, found: object, outline: Outline) -> None:
        """Read the holes, their kinds, centers and sizes checked.

        Arguments:
        * `found` (`object`): The file's `holes`.
        * `outline` (`Outline`): Given the good ones.
        """
        if not isinstance(found, list):
            self.note("holes", "is not a list of tables")
            return
        index: int
        table: object
        for index, table in enumerate(found):
            where: str = f"holes[{index}]"
            if not isinstance(table, dict):
                self.note(where, "is not a table")
                continue
            kind: object = table.get("kind")
            at: object = table.get("at")
            letter: object = table.get("letter")
            sizes: list[object] = [table.get(size, "") for size in HOLE_SIZES]
            if kind not in HOLE_KINDS:
                self.note(where, f"kind is not one of {', '.join(HOLE_KINDS)}")
            elif not (
                isinstance(at, list)
                and len(at) == 2
                and all(_is_number(number) for number in at)
            ):
                self.note(where, "at is not [x, y]")
            elif not isinstance(letter, str) or not letter:
                self.note(where, "needs a letter")
            elif not all(isinstance(size, str) for size in sizes):
                self.note(where, f"{', '.join(HOLE_SIZES)} must be text")
            elif kind == PLAIN and any(sizes):
                self.note(where, "a plain hole has only its letter's size")
            else:
                outline.holes.append(
                    Hole(
                        str(kind),
                        (float(at[0]), float(at[1])),
                        letter,
                        *(str(size) for size in sizes),
                    )
                )

    # Method `_Reader.vertices()`:
    def vertices(
        self, found: object, names: list[str]
    ) -> list[tuple[float, float]]:
        """Read the named corners (version 5 on, #787): at least 3,
        each `name` (unique, not an end's word) and `at = [x, y]`.

        Arguments:
        * `found` (`object`): The file's `vertices`.
        * `names` (`list[str]`): Given the good ones' names.

        Returns:
        * (`list[tuple[float, float]]`): The good ones' places.
        """
        points: list[tuple[float, float]] = []
        if not isinstance(found, list):
            self.note("vertices", "is not a list of tables")
            return points
        index: int
        table: object
        for index, table in enumerate(found):
            where: str = f"vertices[{index}]"
            if not isinstance(table, dict):
                self.note(where, "is not a table")
                continue
            name: object = table.get("name")
            at: object = table.get("at")
            if not (
                isinstance(at, list)
                and len(at) == 2
                and all(_is_number(value) for value in at)
            ):
                self.note(where, "needs at = [x, y]")
            elif not isinstance(name, str) or not VERTEX_NAME.fullmatch(name):
                self.note(
                    where,
                    f"name = {name!r}: not a letter, then"
                    " letters, digits or _",
                )
            elif name in ENDS.values():
                self.note(where, f"name = {name!r}: is an end's word")
            elif name in self.corners:
                self.note(where, f"name = {name!r}: is used twice")
            else:
                self.corners[name] = len(points)
                names.append(name)
                points.append((float(at[0]), float(at[1])))
        if len(found) < 3:
            self.note("vertices", f"has {len(found)} corners; 3 at least")
        return points

    # Method `_Reader.letters()`:
    def letters(self, found: object) -> list[Letter]:
        """Read the letters: `name`, `default` (or `formula`, #430),
        `help`, maybe `fillet`.  Formula letters' values are worked
        out.

        Arguments:
        * `found` (`object`): The file's `letters`.

        Returns:
        * (`list[Letter]`): The good ones, in the file's order.
        """
        letters: list[Letter] = []
        if not isinstance(found, dict):
            self.note("letters", "is not a table of tables")
            return letters
        name: str
        table: object
        for name, table in found.items():
            # A formula letter has a `formula` in place of `default`.
            formula: object = (
                table.get("formula", "") if isinstance(table, dict) else ""
            )
            texts: list[object] = [
                table.get(key) if isinstance(table, dict) else None
                for key in ("name", "default", "help")
            ]
            if isinstance(formula, str) and formula and texts[1] is None:
                texts[1] = ""
            fillet: object = (
                table.get("fillet", False)
                if isinstance(table, dict)
                else False
            )
            key: object = (
                table.get("key", "") if isinstance(table, dict) else ""
            )
            if not isinstance(key, str) or (
                key and not re.fullmatch("[a-z][a-z0-9_]*", key)
            ):
                self.note(f"letters.{name}.key", "is not a field's name")
            elif not isinstance(fillet, bool):
                self.note(f"letters.{name}.fillet", "is not true or false")
            elif not isinstance(formula, str):
                self.note(f"letters.{name}.formula", "is not text")
            elif all(isinstance(text, str) for text in texts):
                letters.append(
                    Letter(
                        name,
                        str(texts[0]),
                        str(texts[1]),
                        str(texts[2]),
                        fillet,
                        formula,
                        key=key,
                    )
                )
            else:
                self.note(
                    f"letters.{name}",
                    "needs name, default (or formula) and help (text)",
                )
        refresh_formulas(letters)
        return letters

    # Method `_Reader.dimension()`:
    def dimension(
        self, where: str, table: object, outline: Outline
    ) -> Dimension | None:
        """Read one dimension, its ends checked against the corners.

        Arguments:
        * `where` (`str`): The entry, for messages.
        * `table` (`object`): Its table.
        * `outline` (`Outline`): The corners and letters read so far.

        Returns:
        * (`Dimension | None`): It, or `None` when it is bad.
        """
        if not isinstance(table, dict):
            self.note(where, "is not a table")
            return None
        count: int = len(self.problems)
        kind: object = table.get("kind")
        if kind not in KINDS:
            self.note(where, f"kind {kind!r} is not one of {', '.join(KINDS)}")
        letter: object = table.get("letter")
        if letter != "" and letter not in {
            each.letter for each in outline.letters
        }:
            # A mark is letterless (#233).
            self.note(where, f"letter {letter!r} is not in [letters]")
        ends: list[int] = [
            self.end(where, key, table.get(key), kind == ANGLE)
            for key in ("from", "to")
        ]
        numbers: list[object] = [table.get("offset"), table.get("along")]
        if not all(_is_number(value) for value in numbers):
            self.note(where, "needs numbers for offset and along")
        rays: object = table.get("rays", [1, 1])
        if not (
            isinstance(rays, list)
            and len(rays) == 2
            and all(ray in (1, -1) for ray in rays)
        ):
            self.note(where, "rays must be two of 1 and -1")
        step: object = table.get("font_step", 0)
        if not isinstance(step, int) or isinstance(step, bool):
            self.note(where, "font_step is not a whole number")
        moved: object = table.get("moved", [0.0, 0.0])
        if not (
            isinstance(moved, list)
            and len(moved) == 2
            and all(_is_number(value) for value in moved)
        ):
            self.note(where, "moved must be two numbers")
            moved = [0.0, 0.0]
        places: tuple[tuple[str, float, float], ...] = self.places(
            where, table.get("places", [])
        )
        if len(self.problems) > count:
            return None
        return Dimension(
            str(letter),
            str(kind),
            ends[0],
            ends[1],
            float(numbers[0]),  # type: ignore[arg-type]  # Checked.
            float(numbers[1]),  # type: ignore[arg-type]  # Checked.
            places,
            (int(rays[0]), int(rays[1])),  # type: ignore[index]  # Checked.
            int(step),  # type: ignore[call-overload]  # Checked.
            (float(moved[0]), float(moved[1])),
        )

    # Method `_Reader.end()`:
    def end(
        self,
        where: str,
        key: str,
        value: object,
        angle: bool,
    ) -> int:
        """Read one end of a dimension: a corner (or an edge, for an
        angle) by name, `"origin"`, or, for an angle, an axis.

        Arguments:
        * `where` (`str`): The entry, for messages.
        * `key` (`str`): `from` or `to`.
        * `value` (`object`): What the file has.
        * `angle` (`bool`): Whether the dimension is an angle.

        Returns:
        * (`int`): The end (`ORIGIN` when bad: the problem is noted).
        """
        allowed: tuple[str, ...] = (
            ("x_axis", "y_axis") if angle else ("origin",)
        )
        if isinstance(value, str) and value in allowed:
            return {word: end for end, word in ENDS.items()}[value]
        corner: int | None = self.corner(value)
        if corner is not None:
            return corner
        self.note(
            where,
            f"{key} = {value!r}: not a corner's name"
            f" or {' or '.join(allowed)}",
        )
        return ORIGIN

    # Method `_Reader.corner()`:
    def corner(self, value: object) -> int | None:
        """Return the corner a file names, by its name (#787).

        Arguments:
        * `value` (`object`): What the file has.

        Returns:
        * (`int | None`): Its index, or `None` when it is not one.
        """
        return self.corners.get(value) if isinstance(value, str) else None

    # Method `_Reader.places()`:
    def places(
        self, where: str, found: object
    ) -> tuple[tuple[str, float, float], ...]:
        """Read a dimension's remembered places, `[kind, offset, along]`.

        Arguments:
        * `where` (`str`): The entry, for messages.
        * `found` (`object`): What the file has.

        Returns:
        * (`tuple[tuple[str, float, float], ...]`): The places.
        """
        places: list[tuple[str, float, float]] = []
        if not isinstance(found, list):
            found = [found]
        place: object
        for place in found:
            if (
                isinstance(place, list)
                and len(place) == 3
                and place[0] in KINDS
                and _is_number(place[1])
                and _is_number(place[2])
            ):
                places.append((place[0], float(place[1]), float(place[2])))
            else:
                self.note(
                    where, f"places: {place!r} is not [kind, offset, along]"
                )
        return tuple(places)


# Function `_is_number()`:
def _is_number(value: object) -> bool:
    """Return whether a TOML value is a number (not a flag).

    Arguments:
    * `value` (`object`): The value.

    Returns:
    * (`bool`): Whether it is an `int` or a `float`.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# Function `_string()`:
def _string(text: str) -> str:
    """Return text as a TOML basic string (JSON's escapes suit it).

    Arguments:
    * `text` (`str`): The text.

    Returns:
    * (`str`): The quoted string.
    """
    return json.dumps(text, ensure_ascii=False)


# Function `_number()`:
def _number(value: float) -> str:
    """Return a float as TOML, the shortest that reads back the same.

    Arguments:
    * `value` (`float`): The number.

    Returns:
    * (`str`): Its text.
    """
    return repr(float(value))
