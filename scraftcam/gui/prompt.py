"""Prompts inside a panel, never over the whole screen (`T.og~6.9` #606).

A question, a choice, a file to open or a form (any `QDialog`) is
shown inside the rectangle where the user must go to answer it (a
panel, the HMI, the letters table, ...): a grey layer covers that
widget, the dialog sits in its middle, and only that widget waits.
The rest of the GUI stays usable; nothing grabs all of the input.

`run_in()` hosts any `QDialog` and gives back its result, waiting in
a local event loop, so a caller reads as it did with `exec()`;
`show_in()` hosts one that acts by itself (a form), without waiting.
The helpers `ask_yes_no()`, `ask_item()`, `ask_open_file()` and
`ask_directory()` build the usual dialogs for it.  Answers queued in
`ANSWERS` (tests, Claude over MCP) are taken first, in order, with
no dialog shown.
"""

from __future__ import annotations

from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QEvent, QEventLoop, QObject, Qt  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QPaintEvent  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

# The grey laid over the widget that waits (alpha of 255).
SHADE: QColor = QColor(0, 0, 0, 110)

# Answers given ahead, taken by the next questions in order: "yes" or
# "no", a choice, a file or directory ("" for Cancel).
ANSWERS: list[str] = []


# Class `Shade`:
class Shade(QWidget):
    """The grey layer over the widget that waits, holding the dialog.

    It covers its parent exactly, following its resizes, and takes
    every click on it, so the widget under it cannot be used.

    Attributes:
    * `host` (`QWidget`): The widget it covers.
    """

    def __init__(self, host: QWidget, dialog: QDialog) -> None:
        """Cover `host`, and put `dialog` in the middle.

        Arguments:
        * `host` (`QWidget`): The widget that waits.
        * `dialog` (`QDialog`): The dialog, made a plain widget here.
        """
        super().__init__(host)
        self.host: QWidget = host
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog.setWindowFlags(Qt.WindowType.Widget)
        dialog.setAutoFillBackground(True)
        layout.addWidget(dialog, 0, Qt.AlignmentFlag.AlignCenter)
        self.setGeometry(host.rect())
        host.installEventFilter(self)
        self.show()
        self.raise_()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Follow the host's size.

        Arguments:
        * `watched` (`QObject`): The host.
        * `event` (`QEvent`): Any of its events.

        Returns:
        * (`bool`): False, so the host gets the event too.
        """
        if watched is self.host and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.host.rect())
        return super().eventFilter(watched, event)

    def paintEvent(self, _event: QPaintEvent) -> None:
        """Grey the host under it.

        Arguments:
        * `_event` (`QPaintEvent`): The paint (unused).
        """
        painter: QPainter = QPainter(self)
        painter.fillRect(self.rect(), SHADE)
        painter.end()


# Function `run_in()`:
def run_in(host: QWidget, dialog: QDialog) -> int:
    """Show `dialog` inside `host`, and wait for its answer there.

    Arguments:
    * `host` (`QWidget`): The widget where the answer is given.
    * `dialog` (`QDialog`): The dialog (a question, a form, ...).

    Returns:
    * (`int`): Its result (`QDialog.DialogCode.Accepted`, ...).
    """
    # Only this widget waits: a local loop, ended by the dialog.
    shade: Shade = Shade(host, dialog)
    loop: QEventLoop = QEventLoop()
    dialog.finished.connect(loop.quit)
    host.destroyed.connect(loop.quit)
    dialog.show()
    dialog.setFocus()
    loop.exec()
    result: int = dialog.result()
    shade.hide()
    shade.deleteLater()
    return result


# Function `show_in()`:
def show_in(host: QWidget, dialog: QDialog) -> None:
    """Show `dialog` inside `host`, not waiting: it acts by itself
    (a form's [Create]), and its shade goes when it closes.

    Arguments:
    * `host` (`QWidget`): The widget where it is filled in.
    * `dialog` (`QDialog`): The dialog.
    """
    shade: Shade = Shade(host, dialog)
    dialog.finished.connect(shade.hide)
    dialog.finished.connect(shade.deleteLater)
    dialog.show()
    dialog.setFocus()


# Function `ask_yes_no()`:
def ask_yes_no(host: QWidget, title: str, message: str) -> bool:
    """Ask a yes or no question inside `host` (No by default).

    Arguments:
    * `host` (`QWidget`): Where it is asked.
    * `title` (`str`): Its title, bold over the message.
    * `message` (`str`): The question.

    Returns:
    * (`bool`): True for Yes.
    """
    if ANSWERS:
        return ANSWERS.pop(0) == "yes"
    box: QMessageBox = QMessageBox(host)
    box.setText(f"<b>{title}</b>")
    box.setInformativeText(message)
    yes: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes
    no: QMessageBox.StandardButton = QMessageBox.StandardButton.No
    box.setStandardButtons(yes | no)
    box.setDefaultButton(no)
    run_in(host, box)
    return box.standardButton(box.clickedButton()) == yes


# Function `ask_item()`:
def ask_item(
    host: QWidget, title: str, label: str, items: list[str]
) -> str | None:
    """Ask for one of `items` inside `host`.

    Arguments:
    * `host` (`QWidget`): Where it is asked.
    * `title` (`str`): Its title.
    * `label` (`str`): What to choose.
    * `items` (`list[str]`): The choices, the first chosen to start.

    Returns:
    * (`str | None`): The choice, or `None` when cancelled.
    """
    if ANSWERS:
        answer: str = ANSWERS.pop(0)
        return answer if answer in items else None
    box: QInputDialog = QInputDialog(host)
    box.setWindowTitle(title)
    box.setLabelText(label)
    box.setComboBoxItems(items)
    box.setComboBoxEditable(False)
    if run_in(host, box) != QDialog.DialogCode.Accepted:
        return None
    return box.textValue()


# Function `ask_open_file()`:
def ask_open_file(
    host: QWidget, title: str, filters: str, start: str = ""
) -> str:
    """Ask for a file to open inside `host`.

    Arguments:
    * `host` (`QWidget`): Where it is asked.
    * `title` (`str`): Its title.
    * `filters` (`str`): Qt's name filters (`"G-code (*.ngc)"`).
    * `start` (`str`): Where it starts.

    Returns:
    * (`str`): The file, or "" when cancelled.
    """
    return _ask_path(
        host,
        title,
        filters,
        QFileDialog.FileMode.ExistingFile,
        start=start,
    )


# Function `ask_directory()`:
def ask_directory(host: QWidget, title: str, start: str = "") -> str:
    """Ask for a directory inside `host`.

    Arguments:
    * `host` (`QWidget`): Where it is asked.
    * `title` (`str`): Its title.
    * `start` (`str`): Where it starts.

    Returns:
    * (`str`): The directory, or "" when cancelled.
    """
    return _ask_path(
        host, title, "", QFileDialog.FileMode.Directory, start=start
    )


# Function `_ask_path()`:
def _ask_path(
    host: QWidget,
    title: str,
    filters: str,
    mode: QFileDialog.FileMode,
    *,
    start: str = "",
) -> str:
    """Ask for a file or directory inside `host`.

    Arguments:
    * `host` (`QWidget`): Where it is asked.
    * `title` (`str`): Its title.
    * `filters` (`str`): Qt's name filters, or "".
    * `mode` (`QFileDialog.FileMode`): A file, or a directory.
    * `start` (`str`): Where it starts.

    Returns:
    * (`str`): The path, or "" when cancelled.
    """
    if ANSWERS:
        return ANSWERS.pop(0)
    box: QFileDialog = QFileDialog(host, title, start, filters)
    box.setOption(QFileDialog.Option.DontUseNativeDialog)
    box.setFileMode(mode)
    if mode == QFileDialog.FileMode.Directory:
        box.setOption(QFileDialog.Option.ShowDirsOnly)
    if run_in(host, box) != QDialog.DialogCode.Accepted:
        return ""
    chosen: list[str] = box.selectedFiles()
    return chosen[0] if chosen else ""
