"""The outline editor's functions reached over MCP (#S3, #493).

Importing this module registers them.  Every one runs on Qt's main
thread (the server's `QtRunner` sees to that) and names live objects
by handle (`HANDLES`).  Gestures go through Qt's own events
(`QTest`), so what they hit is tested too (#491), at points in the
drawing's own steps.
"""

from __future__ import annotations

import re
import time
import typing
import weakref
from pathlib import Path

from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError
from scraftcam.exposed.handles import Handles
from scraftcam.gui.dimensions import ORIGIN
from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
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

# Where `screenshot()` writes its pictures (#567).
SHOTS: Path = Path.home() / ".scraftcam" / "screenshots"

# The open editors, added by whoever makes one (a tool's panel,
# `outline_panel.py`, a tutorial, a test).
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
    corner: str
    x: float
    y: float
    for corner, (x, y) in zip(drawing.names, drawing.points, strict=True):
        lines.append(f"  {corner}: ({_number(x)}, {_number(y)})")

    # The dimensions and the letters.
    lines.append("dimensions:")
    dimension: Dimension
    for dimension in drawing.dimensions:
        lines.append(
            f"  {dimension.letter}: {dimension.kind}"
            f" {drawing.name(dimension.start)}"
            f" -> {drawing.name(dimension.end)}"
        )
    lines.append("letters:")
    letter: Letter
    for letter in drawing.letters:
        value: str = letter.formula or letter.default
        lines.append(f"  {letter.letter} = {value}")

    # The selection, the problems and the undo depth.
    lines.extend(
        (
            "chosen corners: ["
            + ", ".join(
                _code_name(drawing, code) for code in view.chosen_points
            )
            + "]",
            f"chosen dimensions: {view.chosen_dimensions}",
            "chosen edges: ["
            + ", ".join(
                _edge_name(drawing, edge) for edge in view.chosen_edges
            )
            + "]",
            "problems:",
        )
    )
    problem: str
    for problem in shown.values.problems.text().splitlines():
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


def view_of(view: OutlineView) -> tuple[float, float, float]:
    """Give the view a gesture is made in (#566).

    Arguments:
    * `view` (`OutlineView`):
        The editor's view.

    Returns:
    * (`tuple[float, float, float]`): the zoom, in pixels per drawing
      step, and the drawing point at the viewport's centre.
    """
    centre: QPointF = view.mapToScene(view.viewport().rect().center())
    return view.zoom(), centre.x(), centre.y()


def place_view(view: OutlineView, shown: tuple[float, ...]) -> None:
    """Show `view` at a recorded zoom and centre (#566), so that a
    replayed gesture snaps as the recorded one did.

    Arguments:
    * `view` (`OutlineView`):
        The editor's view.
    * `shown` (`tuple[float, ...]`):
        The zoom and the centre's X and Y, as `view_of()` gives them.

    Raises:
    * `ExposedError`: when it is not three numbers, or the zoom is
      not positive.
    """
    # The zoom first (any quarter turns are kept), then the centre.
    if len(shown) != 3 or shown[0] <= 0.0:
        raise ExposedError(f"a view is (zoom, x, y), not {shown!r}")
    zoom: float
    x: float
    y: float
    zoom, x, y = shown
    factor: float = zoom / view.zoom()
    view.scale(factor, factor)
    view.centerOn(QPointF(x, y))
    view.place_handles()


# A target as a step names it (#550): a point by its corner's name
# (#787, #792), or a spot.
TARGET: re.Pattern[str] = re.compile(
    r"^(?:(?P<kind>Vertex|Mirror) (?P<name>[A-Za-z]\w*)|(?P<origin>Origin)"
    r"|(?:background )?\((?P<x>[^,()]+),(?P<y>[^,()]+)\))$"
)


def _spot(value: float) -> str:
    """Give a coordinate as a step writes it (`3`, `-1.25`).

    Arguments:
    * `value` (`float`):
        The coordinate, in drawing steps.

    Returns:
    * (`str`): it, whole numbers without `.0`.
    """
    return str(int(value)) if float(value).is_integer() else repr(value)


def _edge_name(drawing: Drawing, edge: tuple[int, int]) -> str:
    """Give an edge's name, `V1-V2`, or an axis's (#797).

    Arguments:
    * `drawing` (`Drawing`):
        The drawing, for its corners' names.
    * `edge` (`tuple[int, int]`):
        The corners it leaves and reaches, or an axis and -1.

    Returns:
    * (`str`): Its name.
    """
    if edge[0] < 0:
        return drawing.name(edge[0])
    return f"{drawing.names[edge[0]]}-{drawing.names[edge[1]]}"


