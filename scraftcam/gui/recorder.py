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

import dataclasses
import time
import typing
from functools import partial
from pathlib import Path

from scraftcam.exposed import exposed
from scraftcam.exposed.steps import (
    Recording,
    Step,
    View,
    recording_markdown,
)
from scraftcam.gui import outline_exposed
from scraftcam.gui.outline_file import outline_text
from scraftcam.packages import require
from scraftcam.speech import Microphone, Word, split, transcribe

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
        The `.steps.md` file written.
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
    * `waiting` (`tuple[str, dict[str, object], float, View] | None`):
        The step whose gesture is being handled (its call, arguments,
        time and view), filed with its state when the next gesture starts
        or Qt is idle.
    * `microphone` (`Microphone | None`):
        The microphone being recorded, if any.
    * `started` (`float`):
        When recording started (`time.monotonic()`).
    * `began` (`float`):
        When the latest gesture began, in seconds from `started`
        (#522): a step's time, to match it with what was said.
    * `target` (`str`):
        What the held press is on (#550): `Vertex 2`, or
        `background (x, y)`.
    * `code` (`int | None`):
        That point's code, or `None` for the background.
    * `seen` (`View`):
        The view when the latest gesture began (#566), restored
        before its step is replayed.
    """

    def __init__(
        self,
        editor: OutlineEditor,
        path: Path,
        title: str,
        *,
        speech: bool = False,
    ) -> None:
        """Start recording `editor` into `path` (written at once).

        Arguments:
        * `editor` (`OutlineEditor`):
            The editor, as it is to start.
        * `path` (`Path`):
            The `.steps.md` file to write.
        * `title` (`str`):
            The recording's title.
        * `speech` (`bool`):
            True to record the microphone too (beside `path`, as a
            `.wav`), for `finish()` to turn into each step's draft.

        Raises:
        * `OSError`: when the microphone cannot be started.
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
        self.waiting: tuple[str, dict[str, object], float, View] | None = None
        self.seen: View = ()
        self.target: str = ""
        self.code: int | None = None
        # The microphone and the steps share time 0 (#532).
        self.microphone: Microphone | None = (
            Microphone(path.with_suffix(".wav")) if speech else None
        )
        self.started: float = time.monotonic()
        self.began: float = 0.0

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
            self.began = time.monotonic() - self.started
            self.seen = outline_exposed.view_of(self.editor.view)

        # A press is held until its release says click or drag.
        if (
            watched is self.port
            and isinstance(event, QMouseEvent)
            and event.button() == Qt.MouseButton.LeftButton
        ):
            at: QPoint = event.position().toPoint()
            if event.type() == QEvent.Type.MouseButtonPress:
                # Named before the press can move or renumber it.
                self.pressed = at
                x: float
                y: float
                x, y = self.scene(at)
                self.target, self.code = outline_exposed.target_at(
                    self.editor.view, x, y
                )
            elif (
                event.type() == QEvent.Type.MouseButtonRelease
                and self.pressed is not None
            ):
                start: QPoint = self.pressed
                self.pressed = None
                moved: int = (at - start).manhattanLength()
                if moved <= QApplication.startDragDistance():
                    self.later("click", {"target": self.target})
                else:
                    # The drop names another point, never the one
                    # dragged there.
                    to_x: float
                    to_y: float
                    to_x, to_y = self.scene(at)
                    to: str = outline_exposed.target_at(
                        self.editor.view, to_x, to_y, skip=self.code
                    )[0]
                    self.later(
                        "drag",
                        {
                            "target": self.target,
                            "to": to.removeprefix("background "),
                        },
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
        self.waiting = (call, dict(arguments), self.began, self.seen)
        QTimer.singleShot(0, self.file)

    def file(self) -> None:
        """Add the waiting step, if any, with the state now, and write
        the file."""
        if self.waiting is not None:
            call: str
            arguments: dict[str, object]
            began: float
            seen: View
            call, arguments, began, seen = self.waiting
            self.waiting = None
            arguments = self.snapped(call, arguments)
            state: str = outline_exposed.state(self.handle)
            # A placeholder for the person to rewrite (#520).
            placeholder: str = exposed.narration(
                call, {**arguments, "editor": "the editor"}
            )
            self.steps.append(
                Step(call, arguments, placeholder, state, "", began, seen)
            )
            self.write()

    def snapped(
        self, call: str, arguments: dict[str, object]
    ) -> dict[str, object]:
        """Give a vertex dropped on nothing the point it snapped to
        (#550), once Qt has handled the drop.

        Arguments:
        * `call` (`str`):
            The step's exposed function.
        * `arguments` (`dict[str, object]`):
            Its arguments.

        Returns:
        * (`dict[str, object]`): them, a drop's `to` the vertex's
          place now.
        """
        # Only a drag of a vertex (code >= 0) to a bare spot.
        to: object = arguments.get("to")
        code: int | None = self.code
        points: list[tuple[float, float]] = self.editor.view.drawing.points
        if (
            call != "drag"
            or not isinstance(to, str)
            or not to.startswith("(")
            or code is None
            or not 0 <= code < len(points)
        ):
            return arguments
        x: float
        y: float
        x, y = points[code]
        spot: str = outline_exposed.target_at(
            self.editor.view, round(x, PLACES), round(y, PLACES), skip=code
        )[0]
        return {**arguments, "to": spot.removeprefix("background ")}

    def finish(self) -> str:
        """Stop the microphone, if any, and give each step the words
        spoken since the step before it as its draft (#532).

        Returns:
        * (`str`): what was done, for the person.
        """
        # A step with nothing said keeps its placeholder.
        self.file()
        if self.microphone is None:
            return f"Recorded {len(self.steps)} steps into {self.path}"
        self.microphone.stop()
        sound: Path = self.microphone.path
        words: list[Word] = transcribe(sound)
        texts: list[str] = split(words, [step.time for step in self.steps])
        index: int
        text: str
        for index, text in enumerate(texts):
            if text:
                self.steps[index] = dataclasses.replace(
                    self.steps[index], narration=text
                )
        self.write()
        return (
            f"Recorded {len(self.steps)} steps and {len(words)} words "
            f"into {self.path} (the sound is in {sound.name})"
        )

    def write(self) -> None:
        """Write the recording as it is now."""
        recording: Recording = Recording(
            self.title, "", self.outline, tuple(self.steps)
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(recording_markdown(recording), encoding="utf-8")
