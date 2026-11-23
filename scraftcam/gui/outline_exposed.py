"""The outline editor's functions reached over MCP (#S3, #493).

Importing this module registers them.  Every one runs on Qt's main
thread (the server's `QtRunner` sees to that) and names live objects
by handle (`HANDLES`).  Gestures go through Qt's own events
(`QTest`), so what they hit is tested too (#491), at points in the
drawing's own steps.
"""

from __future__ import annotations

import typing
import weakref

from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError
from scraftcam.exposed.handles import Handles
from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QKeyCombination, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QToolButton, QWidget  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order

if typing.TYPE_CHECKING:
    from scraftcam.gui.dimensions import Dimension
    from scraftcam.gui.letters import Letter
    from scraftcam.gui.outline_editor import (
        Drawing,
        OutlineEditor,
        OutlineView,
    )

# The session's handles (reset when a replay starts).
HANDLES: Handles = Handles()

# The open editors, added by whoever makes one (`outline_editor.main()`
# runs as `__main__`, so its class cannot be imported here to look
# for them).
EDITORS: weakref.WeakSet[object] = weakref.WeakSet()


@exposed.reads
def editors() -> list[str]:
    """List the open outline editors."""
    return sorted(HANDLES.handle(widget) for widget in EDITORS)


def _number(value: float) -> str:
    """Give `value` as short, stable text (`3`, `-1.25`, `0.3333`).

    Arguments:
    * `value` (`float`):
        The number.

    Returns:
    * (`str`): it, to 4 significant places, with no `-0`.
    """
    text: str = f"{value:.4g}"
    return "0" if text == "-0" else text


def _editor(handle: str) -> OutlineEditor:
    """Give the open editor named `handle`.

    Arguments:
    * `handle` (`str`):
        Its handle, as `"OutlineEditor 1"`.

    Returns:
    * (`OutlineEditor`): the editor.

    Raises:
    * `ExposedError`: when no open editor has that handle.
    """
    # The class may be `__main__`'s copy, so only membership counts.
    thing: object = HANDLES.find(handle)
    if thing not in EDITORS:
        raise ExposedError(f"`{handle}` is not an outline editor")
    return typing.cast("OutlineEditor", thing)


@exposed.reads
def state(editor: str) -> str:
    """Describe what {editor} shows."""
    # The file, then the corners in drawing steps.
    shown: OutlineEditor = _editor(editor)
    view: OutlineView = shown.view
    drawing: Drawing = view.drawing
    name: str = "(new)" if shown.path is None else shown.path.name
    lines: list[str] = [
        f"file: {name}",
        f"revolve: {drawing.revolve}",
        "corners:",
    ]
    index: int
    x: float
    y: float
    for index, (x, y) in enumerate(drawing.points):
        lines.append(f"  {index}: ({_number(x)}, {_number(y)})")

    # The dimensions and the letters.
    lines.append("dimensions:")
    dimension: Dimension
    for dimension in drawing.dimensions:
        lines.append(
            f"  {dimension.letter}: {dimension.kind}"
            f" {dimension.start} -> {dimension.end}"
        )
    lines.append("letters:")
    letter: Letter
    for letter in drawing.letters:
        value: str = letter.formula or letter.default
        lines.append(f"  {letter.letter} = {value}")

    # The selection, the problems and the undo depth.
    lines.extend(
        (
            f"chosen corners: {view.chosen_points}",
            f"chosen dimensions: {view.chosen_dimensions}",
            f"chosen edges: {view.chosen_edges}",
            "problems:",
        )
    )
    problem: str
    for problem in shown.problems.text().splitlines():
        lines.append(f"  {problem}")
    lines.append(f"undo depth: {len(view.history.done)}")
    return "\n".join(lines)


def _at(view: OutlineView, x: float, y: float) -> QPoint:
    """Give the viewport pixel showing the drawing point (`x`, `y`).

    Arguments:
    * `view` (`OutlineView`):
        The editor's view.
    * `x` (`float`):
        Across, in drawing steps.
    * `y` (`float`):
        Up, in drawing steps.

    Returns:
    * (`QPoint`): the pixel.
    """
    return view.mapFromScene(QPointF(x, y))


@exposed.changes
def click(editor: str, x: float, y: float) -> str:
    """Click {editor} at ({x}, {y})."""
    # A press and release at one pixel; then the events it caused.
    view: OutlineView = _editor(editor).view
    QTest.mouseClick(
        view.viewport(), Qt.MouseButton.LeftButton, pos=_at(view, x, y)
    )
    QTest.qWait(1)
    return state(editor)


@exposed.changes
def drag(editor: str, x: float, y: float, *, to_x: float, to_y: float) -> str:
    """Drag in {editor} from ({x}, {y}) to ({to_x}, {to_y})."""
    # Pressed, moved through the middle (a drag starts only once the
    # pointer moves), then released.
    view: OutlineView = _editor(editor).view
    start: QPoint = _at(view, x, y)
    end: QPoint = _at(view, to_x, to_y)
    port: QWidget = view.viewport()
    QTest.mousePress(port, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(port, (start + end) / 2)
    QTest.mouseMove(port, end)
    QTest.mouseRelease(port, Qt.MouseButton.LeftButton, pos=end)
    QTest.qWait(1)
    return state(editor)


@exposed.changes
def press(editor: str, keys: str) -> str:
    """Press {keys} in {editor}."""
    # Keys as Qt spells them (`G`, `Delete`, `Ctrl+Z`).
    view: OutlineView = _editor(editor).view
    sequence: QKeySequence = QKeySequence(keys)
    if sequence.isEmpty():
        raise ExposedError(f"`{keys}` names no keys")
    index: int
    for index in range(sequence.count()):
        # PySide6's stubs lack `QKeySequence.__getitem__()`.
        combination: QKeyCombination = sequence[index]  # type: ignore[index]
        QTest.keyClick(
            view, combination.key(), combination.keyboardModifiers()
        )
    QTest.qWait(1)
    return state(editor)


@exposed.changes
def button(editor: str, word: str) -> str:
    """Press [{word}] in {editor}."""
    # Clicked as a user clicks it, so a hidden or disabled one fails
    # as it would for them.
    shown: OutlineEditor = _editor(editor)
    found: QToolButton | None = shown.buttons.get(word)
    if found is None:
        words: str = ", ".join(sorted(shown.buttons))
        raise ExposedError(f"no button [{word}]; there are: {words}")
    if not found.isEnabled():
        raise ExposedError(f"[{word}] is not enabled now")
    found.click()
    QTest.qWait(1)
    return state(editor)