def _code_name(drawing: Drawing, code: int) -> str:
    """Give a point's name: `Vertex V2`, `Mirror V2` or `Origin`.

    Arguments:
    * `drawing` (`Drawing`):
        The drawing, for its corners' names (#792).
    * `code` (`int`):
        Its code (`OutlineView.corner_near()`).

    Returns:
    * (`str`): its name, as of now (#558).
    """
    # `outline_editor` imports this module's importers: imported late.
    # pylint: disable-next=import-outside-toplevel
    from scraftcam.gui.outline_editor import MIRRORED

    if code == ORIGIN:
        return "Origin"
    if code <= MIRRORED:
        return f"Mirror {drawing.names[MIRRORED - code]}"
    return f"Vertex {drawing.names[code]}"


def target_at(
    view: OutlineView, x: float, y: float, *, skip: int | None = None
) -> tuple[str, int | None]:
    """Name what a gesture at (`x`, `y`) acts on (#550).

    Arguments:
    * `view` (`OutlineView`):
        The editor's view.
    * `x` (`float`):
        Across, in drawing steps.
    * `y` (`float`):
        Up, in drawing steps.
    * `skip` (`int | None`):
        A point not to name (the one being dragged), or `None`.

    Returns:
    * (`tuple[str, int | None]`): `Vertex V2` (or `Mirror V2`,
      `Origin`) and its code, else `background (x, y)` and `None`.
    """
    code: int | None = view.corner_near(QPointF(x, y))
    if code is None or code == skip:
        return f"background ({_spot(x)}, {_spot(y)})", None
    return _code_name(view.drawing, code), code


def _place(view: OutlineView, target: str) -> tuple[QPointF, int | None]:
    """Find where a named target is now.

    Arguments:
    * `view` (`OutlineView`):
        The editor's view.
    * `target` (`str`):
        `Vertex V2`, `Mirror V2`, `Origin`, `background (x, y)` or
        `(x, y)`.

    Returns:
    * (`tuple[QPointF, int | None]`): the drawing point, and the
      point's code (`None` for a spot).

    Raises:
    * `ExposedError`: when it names nothing there is.
    """
    # `outline_editor` imports this module's importers: imported late.
    # pylint: disable-next=import-outside-toplevel
    from scraftcam.gui.outline_editor import mirror_code

    match: re.Match[str] | None = TARGET.match(target.strip())
    if match is None:
        raise ExposedError(
            f"`{target}` is not `Vertex NAME`, `Mirror NAME`, `Origin`"
            " or `(x, y)`"
        )
    if match.group("origin"):
        return QPointF(0.0, 0.0), ORIGIN
    if match.group("kind"):
        if match.group("name") not in view.drawing.names:
            raise ExposedError(
                f"no {target}: the vertices are"
                f" {', '.join(view.drawing.names)}"
            )
        index: int = view.drawing.names.index(match.group("name"))
        x: float
        y: float
        x, y = view.drawing.points[index]
        if match.group("kind") == "Mirror":
            if not view.drawing.revolve:
                raise ExposedError(f"no {target}: the outline is not revolved")
            return QPointF(-x, y), mirror_code(index)
        return QPointF(x, y), index
    try:
        return (
            QPointF(float(match.group("x")), float(match.group("y"))),
            None,
        )
    except ValueError as error:
        raise ExposedError(f"`{target}` has a bad number") from error


def _hit(view: OutlineView, target: str) -> QPointF:
    """Find a target, checking that it is what is there now, so a
    replay acts on what the recording did (#550).

    Arguments:
    * `view` (`OutlineView`):
        The editor's view.
    * `target` (`str`):
        The target, as `_place()` reads it.

    Returns:
    * (`QPointF`): its drawing point.

    Raises:
    * `ExposedError`: when it names nothing, or something else is hit.
    """
    point: QPointF
    code: int | None
    point, code = _place(view, target)
    found: str
    hit: int | None
    found, hit = target_at(view, point.x(), point.y())
    if hit != code:
        raise ExposedError(f"`{target}` is not what is there: {found}")
    return point


@exposed.changes
def click(editor: str, target: str) -> str:
    """Click {target} in {editor}."""
    # A press and release at one pixel; then the events it caused.
    view: OutlineView = _editor(editor).view
    point: QPointF = _hit(view, target)
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        pos=_at(view, point.x(), point.y()),
    )
    QTest.qWait(1)
    return state(editor)


