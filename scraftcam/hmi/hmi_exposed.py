"""The HMI's functions reached over MCP (`T.og~6.9` #604).

They replace the HMI's own line port (now gone, `--hmi-port`):
the one GUI serves a single MCP port (#577, #608).  Importing this
module registers them; `scraftcam.run --program` does so, and adds
the HMI it makes to `HMIS`.  Each one hands its words to the HMI's
line handler (`HMI.handle()`), so it behaves exactly as the port
did, and turns an `error: ...` answer into an `ExposedError`.
"""

from __future__ import annotations

import json
import typing
import weakref

from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError
from scraftcam.exposed.handles import Handles

if typing.TYPE_CHECKING:
    from scraftcam.hmi.machine_panel import HMI

# The session's handles, and the HMIs (the machine panels' controls).
HANDLES: Handles = Handles()
HMIS: weakref.WeakSet[object] = weakref.WeakSet()


# Function `_hmi()`:
def _hmi(handle: str) -> HMI:
    """Give the HMI named `handle`.

    Arguments:
    * `handle` (`str`): Its handle, as `"HMI 1"`.

    Returns:
    * (`HMI`): The HMI.

    Raises:
    * `ExposedError`: When no HMI has that handle.
    """
    thing: object = HANDLES.find(handle)
    if thing not in HMIS:
        raise ExposedError(f"`{handle}` is not an HMI")
    return typing.cast("HMI", thing)


# Function `_may_move()`:
def _may_move(hmi: HMI) -> None:
    """Refuse a call that moves a real machine (`T.mi~7` #489).

    Every machine is a simulator today (LinuxCNC's, or `--dry-run`),
    so none is refused; this is the one place a real one will be.

    Arguments:
    * `hmi` (`HMI`): The HMI the call would move.
    """
    del hmi


# Function `_line()`:
def _line(handle: str, line: str, *, moves: bool = False) -> str:
    """Hand `line` to the HMI's line handler.

    Arguments:
    * `handle` (`str`): The HMI's handle.
    * `line` (`str`): The words, as the old port took them.
    * `moves` (`bool`): True when it may move the machine.

    Returns:
    * (`str`): The answer.

    Raises:
    * `ExposedError`: When the answer is `error: ...`.
    """
    hmi: HMI = _hmi(handle)
    if moves:
        _may_move(hmi)
    answer: str = hmi.handle(line)
    if answer.startswith("error: "):
        raise ExposedError(answer.removeprefix("error: "))
    return answer


# Function `hmis()`:
@exposed.reads
def hmis() -> list[str]:
    """List the machine panels' HMIs."""
    return sorted(HANDLES.handle(hmi) for hmi in HMIS)


# Function `hmi_show()`:
@exposed.reads
def hmi_show(hmi: str) -> dict[str, object]:
    """Tell what {hmi} shows: its G-code, position, buttons, texts."""
    shown: object = json.loads(_line(hmi, "show"))
    assert isinstance(shown, dict)
    return shown


# Function `hmi_status()`:
@exposed.reads
def hmi_status(hmi: str) -> str:
    """Tell {hmi}'s machine state: file, line, position, tool."""
    return _line(hmi, "status")


# Function `hmi_messages()`:
@exposed.reads
def hmi_messages(hmi: str) -> str:
    """Give {hmi}'s machine messages."""
    return _line(hmi, "messages")


# Function `hmi_log()`:
@exposed.reads
def hmi_log(hmi: str) -> str:
    """Give {hmi}'s machine log."""
    return _line(hmi, "log")


# Function `hmi_press()`:
@exposed.changes
def hmi_press(hmi: str, label: str) -> str:
    """Press {label} in {hmi}, as a person would."""
    return _line(hmi, f"press {label}", moves=True)


# Function `hmi_origin()`:
@exposed.changes
def hmi_origin(hmi: str, axis: str, value: str) -> str:
    """Type {value} as {hmi}'s {axis} origin."""
    return _line(hmi, f"origin {axis} {value}")


# Function `hmi_tab()`:
@exposed.changes
def hmi_tab(hmi: str, name: str) -> str:
    """Show {hmi}'s {name} tab."""
    return _line(hmi, f"tab {name}")


# Function `hmi_type()`:
@exposed.changes
def hmi_type(hmi: str, text: str) -> str:
    """Type {text} into {hmi}'s MDI line."""
    return _line(hmi, f"type {text}")


# Function `hmi_open()`:
@exposed.changes
def hmi_open(hmi: str, path: str) -> str:
    """Open the G-code {path} in {hmi}."""
    return _line(hmi, f"open {path}")


# Function `hmi_speed()`:
@exposed.changes
def hmi_speed(hmi: str, speed: float) -> str:
    """Set {hmi}'s speed to {speed}."""
    return _line(hmi, f"speed {speed}", moves=True)


# Function `hmi_line()`:
@exposed.changes
def hmi_line(hmi: str, line: str) -> str:
    """Send {line} to {hmi}, in the old line port's words, and give
    its answer as it is (`ok`, `error: ...`, JSON for `show`): for the
    LinuxCNC end-to-end tests (#608)."""
    found: HMI = _hmi(hmi)
    _may_move(found)
    return found.handle(line)


# Function `hmi_answer()`:
@exposed.changes
def hmi_answer(hmi: str, answer: str) -> str:
    """Queue {answer} for {hmi}'s next question (headless, until the
    in-panel prompts of #606)."""
    return _line(hmi, f"answer {answer}")
