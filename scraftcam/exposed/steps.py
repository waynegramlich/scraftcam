"""Recordings: tutorials and tests in one Markdown file (#520, #527).

A recording, `NAME.steps.md`, is written and edited by a person, as
Markdown; only its HTML comments are the tools':
```markdown
# Moving a Corner

A new outline starts as a triangle.

## Corners

* Click the lower left corner.  It turns yellow.
  <!-- do: click -4, -3 -->
* Drag the top corner up and to the right.
  <!-- do: drag 0, 4 -> 1, 6 -->
* A step with no `do:` is there to be read.

<!-- recording
format = 2
scraftcam = "0.1.0"
outline = ''
[[states]]
step = 1
call = "click -4, -3"
state = '''
...
'''
-->
```
The `# ` line is the title; text before the first step or `## `
section is the introduction; a `## ` section, and any text after it,
is shown above the step that follows.  Each `* ` bullet at the left
margin is a step, with its continuation lines indented; its
`<!-- do: ... -->` is the exposed call, its arguments in signature
order (`->` reads as a comma), the object it acts on (`editor`)
left out: the player fills it in.  The final `<!-- recording ... -->`
is TOML: the format, the version, the starting outline file ('' is
a new one) and each step's expected state, matched to its step by
number and call, so an inserted step has no state until `--update`.
A `Player` runs the steps forward and back, without Qt.
"""

from __future__ import annotations

import inspect
import json
import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from scraftcam import __version__
from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError

# The recording format this module reads and writes.
FORMAT: int = 2

# The arguments naming what a step acts on, filled in by the player.
TARGETS: frozenset[str] = frozenset(("editor",))

# Each step's recorded state and time, by (step number, call).
Recorded = dict[tuple[int, str], tuple[str, float]]

# A step's call, and the recording's closing comment.
DO: re.Pattern[str] = re.compile(r"^\s*<!--\s*do:\s*(.*?)\s*-->\s*$")
TRAILER: re.Pattern[str] = re.compile(
    r"^<!--\s*recording\s*\n(.*?)^-->\s*\Z", re.DOTALL | re.MULTILINE
)


@dataclass(frozen=True, slots=True)
class Step:
    """One step of a recording.

    Constructor:
    * `Step(call, arguments, narration, state, section, time)`

    Attributes:
    * `call` (`str`):
        The exposed function to call; "" for a step to read only.
    * `arguments` (`dict[str, object]`):
        Its arguments, but for the object it acts on.
    * `narration` (`str`):
        Its Markdown text; "" takes the docstring's line.
    * `state` (`str`):
        The state text expected after it; "" is not checked.
    * `section` (`str`):
        Markdown shown above it (a `## ` section and its text).
    * `time` (`float`):
        When its gesture began, in seconds from the start of
        recording (#522), to match it with what was said; -1 when
        not known.
    """

    # Constructor arguments:
    call: str = field(init=True)
    arguments: dict[str, object] = field(init=True)
    narration: str = field(init=True, default="")
    state: str = field(init=True, default="")
    section: str = field(init=True, default="")
    time: float = field(init=True, default=-1.0)


@dataclass(frozen=True, slots=True)
class Recording:
    """A recording: a starting outline and its steps.

    Constructor:
    * `Recording(title, intro, outline, steps, version)`

    Attributes:
    * `title` (`str`):
        What it shows, in a few words.
    * `intro` (`str`):
        The Markdown before the first section or step.
    * `outline` (`str`):
        The starting outline file's text; "" starts a new outline.
    * `steps` (`tuple[Step, ...]`):
        The steps, in order.
    * `version` (`str`):
        The scraftcam version it was made with.
    """

    # Constructor arguments:
    title: str = field(init=True)
    intro: str = field(init=True)
    outline: str = field(init=True)
    steps: tuple[Step, ...] = field(init=True)
    version: str = field(init=True, default="")


def _parameters(call: str) -> list[str]:
    """Give the names of `call`'s arguments a step writes, in order.

    Arguments:
    * `call` (`str`):
        The exposed function.

    Returns:
    * (`list[str]`): its parameters, but for the `TARGETS`.

    Raises:
    * `ExposedError`: when nothing exposed has that name.
    """
    function: Callable[..., object] = exposed.lookup(call).function
    return [
        name
        for name in inspect.signature(function).parameters
        if name not in TARGETS
    ]


