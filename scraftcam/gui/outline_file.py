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

[[points]]
at = [0.0, 0.0]

[[dimensions]]
letter = "A"
kind = "angle"
from = 0
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
letter's ([Font +], [Font -]; absent: 0).  A dimension's `from` and `to`
are a corner's index or `"origin"`, and for an angle an edge (by the
corner it leaves) or `"x_axis"` / `"y_axis"`.
"""

import json
import tomllib
from dataclasses import dataclass, field

from .dimensions import (
    ANGLE,
    HORIZONTAL,
    LENGTH,
    ORIGIN,
    RADIUS,
    VERTICAL,
    X_AXIS,
    Y_AXIS,
    Dimension,
    drawn_marks,
)
from .hides import Hide
from .letters import Letter

# The words a file uses for the points that are not corners.
ENDS: dict[int, str] = {
    ORIGIN: "origin",
    X_AXIS: "x_axis",
    Y_AXIS: "y_axis",
}


# A hide strip's axis, as written (`HIDE_X`, `HIDE_Y`).
AXES: tuple[str, ...] = ("x", "y")

# The file format's version: 2 since marks (#233), 3 since text sizes
# (`T.sfoe~6.4` #280); a file without one is 1, and gets the marks
# its drawing showed.
VERSION: int = 3
VERSIONS: tuple[int, ...] = (1, 2, 3)

# The kinds of dimension a file may hold.
KINDS: tuple[str, ...] = (HORIZONTAL, VERTICAL, LENGTH, ANGLE, RADIUS)


# Class `OutlineError`:
class OutlineError(ValueError):
    """An outline file that cannot be read, with every problem found."""


# Class `Outline`:
@dataclass(slots=True)
class Outline:
    """What an outline file holds.

    Attributes:
    * `points` (`list[tuple[float, float]]`): The corners, as drawn.
    * `letters` (`list[Letter]`): The letters, in table order.
    * `dimensions` (`list[Dimension]`): The dimensions.
    * `revolve` (`bool`): Whether it is revolved about the Y axis.
    * `note_radius` (`str`): The letter of every fillet without a
      radius of its own ("" for none, #116).
    * `hides` (`list[Hide]`): The hide strips (#157).
    * `text_height` (`float`): The diagram's letter height (drawing
      steps); 0 picks one from the outline's size (`T.sfoe~6.4`
      #280).

    Constructor:
    * `Outline(points, letters, dimensions, revolve, note_radius,
      hides, text_height)`
    """

    # Constructor arguments:
    points: list[tuple[float, float]] = field(init=True, default_factory=list)
    letters: list[Letter] = field(init=True, default_factory=list)
    dimensions: list[Dimension] = field(init=True, default_factory=list)
    revolve: bool = field(init=True, default=False)
    note_radius: str = field(init=True, default="")
    hides: list[Hide] = field(init=True, default_factory=list)
    text_height: float = field(init=True, default=0.0)


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

    # The letters, a table each, in the order of the table.
    letter: Letter
    for letter in outline.letters:
        lines += [
            "",
            f"[letters.{letter.letter}]",
            f"name = {_string(letter.name)}",
            f"default = {_string(letter.default)}",
            f"help = {_string(letter.help)}",
        ]
        if letter.fillet:
            lines.append("fillet = true")

    # The corners, then the dimensions.
    x: float
    y: float
    for x, y in outline.points:
        lines += ["", "[[points]]", f"at = [{_number(x)}, {_number(y)}]"]
    dimension: Dimension
    for dimension in outline.dimensions:
        lines += [
            "",
            "[[dimensions]]",
            f"letter = {_string(dimension.letter)}",
            f"kind = {_string(dimension.kind)}",
            f"from = {_end(dimension.start)}",
            f"to = {_end(dimension.end)}",
            f"offset = {_number(dimension.offset)}",
            f"along = {_number(dimension.along)}",
        ]
        if dimension.kind == ANGLE:
            lines.append(f"rays = [{dimension.rays[0]}, {dimension.rays[1]}]")
        if dimension.font_step:
            lines.append(f"font_step = {dimension.font_step}")
        if dimension.places:
            places: str = ", ".join(
                f"[{_string(kind)}, {_number(offset)}, {_number(along)}]"
                for kind, offset, along in dimension.places
            )
            lines.append(f"places = [{places}]")
    hide: Hide
    for hide in outline.hides:
        lines += [
            "",
            "[[hides]]",
            f"axis = {_string(AXES[hide.axis])}",
            f"below = {hide.below}",
            f"above = {hide.above}",
            f"low = {_number(hide.low)}",
            f"high = {_number(hide.high)}",
            f"under = {_number(hide.under)}",
            f"over = {_number(hide.over)}",
        ]
    return "\n".join(lines) + "\n"


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
    * `problems` (`list[str]`): What is wrong, a line each.

    Constructor:
    * `_Reader(source)`
    """

    # Constructor arguments:
    source: str = field(init=True)

    # Remaining attributes (alphabetized):
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
        height: object = data.get("text_height", 0.0)
        if not _is_number(height) or float(height) < 0.0:  # type: ignore[arg-type]  # Checked.
            self.note("text_height", "is not a number, 0 or more")
            height = 0.0
        outline: Outline = Outline(
            self.points(data.get("points", [])),
            self.letters(data.get("letters", {})),
            [],
            revolve,
            note,
            text_height=float(height),  # type: ignore[arg-type]  # Checked.
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

        # A file from before marks (#233) took its level and upright
        # edges and its corners on an axis from the drawing: they are
        # its marks now.
        version: object = data.get("version", 1)
        if version not in VERSIONS:
            self.note(
                "version", f"is not one of {', '.join(map(str, VERSIONS))}"
            )
        elif version == 1:
            # First, as the old solving took them before any dimension.
            outline.dimensions[:0] = drawn_marks(outline.points)
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
            corners: list[object] = [table.get("below"), table.get("above")]
            sides: list[object] = [
                table.get(key, 1.0) for key in ("low", "high", "under", "over")
            ]
            sides[:2] = [table.get("low"), table.get("high")]
            if not all(
                isinstance(corner, int)
                and not isinstance(corner, bool)
                and 0 <= corner < len(outline.points)
                for corner in corners
            ) or not all(_is_number(side) for side in sides):
                self.note(where, "needs corners below, above and numbers")
                continue
            outline.hides.append(
                Hide(
                    AXES.index(str(table["axis"])),
                    int(table["below"]),
                    int(table["above"]),
                    float(table["low"]),
                    float(table["high"]),
                    float(table.get("under", 1.0)),
                    float(table.get("over", 1.0)),
                )
            )

    # Method `_Reader.points()`:
    def points(self, found: object) -> list[tuple[float, float]]:
        """Read the corners: at least 3, each `at = [x, y]`.

        Arguments:
        * `found` (`object`): The file's `points`.

        Returns:
        * (`list[tuple[float, float]]`): The good ones.
        """
        points: list[tuple[float, float]] = []
        if not isinstance(found, list):
            self.note("points", "is not a list of tables")
            return points
        index: int
        table: object
        for index, table in enumerate(found):
            at: object = table.get("at") if isinstance(table, dict) else None
            if (
                isinstance(at, list)
                and len(at) == 2
                and all(_is_number(value) for value in at)
            ):
                points.append((float(at[0]), float(at[1])))
            else:
                self.note(f"points[{index}]", "needs at = [x, y]")
        if len(found) < 3:
            self.note("points", f"has {len(found)} corners; 3 at least")
        return points

    # Method `_Reader.letters()`:
    def letters(self, found: object) -> list[Letter]:
        """Read the letters: `name`, `default`, `help`, maybe `fillet`.

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
            texts: list[object] = [
                table.get(key) if isinstance(table, dict) else None
                for key in ("name", "default", "help")
            ]
            fillet: object = (
                table.get("fillet", False)
                if isinstance(table, dict)
                else False
            )
            if not isinstance(fillet, bool):
                self.note(f"letters.{name}.fillet", "is not true or false")
            elif all(isinstance(text, str) for text in texts):
                letters.append(
                    Letter(
                        name,
                        str(texts[0]),
                        str(texts[1]),
                        str(texts[2]),
                        fillet,
                    )
                )
            else:
                self.note(
                    f"letters.{name}", "needs name, default and help (text)"
                )
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
            self.end(where, key, table.get(key), kind == ANGLE, outline)
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
        )

    # Method `_Reader.end()`:
    def end(
        self,
        where: str,
        key: str,
        value: object,
        angle: bool,
        outline: Outline,
    ) -> int:
        """Read one end of a dimension: a corner (or an edge, for an
        angle) by index, `"origin"`, or, for an angle, an axis.

        Arguments:
        * `where` (`str`): The entry, for messages.
        * `key` (`str`): `from` or `to`.
        * `value` (`object`): What the file has.
        * `angle` (`bool`): Whether the dimension is an angle.
        * `outline` (`Outline`): The corners read.

        Returns:
        * (`int`): The end (`ORIGIN` when bad: the problem is noted).
        """
        allowed: tuple[str, ...] = (
            ("x_axis", "y_axis") if angle else ("origin",)
        )
        if isinstance(value, str) and value in allowed:
            return {word: end for end, word in ENDS.items()}[value]
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value < len(outline.points)
        ):
            return value
        self.note(
            where,
            f"{key} = {value!r}: not a corner 0-{len(outline.points) - 1}"
            f" or {' or '.join(allowed)}",
        )
        return ORIGIN

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


# Function `_end()`:
def _end(end: int) -> str:
    """Return a dimension's end in file form.

    Arguments:
    * `end` (`int`): A corner's index, or `ORIGIN`, `X_AXIS`, `Y_AXIS`.

    Returns:
    * (`str`): The TOML value.
    """
    return _string(ENDS[end]) if end in ENDS else str(end)


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
