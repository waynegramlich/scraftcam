"""The [Fillets] tab of the outline editor (#142.2).

It shows the selected corners: an "All" row, a line, then a row per
corner, numbered 1 to N in the order they were selected (a name for
the moment, #209).
Each row is a row of buttons, one down: [No fillet], the note letter
(`UDF`) and each fillet letter in use.  A press applies at once, one
change each.  Pointing at or clicking a row lights its corner on the
drawing; pointing at a corner frames its row (#199).
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..packages import require

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtGui import QEnterEvent, QMouseEvent  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

if TYPE_CHECKING:
    from .outline_editor import OutlineView

# The label of the row setting every corner at once.
ALL: str = "All"

# What the tab says while no corner is selected.
EMPTY: str = "Select corners on the drawing to fillet them here."

# The button that makes a corner sharp.
NO_FILLET: str = "No fillet"

# The note's letter (#120): "All undimensioned fillets are radius UDF".
NOTE_LETTER: str = "UDF"

# The note letter's choice, standing for it before it is made.
NOTE_CHOICE: str = "*note*"


# Class `FilletPanel`:
class FilletPanel(QWidget):
    """The [Fillets] tab: buttons choosing each selected corner's
    fillet, made again whenever the selection changes.

    Attributes:
    * `view` (`OutlineView`): The drawing's view.
    * `corners` (`list[int]`): The corners shown, in the order
      selected.
    * `rows` (`dict[str, list[QPushButton]]`): Each row's buttons, by
      row label (`ALL`, or the corner's index as text).
    * `frames` (`dict[str, Row]`): Each row, by the same labels.
    * `letters` (`list[str]`): The buttons' letters (`choices()` when
      the corners were shown), kept while letters come and go out of
      use.
    * `body` (`QWidget`): The rows (or the `EMPTY` text), replaced
      whole for each new selection.
    * `stack` (`QVBoxLayout`): The tab's layout, holding `body`.
    """

    # Method `FilletPanel.__init__()`:
    def __init__(self, view: "OutlineView") -> None:
        """Make the tab, showing no corners yet.

        Arguments:
        * `view` (`OutlineView`): The drawing's view.
        """
        super().__init__()
        self.view: OutlineView = view
        self.corners: list[int] = []
        self.rows: dict[str, list[QPushButton]] = {}
        self.frames: dict[str, Row] = {}
        self.letters: list[str] = []
        self.body: QWidget = QWidget()
        self.stack: QVBoxLayout = QVBoxLayout(self)
        self.stack.addWidget(self.body)
        self.stack.addStretch(1)
        self.show_corners([], force=True)

    # Method `FilletPanel.show_corners()`:
    def show_corners(self, corners: list[int], *, force: bool = False) -> None:
        """Show rows for some corners (only if they changed, so a press
        never deletes the button being pressed).

        Arguments:
        * `corners` (`list[int]`): The selected corners.
        * `force` (`bool`): Whether to make the rows even so.
        """
        ordered: list[int] = list(dict.fromkeys(corners))
        if ordered == self.corners and not force:
            self.show_choices()
            return
        self.corners = ordered
        self.rows = {}
        self.frames = {}
        self.letters = self.choices()
        old: QWidget = self.body
        self.body = QWidget()
        self.stack.replaceWidget(old, self.body)
        old.deleteLater()
        self.build()

    # Method `FilletPanel.choices()`:
    def choices(self) -> list[str]:
        """Return the buttons' letters: "" for [No fillet], then the
        note letter, then each other fillet letter in use.

        Returns:
        * (`list[str]`): The letters.
        """
        note: str = self.view.drawing.note_radius or NOTE_CHOICE
        return ["", note] + [
            letter
            for letter in self.view.fillet_letters()
            if letter != self.view.drawing.note_radius
        ]

    # Method `FilletPanel.build()`:
    def build(self) -> None:
        """Lay out the "All" row, a line under it, then a row of
        buttons per corner, numbered from 1."""
        stack: QVBoxLayout = QVBoxLayout(self.body)
        stack.setContentsMargins(0, 0, 0, 0)
        if not self.corners:
            stack.addWidget(QLabel(EMPTY))
            return
        labels: list[str] = [ALL] + [str(corner) for corner in self.corners]
        number: int
        label: str
        for number, label in enumerate(labels):
            row: Row = Row(self, -1 if label == ALL else int(label))
            line: QHBoxLayout = QHBoxLayout(row)
            line.setContentsMargins(4, 2, 4, 2)
            line.addWidget(QLabel(f"{ALL if label == ALL else number}:"))
            buttons: list[QPushButton] = []
            choice: str
            for choice in self.letters:
                button: QPushButton = QPushButton(self.shown(choice))
                button.setCheckable(True)
                button.clicked.connect(self.pressed(label, choice))
                line.addWidget(button)
                buttons.append(button)
            line.addStretch(1)
            stack.addWidget(row)
            self.rows[label] = buttons
            self.frames[label] = row
            if label == ALL:
                rule: QFrame = QFrame()
                rule.setFrameShape(QFrame.Shape.HLine)
                stack.addWidget(rule)
        self.show_choices()

    # Method `FilletPanel.light()`:
    def light(self, corner: int) -> None:
        """Frame the row of a corner (none for -1), so it is told apart
        without color (#124): its corner on the drawing is lit too.

        Arguments:
        * `corner` (`int`): The corner, or -1.
        """
        label: str
        row: Row
        for label, row in self.frames.items():
            lit: bool = label == str(corner)
            row.setFrameShape(
                QFrame.Shape.Box if lit else QFrame.Shape.NoFrame
            )
            row.setLineWidth(2 if lit else 0)

    # Method `FilletPanel.shown()`:
    def shown(self, choice: str) -> str:
        """Return a button's text.

        Arguments:
        * `choice` (`str`): Its letter ("" for none).

        Returns:
        * (`str`): The text.
        """
        if not choice:
            return NO_FILLET
        if choice == NOTE_CHOICE:
            return NOTE_LETTER
        return choice

    # Method `FilletPanel.pressed()`:
    def pressed(self, label: str, choice: str) -> Callable[[], None]:
        """Return what a button does when pressed.

        Arguments:
        * `label` (`str`): Its row.
        * `choice` (`str`): Its letter.

        Returns:
        * (`Callable[[], None]`): The slot.
        """

        # Function `press()`:
        def press() -> None:
            self.choose(label, choice)

        return press

    # Method `FilletPanel.choose()`:
    def choose(self, label: str, choice: str) -> None:
        """Give a row's corners (every corner for "All") a fillet.

        Arguments:
        * `label` (`str`): The row.
        * `choice` (`str`): The letter ("" for none).
        """
        corners: list[int] = self.corners if label == ALL else [int(label)]
        self.view.set_fillets(corners, choice)
        self.show_choices()

    # Method `FilletPanel.show_choices()`:
    def show_choices(self) -> None:
        """Press down each row's button for its corner's fillet; the
        "All" row's only when every corner has the same."""
        now: dict[int, str] = self.view.fillets()
        note: str = self.view.drawing.note_radius
        # The note letter's button stands for it before it is made.
        held: dict[str, str] = {
            str(corner): now.get(corner, "") for corner in self.corners
        }
        alike: set[str] = set(held.values())
        held[ALL] = alike.pop() if len(alike) == 1 else "-"
        label: str
        buttons: list[QPushButton]
        for label, buttons in self.rows.items():
            button: QPushButton
            choice: str
            for button, choice in zip(buttons, self.letters, strict=True):
                letter: str = note if choice == NOTE_CHOICE else choice
                button.setChecked(held[label] == letter)


# Class `Row`:
class Row(QFrame):
    """One corner's row of [Fillets]: pointing at it or clicking it
    lights its corner on the drawing (#199).

    Attributes:
    * `panel` (`FilletPanel`): The tab.
    * `corner` (`int`): The corner (-1 for the "All" row).
    """

    # Method `Row.__init__()`:
    def __init__(self, panel: FilletPanel, corner: int) -> None:
        """Make an empty row.

        Arguments:
        * `panel` (`FilletPanel`): The tab.
        * `corner` (`int`): The corner (-1 for the "All" row).
        """
        super().__init__()
        self.panel: FilletPanel = panel
        self.corner: int = corner

    # Method `Row.enterEvent()`:
    def enterEvent(self, event: QEnterEvent) -> None:
        """Light the corner while the pointer is on the row."""
        self.panel.view.light(self.corner)
        super().enterEvent(event)

    # Method `Row.leaveEvent()`:
    def leaveEvent(self, event: QEvent) -> None:
        """Put the corner out when the pointer leaves."""
        self.panel.view.light(-1)
        super().leaveEvent(event)

    # Method `Row.mousePressEvent()`:
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Light the corner on a click too."""
        self.panel.view.light(self.corner)
        super().mousePressEvent(event)