def _value(text: str) -> object:
    """Read one argument's value: a number, `true`/`false`, a JSON
    string, or else the bare text (`Ctrl+Z`, `Grid`).

    Arguments:
    * `text` (`str`):
        The value as written.

    Returns:
    * (`object`): the value.
    """
    # Numbers, then the two words, then quoted and bare text.
    kind: type[int | float]
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    if text in ("true", "false"):
        return text == "true"
    if text.startswith('"'):
        try:
            loaded: object = json.loads(text)
        except json.JSONDecodeError:
            return text
        return loaded
    return text


def _value_text(value: object) -> str:
    """Write one argument's value as `_value()` reads it back.

    Arguments:
    * `value` (`object`):
        The value.

    Returns:
    * (`str`): its text (`-4`, `1.5`, `Ctrl+Z`, `"a, b"`).
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return repr(value)
    text: str = str(value)
    bare: bool = bool(text) and not any(
        mark in text for mark in (",", '"', "->", "--")
    )
    if bare and text.strip() == text and _value(text) == text:
        return text
    return json.dumps(text)


def parse_call(text: str) -> tuple[str, dict[str, object]]:
    """Read a `do:` call (`drag 0, 4 -> 1, 6`).

    Arguments:
    * `text` (`str`):
        The call: its name, then its values in signature order,
        separated by commas (`->` reads as one).

    Returns:
    * (`tuple[str, dict[str, object]]`): the name and the arguments.

    Raises:
    * `ExposedError`: when the name is unknown or there are too many
      values.
    """
    # The name, then the values (a quoted one may hold a comma).
    name: str
    rest: str
    name, _, rest = text.strip().partition(" ")
    names: list[str] = _parameters(name)
    pieces: list[str] = [
        piece.strip()
        for piece in re.findall(
            r'"(?:[^"\\]|\\.)*"|[^,"]+', rest.replace("->", ",")
        )
        if piece.strip()
    ]
    if len(pieces) > len(names):
        raise ExposedError(
            f"`{name}` takes {len(names)} values, not {len(pieces)}"
        )
    return name, {
        key: _value(piece) for key, piece in zip(names, pieces, strict=False)
    }


def call_text(step: Step) -> str:
    """Write a step's call as `parse_call()` reads it back.

    Arguments:
    * `step` (`Step`):
        The step (one with a call).

    Returns:
    * (`str`): the call, `->` before the first `to_` argument.
    """
    # The values in signature order.
    text: str = step.call
    first: bool = True
    arrow: bool = False
    key: str
    for key in _parameters(step.call):
        if key in step.arguments:
            mark: str = " " if first else ", "
            if key.startswith("to_") and not arrow:
                mark, arrow = " -> ", True
            text += mark + _value_text(step.arguments[key])
            first = False
    return text


def _comment_safe(text: str, what: str) -> str:
    """Refuse text that would end its HTML comment early.

    Arguments:
    * `text` (`str`):
        The text to go inside a comment.
    * `what` (`str`):
        What it is, for the message.

    Returns:
    * (`str`): the text.

    Raises:
    * `ExposedError`: when it holds `-->`.
    """
    if "-->" in text:
        raise ExposedError(f"{what} holds `-->`, which ends a comment")
    return text


def _trailer(text: str, source: str) -> tuple[int, str, str, Recorded]:
    """Read the closing `<!-- recording ... -->` comment.

    Arguments:
    * `text` (`str`):
        The whole file.
    * `source` (`str`):
        The file, for the messages.

    Returns:
    * (`tuple[int, str, str, Recorded]`): where
      the comment starts, the version, the starting outline, and each
      state by (step number, call).

    Raises:
    * `ExposedError`: when it is missing or not one this code reads.
    """
    # The comment's TOML.
    match: re.Match[str] | None = TRAILER.search(text)
    if match is None:
        raise ExposedError(f"{source}: no closing `<!-- recording` comment")
    try:
        table: dict[str, object] = tomllib.loads(match.group(1))
    except tomllib.TOMLDecodeError as error:
        raise ExposedError(f"{source}: recording: {error}") from error

    # The format, then the outline and states.
    if table.get("format") != FORMAT:
        raise ExposedError(
            f"{source}: format {table.get('format')!r}, not {FORMAT}"
        )
    version: object = table.get("scraftcam", "")
    outline: object = table.get("outline", "")
    found: object = table.get("states", [])
    if not (
        isinstance(version, str)
        and isinstance(outline, str)
        and isinstance(found, list)
    ):
        raise ExposedError(f"{source}: a bad `recording` table")
    states: Recorded = {}
    item: object
    for item in found:
        if not isinstance(item, dict):
            raise ExposedError(f"{source}: a state is not a table")
        number: object = item.get("step")
        call: object = item.get("call")
        state: object = item.get("state", "")
        when: object = item.get("time", -1.0)
        if not (
            isinstance(number, int)
            and isinstance(call, str)
            and isinstance(state, str)
            and isinstance(when, (int, float))
            and not isinstance(when, bool)
        ):
            raise ExposedError(f"{source}: state {item!r} is bad")
        states[(number, call)] = (state, float(when))
    return match.start(), version, outline, states


def _make_step(
    lines: list[tuple[int, str]],
    section: str,
    states: Recorded,
    index: int,
    source: str,
) -> Step:
    """Make one step from its bullet's lines.

    Arguments:
    * `lines` (`list[tuple[int, str]]`):
        Its lines with their numbers, the bullet's `* ` made `  `.
    * `section` (`str`):
        The Markdown shown above it.
    * `states` (`Recorded`):
        The recorded states, by (step number, call).
    * `index` (`int`):
        Its number, from 1.
    * `source` (`str`):
        The file, for the messages.

    Returns:
    * (`Step`): the step, its state found by number and call.

    Raises:
    * `ExposedError`: when its `do:` is bad, or there are two.
    """
    # The `do:` comment is the call; the rest is prose.
    call: str = ""
    arguments: dict[str, object] = {}
    prose: list[str] = []
    number: int
    line: str
    for number, line in lines:
        do: re.Match[str] | None = DO.match(line)
        if do is None:
            prose.append(line.removeprefix("  "))
        elif call:
            raise ExposedError(f"{source}:{number}: a second `do:`")
        else:
            try:
                call, arguments = parse_call(do.group(1))
            except ExposedError as error:
                raise ExposedError(f"{source}:{number}: {error}") from error
    narration: str = "\n".join(prose).strip()
    state: str = ""
    when: float = -1.0
    if call:
        state, when = states.get(
            (index, call_text(Step(call, arguments))), ("", -1.0)
        )
    return Step(call, arguments, narration, state, section, when)


def recording_from_markdown(text: str, source: str = "") -> Recording:
    """Read a recording from its Markdown text.

    Arguments:
    * `text` (`str`):
        The `.steps.md` file's text.
    * `source` (`str`):
        Its file name, for the messages.

    Returns:
    * (`Recording`): the recording.

    Raises:
    * `ExposedError`: when it is not a recording this code reads;
      the message names the line.
    """
    # The closing comment holds the outline and the states.
    end: int
    version: str
    outline: str
    states: Recorded
    end, version, outline, states = _trailer(text, source)

    # The title, the introduction, then the steps line by line.
    title: str = ""
    intro: list[str] = []
    section: list[str] = []
    steps: list[Step] = []
    lines: list[tuple[int, str]] = []  # the open step's lines
    started: bool = False

    def close() -> None:
        """Make the open step from its lines, if there is one."""
        if lines:
            steps.append(
                _make_step(
                    lines,
                    "\n".join(section).strip(),
                    states,
                    len(steps) + 1,
                    source,
                )
            )
            lines.clear()
            section.clear()

    number: int
    line: str
    for number, line in enumerate(text[:end].splitlines(), start=1):
        if line.startswith("* "):
            close()
            started = True
            lines.append((number, "  " + line[2:]))
        elif lines and (line.startswith("  ") or not line.strip()):
            lines.append((number, line))
        elif line.startswith("# ") and not title and not started:
            title = line[2:].strip()
        elif line.startswith("## "):
            close()
            started = True
            section.append(line)
        else:
            close()
            (section if started else intro).append(line)
    close()
    return Recording(
        title, "\n".join(intro).strip(), outline, tuple(steps), version
    )


def recording_markdown(recording: Recording) -> str:
    """Give `recording` as the text of its `.steps.md` file.

    Arguments:
    * `recording` (`Recording`):
        The recording.

    Returns:
    * (`str`): the text, which `recording_from_markdown()` reads back.

    Raises:
    * `ExposedError`: when a call or state holds `-->`.
    """
    # The title and introduction, then each step as a bullet.
    lines: list[str] = [f"# {recording.title}", ""]
    if recording.intro:
        lines.extend((recording.intro, ""))
    table: list[str] = [
        f"format = {FORMAT}",
        f"scraftcam = {json.dumps(recording.version or __version__)}",
        "outline = "
        + _toml_text(_comment_safe(recording.outline, "the outline")),
    ]
    index: int
    step: Step
    for index, step in enumerate(recording.steps, start=1):
        if step.section:
            if lines[-1]:
                lines.append("")
            lines.extend((step.section, ""))
        prose: list[str] = step.narration.splitlines() or [""]
        lines.append(f"* {prose[0]}".rstrip())
        lines.extend(f"  {line}".rstrip() for line in prose[1:])
        if step.call:
            call: str = _comment_safe(call_text(step), f"step {index}")
            lines.append(f"  <!-- do: {call} -->")
            if step.state or step.time >= 0:
                table.extend(
                    (
                        "",
                        "[[states]]",
                        f"step = {index}",
                        f"call = {json.dumps(call)}",
                    )
                )
            if step.time >= 0:
                table.append(f"time = {round(step.time, 3)!r}")
            if step.state:
                table.append(
                    "state = " + _toml_text(_comment_safe(step.state, call))
                )
    lines.extend(("", "<!-- recording", *table, "-->"))
    return "\n".join(lines) + "\n"


def _toml_text(text: str) -> str:
    """Give `text` as a TOML string, multi-line ones kept readable.

    Arguments:
    * `text` (`str`):
        The text.

    Returns:
    * (`str`): a literal `\'\'\'` string when it can be one, else a
      basic one.
    """
    if "\n" in text and "'''" not in text:
        return "'''\n" + text.rstrip("\n") + "\n'''"
    return json.dumps(text)


def load(path: Path) -> Recording:
    """Read the recording in `path`.

    Arguments:
    * `path` (`Path`):
        The `.steps.md` file.

    Returns:
    * (`Recording`): the recording.

    Raises:
    * `ExposedError`: when it is not a recording this code reads.
    * `OSError`: when it cannot be read at all.
    """
    return recording_from_markdown(path.read_text(encoding="utf-8"), str(path))


@dataclass(slots=True)
class Player:
    """Runs a recording's steps forward and back, on one object.

    Constructor:
    * `Player(recording, target, depth, undo)`

    Attributes:
    * `recording` (`Recording`):
        The steps.
    * `target` (`dict[str, object]`):
        The arguments naming what each step acts on
        (`{"editor": "OutlineEditor 1"}`).
    * `depth` (`Callable[[], int]`):
        Gives the undo depth now.
    * `undo` (`Callable[[], None]`):
        Undoes one change.
    * `done` (`int`):
        How many steps have run.
    * `depths` (`list[int]`):
        The undo depth before each step run, to go back to.
    """

    # Constructor arguments:
    recording: Recording = field(init=True)
    target: dict[str, object] = field(init=True)
    depth: Callable[[], int] = field(init=True)
    undo: Callable[[], None] = field(init=True)

    # Remaining attributes (alphabetized):
    depths: list[int] = field(init=False, default_factory=list)
    done: int = field(init=False, default=0)

    def narration(self, index: int) -> str:
        """Give step `index`'s line (its own, or its docstring's).

        Arguments:
        * `index` (`int`):
            The step, from 0.

        Returns:
        * (`str`): the line.
        """
        step: Step = self.recording.steps[index]
        if step.narration or not step.call:
            return step.narration
        return exposed.narration(step.call, step.arguments)

    def forward(self) -> str:
        """Run the next step.

        Returns:
        * (`str`): what it gave (the state, for a gesture).

        Raises:
        * `ExposedError`: when every step has run, or the step fails.
        """
        # Remember where to come back to, then run it.
        if self.done >= len(self.recording.steps):
            raise ExposedError("every step has run")
        step: Step = self.recording.steps[self.done]
        self.depths.append(self.depth())
        if not step.call:
            # A step to read, with nothing to do.
            self.done += 1
            return ""
        try:
            result: object = exposed.call(
                step.call, {**step.arguments, **self.target}
            )
        except ExposedError:
            self.depths.pop()
            raise
        self.done += 1
        return str(result)

    def backward(self) -> None:
        """Undo the last step run, back to where it started.

        Raises:
        * `ExposedError`: when no step has run.
        """
        # Undo until the depth is what it was (a step may change
        # nothing, or several things).
        if not self.depths:
            raise ExposedError("no step has run")
        start: int = self.depths.pop()
        while self.depth() > start:
            self.undo()
        self.done -= 1

    def mismatches(self) -> list[str]:
        """Run every step left, checking each step's state.

        Returns:
        * (`list[str]`): one message per step whose state differs
          from the recording's (empty when all match).
        """
        # Each step's expected state against what it gave.
        found: list[str] = []
        while self.done < len(self.recording.steps):
            step: Step = self.recording.steps[self.done]
            number: int = self.done + 1
            given: str = self.forward()
            if (
                step.call
                and step.state
                and given.strip() != step.state.strip()
            ):
                found.append(
                    f"step {number} ({step.call}): expected\n"
                    f"{step.state.strip()}\ngot\n{given.strip()}"
                )
        return found
