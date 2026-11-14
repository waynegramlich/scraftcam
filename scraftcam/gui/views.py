"""The views in a window: the tree, and the panels beside it.

* `TreeView`: the one tree (`T.osiade~5.1.9` #121), the shop's and
  the design's files, as `tree.py` reads them; an item that does not
  read cleanly is red, with the problem as its tooltip (#125).  The
  roots open one level (#128); when the tree is read again, what was
  open stays open.
* `Panel`: shows one item (#122), one machine's controls (#135), or
  the `machines/` summary (#134, `machines.py`): a shop file's plain
  fields, one row each, edited in place (S3.4, `fields.py`), with its
  kind's sketch from `Tool_Models.md` to the right (#5, #14), and the
  rest of it as TOML, read only; another TOML file's text; a Python
  file's or package's top docstring (#74), or the problem for an item
  that does not read cleanly, both wrapped.
* `TreeWatcher`: reads the trees again whenever a file or directory
  in them changes outside the GUI (#11, #123), so there is no
  [Refresh].  The
  current panel (the one last clicked) is outlined.
"""

import functools
from collections.abc import Callable
from pathlib import Path

from ..packages import require
from ..shops import KINDS, not_initialized, vendor_triple
from .app import App
from .fields import (
    Row,
    check,
    read_item,
    rest_text,
    rows,
    sketches,
    with_value,
    write_item,
)
from .machines import (
    MachineControl,
    MachinesView,
    MachineTab,
    is_machines_directory,
)
from .templates import FollowUp, FollowUpView, follow_ups, is_template
from .theme import colors, sketch_text
from .tree import DIRECTORY, ERROR, FILE, PACKAGE, SHOP, Node, docstring

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import (  # noqa: E402
    QByteArray,
    QEvent,
    QFileSystemWatcher,
    QObject,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (  # noqa: E402
    QBrush,
    QColor,
    QPainter,
    QPaintEvent,
)
from PySide6.QtSvgWidgets import QSvgWidget  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QFrame,
    QGridLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QSplitter,
    QSplitterHandle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

# A splitter's handle: wide enough to see and grab, in the palette's
# colors, so it shows in light and dark mode alike (#25).
HANDLE_WIDTH: int = 7
HANDLE_STYLE: str = (
    "QSplitter::handle { background: palette(mid); } "
    "QSplitter::handle:hover { background: palette(highlight); }"
)

# A handle's grip, the sign that it can be dragged: how many dots, how
# big, and how far apart (pixels).
GRIP_DOTS: int = 3
GRIP_DOT: int = 3
GRIP_GAP: int = 4

# A panel's splitters start 2:1: the field rows wider than the sketch,
# and taller than the text (Qt scales these to the room there is).
SHARES: list[int] = [2000, 1000]

# The least width the sketches keep when the rows are fitted (pixels).
MIN_SKETCH: int = 120

# The outline of the current panel, and of the others.
CURRENT_STYLE: str = "Panel { border: 2px solid palette(highlight); }"
OTHER_STYLE: str = "Panel { border: 2px solid transparent; }"

# How long the watcher waits for a burst of changes to end.
SETTLE_MS: int = 300

# Where an item keeps its path (the key into `TreeView.nodes`).
PATH_ROLE: int = Qt.ItemDataRole.UserRole


# Function `item_text()`:
def item_text(node: Node) -> str:
    """Return what a panel shows for an item.

    Arguments:
    * `node` (`Node`): The item.

    Returns:
    * (`str`): Its problem, its text, its docstring, or a count.
    """
    if node.kind == ERROR:
        return f"{node.path}:\n{node.error}"
    if node.kind in (SHOP, FILE):
        try:
            return node.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            return f"{node.path}: can not be read: {error}"
    if node.kind == DIRECTORY:
        return f"{node.path}\n{len(node.children)} items."
    if node.kind == PACKAGE and not (node.path / "__init__.py").is_file():
        return f"{node.path}"
    return docstring(node.path)


# Function `no_controls()`:
def no_controls() -> list[MachineControl]:
    """Return no machines: a panel's `controls` until the window's.

    Returns:
    * (`list[MachineControl]`): `[]`.
    """
    return []


# Function `no_machine()`:
def no_machine(_name: str) -> None:
    """Do nothing: a panel's `open_machine` and `say` until the window's."""


# Function `guide_label()`:
def guide_label() -> QLabel:
    """Return the label a panel shows its guide in, hidden (#139).

    Returns:
    * (`QLabel`): Wrapped, at the top left.
    """
    label: QLabel = QLabel()
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    label.hide()
    return label


# Function `shared()`:
def shared(
    orientation: Qt.Orientation, first: QWidget, second: QWidget
) -> QSplitter:
    """Return a splitter between two widgets, the first taking 2:1.

    Arguments:
    * `orientation` (`Qt.Orientation`): Side by side, or one above.
    * `first` (`QWidget`): The left or upper one.
    * `second` (`QWidget`): The other.

    Returns:
    * (`QSplitter`): The splitter, holding both.
    """
    split: QSplitter = splitter(orientation)
    split.addWidget(first)
    split.addWidget(second)
    split.setStretchFactor(0, 2)
    split.setStretchFactor(1, 1)
    split.setSizes(SHARES)
    return split


# Function `missing_label()`:
def missing_label() -> QLabel:
    """Return the label for the fields not initialized yet, hidden.

    Returns:
    * (`QLabel`): Wrapped, in the quiet color (not a problem, #145).
    """
    label: QLabel = QLabel()
    label.setWordWrap(True)
    label.setStyleSheet(f"color: {colors().quiet}")
    label.hide()
    return label


# Class `Panel`:
class Panel(QFrame):  # pylint: disable=too-many-instance-attributes
    """A panel: shows one item, outlined while it is the current one.

    Attributes:
    * `title` (`QLabel`): The item's label.
    * `text` (`QPlainTextEdit`): What the item holds, read only (for
      a shop file, what its fields do not show).
    * `node` (`Node | None`): The item shown, if any.
    * `machines` (`list[MachineControl]`): The machine it controls,
      if any (`show_machine()`), at most one (#135); then it shows
      nothing else.
    * `header` (`MachineTab | None`): Its header: its name over its
      bar.
    * `summary` (`MachinesView | None`): The `machines/` summary,
      while it shows that (#134).
    * `controls` (`Callable[[], list[MachineControl]]`): Gives the
      machines connected, for the summary (set by the window).
    * `open_machine` (`Callable[[str], None]`): Shows a machine's
      own panel, by name (set by the window).
    * `guide` (`QLabel`): The guide shown at start, until an item or
      machine is (#139).
    * `missing` (`QLabel`): The fields the item needs to run that it
      does not have yet, "Not initialized yet" (#145), hidden when
      none.
    * `follow_up` (`FollowUpView | None`): What a change to the
      controller template shown means for its machines (#142).
    * `say` (`Callable[[str], None]`): Reports a problem (set by the
      window).
    * `editing` (`bool`): True while its fields may be edited
      ([Enable Editing], #140); a new item starts read only, unless
      it was just made.
    * `clicked` (`Signal`): Sent when the panel is clicked.
    * `entries` (`dict[str, QLineEdit | QPlainTextEdit]`): Each
      field's entry, by key.
    * `fields` (`QScrollArea`): The field rows, hidden for an item
      that has none.
    * `item` (`dict[str, object]`): The shop file shown, as read.
    * `rows` (`list[Row]`): Its plain fields.
    * `shown` (`dict[str, QLabel]`): Each measurement's value in the
      shop's units, by key.
    * `sketch` (`QWidget`): The item's kind's sketches, one above
      another, hidden when it has none.
    * `views` (`list[QSvgWidget]`): Those sketches, top first.
    * `split` (`QSplitter`): The field rows above the text.
    * `top` (`QSplitter`): The field rows left of the sketch.
    * `units` (`str`): The shop's units.
    * `written` (`str`): The text last written, so that the file
      watcher's redraw does not rebuild the rows under the cursor.
    """

    clicked: Signal = Signal()

    def __init__(self, number: int) -> None:
        """Make an empty panel.

        Arguments:
        * `number` (`int`): Its number (from 1), until it shows an item.
        """
        super().__init__()
        self.node: Node | None = None
        self.machines: list[MachineControl] = []
        self.header: MachineTab | None = None
        self.summary: MachinesView | None = None
        self.controls: Callable[[], list[MachineControl]] = no_controls
        self.open_machine: Callable[[str], None] = no_machine
        self.editing: bool = False
        self.follow_up: FollowUpView | None = None
        self.say: Callable[[str], None] = no_machine
        self.guide: QLabel = guide_label()
        self.missing: QLabel = missing_label()
        self.item: dict[str, object] = {}
        self.rows: list[Row] = []
        self.entries: dict[str, QLineEdit | QPlainTextEdit] = {}
        self.shown: dict[str, QLabel] = {}
        self.units: str = "in"
        self.written: str = ""
        self.title: QLabel = QLabel(f"Panel {number}: click an item.")
        self.title.setStyleSheet(f"color: {colors().quiet}")
        self.fields: QScrollArea = QScrollArea()
        self.fields.setWidgetResizable(True)
        self.fields.hide()
        self.sketch: QWidget = QWidget()
        self.views: list[QSvgWidget] = []
        QVBoxLayout(self.sketch).setContentsMargins(0, 0, 0, 0)
        self.sketch.hide()
        self.text: QPlainTextEdit = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.title)
        layout.addWidget(self.missing)

        # The field rows, with the sketch to their right, above the
        # text; the user drags the lines between them (#25).
        self.top: QSplitter = shared(
            Qt.Orientation.Horizontal, self.fields, self.sketch
        )
        self.split: QSplitter = shared(
            Qt.Orientation.Vertical, self.top, self.text
        )
        layout.addWidget(self.split, 1)
        layout.addWidget(self.guide, 1)
        self.text.viewport().installEventFilter(self)
        self.set_current(False)

    def eventFilter(  # pylint: disable=invalid-name
        self, watched: QObject, event: QEvent
    ) -> bool:
        """Notice a click on the text, and `notes` losing the focus.

        Arguments:
        * `watched` (`QObject`): The text's viewport, or an entry.
        * `event` (`QEvent`): Any event; a mouse press makes this the
          current panel; a multi-line entry losing the focus is
          written.

        Returns:
        * (`bool`): False, so the text gets the event too.
        """
        if event.type() == QEvent.Type.MouseButtonPress:
            self.clicked.emit()
        elif event.type() == QEvent.Type.FocusOut:
            key: str
            entry: QLineEdit | QPlainTextEdit
            for key, entry in self.entries.items():
                if entry is watched:
                    self.write(key)
        return super().eventFilter(watched, event)

    def mousePressEvent(  # pylint: disable=invalid-name
        self, event: object
    ) -> None:
        """Make this the current panel when it is clicked.

        Arguments:
        * `event` (`object`): The mouse press (unused).
        """
        del event
        self.clicked.emit()

    def show_machine(self, machine: MachineControl) -> None:
        """Show a machine's controls, in place of any item.

        A tree click never replaces them (#58); a panel holds one
        machine, its header the machine's name over its bar (#135).

        Arguments:
        * `machine` (`MachineControl`): The controls.
        """
        assert not self.machines, "a panel holds one machine"
        self.drop_summary()
        self.guide.hide()
        self.machines.append(machine)
        self.node = None
        self.title.hide()
        self.split.hide()
        self.header = MachineTab(machine.name)
        layout: QLayout | None = self.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.addWidget(self.header)
        layout.addWidget(machine.widget, 1)

    def show_dues(self, blink: bool) -> None:
        """Bring the machine's bar, or the summary, up to date (#102).

        Arguments:
        * `blink` (`bool`): Which half of a blink this is.
        """
        if self.header is not None:
            self.header.show_due(self.machines[0].due(), blink)
        if self.summary is not None:
            self.summary.refresh(blink)

    def set_editing(self, editing: bool) -> None:
        """Let the fields be edited, or make them read only (#140).

        Arguments:
        * `editing` (`bool`): True to let them be edited.
        """
        self.editing = editing
        row: Row
        for row in self.rows:
            entry: QLineEdit | QPlainTextEdit | None = self.entries.get(
                row.schema.key
            )
            if entry is not None:
                entry.setReadOnly(not (row.editable and editing))

    def show_guide(self, text: str) -> None:
        """Show the guide, until an item or a machine is shown (#139).

        Arguments:
        * `text` (`str`): The guide, as plain text.
        """
        self.title.setText("scraftcam")
        self.title.setStyleSheet("font-weight: bold; font-size: 16pt")
        self.split.hide()
        self.guide.setText(text)
        self.guide.show()

    def drop_summary(self) -> None:
        """Take the `machines/` summary away, if it is shown."""
        if self.summary is not None:
            layout: QLayout | None = self.layout()
            assert layout is not None
            layout.removeWidget(self.summary)
            self.summary.deleteLater()
            self.summary = None

    def set_current(self, current: bool) -> None:
        """Outline the panel, or not.

        Arguments:
        * `current` (`bool`): True for the current panel.
        """
        self.setStyleSheet(CURRENT_STYLE if current else OTHER_STYLE)

    def show_node(
        self, node: Node, units: str = "in", *, created: bool = False
    ) -> None:
        """Show an item.

        Arguments:
        * `node` (`Node`): The item.
        * `units` (`str`): The shop's units, `"in"` or `"mm"`.
        * `created` (`bool`): True if it was just made: a new item then
          opens with editing enabled (#140).
        """
        # The file holds what this panel just wrote: keep the rows,
        # and the cursor in them.  Another item starts read only,
        # unless it was just made.
        same: bool = self.node is not None and self.node.path == node.path
        previous: dict[str, object] = self.item if same else {}
        if not same:
            self.editing = created
            self.show_follow_ups([])
        self.node = node
        self.units = units
        if same and self.written and node.kind in (SHOP, FILE):
            try:
                if node.path.read_text(encoding="utf-8") == self.written:
                    return
            except (OSError, UnicodeDecodeError):
                pass
        self.written = ""
        self.drop_summary()
        self.missing.hide()

        # The `machines/` directory: its summary, in place of the rest.
        self.guide.hide()
        self.split.setVisible(not is_machines_directory(node))
        if is_machines_directory(node):
            self.title.setText(node.label())
            self.title.setStyleSheet("")
            self.summary = MachinesView(node, self.controls, self.open_machine)
            layout: QLayout | None = self.layout()
            assert isinstance(layout, QVBoxLayout)
            layout.addWidget(self.summary, 1)
            return

        # The title, and the text.
        self.title.setText(node.label())
        self.title.setStyleSheet(
            f"color: {colors().problem}" if node.kind == ERROR else ""
        )
        self.text.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
            if node.kind in (SHOP, FILE)
            else QPlainTextEdit.LineWrapMode.WidgetWidth
        )
        self.item = {}
        self.rows = []
        if node.kind in (SHOP, FILE) and node.path.suffix == ".toml":
            self.item = read_item(node.path)[0]
            self.rows = rows(self.item, units)
        self.show_sketches(sketches(self.item) if self.rows else [])
        if not self.rows:
            self.fields.hide()
            self.text.show()
            self.text.setPlainText(item_text(node))
            return
        self.fill_rows()
        self.show_missing()
        rest: str = rest_text(self.item)
        self.text.setVisible(bool(rest))
        self.text.setPlainText(rest)

        # A template changed outside the panel ([Edit]): follow it up
        # (#142).
        if previous and previous != self.item and is_template(node.path):
            self.show_follow_ups(follow_ups(node.path, previous, self.item))

        # Once laid out, move the lines in until they meet the rows.
        QTimer.singleShot(0, self.fit)

    def fit(self) -> None:
        """Move the panel's lines in until they meet what is there (#43).

        The line between the field rows and the sketches moves left to
        the rows' own width, the sketches taking the rest; the line
        above the text moves up until the text has room for all of its
        lines, though never above a third of the panel.  What the user
        drags stays until the next item is shown.
        """
        # Across: the rows' width, with their scroll bar and frame.
        frame: int = 2 * self.fields.frameWidth()
        content: QWidget | None = self.fields.widget()
        across: int = sum(self.top.sizes())
        if content is not None and not self.sketch.isHidden() and across > 0:
            wanted: int = (
                content.sizeHint().width()
                + self.fields.verticalScrollBar().sizeHint().width()
                + frame
            )
            rows_width: int = min(wanted, across - MIN_SKETCH)
            self.top.setSizes([rows_width, across - rows_width])

        # Down: the text's lines, at most a third of the height.
        down: int = sum(self.split.sizes())
        if not self.text.isHidden() and down > 0:
            lines: int = self.text.document().lineCount()
            text_height: int = min(
                (lines + 1) * self.text.fontMetrics().lineSpacing() + frame,
                down // 3,
            )
            self.split.setSizes([down - text_height, text_height])

    def restyle(self) -> None:
        """Draw the panel again, in the scheme now in use (#24)."""
        self.title.setStyleSheet(
            f"color: {colors().quiet}" if self.node is None else ""
        )
        if self.node is not None:
            self.written = ""
            self.show_node(self.node, self.units)

    def show_sketches(self, paths: list[Path]) -> None:
        """Show sketches one above another, each as tall as it draws.

        Arguments:
        * `paths` (`list[Path]`): The SVG files, top first; none hides
          the sketches.
        """
        layout: QLayout | None = self.sketch.layout()
        assert layout is not None
        view: QSvgWidget
        for view in self.views:
            layout.removeWidget(view)
            view.deleteLater()
        self.views = []
        path: Path
        for path in paths:
            view = QSvgWidget()
            view.load(
                QByteArray(
                    sketch_text(path.read_text(encoding="utf-8")).encode()
                )
            )
            view.renderer().setAspectRatioMode(
                Qt.AspectRatioMode.KeepAspectRatio
            )
            assert isinstance(layout, QVBoxLayout)
            layout.addWidget(
                view, max(1, view.renderer().defaultSize().height())
            )
            self.views.append(view)
        self.sketch.setVisible(bool(paths))

    def fill_rows(self) -> None:
        """Make a row per field: its key, its entry, its value shown."""
        grid_widget: QWidget = QWidget()
        grid: QGridLayout = QGridLayout(grid_widget)
        grid.setColumnStretch(1, 1)
        self.entries = {}
        self.shown = {}
        number: int
        row: Row
        for number, row in enumerate(self.rows):
            key: str = row.schema.key
            letter: str = row.schema.letter
            label: QLabel = QLabel(f"{key} ({letter})" if letter else key)
            label.setToolTip(row.schema.meaning)
            entry: QLineEdit | QPlainTextEdit
            if key == "notes":
                entry = QPlainTextEdit(row.text)
                entry.setFixedHeight(4 * entry.fontMetrics().height() + 12)
                entry.textChanged.connect(
                    functools.partial(self.notes_typed, key)
                )
                entry.installEventFilter(self)
            else:
                entry = QLineEdit(row.text)
                entry.textEdited.connect(functools.partial(self.typed, key))
                entry.editingFinished.connect(
                    functools.partial(self.write, key)
                )
            entry.setReadOnly(not (row.editable and self.editing))
            entry.setToolTip(row.schema.meaning)
            shown: QLabel = QLabel(row.shown)
            shown.setStyleSheet(f"color: {colors().quiet}")
            grid.addWidget(label, number, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(entry, number, 1)
            grid.addWidget(shown, number, 2, Qt.AlignmentFlag.AlignTop)
            self.entries[key] = entry
            self.shown[key] = shown
            self.look(row)
        grid.setRowStretch(len(self.rows), 1)
        self.fields.setWidget(grid_widget)
        self.fields.show()

    def row(self, key: str) -> Row:
        """Return a field's row.

        Arguments:
        * `key` (`str`): The field's key.

        Returns:
        * (`Row`): Its row.
        """
        return next(row for row in self.rows if row.schema.key == key)

    def look(self, row: Row) -> None:
        """Show a field's problem (light red), or its converted value.

        Arguments:
        * `row` (`Row`): The field.
        """
        entry: QLineEdit | QPlainTextEdit = self.entries[row.schema.key]
        entry.setStyleSheet(bad_style() if row.problem else "")
        entry.setToolTip(row.problem or row.schema.meaning)
        self.shown[row.schema.key].setText(row.shown)

    def typed(self, key: str, text: str) -> None:
        """Check a field as it is typed (#15).

        Arguments:
        * `key` (`str`): The field's key.
        * `text` (`str`): Its text now.
        """
        row: Row = self.row(key)
        check(row, text, self.units)
        self.look(row)

    def notes_typed(self, key: str) -> None:
        """Check a multi-line field as it is typed.

        Arguments:
        * `key` (`str`): The field's key.
        """
        entry: QLineEdit | QPlainTextEdit = self.entries[key]
        if isinstance(entry, QPlainTextEdit):
            self.typed(key, entry.toPlainText())

    def write(self, key: str) -> None:
        """Write the file if a field's value is good and has changed.

        Arguments:
        * `key` (`str`): The field's key.
        """
        changed: dict[str, object] | None = with_value(
            self.item, self.row(key)
        )
        if changed is None or changed == self.item or self.node is None:
            return

        # A controller's `vendor_version`: our reading of it too (#144).
        triple: QLineEdit | QPlainTextEdit | None = self.entries.get(
            "vendor_triple"
        )
        if key == "vendor_version" and changed.get("kind") == "controller":
            changed["vendor_triple"] = vendor_triple(
                str(changed.get("vendor_version", ""))
            )
            if isinstance(triple, QLineEdit):
                triple.setText(str(changed["vendor_triple"]))
                self.row("vendor_triple").text = triple.text()

        # Written; then what is still missing.
        self.written = write_item(self.node.path, changed)
        old: dict[str, object] = self.item
        self.item = changed
        self.show_missing()

        # A template changed: follow it up, at once (#142).
        if is_template(self.node.path):
            self.show_follow_ups(follow_ups(self.node.path, old, changed))

    def show_missing(self) -> None:
        """Say which fields the item does not have yet, if any (#145)."""
        kind: object = self.item.get("kind")
        missing: list[str] = (
            not_initialized(self.item, kind)
            if isinstance(kind, str) and kind in KINDS
            else []
        )
        self.missing.setText(
            "Not initialized yet: " + ", ".join(missing) if missing else ""
        )
        self.missing.setVisible(bool(missing))

    def show_follow_ups(self, found: list[FollowUp]) -> None:
        """Show what a template change means for its machines (#142).

        Arguments:
        * `found` (`list[FollowUp]`): What to show; none takes the
          list away.
        """
        layout: QLayout | None = self.layout()
        assert isinstance(layout, QVBoxLayout)
        if self.follow_up is not None:
            layout.removeWidget(self.follow_up)
            self.follow_up.deleteLater()
            self.follow_up = None
        if found:
            self.follow_up = FollowUpView(found, self.say)
            layout.addWidget(self.follow_up)


# Function `bad_style()`:
def bad_style() -> str:
    """Return the look of a field while its value is bad (#15, #24).

    Returns:
    * (`str`): A style sheet: the scheme's light red background.
    """
    return f"background-color: {colors().bad}"


# Class `GripHandle`:
class GripHandle(QSplitterHandle):
    """A splitter's handle with a grip: a few dots at its middle (#44).

    Attributes: none of its own.
    """

    def paintEvent(  # pylint: disable=invalid-name
        self, event: QPaintEvent
    ) -> None:
        """Draw the handle as the style says, then the grip's dots.

        Arguments:
        * `event` (`QPaintEvent`): What to paint.
        """
        super().paintEvent(event)
        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().color(self.foregroundRole()))
        across: bool = self.orientation() == Qt.Orientation.Horizontal
        step: int = GRIP_DOT + GRIP_GAP
        length: int = GRIP_DOTS * step - GRIP_GAP
        middle_x: int = self.width() // 2
        middle_y: int = self.height() // 2
        index: int
        for index in range(GRIP_DOTS):
            along: int = index * step - length // 2
            x: int = middle_x - GRIP_DOT // 2 + (0 if across else along)
            y: int = middle_y - GRIP_DOT // 2 + (along if across else 0)
            painter.drawEllipse(x, y, GRIP_DOT, GRIP_DOT)
        painter.end()


