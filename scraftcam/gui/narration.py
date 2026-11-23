"""The narration panel: a recording's steps, played (#S4, #499).

A panel at the bottom of a window, never a pop-up: the steps' lines,
the next one picked out, and [Backward], [Forward] and [Play] /
[Pause].  [Forward] runs the next step's real call (a gesture goes
through Qt's events); [Backward] undoes it.  The user may use the
window themselves at any time.
"""

from __future__ import annotations

from scraftcam.exposed.exposed import ExposedError
from scraftcam.exposed.steps import Player
from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

# Milliseconds between steps while playing.
PACE: int = 1500


class NarrationPanel(QWidget):  # pylint: disable=too-many-instance-attributes
    """Shows a recording's steps and plays them.

    Attributes:
    * `player` (`Player`):
        Runs the steps.
    * `title` (`QLabel`):
        The recording's title, then any step's error.
    * `lines` (`QListWidget`):
        One row per step; the next to run is the current row.
    * `backward` (`QPushButton`):
        Undoes the last step run.
    * `forward` (`QPushButton`):
        Runs the next step.
    * `play` (`QPushButton`):
        [Play] runs a step every `PACE` ms; [Pause] stops it.
    * `timer` (`QTimer`):
        Drives [Play].
    """

    def __init__(self, player: Player) -> None:
        """Make the panel, before the first step.

        Arguments:
        * `player` (`Player`):
            Runs the recording's steps.
        """
        # The title and a row for each step.
        super().__init__()
        self.player: Player = player
        self.title: QLabel = QLabel(player.recording.title)
        self.lines: QListWidget = QListWidget()
        index: int
        for index in range(len(player.recording.steps)):
            self.lines.addItem(f"{index + 1}. {player.narration(index)}")
        self.lines.setMaximumHeight(120)

        # The buttons, under the lines.
        self.backward: QPushButton = QPushButton("Backward")
        self.forward: QPushButton = QPushButton("Forward")
        self.play: QPushButton = QPushButton("Play")
        self.backward.clicked.connect(self.step_backward)
        self.forward.clicked.connect(self.step_forward)
        self.play.clicked.connect(self.toggle_play)
        self.timer: QTimer = QTimer(self)
        self.timer.setInterval(PACE)
        self.timer.timeout.connect(self.step_forward)
        buttons: QHBoxLayout = QHBoxLayout()
        button: QPushButton
        for button in (self.backward, self.forward, self.play):
            buttons.addWidget(button)
        buttons.addStretch()
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title)
        layout.addWidget(self.lines)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        """Pick out the next step and enable the buttons that apply."""
        steps: int = len(self.player.recording.steps)
        self.lines.setCurrentRow(min(self.player.done, steps - 1))
        self.backward.setEnabled(self.player.done > 0)
        self.forward.setEnabled(self.player.done < steps)
        if self.player.done >= steps:
            self.timer.stop()
        self.play.setText("Pause" if self.timer.isActive() else "Play")
        self.play.setEnabled(self.player.done < steps)

    def step_forward(self) -> None:
        """Run the next step, showing any error in the title."""
        try:
            self.player.forward()
            self.title.setText(self.player.recording.title)
        except ExposedError as error:
            self.timer.stop()
            self.title.setText(f"Step {self.player.done + 1}: {error}")
        self.refresh()

    def step_backward(self) -> None:
        """Undo the last step run."""
        self.timer.stop()
        try:
            self.player.backward()
        except ExposedError as error:
            self.title.setText(str(error))
        self.refresh()

    def toggle_play(self) -> None:
        """Start or stop running a step every `PACE` ms."""
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start()
        self.refresh()