@exposed.changes
def drag(editor: str, target: str, *, to: str) -> str:
    """Drag {target} in {editor} to {to}."""
    # Pressed, moved through the middle (a drag starts only once the
    # pointer moves), then released where the drop is now.
    view: OutlineView = _editor(editor).view
    start_at: QPointF = _hit(view, target)
    drop: QPointF = _place(view, to)[0]
    start: QPoint = _at(view, start_at.x(), start_at.y())
    end: QPoint = _at(view, drop.x(), drop.y())
    port: QWidget = view.viewport()
    QTest.mousePress(port, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(port, (start + end) / 2)
    QTest.mouseMove(port, end)
    QTest.mouseRelease(port, Qt.MouseButton.LeftButton, pos=end)
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


@exposed.changes
def rename(editor: str, name: str) -> str:
    """Type {name} into {editor}'s Vertex field and press Enter,
    renaming the one chosen corner (`T.sa~6.11` #795)."""
    # Through the field, so a greyed one fails as it would for a user.
    shown: OutlineEditor = _editor(editor)
    if not shown.vertex_name.isEnabled():
        raise ExposedError("the Vertex field is greyed: choose one corner")
    corner: int = shown.chosen_corner()
    shown.vertex_name.setText(name)
    shown.vertex_name.returnPressed.emit()
    QTest.qWait(1)
    if shown.drawing.names[corner] != name.strip():
        raise ExposedError(f"not renamed: {shown.view.message}")
    return state(editor)


@exposed.changes
def tab(editor: str, name: str) -> str:
    """Choose the [{name}] tab of {editor}'s drawing: Drawing, SVG or
    Edit (`T.toasl~6.8` #755)."""
    # Chosen as a user chooses it, so a greyed or hidden one fails as
    # it would for them.
    shown: OutlineEditor = _editor(editor)
    names: list[str] = [
        shown.tab_bar.tabText(index) for index in range(shown.tab_bar.count())
    ]
    if name not in names:
        raise ExposedError(f"no tab [{name}]; there are: {', '.join(names)}")
    index: int = names.index(name)
    if not shown.tab_bar.isTabVisible(index):
        raise ExposedError(f"[{name}] is not shown here")
    if not shown.tab_bar.isTabEnabled(index):
        why: str = shown.tab_bar.tabToolTip(index)
        raise ExposedError(f"[{name}] is greyed: {why}")
    shown.tab_bar.setCurrentIndex(index)
    QTest.qWait(1)
    return state(editor)


@exposed.changes
def solid(editor: str) -> str:
    """Press {editor}'s [Solid]: its solid is made (headless, into the
    cache) and shown alone in SolidCraft, which is started if need be
    (`T.sa~6.11` #819, #848).  Returns its state, then the message,
    if any."""
    # Pressed as a user presses it, so a hidden one fails as it would.
    shown: OutlineEditor = _editor(editor)
    if not shown.solid_button.isVisible():
        raise ExposedError("[Solid] is not shown here")
    shown.solid_button.click()
    QTest.qWait(1)
    told: str = shown.view.message
    return state(editor) + (f"\nmessage: {told}" if told else "")


@exposed.changes
def resize(editor: str, width: int, height: int) -> str:
    """Make {editor}'s window `width` by `height` pixels, then fit
    the drawing to it (a headless window starts small, too small to
    point at a long, thin outline's parts; `T.toasl~6.8` #740)."""
    shown: OutlineEditor = _editor(editor)
    if not 200 <= width <= 4000 or not 200 <= height <= 4000:
        raise ExposedError("width and height go from 200 to 4000 pixels")
    shown.window().resize(width, height)
    QTest.qWait(1)
    shown.view.fit()
    return state(editor)


@exposed.reads
def screenshot(editor: str, name: str = "") -> str:
    """Take a picture of {editor}."""
    # The whole window as drawn now, into `SHOTS`; its path comes
    # back, for Claude to look at (#567).
    shown: OutlineEditor = _editor(editor)
    QTest.qWait(1)
    if not name:
        name = time.strftime("%Y-%m-%d_%H-%M-%S")
    if not re.fullmatch(r"[\w.-]+", name) or name.startswith("."):
        raise ExposedError(f"`{name}` is not a plain file name")
    SHOTS.mkdir(parents=True, exist_ok=True)
    path: Path = SHOTS / f"{name.removesuffix('.png')}.png"
    picture: QPixmap = shown.grab()
    if picture.isNull() or not picture.save(str(path), "PNG"):
        raise ExposedError(f"no picture could be written to {path}")
    return str(path)