# Class `GripSplitter`:
class GripSplitter(QSplitter):
    """A splitter whose handles show a grip (`GripHandle`).

    Attributes: none of its own.
    """

    def createHandle(  # pylint: disable=invalid-name
        self,
    ) -> QSplitterHandle:
        """Return a new handle, with a grip.

        Returns:
        * (`QSplitterHandle`): The handle.
        """
        return GripHandle(self.orientation(), self)


# Function `splitter()`:
def splitter(orientation: Qt.Orientation) -> QSplitter:
    """Return an empty splitter whose handles can be seen and dragged.

    Arguments:
    * `orientation` (`Qt.Orientation`): `Horizontal` puts its parts
      side by side; `Vertical`, one above another.

    Returns:
    * (`QSplitter`): The splitter.
    """
    made: QSplitter = GripSplitter(orientation)
    made.setHandleWidth(HANDLE_WIDTH)
    made.setStyleSheet(HANDLE_STYLE)
    made.setChildrenCollapsible(False)
    return made


# Class `TreeView`:
class TreeView(QTreeWidget):
    """The one tree: the shop's and the design's files.

    Attributes:
    * `nodes` (`dict[str, Node]`): Each item's node, by its path.
    * `version` (`int`): The model's `tree_version` last shown.
    """

    def __init__(self) -> None:
        """Make an empty tree."""
        super().__init__()
        self.setHeaderHidden(True)
        self.nodes: dict[str, Node] = {}
        self.version: int = -1

    def wanted_width(self) -> int:
        """Return the width that shows the open items' labels whole.

        Returns:
        * (`int`): The width, in pixels, with no space to spare (#22).
        """
        # The labels' own width: the column itself stretches to fill
        # the view, so its width says nothing.
        return (
            self.sizeHintForColumn(0)
            + 2 * self.frameWidth()
            + self.verticalScrollBar().sizeHint().width()
        )

    def fill(self, roots: list[Node], version: int) -> None:
        """Show the trees, keeping open what was open.

        Arguments:
        * `roots` (`list[Node]`): The shop's and the design's roots.
        * `version` (`int`): The model's `tree_version`.
        """
        # What was open, by path; the roots open at first (#128).
        first: bool = self.version < 0
        opened: set[str] = set()
        index: int
        for index in range(self.topLevelItemCount()):
            opened |= open_paths(self.topLevelItem(index))

        # The items, again.
        self.clear()
        self.nodes = {}
        root: Node
        for root in roots:
            item: QTreeWidgetItem = self.add(root, None, opened)
            if first:
                item.setExpanded(True)
        self.version = version

    def add(
        self, node: Node, parent: QTreeWidgetItem | None, opened: set[str]
    ) -> QTreeWidgetItem:
        """Add an item, and those under it.

        Arguments:
        * `node` (`Node`): The item.
        * `parent` (`QTreeWidgetItem | None`): Its parent; None for a
          root.
        * `opened` (`set[str]`): The paths of the items to open.

        Returns:
        * (`QTreeWidgetItem`): The item.
        """
        item: QTreeWidgetItem
        if parent is None:
            item = QTreeWidgetItem(self)
        else:
            item = QTreeWidgetItem(parent)
        key: str = str(node.path)
        item.setText(0, node.label())
        item.setData(0, PATH_ROLE, key)
        if node.kind == ERROR:
            item.setForeground(0, QBrush(QColor(colors().problem)))
            item.setToolTip(0, node.error)
        elif node.about:
            item.setToolTip(0, node.about)
        self.nodes[key] = node
        child: Node
        for child in node.children:
            self.add(child, item, opened)
        item.setExpanded(key in opened)
        return item

    def labels(self) -> list[object]:
        """Return what the tree shows (the command port's `tree`).

        Returns:
        * (`list[object]`): Per root, its label, then a list per
          child, nested as the tree is.
        """
        return [
            item_labels(self.topLevelItem(index))
            for index in range(self.topLevelItemCount())
        ]

    def node_of(self, item: QTreeWidgetItem) -> Node | None:
        """Return an item's node.

        Arguments:
        * `item` (`QTreeWidgetItem`): The item.

        Returns:
        * (`Node | None`): Its node, if it has one.
        """
        return self.nodes.get(str(item.data(0, PATH_ROLE)))

    def item_at_path(self, path: Path) -> QTreeWidgetItem | None:
        """Find the item for a path.

        Arguments:
        * `path` (`Path`): The item's file or directory.

        Returns:
        * (`QTreeWidgetItem | None`): The item, if there is one.
        """
        found: list[QTreeWidgetItem] = [
            item
            for item in self.findItems(
                "", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive
            )
            if str(item.data(0, PATH_ROLE)) == str(path)
        ]
        return found[0] if found else None


