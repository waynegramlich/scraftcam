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
from enum import StrEnum

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
from .values import formula_names, refresh_formulas

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
# (`T.sa~6.11` #787), 6 since several polygons (#765).  Only the
# latest is read: the shipped outlines are converted once (#773).
VERSION: int = 6

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


# Class `Role`:
class Role(StrEnum):
    """What a polygon is for (`T.sa~6.11` #767a).

    Attributes:
    * `CUTTING`: It cuts (a tool's flutes).
    * `SUPPORT`: It holds (a shank, a body).
    * `KEEP_OUT`: Where no cutter may go (#783g).
    * `OTHER`: Anything else.
    """

    CUTTING = "cutting"
    SUPPORT = "support"
    KEEP_OUT = "keep_out"
    OTHER = "other"


# Class `Polygon`:
@dataclass(slots=True)
class Polygon:
    """One named polygon of an outline (`T.sa~6.11` #765), drawn
    through vertices of the outline's one pool, which polygons may
    share (#787).

    Attributes:
    * `name` (`str`): Its name, unique in its outline (#767).
    * `role` (`Role`): What it is for (#767a).
    * `vertices` (`list[str]`): Its corners' names, in order.

    A polygon has no material or colour: whatever uses the outline
    gives one, as a tool its `material` (`T.sa~6.11` #838, #840).

    Constructor:
    * `Polygon(name, role, vertices)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    role: Role = field(init=True)
    vertices: list[str] = field(init=True, default_factory=list)


# The name of the polygon a drawing starts with.
FIRST_POLYGON: str = "outline"


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
    * `polygons` (`list[Polygon]`): The polygons (#765); with none
      given, one through every corner in order.

    Constructor:
    * `Outline(points, letters, dimensions, revolve, note_radius,
      hides, text_height, turns, holes, names, polygons)`
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
    polygons: list[Polygon] = field(init=True, default_factory=list)

    # Method `Outline.__post_init__()`:
    def __post_init__(self) -> None:
        """Name the corners that have no name yet; with no polygons,
        make one through every corner."""
        self.fill_names()
        self.fill_polygons()

    # Method `Outline.fill_polygons()`:
    def fill_polygons(self) -> None:
        """With corners but no polygons, make one through them all,
        in order (#765)."""
        if self.points and not self.polygons:
            self.polygons.append(
                Polygon(FIRST_POLYGON, Role.OTHER, list(self.names))
            )

    # Method `Outline.fill_names()`:
    def fill_names(self) -> None:
        """Make `names` as long as `points`: extra names go, and each
        corner without one gets the next `V` number above every name
        used (#787), so a deleted corner's name is not given again.
        """
        del self.names[len(self.points) :]
        while len(self.names) < len(self.points):
            self.names.append(self.new_name())

    # Method `Outline.reset_corners()`:
    def reset_corners(self, points: list[tuple[float, float]]) -> None:
        """Start over with new corners: fresh names and one polygon
        through them all, in order (#765).

        Arguments:
        * `points` (`list[tuple[float, float]]`): The corners.
        """
        self.points[:] = points
        self.names.clear()
        self.polygons.clear()
        self.fill_names()
        self.fill_polygons()

    # Method `Outline.loops()`:
    def loops(self) -> list[list[int]]:
        """Return each polygon's corners, as indices into `points`, in
        its own order (#765, #799).

        Returns:
        * (`list[list[int]]`): A list of corners per polygon.
        """
        self.fill_polygons()
        where: dict[str, int] = {
            name: index for index, name in enumerate(self.names)
        }
        return [
            [where[name] for name in polygon.vertices if name in where]
            for polygon in self.polygons
        ]

    # Method `Outline.sharing()`:
    def sharing(self, corner: int) -> list[str]:
        """Return the names of the polygons through a corner (#777,
        #798).

        Arguments:
        * `corner` (`int`): The corner's index.

        Returns:
        * (`list[str]`): The polygons' names, in order.
        """
        name: str = self.names[corner]
        return [
            polygon.name
            for polygon in self.polygons
            if name in polygon.vertices
        ]

    # Method `Outline.edges()`:
    def edges(self) -> list[tuple[int, int]]:
        """Return every polygon's edges, a shared one once (#797).

        Returns:
        * (`list[tuple[int, int]]`): Each edge's corners, as walked.
        """
        edges: list[tuple[int, int]] = []
        seen: set[frozenset[int]] = set()
        loop: list[int]
        for loop in self.loops():
            spot: int
            corner: int
            for spot, corner in enumerate(loop):
                edge: tuple[int, int] = (corner, loop[(spot + 1) % len(loop)])
                if frozenset(edge) not in seen:
                    seen.add(frozenset(edge))
                    edges.append(edge)
        return edges

    # Method `Outline.new_polygon_name()`:
    def new_polygon_name(self) -> str:
        """Return a name for a new polygon: `P2`, `P3`, ... unused.

        Returns:
        * (`str`): The name.
        """
        used: set[str] = {polygon.name for polygon in self.polygons}
        number: int = 2
        while f"P{number}" in used:
            number += 1
        return f"P{number}"

    # Method `Outline.neighbours()`:
    def neighbours(self, corner: int) -> tuple[int, int]:
        """Return the corners before and after one, in the first
        polygon through it (a fillet's corner is in only one, #798).

        Arguments:
        * `corner` (`int`): The corner's index.

        Returns:
        * (`tuple[int, int]`): The corners before and after it; the
          neighbours in `points` when no polygon has it.
        """
        loop: list[int]
        for loop in self.loops():
            if corner in loop:
                spot: int = loop.index(corner)
                return loop[spot - 1], loop[(spot + 1) % len(loop)]
        count: int = len(self.points)
        return (corner - 1) % count, (corner + 1) % count

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


# Function `letter_scope_problems()`:
def letter_scope_problems(outline: Outline) -> list[str]:
    """Return what breaks the letters' scopes (`T.sa~6.11` #783b): a
    polygon's letter is seen only by its own polygon's corners,
    dimensions and letters; an outline's own formula never uses one;
    a tool's field (`key`) is never internal.

    Arguments:
    * `outline` (`Outline`): The outline.

    Returns:
    * (`list[str]`): The problems, a line each.
    """
    owners: dict[str, str] = {
        letter.letter: letter.polygon for letter in outline.letters
    }
    problems: list[str] = _letter_problems(outline.letters, owners)
    corners: dict[str, set[int]] = {
        polygon.name: set(loop)
        for polygon, loop in zip(
            outline.polygons, outline.loops(), strict=True
        )
    }
    letter: Letter
    for letter in outline.letters:
        if letter.polygon and letter.polygon not in corners:
            problems.append(
                f"{letter.letter}: polygon {letter.polygon!r} is not one"
            )
    dimension: Dimension
    for dimension in outline.dimensions:
        owner: str = owners.get(dimension.letter, "")
        if not owner or owner not in corners:
            continue
        ends: set[int] = {
            end
            for end in (
                dimension.start,
                dimension.end,
                dimension.start_to,
                dimension.end_to,
            )
            if end >= 0
        }
        if not ends <= corners[owner]:
            problems.append(
                f"{dimension.letter}: polygon {owner}'s letter measures"
                " corners of another"
            )
    return problems


# Function `_letter_problems()`:
def _letter_problems(
    letters: list[Letter], owners: dict[str, str]
) -> list[str]:
    """Return what breaks the letters' own scopes (#783b): a tool's
    field never internal, a formula never using another polygon's
    letter.

    Arguments:
    * `letters` (`list[Letter]`): The letters.
    * `owners` (`dict[str, str]`): Each letter's polygon ("" for the
      outline's own).

    Returns:
    * (`list[str]`): The problems, a line each.
    """
    problems: list[str] = []
    letter: Letter
    for letter in letters:
        if letter.key and (letter.internal or letter.polygon):
            problems.append(
                f"{letter.letter}: a tool's field ({letter.key}) is never"
                " internal"
            )
        name: str
        for name in formula_names(letter.formula):
            if owners.get(name, "") not in ("", letter.polygon):
                problems.append(
                    f"{letter.letter}: its formula uses {name}, polygon"
                    f" {owners[name]}'s"
                )
    return problems


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
        lines += _letter_lines(letter)

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
    outline.fill_polygons()
    polygon: Polygon
    for polygon in outline.polygons:
        lines += [
            "",
            "[[polygons]]",
            f"name = {_string(polygon.name)}",
            f"role = {_string(polygon.role.value)}",
        ]
        lines.append(
            "vertices = ["
            + ", ".join(_string(name) for name in polygon.vertices)
            + "]"
        )
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


# Function `_letter_lines()`:
def _letter_lines(letter: Letter) -> list[str]:
    """Return a letter's table, its optional fields only when set.

    Arguments:
    * `letter` (`Letter`): The letter.

    Returns:
    * (`list[str]`): Its lines, a blank one first.
    """
    lines: list[str] = ["", f"[letters.{letter.letter}]"]
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
    if letter.polygon:
        lines.append(f"polygon = {_string(letter.polygon)}")
    elif letter.internal:
        lines.append("internal = true")
    return lines


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
        f"from = {_string(_end_name(outline, dimension, 0))}",
        f"to = {_string(_end_name(outline, dimension, 1))}",
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


# Function `_end_name()`:
def _end_name(outline: Outline, dimension: Dimension, which: int) -> str:
    """Return a dimension's end as a file names it: a corner, or for
    an angle an edge as `V2-V3` (#797), or a word.

    Arguments:
    * `outline` (`Outline`): Its outline, for the corners' names.
    * `dimension` (`Dimension`): The dimension.
    * `which` (`int`): 0 for `from`, 1 for `to`.

    Returns:
    * (`str`): The name.
    """
    end: int = (dimension.start, dimension.end)[which]
    if dimension.kind != ANGLE or end in ENDS:
        return outline.name(end)
    reached: int = (dimension.start_to, dimension.end_to)[which]
    if reached < 0:
        reached = (end + 1) % len(outline.points)
    return f"{outline.name(end)}-{outline.name(reached)}"


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
        # The file's polygons, not the one a new outline is given.
        outline.polygons.clear()
        self.polygons(data.get("polygons"), outline)
        problem: str
        for problem in letter_scope_problems(outline):
            self.note("letters", problem)

        self.angle_edges(outline)

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

    # Method `_Reader.angle_edges()`:
    @staticmethod
    def angle_edges(outline: Outline) -> None:
        """Keep an angle's edge to the corner after it in `points` as
        -1, as the editor makes it and draws it (#797).

        Arguments:
        * `outline` (`Outline`): Its angles changed in place.
        """
        count: int = len(outline.points)
        dimension: Dimension
        for dimension in outline.dimensions:
            if dimension.kind == ANGLE and count:
                if dimension.start_to == (dimension.start + 1) % count:
                    dimension.start_to = -1
                if dimension.end_to == (dimension.end + 1) % count:
                    dimension.end_to = -1

    # Method `_Reader.polygons()`:
    def polygons(self, found: object, outline: Outline) -> None:
        """Read the polygons (#765): at least one; each a unique
        `name`, a `role`, and 3 or more of the
        outline's vertices by name, none twice.

        Arguments:
        * `found` (`object`): The file's `polygons`.
        * `outline` (`Outline`): Given the good ones.
        """
        if not isinstance(found, list) or not found:
            self.note("polygons", "needs at least one [[polygons]] table")
            return
        roles: str = ", ".join(role.value for role in Role)
        index: int
        table: object
        for index, table in enumerate(found):
            where: str = f"polygons[{index}]"
            if not isinstance(table, dict):
                self.note(where, "is not a table")
                continue
            name: object = table.get("name")
            role: object = table.get("role")
            vertices: object = table.get("vertices")
            if not isinstance(name, str) or not VERTEX_NAME.fullmatch(name):
                self.note(
                    where,
                    f"name = {name!r}: not a letter, then"
                    " letters, digits or _",
                )
            elif any(each.name == name for each in outline.polygons):
                self.note(where, f"name = {name!r}: is used twice")
            elif not isinstance(role, str) or role not in tuple(Role):
                self.note(where, f"role = {role!r}: not one of {roles}")
            elif "material" in table or "color" in table:
                self.note(
                    where,
                    "a polygon has no material or color: what uses the"
                    " outline gives one (#840)",
                )
            elif not (
                isinstance(vertices, list)
                and len(vertices) >= 3
                and all(vertex in self.corners for vertex in vertices)
                and len(set(vertices)) == len(vertices)
            ):
                self.note(
                    where,
                    "needs vertices: 3 or more of the"
                    " vertices' names, none twice",
                )
            else:
                outline.polygons.append(
                    Polygon(name, Role(role), list(vertices))
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
            polygon: object = (
                table.get("polygon", "") if isinstance(table, dict) else ""
            )
            internal: object = (
                table.get("internal", False)
                if isinstance(table, dict)
                else False
            )
            if not isinstance(polygon, str):
                self.note(f"letters.{name}.polygon", "is not a name")
            elif not isinstance(internal, bool):
                self.note(f"letters.{name}.internal", "is not true or false")
            elif not isinstance(key, str) or (
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
                        polygon=polygon,
                        internal=internal or bool(polygon),
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
        ends: list[tuple[int, int]] = [
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
            ends[0][0],
            ends[1][0],
            float(numbers[0]),  # type: ignore[arg-type]  # Checked.
            float(numbers[1]),  # type: ignore[arg-type]  # Checked.
            places,
            (int(rays[0]), int(rays[1])),  # type: ignore[index]  # Checked.
            int(step),  # type: ignore[call-overload]  # Checked.
            (float(moved[0]), float(moved[1])),
            ends[0][1],
            ends[1][1],
        )

    # Method `_Reader.end()`:
    def end(
        self,
        where: str,
        key: str,
        value: object,
        angle: bool,
    ) -> tuple[int, int]:
        """Read one end of a dimension: a corner by name or
        `"origin"`; for an angle, an edge by its corners' names,
        `"V2-V3"` (#797), or an axis.

        Arguments:
        * `where` (`str`): The entry, for messages.
        * `key` (`str`): `from` or `to`.
        * `value` (`object`): What the file has.
        * `angle` (`bool`): Whether the dimension is an angle.

        Returns:
        * (`tuple[int, int]`): The end, and for an angle's edge the
          corner it reaches (else -1); `ORIGIN` when bad (the problem
          is noted).
        """
        allowed: tuple[str, ...] = (
            ("x_axis", "y_axis") if angle else ("origin",)
        )
        if isinstance(value, str) and value in allowed:
            return {word: end for end, word in ENDS.items()}[value], -1
        if angle:
            names: list[str] = (
                value.split("-") if isinstance(value, str) else []
            )
            corners: list[int] = [
                self.corners[name] for name in names if name in self.corners
            ]
            if len(names) == 2 and len(corners) == 2:
                return corners[0], corners[1]
        else:
            corner: int | None = self.corner(value)
            if corner is not None:
                return corner, -1
        self.note(
            where,
            f"{key} = {value!r}: not "
            + ("an edge's corners, V1-V2," if angle else "a corner's name")
            + f" or {' or '.join(allowed)}",
        )
        return ORIGIN, -1

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
