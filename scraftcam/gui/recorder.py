"""Recording what a user does in the outline editor (#21, #496).

`--record` writes the user's own gestures as the steps of a
recording, so a tutorial (or a bug report) is made by doing it: a
left click or drag in the drawing (`click`, `drag`), a key that
fires a shortcut (`press`), a button clicked (`button`).  Each step
keeps the state after it, and the file is written after every step,
so nothing is lost if the editor dies.

Not recorded yet: the letters table's edits, the wheel and panning
(points are kept in drawing steps, so a replay hits the same thing
at any zoom), modifier keys held while clicking.
"""

from __future__ import annotations

import typing
from functools import partial
from pathlib import Path

from scraftcam.exposed.steps import Recording, Step, recording_text
from scraftcam.gui import outline_exposed
from scraftcam.gui.outline_file import outline_text
from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
import shiboken6  # noqa: E402
from PySide6.QtCore import (  # noqa: E402
    QCoreApplication,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    Qt,
    QTimer,
)
from PySide6.QtGui import QAction, QMouseEvent, QShortcut  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton, QWidget  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order

if typing.TYPE_CHECKING:
    from scraftcam.gui.outline_editor import OutlineEditor

# The events that start a gesture (a shortcut's key comes first as
# `ShortcutOverride`).
STARTS: frozenset[QEvent.Type] = frozenset(
    (
        QEvent.Type.MouseButtonPress,
        QEvent.Type.KeyPress,
        QEvent.Type.ShortcutOverride,
    )
)

# Places kept in a recorded point (drawing steps).
PLACES: int = 3


class Recorder(QObject):  # pylint: disable=too-many-instance-attributes
    """Writes an editor's gestures to a recording as they happen.

    Attributes:
    * `editor` (`OutlineEditor`):
        The editor watched.
    * `handle` (`str`):
        Its handle, for the state after each step.
    * `path` (`Path`):
        The `.steps.toml` file written.
    * `title` (`str`):
        The recording's title.
    * `outline` (`str`):
        The outline file as it was when recording started.
    * `steps` (`list[Step]`):
        The steps so far.
    * `port` (`QWidget`):
        The drawing's viewport, whose mouse is recorded.
    * `pressed` (`QPoint | None`):
        Where the left button went down in the viewport, while held.
    * `waiting` (`tuple[str, dict[str, object]] | None`):
        The step whose gesture is being handled, filed with its state
        when the next gesture starts or Qt is idle.
    """

    def __init__(self, editor: OutlineEditor, path: Path, title: str) -> None:
        """Start recording `editor` into `path` (written at once).

        Arguments:
        * `editor` (`OutlineEditor`):
            The editor, as it is to start.
        * `path` (`Path`):
            The `.steps.toml` file to write.
        * `title` (`str`):
            The recording's title.
        """
        # The editor by handle, as replays reach it.
        super().__init__(editor)
        outline_exposed.EDITORS.add(editor)
        self.editor: OutlineEditor = editor
        self.handle: str = outline_exposed.HANDLES.handle(editor)
        self.path: Path = path
        self.title: str = title
        self.outline: str = outline_text(editor.view.drawing)
        self.steps: list[Step] = []
        self.pressed: QPoint | None = None
        self.waiting: tuple[str, dict[str, object]] | None = None

        # Every event (a new gesture files the last step), the
        # drawing's mouse, each shortcut and each button.
        self.port: QWidget = editor.view.viewport()
        application: QCoreApplication | None = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)
            editor.destroyed.connect(
                partial(application.removeEventFilter, self)
            )
        shortcut: QShortcut
        for shortcut in editor.keys.values():
            shortcut.activated.connect(
                partial(
                    self.later, "press", {"keys": shortcut.key().toString()}
                )
            )
        words: dict[QAction, str] = {
            action: word for word, action in editor.button_actions.items()
        }
        button: QToolButton
        for button in editor.findChildren(QToolButton):
            word: str | None = words.get(button.defaultAction())
            if word is not None:
                button.clicked.connect(
                    partial(self.later, "button", {"word": word})
                )
        self.write()

    def eventFilter(  # pylint: disable=invalid-name
        self, watched: QObject, event: QEvent
    ) -> bool:
        """File the waiting step as a new gesture starts; turn the
        drawing's left button press and release into a step.

        Arguments:
        * `watched` (`QObject`):
            Whatever the event is for.
        * `event` (`QEvent`):
            The event, which the view still gets.

        Returns:
        * (`bool`): False: nothing is taken from the view.
        """
        # Nothing once Qt has deleted the editor's view.
        # (`shiboken6` is compiled: pylint cannot see its members.)
        if not shiboken6.isValid(self.port):  # pylint: disable=no-member
            return False

        # A new gesture starts after the last one was handled whole.
        if event.type() in STARTS:
            self.file()

        # A press is held until its release says click or drag.
        if (
            watched is self.port
            and isinstance(event, QMouseEvent)
            and event.button() == Qt.MouseButton.LeftButton
        ):
            at: QPoint = event.position().toPoint()
            if event.type() == QEvent.Type.MouseButtonPress:
                self.pressed = at
            elif (
                event.type() == QEvent.Type.MouseButtonRelease
                and self.pressed is not None
            ):
                start: QPoint = self.pressed
                self.pressed = None
                x: float
                y: float
                x, y = self.scene(start)
                moved: int = (at - start).manhattanLength()
                if moved <= QApplication.startDragDistance():
                    self.later("click", {"x": x, "y": y})
                else:
                    to_x: float
                    to_y: float
                    to_x, to_y = self.scene(at)
                    self.later(
                        "drag", {"x": x, "y": y, "to_x": to_x, "to_y": to_y}
                    )
        return super().eventFilter(watched, event)

    def scene(self, pixel: QPoint) -> tuple[float, float]:
        """Give the drawing point under a viewport pixel.

        Arguments:
        * `pixel` (`QPoint`):
            The pixel.

        Returns:
        * (`tuple[float, float]`): the point, in drawing steps, to
          `PLACES` places.
        """
        point: QPointF = self.editor.view.mapToScene(pixel)
        return round(point.x(), PLACES), round(point.y(), PLACES)

    def later(self, call: str, arguments: dict[str, object]) -> None:
        """Add a step once Qt has finished handling its gesture: when
        the next gesture starts, or Qt is idle, whichever is first.

        Arguments:
        * `call` (`str`):
            The exposed function that replays it.
        * `arguments` (`dict[str, object]`):
            Its arguments, but for the editor.
        """
        self.file()
        self.waiting = (call, dict(arguments))
        QTimer.singleShot(0, self.file)

    def file(self) -> None:
        """Add the waiting step, if any, with the state now, and write
        the file."""
        if self.waiting is not None:
            call: str
            arguments: dict[str, object]
            call, arguments = self.waiting
            self.waiting = None
            state: str = outline_exposed.state(self.handle)
            self.steps.append(Step(call, arguments, "", state))
            self.write()

    def write(self) -> None:
        """Write the recording as it is now."""
        recording: Recording = Recording(
            self.title, self.outline, tuple(self.steps)
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(recording_text(recording), encoding="utf-8")