# Function `open_paths()`:
def open_paths(item: QTreeWidgetItem | None) -> set[str]:
    """Return the paths of the open items at and under an item.

    Arguments:
    * `item` (`QTreeWidgetItem | None`): The item (None: none).

    Returns:
    * (`set[str]`): Their paths.
    """
    opened: set[str] = set()
    if item is None:
        return opened
    if item.isExpanded():
        opened.add(str(item.data(0, PATH_ROLE)))
    index: int
    for index in range(item.childCount()):
        opened |= open_paths(item.child(index))
    return opened


# Function `item_labels()`:
def item_labels(item: QTreeWidgetItem | None) -> list[object]:
    """Return an item's label, then a list per child, nested.

    Arguments:
    * `item` (`QTreeWidgetItem | None`): The item (None: none).

    Returns:
    * (`list[object]`): The labels.
    """
    if item is None:
        return []
    return [
        item.text(0),
        *[
            item_labels(item.child(index))
            for index in range(item.childCount())
        ],
    ]


# Function `node_paths()`:
def node_paths(node: Node | None) -> list[str]:
    """Return the paths of an item and of every item under it.

    Arguments:
    * `node` (`Node | None`): The item (None: none).

    Returns:
    * (`list[str]`): Their paths, the item's first.
    """
    if node is None:
        return []
    paths: list[str] = [str(node.path)]
    child: Node
    for child in node.children:
        paths.extend(node_paths(child))
    return paths


