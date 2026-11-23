"""Recordings: tutorials and tests in one file (#495, #502).

A recording, `NAME.steps.toml`, is self-contained and versioned:
```toml
format = 1                 # this module's `FORMAT`
scraftcam = "0.1.0"        # the version it was made with
title = "Move a corner"
outline = '''...'''        # the starting outline file; "" is new

[[steps]]
call = "drag"              # an exposed function
arguments = { x = 0, y = 4, to_x = 1, to_y = 6 }
narration = "..."          # optional: else the docstring's line
state = '''...'''          # optional: the state expected after
```
The object a step acts on (`editor`) is not in its arguments: the
player fills it in, so a recording replays on any session.  A
`Player` runs the steps forward and back, without Qt: the panel
shows them to a user (#S4), `--headless` checks every state.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from scraftcam import __version__
from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError

# The recording format this module reads.
FORMAT: int = 1


@dataclass(frozen=True, slots=True)
class Step:
    """One step of a recording.

    Constructor:
    * `Step(call, arguments, narration, state)`

    Attributes:
    * `call` (`str`):
        The exposed function to call.
    * `arguments` (`dict[str, object]`):
        Its arguments, but for the object it acts on.
    * `narration` (`str`):
        The line shown for it; "" takes the docstring's.
    * `state` (`str`):
        The state text expected after it; "" is not checked.
    """

    # Constructor arguments:
    call: str = field(init=True)
    arguments: dict[str, object] = field(init=True)
    narration: str = field(init=True, default="")
    state: str = field(init=True, default="")


@dataclass(frozen=True, slots=True)
class Recording:
    """A recording: a starting outline and its steps.

    Constructor:
    * `Recording(title, outline, steps, version)`

    Attributes:
    * `title` (`str`):
        What it shows, in a few words.
    * `outline` (`str`):
        The starting outline file's text; "" starts a new outline.
    * `steps` (`tuple[Step, ...]`):
        The steps, in order.
    * `version` (`str`):
        The scraftcam version it was made with.
    """

    # Constructor arguments:
    title: str = field(init=True)
    outline: str = field(init=True)
    steps: tuple[Step, ...] = field(init=True)
    version: str = field(init=True, default="")


def _text(table: dict[str, object], key: str, where: str) -> str:
    """Give `table[key]` as a string, "" when it is absent.

    Arguments:
    * `table` (`dict[str, object]`):
        The TOML table.
    * `key` (`str`):
        The key.
    * `where` (`str`):
        Where the table is, for the message.

    Returns:
    * (`str`): the value.

    Raises:
    * `ExposedError`: when the value is not a string.
    """
    value: object = table.get(key, "")
    if not isinstance(value, str):
        raise ExposedError(f"{where}: `{key}` is not a string")
    return value


def recording_from_text(text: str, source: str = "") -> Recording:
    """Read a recording from its TOML text.

    Arguments:
    * `text` (`str`):
        The `.steps.toml` file's text.
    * `source` (`str`):
        Its file name, for the messages.

    Returns:
    * (`Recording`): the recording.

    Raises:
    * `ExposedError`: when it is not a recording this code reads.
    """
    # The whole file, then its format.
    try:
        table: dict[str, object] = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ExposedError(f"{source}: {error}") from error
    if table.get("format") != FORMAT:
        raise ExposedError(
            f"{source}: format {table.get('format')!r}, not {FORMAT}"
        )

    # Each step.
    found: object = table.get("steps", [])
    if not isinstance(found, list):
        raise ExposedError(f"{source}: `steps` is not a list of tables")
    steps: list[Step] = []
    index: int
    item: object
    for index, item in enumerate(found, start=1):
        where: str = f"{source}: step {index}"
        if not isinstance(item, dict):
            raise ExposedError(f"{where} is not a table")
        arguments: object = item.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ExposedError(f"{where}: `arguments` is not a table")
        call: str = _text(item, "call", where)
        if not call:
            raise ExposedError(f"{where} has no `call`")
        steps.append(
            Step(
                call,
                {str(key): value for key, value in arguments.items()},
                _text(item, "narration", where),
                _text(item, "state", where),
            )
        )
    return Recording(
        _text(table, "title", source),
        _text(table, "outline", source),
        tuple(steps),
        _text(table, "scraftcam", source),
    )


def load(path: Path) -> Recording:
    """Read the recording in `path`.

    Arguments:
    * `path` (`Path`):
        The `.steps.toml` file.

    Returns:
    * (`Recording`): the recording.

    Raises:
    * `ExposedError`: when it is not a recording this code reads.
    * `OSError`: when it cannot be read at all.
    """
    return recording_from_text(path.read_text(encoding="utf-8"), str(path))


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
        return step.narration or exposed.narration(step.call, step.arguments)

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
            if step.state and given.strip() != step.state.strip():
                found.append(
                    f"step {number} ({step.call}): expected\n"
                    f"{step.state.strip()}\ngot\n{given.strip()}"
                )
        return found


def _toml_value(value: object) -> str:
    """Give `value` as a TOML value (a JSON kind, as arguments are).

    Arguments:
    * `value` (`object`):
        A `bool`, `int`, `float`, `str`, or a list of them.

    Returns:
    * (`str`): its TOML text.

    Raises:
    * `ExposedError`: when it is none of those.
    """
    # `bool` before `int`: it is one.  JSON's string escapes are TOML's.
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise ExposedError(f"{value!r} cannot be written to a recording")


def _toml_text(text: str) -> str:
    """Give `text` as a TOML string, multi-line ones kept readable.

    Arguments:
    * `text` (`str`):
        The text.

    Returns:
    * (`str`): a literal `'''` string when it can be one, else a
      basic one.
    """
    if "\n" in text and "'''" not in text:
        return "'''\n" + text.rstrip("\n") + "\n'''"
    return json.dumps(text)


def recording_text(recording: Recording) -> str:
    """Give `recording` as the text of its `.steps.toml` file.

    Arguments:
    * `recording` (`Recording`):
        The recording.

    Returns:
    * (`str`): the text, which `recording_from_text()` reads back.
    """
    # The header, then a table per step (empty fields left out).
    lines: list[str] = [
        f"format = {FORMAT}",
        f"scraftcam = {json.dumps(recording.version or __version__)}",
        f"title = {json.dumps(recording.title)}",
        f"outline = {_toml_text(recording.outline)}",
    ]
    step: Step
    for step in recording.steps:
        pairs: str = ", ".join(
            f"{key} = {_toml_value(value)}"
            for key, value in step.arguments.items()
        )
        lines.extend(("", "[[steps]]", f"call = {json.dumps(step.call)}"))
        lines.append(
            f"arguments = {{ {pairs} }}" if pairs else "arguments = {}"
        )
        if step.narration:
            lines.append(f"narration = {json.dumps(step.narration)}")
        if step.state:
            lines.append(f"state = {_toml_text(step.state)}")
    return "\n".join(lines) + "\n"
