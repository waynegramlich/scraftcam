"""The views in a window: the tree, and the panels beside it.

* `TreeView`: the one tree (`T.g~6` #121), the shop's and
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
import importlib
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, assert_never

from ..packages import require
from ..shops import (
    KINDS,
    OUTLINE_SUFFIX,
    UNITS,
    is_read_only,
    measurement_problem,
    not_initialized,
    vendor_triple,
)
from .app import App

# Only for its type: loaded by name when an outline is shown.
if TYPE_CHECKING:
    from .outline_editor import OutlineEditor
from .fields import (
    Row,
    check,
    field_help,
    read_item,
    rows,
    sketches,
    with_value,
    write_item,
)
from .machines import (
    MachineControl,
    MachinesView,
    MachineTab,
    is_active,
    is_machines_directory,
    machine_item,
)
from .outline_values import ToolValues
from .templates import (
    FollowUp,
    FollowUpView,
    copied_from,
    follow_ups,
    is_template,
)
from .theme import colors, sketch_text
from .tree import (
    ERROR,
    EXPLANATIONS,
    FILE,
    OUTLINE,
    SHOP,
    Kind,
    Node,
    docstring,
    edit_path,
    shop_relative,
)

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
    QFont,
    QPainter,
    QPaintEvent,
)
from PySide6.QtSvgWidgets import QSvgWidget  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSplitterHandle,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

# [Edit TOML File]'s label (#148).
EDIT: str = "Edit TOML File"

# A catalog's button, beside [Edit TOML File] (`T.c~6.3` #68).
OPEN_PAGES: str = "Open Pages"

# A splitter's handle: wide enough to see and grab, in the palette's
# colors, so it shows in light and dark mode alike (#25).
HANDLE_WIDTH: int = 7

# A field's entry: a line, the notes' lines, or a closed choice's
# drop-down (#148).
Entry = QLineEdit | QPlainTextEdit | QComboBox

# What a choice's drop-down shows for a value, where its value alone
# does not say enough (#148).
CHOICE_LABELS: dict[str, str] = {
    "in": "imperial (in)",
    "mm": "metric (mm)",
}
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
    # Every kind, so that `mypy` names a new one left out (#761).
    match node.kind:
        case Kind.ERROR:
            return f"{node.path}:\n{node.error}"
        case Kind.SHOP | Kind.FILE | Kind.OUTLINE:
            try:
                return node.path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                return f"{node.path}: can not be read: {error}"
        case Kind.DIRECTORY:
            return EXPLANATIONS.get(
                shop_relative(node.path),
                f"{node.path}\n{len(node.children)} items.",
            )
        case Kind.PACKAGE if not (node.path / "__init__.py").is_file():
            return f"{node.path}"
        case Kind.PACKAGE | Kind.DESIGN | Kind.PYTHON:
            return docstring(node.path)
        case _:
            assert_never(node.kind)


# Function `toggle_help()`:
def toggle_help(arrow: QToolButton, about: QLabel) -> None:
    """Show or hide how to fill in a field, turning its ▶ to ▼ (#149).

    Arguments:
    * `arrow` (`QToolButton`): The field's ▶.
    * `about` (`QLabel`): How to fill it in.
    """
    about.setVisible(about.isHidden())
    arrow.setArrowType(
        Qt.ArrowType.RightArrow if about.isHidden() else Qt.ArrowType.DownArrow
    )


# Function `entry_text()`:
def entry_text(entry: Entry) -> str:
    """Return what a field's entry holds, as the file would.

    Arguments:
    * `entry` (`Entry`): The entry.

    Returns:
    * (`str`): Its text, or a drop-down's value (#148).
    """
    if isinstance(entry, QComboBox):
        return str(entry.currentData())
    if isinstance(entry, QPlainTextEdit):
        return entry.toPlainText()
    return entry.text()


# Function `read_only()`:
def read_only(entry: Entry, fixed: bool) -> None:
    """Make a field's entry read only, or editable.

    Arguments:
    * `entry` (`Entry`): The entry.
    * `fixed` (`bool`): True for read only (a drop-down is greyed).
    """
    if isinstance(entry, QComboBox):
        entry.setEnabled(not fixed)
    else:
        entry.setReadOnly(fixed)


# Function `text_view()`:
def text_view() -> QPlainTextEdit:
    """Return a panel's text: read only, not wrapped.

    Returns:
    * (`QPlainTextEdit`): The text.
    """
    text: QPlainTextEdit = QPlainTextEdit()
    text.setReadOnly(True)
    text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    return text


# Function `no_edit()`:
def no_edit() -> None:
    """Do nothing: a panel's `edit_file` (or `open_pages`) until the
    window's."""


# Function `no_move()`:
def no_move(_step: int) -> None:
    """Do nothing: a panel's `move_panel` until the window's.

    Arguments:
    * `_step` (`int`): -1 (left) or 1 (right); unused.
    """


# Function `no_controls()`:
def no_controls() -> list[MachineControl]:
    """Return no machines: a panel's `controls` until the window's.

    Returns:
    * (`list[MachineControl]`): `[]`.
    """
    return []


# Function `no_machine()`:
def no_machine(_name: str) -> None:
    """Do nothing: a panel's `open_machine`, `open_path` and `say`
    until the window's."""


# Function `narrow()`:
def narrow(button: QPushButton, longest: str = "") -> None:
    """Make a button only as wide as its text (#181).

    Qt's buttons are at least 80 pixels wide, however short their
    text.

    Arguments:
    * `button` (`QPushButton`): The button.
    * `longest` (`str`): The longest text it will show, if not its
      text now.
    """
    text: str = longest or button.text()
    button.setMaximumWidth(
        button.fontMetrics().horizontalAdvance(f"  {text}  ")
    )


# Function `field_area()`:
def field_area() -> QScrollArea:
    """Return a panel's area for its field rows, hidden until used.

    Returns:
    * (`QScrollArea`): The area.
    """
    area: QScrollArea = QScrollArea()
    area.setWidgetResizable(True)
    area.hide()
    return area


# Function `sketch_box()`:
def sketch_box() -> QWidget:
    """Return a panel's box for its sketches, hidden until used.

    Returns:
    * (`QWidget`): The box, with an empty vertical layout.
    """
    box: QWidget = QWidget()
    QVBoxLayout(box).setContentsMargins(0, 0, 0, 0)
    box.hide()
    return box


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


# Function `outline_of()`:
def outline_of(path: Path, item: dict[str, object]) -> Path | None:
    """Return the outline file of an item's kind, beside the item.

    A tool of kind `end_mill` has `end_mill.outline.toml` in its own
    directory (#584).

    Arguments:
    * `path` (`Path`): The item's file.
    * `item` (`dict[str, object]`): The item, as read.

    Returns:
    * (`Path | None`): The outline file, or `None` when it has none.
    """
    kind: object = item.get("kind")
    if not isinstance(kind, str) or not kind:
        return None
    outline: Path = path.parent / f"{kind}{OUTLINE_SUFFIX}"
    return outline if outline.is_file() else None


# Class `Panel`:
# A panel shows an item, a machine, the guide or the `machines/`
# summary, each with its own few methods, so the counts are fine.
# pylint: disable-next=too-many-instance-attributes,too-many-public-methods
class Panel(QFrame):
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
    * `copied` (`QLabel`): Which template a machine's controller
      was copied from (#151), hidden when none.
    * `missing` (`QLabel`): The fields the item needs to run that it
      does not have yet, "Not initialized yet" (#145), hidden when
      none.
    * `follow_up` (`FollowUpView | None`): What a change to the
      controller template shown means for its machines (#142).
    * `say` (`Callable[[str], None]`): Reports a problem (set by the
      window).
    * `editing` (`bool`): True while its fields may be edited
      ([Allow Changes], #140); a new item starts read only, unless
      it was just made.
    * `edit_row` (`QWidget`): [Allow Changes] and [Edit TOML File],
      under the title, for an item that can be edited (#153).
    * `editing_box` (`QCheckBox`): [Allow Changes].
    * `edit_button` (`QPushButton`): [Edit TOML File], greyed while
      [Allow Changes] is unchecked.
    * `edit_file` (`Callable[[], None]`): What [Edit TOML File] calls
      (set by the window).
    * `pages_button` (`QPushButton`): [Open Pages], for a catalog
      (`T.c~6.3` #68), never greyed: marking pages does not
      change the catalog's file.
    * `open_pages` (`Callable[[], None]`): What [Open Pages] calls
      (set by the window).
    * `close_button` (`QPushButton`): [Close] (#181), at the right end
      of the title line (#156), hidden on a window's last panel.
    * `close_panel` (`Callable[[], None]`): What [Close] calls
      (set by the window).
    * `pin_box` (`QCheckBox`): [ ] Pin (#201): checked, tree clicks
      go to another panel; checked and greyed while its machine is
      active.
    * `pinned` (`bool`): True when the user pinned it ([ ] Pin).
    * `left_button` (`QPushButton`): [<], moving it left (#174,
      #181), greyed on the leftmost panel.
    * `right_button` (`QPushButton`): [>], moving it right (#174,
      #181), greyed on the rightmost panel.
    * `move_panel` (`Callable[[int], None]`): What they call, with -1
      (left) or 1 (right) (set by the window).
    * `clicked` (`Signal`): Sent when the panel is clicked.
    * `entries` (`dict[str, Entry]`): Each
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
    * `tabs` (`QTabWidget`): [Fields] (`split`) and, for a tool whose
      kind has an outline file, [Outline] (#587); or, in place of
      [Fields], its own tab (`own`).  The tab bar always shows
      (#586).
    * `own` (`QWidget | None`): The tab shown in place of [Fields],
      if any: [Guide] (`guide`), [Machines] (`summary`), or
      [Machine] (`header` over the machine's controls).
    * `outline` (`OutlineEditor | None`): That outline's editor
      (#578), if shown; a kind's outline is changed only in its
      [Edit] tab (`T.toasl~6.8` #755), a tool's never, and it saves
      every change (#578c).
    * `open_path` (`Callable[[str], None]`): Shows the tree item at
      a path (the window's), as a tool's link to its outline (#757).
    * `outline_path` (`Path | None`): Its outline file.
    * `outline_item` (`Path | None`): The item its [Outline] tab was
      made for: a tool, or the outline file itself (#750, #751).
    * `pages` (`QWidget | None`): A catalog's pages in `catxtract`,
      in the [Pages] tab ([Open Pages], #600), if open; closed (its
      marks saved) when the panel shows anything else.
    * `top` (`QSplitter`): The field rows left of the sketch.
    * `units` (`str`): The shop's units.
    * `written` (`str`): The text last written, so that the file
      watcher's redraw does not rebuild the rows under the cursor.
    """

    clicked: Signal = Signal()

    # It makes every one of the panel's widgets, a statement or two
    # each; split up, it would only scatter them.
    # pylint: disable-next=too-many-statements
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
        self.open_path: Callable[[str], None] = no_machine
        self.editing: bool = False
        self.follow_up: FollowUpView | None = None
        self.say: Callable[[str], None] = no_machine
        self.edit_file: Callable[[], None] = no_edit
        self.open_pages: Callable[[], None] = no_edit
        self.close_panel: Callable[[], None] = no_edit
        self.move_panel: Callable[[int], None] = no_move
        self.guide: QLabel = guide_label()
        self.missing: QLabel = missing_label()
        self.copied: QLabel = missing_label()
        self.item: dict[str, object] = {}
        self.rows: list[Row] = []
        self.entries: dict[str, Entry] = {}
        self.shown: dict[str, QLabel] = {}
        self.units: str = "in"
        self.written: str = ""
        self.title: QLabel = QLabel(f"Panel {number}: click an item.")
        self.title.setStyleSheet(f"color: {colors().quiet}")
        self.fields: QScrollArea = field_area()
        self.sketch: QWidget = sketch_box()
        self.views: list[QSvgWidget] = []
        self.text: QPlainTextEdit = text_view()
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.close_button: QPushButton = QPushButton("Close")
        self.pin_box: QCheckBox = QCheckBox("Pin")
        self.pinned: bool = False
        self.left_button: QPushButton = QPushButton("<")
        self.right_button: QPushButton = QPushButton(">")
        layout.addLayout(self._make_title_line())
        self.editing_box: QCheckBox = QCheckBox("Allow Changes")
        self.edit_button: QPushButton = QPushButton(EDIT)
        self.pages_button: QPushButton = QPushButton(OPEN_PAGES)
        self.edit_row: QWidget = self._make_edit_row()
        layout.addWidget(self.edit_row)
        layout.addWidget(self.missing)
        layout.addWidget(self.copied)

        # The field rows, with the sketch to their right, above the
        # text; the user drags the lines between them (#25).
        self.top: QSplitter = shared(
            Qt.Orientation.Horizontal, self.fields, self.sketch
        )
        self.split: QSplitter = shared(
            Qt.Orientation.Vertical, self.top, self.text
        )
        self.tabs: QTabWidget = QTabWidget()
        self.tabs.addTab(self.split, "Fields")
        self.own: QWidget | None = None
        self.outline: OutlineEditor | None = None
        self.outline_path: Path | None = None
        self.outline_item: Path | None = None
        self.pages: QWidget | None = None
        layout.addWidget(self.tabs, 1)
        self.text.viewport().installEventFilter(self)
        self.set_current(False)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
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
            entry: Entry
            for key, entry in self.entries.items():
                if entry is watched:
                    self.write(key)
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: object) -> None:
        """Make this the current panel when it is clicked.

        Arguments:
        * `event` (`object`): The mouse press (unused).
        """
        del event
        self.clicked.emit()

    def show_machine(self, machine: MachineControl, label: str = "") -> None:
        """Show a machine's controls, in place of any item.

        A tree click never replaces them (#58); a panel holds one
        machine, its header the machine's name over its bar (#135).

        Arguments:
        * `machine` (`MachineControl`): The controls.
        * `label` (`str`): The title: its file's label in the tree, as
          any item's (#183), or "" for its name.
        """
        assert not self.machines, "a panel holds one machine"
        self.drop_summary()
        self.machines.append(machine)
        self.node = None
        self.title.setText(label or machine.name)
        self.title.setStyleSheet("")
        self.show_outline(None)
        self.drop_pages()
        self._show_edit_row()
        self.header = MachineTab(machine.name)
        page: QWidget = QWidget()
        column: QVBoxLayout = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self.header)
        column.addWidget(machine.widget, 1)
        machine.widget.show()
        self.show_own(page, "Machine")

    def drop_machine(self) -> None:
        """Give up the machine shown, if any, so an item can be (#154).

        Only for a machine that is not active; its controls are kept
        (hidden, with no parent) until it is opened again.
        """
        if not self.machines:
            return
        machine: MachineControl = self.machines.pop()
        machine.widget.hide()
        machine.widget.setParent(None)
        self.header = None
        page: QWidget | None = self.show_own(None, "")
        if page is not None:
            page.deleteLater()

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
        tool: ToolValues | None = (
            None if self.outline is None else self.outline.values.tool
        )
        if tool is not None and self.outline is not None:
            # A tool's values may be typed in; its outline, never.
            tool.editing = editing
            self.outline.values.show_rows()
        row: Row
        for row in self.rows:
            entry: Entry | None = self.entries.get(row.schema.key)
            if entry is not None:
                read_only(entry, not (row.editable and editing))
        self._show_edit_row()

    def _make_title_line(self) -> QHBoxLayout:
        """Make the title line: the title, then the panel's buttons.

        [Move Left], [Move Right] (#174), [Detach] (#157) and [Close
        Panel] (#156).

        Returns:
        * (`QHBoxLayout`): The line.
        """
        self.close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_button.clicked.connect(self._press_close)
        self.close_button.hide()
        self.pin_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pin_box.toggled.connect(self._press_pin)
        self.left_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.left_button.clicked.connect(self._press_left)
        self.right_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.right_button.clicked.connect(self._press_right)
        self.left_button.setToolTip("Move this panel left")
        self.right_button.setToolTip("Move this panel right")
        self.pin_box.setToolTip(
            "Keep what this panel shows: tree clicks go to another panel"
        )
        self.close_button.setToolTip("Close this panel")
        narrow(self.left_button)
        narrow(self.right_button)
        narrow(self.close_button)
        self.title.setWordWrap(True)
        line: QHBoxLayout = QHBoxLayout()
        line.addWidget(self.title, 1)

        # The buttons packed to the right, also while the title is
        # hidden (a machine's header shows instead).
        line.addStretch(0)
        line.addWidget(self.left_button)
        line.addWidget(self.right_button)
        line.addWidget(self.pin_box)
        line.addWidget(self.close_button)
        return line

    def _make_edit_row(self) -> QWidget:
        """Make the row of [Allow Changes] and [Edit TOML File] (#153).

        Returns:
        * (`QWidget`): The row, hidden until an item can be edited.
        """
        self.editing_box.setToolTip(
            "Let this item be changed, here or with [Edit TOML File]"
        )
        self.editing_box.toggled.connect(self.set_editing)
        self.edit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.edit_button.clicked.connect(self._press_edit)
        row: QWidget = QWidget()
        line: QHBoxLayout = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        self.pages_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pages_button.setToolTip(
            "Mark the catalog's pages in catxtract, starting at its index"
        )
        self.pages_button.clicked.connect(self._press_pages)
        self.pages_button.hide()
        line.addWidget(self.editing_box)
        line.addWidget(self.edit_button)
        line.addWidget(self.pages_button)
        line.addStretch(1)
        row.hide()
        return row

    def _show_edit_row(self) -> None:
        """Show [Allow Changes] and [Edit TOML File] if they fit (#153).

        Only for an item with a file to edit, never with a machine,
        the `machines/` summary or the guide.
        """
        # An outline is changed in its [Edit] tab, never here (#758).
        self.edit_row.setVisible(
            self.node is not None
            and self.node.kind != OUTLINE
            and not self.machines
            and self.summary is None
            and edit_path(self.node) is not None
        )
        # A shop in the package is never changed (#683, #717).
        locked: bool = self.node is not None and is_read_only(self.node.path)
        if locked and self.editing:
            self.set_editing(False)
            return
        self.editing_box.setEnabled(not locked)
        self.editing_box.setToolTip(
            "The example shop is read only: [Copy Shop] makes one of your own"
            if locked
            else "Let this item be changed, here or with [Edit TOML File]"
        )
        self.editing_box.blockSignals(True)
        self.editing_box.setChecked(self.editing)
        self.editing_box.blockSignals(False)
        self.edit_button.setEnabled(self.editing)
        self.pages_button.setVisible(self.item.get("kind") == "catalog")

    def _press_close(self) -> None:
        """Close the panel ([Close Panel], #156)."""
        self.close_panel()

    def _press_pin(self, checked: bool) -> None:
        """Pin the panel, or not ([ ] Pin, #201).

        Arguments:
        * `checked` (`bool`): The box's new state.
        """
        self.pinned = checked

    def is_pinned(self) -> bool:
        """Tell whether tree clicks go past this panel (#201).

        Returns:
        * (`bool`): True when the user pinned it, or its machine is
          active (#154).
        """
        return self.pinned or self.machine_active()

    def machine_active(self) -> bool:
        """Tell whether this panel's machine is active (#154).

        Returns:
        * (`bool`): True while its machine runs, is paused or waits.
        """
        return bool(self.machines) and is_active(self.machines[0])

    def show_pin(self) -> None:
        """Show [ ] Pin: checked and greyed while the machine is active.

        Once it stops, the box shows the user's own choice again
        (#201).
        """
        active: bool = self.machine_active()
        self.pin_box.blockSignals(True)
        self.pin_box.setChecked(self.pinned or active)
        self.pin_box.blockSignals(False)
        self.pin_box.setEnabled(not active)

    def _press_left(self) -> None:
        """Move the panel one place left ([Move Left], #174)."""
        self.move_panel(-1)

    def _press_right(self) -> None:
        """Move the panel one place right ([Move Right], #174)."""
        self.move_panel(1)

    def _press_edit(self) -> None:
        """Open the item's file in an editor ([Edit TOML File])."""
        self.clicked.emit()
        self.edit_file()

    def _press_pages(self) -> None:
        """Open the catalog in `catxtract` ([Open Pages], #68)."""
        self.clicked.emit()
        self.open_pages()

    def show_guide(self, text: str) -> None:
        """Show the guide, until an item or a machine is shown (#139).

        Arguments:
        * `text` (`str`): The guide, as plain text.
        """
        self.title.setText("scraftcam")
        self.title.setStyleSheet("font-weight: bold; font-size: 16pt")
        self.guide.setText(text)
        self.show_own(self.guide, "Guide")
        self._show_edit_row()

    def hide_guide(self) -> None:
        """Take the guide away, leaving an empty panel (#200)."""
        self.hide_own_guide()
        self.title.setText("Click an item in the tree.")
        self.title.setStyleSheet(f"color: {colors().quiet}")

    def hide_own_guide(self) -> None:
        """Put [Fields] back in place of [Guide], if it is shown."""
        if self.own is self.guide:
            self.show_own(None, "")

    def show_own(self, page: QWidget | None, label: str) -> QWidget | None:
        """Show `page` as the panel's own tab, in place of [Fields].

        Arguments:
        * `page` (`QWidget | None`): The tab's content, or `None` to
          put [Fields] back.
        * `label` (`str`): The tab's label.

        Returns:
        * (`QWidget | None`): The own tab it replaced, if any (the
          caller deletes it, unless it is `guide`).
        """
        old: QWidget | None = self.own
        if old is not None:
            self.tabs.removeTab(self.tabs.indexOf(old))
            old.setParent(None)
        self.own = page
        self.tabs.setTabVisible(0, page is None)
        if page is not None:
            self.tabs.insertTab(0, page, label)
            self.tabs.setCurrentWidget(page)
        else:
            self.tabs.setCurrentIndex(0)
        return old

    def show_outline(self, path: Path | None) -> None:
        """Show `path` in the [Outline] tab, or take the tab away.

        The same file for the same item keeps its editor, so a redraw
        (the editor saving its own change) leaves it alone.  Another
        item gets a new one, though its kind's outline is the same
        file: each tool shows its own values, and the outline itself
        none (#750, #751).

        Arguments:
        * `path` (`Path | None`): The outline file, or `None` for no
          [Outline] tab.
        """
        # The same file and item: the same editor (none, none).
        item: Path | None = None if self.node is None else self.node.path
        if (
            path == self.outline_path
            and item == self.outline_item
            and (self.outline is not None) == (path is not None)
        ):
            return

        # The old editor goes.
        self.drop_outline()
        self.outline_path = path
        self.outline_item = item
        if path is None:
            return

        # The editor, by name: it imports `window`, which imports this
        # module (no cycle at load time).
        editors: ModuleType = importlib.import_module(
            f"{__package__}.outline_editor"
        )
        exposed: ModuleType = importlib.import_module(
            f"{__package__}.outline_exposed"
        )
        try:
            drawing: object = editors.drawing_from(path)
        except (OSError, ValueError) as error:
            self.say(f"{path.name}: {error}")
            return
        # A kind's outline opens on [Drawing], [Edit] greyed in a read
        # only shop (#755, #756); a tool's has a link to it (#757).
        editor: OutlineEditor = editors.OutlineEditor(drawing, path=path)
        editor.set_read_only(is_read_only(path))
        editor.show_tab(editors.ViewTab.DRAWING)
        if self.node is not None and self.node.kind != OUTLINE:
            self.show_tool_values(editor)
            kind: str = path.name.removesuffix(OUTLINE_SUFFIX)

            # Function `open_outline()`:
            def open_outline() -> None:
                """Show the kind's outline (the window's, when clicked)."""
                self.open_path(str(path))

            editor.offer_outline(
                kind.replace("_", " ").capitalize(), open_outline
            )
        exposed.EDITORS.add(editor)
        self.outline = editor
        self.tabs.addTab(editor, "Outline")

    def show_tool_values(self, editor: "OutlineEditor") -> None:
        """Show this tool's values in its kind's outline (#735, #736).

        Arguments:
        * `editor` (`OutlineEditor`): The kind's outline, in the
          [Outline] tab; it shows the tool's values beside the
          defaults, and writes only the tool's file.
        """
        defaults: dict[str, str] = {
            letter.letter: letter.default
            for letter in editor.drawing.letters
            if not letter.formula
        }

        # Function `value_problem()`:
        def value_problem(letter: str, text: str) -> str:
            """Say what is wrong with a value, as its default measures."""
            form: str = next(
                (
                    each
                    for each in ("length", "angle")
                    if not measurement_problem(
                        defaults.get(letter), UNITS[each]
                    )
                ),
                "length",
            )
            return measurement_problem(text.strip(), UNITS[form])

        # Function `save()`:
        def save(letter: str, text: str) -> str:
            """Write one letter's value into the tool's file."""
            problem: str = value_problem(letter, text)
            if problem or self.node is None:
                return problem
            changed: dict[str, object] = dict(self.item)
            changed[letter] = text.strip()
            self.written = write_item(self.node.path, changed)
            self.item = changed
            self.show_missing()

            # Its diagram beside it, drawn for it (#737b).
            values[letter] = text.strip()
            if self.outline_path is not None:
                editors: ModuleType = importlib.import_module(
                    f"{__package__}.outline_editor"
                )
                self.node.path.with_suffix(".svg").write_text(
                    editors.tool_svg(self.outline_path, values),
                    encoding="utf-8",
                )
            return ""

        values: dict[str, str] = {
            letter: str(self.item[letter])
            for letter in defaults
            if letter in self.item
        }
        tool: ToolValues = ToolValues(values, defaults, save, value_problem)
        tool.editing = self.editing
        editor.show_tool(tool)

    def show_outline_of(self, node: Node) -> None:
        """Show an item's outline: its kind's, or itself, in front.

        Arguments:
        * `node` (`Node`): The item; a kind's outline file (#730)
          opens in front, a tool shows its kind's in [Outline].
        """
        if node.kind != OUTLINE:
            self.show_outline(outline_of(node.path, self.item))
            return
        self.show_outline(node.path)
        if self.outline is not None:
            self.tabs.setCurrentWidget(self.outline)

    def show_pages(self, pages: QWidget) -> None:
        """Show a catalog's pages in the [Pages] tab (#600).

        Arguments:
        * `pages` (`QWidget`): `catxtract`'s `App` on the catalog.
        """
        if pages is not self.pages:
            self.drop_pages()
            self.pages = pages
            self.tabs.addTab(pages, "Pages")
        self.tabs.setCurrentWidget(pages)

    def drop_pages(self) -> None:
        """Close the [Pages] tab, if open: its marks are saved."""
        if self.pages is not None:
            index: int = self.tabs.indexOf(self.pages)
            if index >= 0:
                self.tabs.removeTab(index)
            self.pages.close()
            self.pages = None

    def drop_outline(self) -> None:
        """Take the [Outline] tab and its editor away, if shown."""
        if self.outline is not None:
            self.tabs.removeTab(self.tabs.indexOf(self.outline))
            self.outline.deleteLater()
            self.outline = None
        self.outline_path = None
        self.outline_item = None

    def hold_editor(self, editor: "OutlineEditor", title: str) -> None:
        """Show `editor`, on no item, as the panel's [Outline] (#595).

        For a tutorial: its outline is its own and never saved, so
        changes are allowed.

        Arguments:
        * `editor` (`OutlineEditor`): The editor, on no file.
        * `title` (`str`): The panel's title.
        """
        self.drop_outline()
        self.drop_summary()
        self.node = None
        self.hide_own_guide()
        self.title.setText(title)
        self.title.setStyleSheet("")
        self._show_edit_row()
        self.editing = True
        editor.set_read_only(False)
        self.outline = editor
        self.tabs.addTab(editor, "Outline")
        self.tabs.setCurrentWidget(editor)

    def drop_summary(self) -> None:
        """Take the `machines/` summary away, if it is shown."""
        if self.summary is not None:
            if self.own is self.summary:
                self.show_own(None, "")
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
            self.drop_pages()
        self.node = node
        self.units = units
        self._show_edit_row()
        if same and self.written and node.kind in (SHOP, FILE):
            try:
                if node.path.read_text(encoding="utf-8") == self.written:
                    return
            except (OSError, UnicodeDecodeError):
                pass
        self.written = ""
        self.drop_summary()
        self.missing.hide()
        self.copied.hide()

        # The `machines/` directory: its summary, in place of the rest.
        self.hide_own_guide()
        if is_machines_directory(node):
            self.show_outline(None)
            self.title.setText(node.label())
            self.title.setStyleSheet("")
            self.summary = MachinesView(node, self.controls, self.open_machine)
            self.show_own(self.summary, "Machines")
            return

        # The title, its tooltip the file's place in the shop (#733),
        # and the text.
        self.title.setText(node.label())
        self.title.setToolTip(shop_relative(node.path))
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

            # A tool's letters are in its [Outline] tab's table (#735).
            if outline_of(node.path, self.item) is not None:
                self.rows = [row for row in self.rows if not row.schema.short]
        self._show_edit_row()
        self.show_outline_of(node)
        self.show_sketches(sketches(self.item) if self.rows else [])
        if not self.rows:
            self.fields.hide()
            self.text.show()
            self.text.setPlainText(item_text(node))
            return
        self.fill_rows()
        self.show_missing()
        self.text.hide()

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
        # Lay the panel out first: with no text below, nothing else
        # makes Qt size the lines before they are measured (#148).
        panel_layout: QLayout | None = self.layout()
        if panel_layout is not None:
            panel_layout.activate()
        self.split.refresh()
        self.top.refresh()

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
        elif down > 0:
            self.split.setSizes([down, 0])

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
        grid.setColumnStretch(2, 1)
        self.entries = {}
        self.shown = {}
        number: int
        row: Row
        for number, row in enumerate(self.rows):
            key: str = row.schema.key
            letter: str = row.schema.letter
            label: QLabel = QLabel(f"{key} ({letter})" if letter else key)
            label.setToolTip(row.schema.meaning)
            entry: Entry
            if key == "notes":
                entry = QPlainTextEdit(row.text)
                entry.setFixedHeight(4 * entry.fontMetrics().height() + 12)
                entry.textChanged.connect(
                    functools.partial(self.notes_typed, key)
                )
                entry.installEventFilter(self)
            elif row.schema.form == "choice" and not row.schema.open:
                entry = self._choice_entry(row)
            else:
                entry = QLineEdit(row.text)
                entry.textEdited.connect(functools.partial(self.typed, key))
                entry.editingFinished.connect(
                    functools.partial(self.write, key)
                )
            read_only(entry, not (row.editable and self.editing))
            entry.setToolTip(row.schema.meaning)
            shown: QLabel = QLabel(row.shown)
            shown.setStyleSheet(f"color: {colors().quiet}")

            # Its ▶, which shows or hides how to fill it in, under it
            # (#149).
            about: QLabel = QLabel(field_help(row.schema))
            about.setTextFormat(Qt.TextFormat.MarkdownText)
            about.setWordWrap(True)
            about.hide()
            arrow: QToolButton = QToolButton()
            arrow.setArrowType(Qt.ArrowType.RightArrow)
            arrow.setAutoRaise(True)
            arrow.setToolTip("How to fill it in")
            arrow.clicked.connect(functools.partial(toggle_help, arrow, about))
            top: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignTop
            grid.addWidget(arrow, 2 * number, 0, top)
            grid.addWidget(label, 2 * number, 1, top)
            grid.addWidget(entry, 2 * number, 2)
            grid.addWidget(shown, 2 * number, 3, top)
            grid.addWidget(about, 2 * number + 1, 1, 1, 3)
            self.entries[key] = entry
            self.shown[key] = shown
            self.look(row)
        grid.setRowStretch(2 * len(self.rows), 1)
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
        entry: Entry = self.entries[row.schema.key]
        entry.setStyleSheet(bad_style() if row.problem else "")
        entry.setToolTip(row.problem or row.schema.meaning)
        self.shown[row.schema.key].setText(row.shown)

    def _choice_entry(self, row: Row) -> QComboBox:
        """Make a closed choice's drop-down, written once picked (#148).

        Arguments:
        * `row` (`Row`): The field.

        Returns:
        * (`QComboBox`): The drop-down, on the row's value (blank
          when it has none or one not in the choices).
        """
        box: QComboBox = QComboBox()
        if row.text not in row.schema.choices:
            box.addItem(row.text, row.text)
        choice: str
        for choice in row.schema.choices:
            box.addItem(CHOICE_LABELS.get(choice, choice), choice)
        box.setCurrentIndex(box.findData(row.text))
        box.activated.connect(
            functools.partial(self._picked, row.schema.key, box)
        )
        return box

    def _picked(self, key: str, box: QComboBox, _index: int) -> None:
        """Check and write a choice just picked (#148).

        Arguments:
        * `key` (`str`): The field's key.
        * `box` (`QComboBox`): Its drop-down.
        * `_index` (`int`): The item picked (`box` says its value).
        """
        self.typed(key, str(box.currentData()))
        self.write(key)

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
        entry: Entry = self.entries[key]
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
        triple: Entry | None = self.entries.get("vendor_triple")
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
        copied: str = (
            copied_from(self.node.path, self.item)
            if self.node is not None
            else ""
        )
        self.copied.setText(copied)
        self.copied.setVisible(bool(copied))

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

    def paintEvent(self, event: QPaintEvent) -> None:
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

    def createHandle(
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
    * `active` (`set[str]`): The machines marked active (#610).
    * `machine_names` (`dict[str, str]`): Each machine file's machine
      name, by its path, read once per fill.
    """

    def __init__(self) -> None:
        """Make an empty tree."""
        super().__init__()
        self.setHeaderHidden(True)
        self.nodes: dict[str, Node] = {}
        self.version: int = -1
        self.active: set[str] = set()
        self.machine_names: dict[str, str] = {}

    def mark_active(self, names: set[str]) -> None:
        """Draw the active machines' items as [Stop All] is drawn
        while one runs, their branches open and in view (#610).

        Arguments:
        * `names` (`set[str]`): The active machines' names.
        """
        # Each machine file's machine, read once per fill.
        if names == self.active:
            return
        self.active = set(names)
        path: str
        node: Node
        for path, node in self.nodes.items():
            if node.kind != FILE or node.path.parent.name != "machines":
                continue
            if path not in self.machine_names:
                self.machine_names[path] = machine_item(node).name
            item: QTreeWidgetItem | None = self.item_at_path(node.path)
            if item is None:
                continue

            # Bold white on the problem color, or as it was.
            on: bool = self.machine_names[path] in names
            font: QFont = item.font(0)
            font.setBold(on)
            item.setFont(0, font)
            item.setForeground(0, QBrush(QColor("white")) if on else QBrush())
            item.setBackground(
                0, QBrush(QColor(colors().problem)) if on else QBrush()
            )
            if on:
                parent: QTreeWidgetItem | None = item.parent()
                while parent is not None:
                    parent.setExpanded(True)
                    parent = parent.parent()
                self.scrollToItem(item)

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
        # Read again, and marked again, after this fill (#610).
        self.machine_names = {}
        self.active = set()

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

    def opened(self) -> list[str]:
        """Return the paths of the items open (#186).

        Returns:
        * (`list[str]`): The paths, sorted.
        """
        opened: set[str] = set()
        index: int
        for index in range(self.topLevelItemCount()):
            opened |= open_paths(self.topLevelItem(index))
        return sorted(opened)

    def open_items(self, paths: list[str]) -> None:
        """Open the items with these paths, as a layout kept them (#186).

        Arguments:
        * `paths` (`list[str]`): The paths; those not in the tree are
          skipped.
        """
        wanted: set[str] = set(paths)
        items: QTreeWidgetItemIterator = QTreeWidgetItemIterator(self)
        while items.value() is not None:
            item: QTreeWidgetItem = items.value()
            item.setExpanded(item.data(0, PATH_ROLE) in wanted)
            items += 1

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