# Class `TreeWatcher`:
class TreeWatcher(QFileSystemWatcher):
    """Reads the trees again when their files change (#123).

    A burst of changes (an editor saving, `git checkout`) is read once,
    `SETTLE_MS` after the last.

    Attributes:
    * `model` (`App`): What every window shows.
    * `timer` (`QTimer`): Waits for a burst of changes to end.
    * `version` (`int`): The model's `tree_version` last watched.
    """

    def __init__(self, model: App) -> None:
        """Watch the model's trees.

        Arguments:
        * `model` (`App`): What every window shows.
        """
        super().__init__()
        self.model: App = model
        self.timer: QTimer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(SETTLE_MS)
        self.timer.timeout.connect(self.reload)
        self.fileChanged.connect(self.changed)
        self.directoryChanged.connect(self.changed)
        self.version: int = -1
        self.watch()
        model.listen(self.follow)

    def watch(self) -> None:
        """Watch every file and directory now in the trees."""
        # Directories show files added and removed; files, edits.
        watched: list[str] = self.files() + self.directories()
        if watched:
            self.removePaths(watched)
        paths: list[str] = node_paths(self.model.shop_root) + node_paths(
            self.model.design_root
        )
        shop: Path | None = self.model.shop
        if shop is not None:
            paths.append(str(shop.parent))
        design: Path | None = self.model.design
        if design is not None and design.is_file():
            paths.append(str(design.parent))
        existing: list[str] = sorted(
            {path for path in paths if Path(path).exists()}
        )
        if existing:
            self.addPaths(existing)
        self.version = self.model.tree_version

    def follow(self) -> None:
        """Watch the trees again once they are read again (a new shop)."""
        if self.version != self.model.tree_version:
            self.watch()

    def changed(self, _path: str) -> None:
        """Note a change; read the trees once the burst is over.

        Arguments:
        * `_path` (`str`): What changed (ignored).
        """
        self.timer.start()

    def reload(self) -> None:
        """Read the trees again (`follow()` then watches them)."""
        self.model.reload_tree()
