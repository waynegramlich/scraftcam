"""The outline editor's Values table (`T.gc~6.10` #637; renamed from
the letters' table, `T.sa~6.11` #802).

[Dimensions] (every letter) and [Fillets] (only those checked
"Fillet", #213) over one table of the letters, a row each, and
[Polygons] (a row per polygon: name, role, corners, #801)
over its own table, with the
letters' problems right under it, in red (#141).  Each cell is kept
and checked at every keystroke (#47).  It edits the editor's
`Drawing`, and tells the editor (`OutlineEditor`) to save and to show
its messages; split out of `outline_editor.py` so that a tool's panel
can show its kind's letters too (`T.toasl~6.8` #631).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import (  # noqa: E402
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtGui import QColor, QFont  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTabBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import theme  # noqa: E402
from .dimensions import ANGLE, RADIUS, Dimension  # noqa: E402
from .letters import (  # noqa: E402
    Letter,
    fillet_kind_problem,
    letter_problem,
    next_letter,
    use_problem,
    value_problem,
)
from .outline_file import VERTEX_NAME, Hole, Polygon, Role  # noqa: E402
from .values import (  # noqa: E402
    fillet_problems,
    formula_problem,
    refresh_formulas,
)

# pylint: enable=wrong-import-position,wrong-import-order

if TYPE_CHECKING:
    from .outline_editor import Drawing, OutlineView

# The tabs over the letters' table: every letter, or only the fillet
# radii (#213).
DIMENSIONS_TAB: int = 0
FILLETS_TAB: int = 1
POLYGONS_TAB: int = 2

# The [Polygons] table's columns (`T.sa~6.11` #801): its name and role
# are typed or chosen; its corners are only shown.
POLYGON_COLUMNS: tuple[str, ...] = ("Name", "Role", "Corners")

# The table's first row, shown only in [Fillets]: "No fillet", a
# fixed entry never edited, deleted or saved (#219, #222); the letters
# follow it, letter `i` in row `i + LETTER_ROW`.
LETTER_ROW: int = 1
NO_FILLET: tuple[str, ...] = (
    "",
    "No fillet",
    "0",
    "",
    "(No Edit Allowed)",
    "",
)

# The letters' table: its columns, each with its `Letter` field.
COLUMNS: tuple[tuple[str, str], ...] = (
    ("Letter", "letter"),
    ("Name", "name"),
    # Its value (#147); `default` in files, or `= PA / 2`: a formula
    # (`T.tfo~6.5` #430).
    ("Value", "default"),
    ("Fillet", "fillet"),  # A check box: a fillet radius (#213).
    ("Help", "help"),
    # Who sees it (`T.sa~6.11` #783b): `outline` (exported), or
    # `internal`, or a polygon's name; last, so no column moves.
    ("Scope", "scope"),
)

# A letter's scope as the table shows it.
OUTLINE_SCOPE: str = "outline"
INTERNAL_SCOPE: str = "internal"

# The table in a tool's panel (`T.toasl~6.8` #735): the outline's
# default beside this tool's value, which alone may be typed in.
TOOL_COLUMNS: tuple[str, ...] = ("Letter", "Name", "Default", "This tool")
TOOL_VALUE: int = 3


# Function `scope_of()`:
def scope_of(letter: Letter) -> str:
    """Return a letter's scope as the table shows it (#783b).

    Arguments:
    * `letter` (`Letter`): The letter.

    Returns:
    * (`str`): Its polygon's name, `internal` or `outline`.
    """
    if letter.polygon:
        return letter.polygon
    return INTERNAL_SCOPE if letter.internal else OUTLINE_SCOPE


# Function `_nothing()`:
def _nothing() -> None:
    """Do nothing: a `ToolValues` not shown yet draws nothing."""


# A tool's material when it names none: huge swaths of tools are high
# speed steel (`T.sa~6.11` #816, #821).
DEFAULT_TOOL_MATERIAL: str = "HSS"


# Class `ToolValues`:
@dataclass(slots=True)
class ToolValues:
    """A tool's own values for its kind's letters (#735, #736).

    Attributes:
    * `values` (`dict[str, str]`): This tool's values, by letter.
    * `defaults` (`dict[str, str]`): The outline's defaults, by
      letter.
    * `save` (`Callable[[str, str], str]`): Writes one letter's value
      into the tool's file (never the outline), giving the problem
      ("" when written).
    * `check` (`Callable[[str, str], str]`): The problem with a value
      as it is typed, or "".
    * `material` (`str`): The tool's material, which hatches its
      drawing (HSS when it names none, `T.sa~6.11` #821, #840).
    * `name` (`str`): The tool's name for its solid ("": the
      outline's, #827).
    * `editing` (`bool`): True while the tool may be changed.
    * `redraw` (`Callable[[], None]`): Draws the outline for the
      values as they are now (the editor's, `show_tool()`).

    Constructor:
    * `ToolValues(values, defaults, save, check, material, name)`
    """

    # Constructor arguments:
    values: dict[str, str] = field(init=True)
    defaults: dict[str, str] = field(init=True)
    save: Callable[[str, str], str] = field(init=True)
    check: Callable[[str, str], str] = field(init=True)
    material: str = field(init=True, default=DEFAULT_TOOL_MATERIAL)
    name: str = field(init=True, default="")

    # Remaining attributes (alphabetized):
    editing: bool = field(init=False, default=False)
    redraw: Callable[[], None] = field(init=False, default=_nothing)


# Class `LiveDelegate`:
class LiveDelegate(QStyledItemDelegate):
    """Edits the letters' cells, keeping each keystroke (#47).

    Attributes:
    * `letters` (`ValuesTable`): The table it edits.
    """

    # Method `LiveDelegate.__init__()`:
    def __init__(self, letters: ValuesTable) -> None:
        """Make the delegate of a letters' table.

        Arguments:
        * `letters` (`ValuesTable`): The table.
        """
        super().__init__(letters.table)
        self.letters: ValuesTable = letters

    # Method `LiveDelegate.createEditor()`:
    def createEditor(
        self,
        parent: QWidget,
        _option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget:
        """Return an entry that keeps and checks every keystroke."""
        entry: QLineEdit = QLineEdit(parent)
        row: int = index.row()
        column: int = index.column()

        # Function `typed()`:
        def typed(text: str) -> None:
            """Keep the text so far, check it, mark the entry."""
            self.letters.keep(row, column, text)
            cell: QTableWidgetItem | None = self.letters.table.item(
                row, column
            )
            problem: str = "" if cell is None else cell.toolTip()
            entry.setToolTip(problem)
            entry.setStyleSheet(
                f"background: {theme.colors().bad}" if problem else ""
            )

        entry.textEdited.connect(typed)
        return entry

    # Method `LiveDelegate.setEditorData()`:
    def setEditorData(
        self,
        editor: QWidget,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        """Fill a fresh entry; never overwrite what is being typed.

        Marking a cell bad changes its data, which would otherwise put
        the cell's old text back into the entry.
        """
        if isinstance(editor, QLineEdit) and editor.isModified():
            return
        super().setEditorData(editor, index)


# Class `PolygonsTable`:
class PolygonsTable(QTableWidget):
    """The Values table's [Polygons] (`T.sa~6.11` #801): a row per
    polygon, its name typed, its role chosen, its corners shown.

    Attributes:
    * `values` (`ValuesTable`): The Values table it is in, for its
      drawing, view, saving and messages.
    """

    # Method `PolygonsTable.__init__()`:
    def __init__(self, values: ValuesTable) -> None:
        """Make the empty table.

        Arguments:
        * `values` (`ValuesTable`): The Values table it is in.
        """
        super().__init__(0, len(POLYGON_COLUMNS))
        self.values: ValuesTable = values
        self.setHorizontalHeaderLabels(list(POLYGON_COLUMNS))
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.itemChanged.connect(self.edited)

    # Method `PolygonsTable.fill()`:
    def fill(self) -> None:
        """Show every polygon, a row each."""
        drawing: Drawing = self.values.drawing
        read_only: bool = self.values.read_only
        self.blockSignals(True)
        self.setRowCount(len(drawing.polygons))
        loops: list[list[int]] = drawing.loops()
        row: int
        polygon: Polygon
        for row, polygon in enumerate(drawing.polygons):
            self.setItem(row, 0, QTableWidgetItem(polygon.name))
            role: QComboBox = QComboBox()
            role.addItems([each.value for each in Role])
            role.setCurrentText(polygon.role.value)
            role.setEnabled(not read_only)
            role.currentTextChanged.connect(self.role_chooser(row))
            self.setCellWidget(row, 1, role)
            corners: QTableWidgetItem = QTableWidgetItem(
                " ".join(drawing.names[at] for at in loops[row])
            )
            corners.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.setItem(row, 2, corners)
        triggers: type[QAbstractItemView.EditTrigger] = (
            QAbstractItemView.EditTrigger
        )
        self.setEditTriggers(
            triggers.NoEditTriggers
            if read_only
            else triggers.DoubleClicked
            | triggers.SelectedClicked
            | triggers.EditKeyPressed
        )
        self.blockSignals(False)

    # Method `PolygonsTable.role_chooser()`:
    def role_chooser(self, row: int) -> Callable[[str], None]:
        """Return what a role choice in a row does.

        Arguments:
        * `row` (`int`): The polygon's row.

        Returns:
        * (`Callable[[str], None]`): Sets its polygon's role and saves.
        """

        # Function `chosen()`:
        def chosen(text: str) -> None:
            """Set the polygon's role.

            Arguments:
            * `text` (`str`): The role chosen.
            """
            self.values.drawing.polygons[row].role = Role(text)
            self.values.save()

        return chosen

    # Method `PolygonsTable.edited()`:
    def edited(self, item: QTableWidgetItem) -> None:
        """Keep a polygon's typed name: a name must be a name and not
        another polygon's; its letters keep to it.

        Arguments:
        * `item` (`QTableWidgetItem`): The cell.
        """
        drawing: Drawing = self.values.drawing
        polygon: Polygon = drawing.polygons[item.row()]
        text: str = item.text().strip()
        if item.column() == 0 and text != polygon.name:
            names: list[str] = [each.name for each in drawing.polygons]
            if not VERTEX_NAME.fullmatch(text) or text in names:
                self.values.view.message = (
                    f"{text!r} is not a name for a polygon: a letter, then"
                    " letters, digits or _, not another polygon's."
                )
                self.fill()
                self.values.show_message()
                return
            letter: Letter
            for letter in drawing.letters:
                if letter.polygon == polygon.name:
                    letter.polygon = text
            polygon.name = text
        self.values.view.message = ""
        self.values.save()
        self.values.show_message()


# Class `ValuesTable`:
# The table's widgets and its state, each signal answered by a method.
# pylint: disable-next=too-many-instance-attributes
class ValuesTable(QWidget):
    """The Values table: the letters' and the polygons' tables, their
    tabs, and the letters' problems.

    Attributes:
    * `drawing` (`Drawing`): The outline whose letters it shows.
    * `view` (`OutlineView`): The drawing area, lit and told of
      changes.
    * `save` (`Callable[[], None]`): Saves the outline (the editor's).
    * `show_message` (`Callable[[], None]`): Shows the messages (the
      editor's).
    * `arm` (`Callable[[str | None], None]`): Arms a fillet letter,
      or disarms (`None`) (the editor's, #214).
    * `read_only` (`bool`): True while the outline may not be changed
      (#590).
    * `table` (`QTableWidget`): The letters, a row each.
    * `tabs` (`QTabBar`): [Dimensions] and [Fillets], over the table.
    * `new_fillet` (`QPushButton`): [New Fillet Dimension], shown
      in [Fillets] only (#214).
    * `polygon_table` (`PolygonsTable`): [Polygons], shown in place
      of `table` (#801).
    * `problems` (`QLabel`): The problems, a line each, red, right
      under the table (#141).
    * `letter_lines` (`list[str]`): The letters' problems, a line
      each, shown above the outline's own.
    * `renaming` (`dict[int, str]`): By table row, a letter's last good
      name while its name is being typed and is not good yet: the
      name its uses still carry (`T.tfo~6.5` #441).
    * `tool` (`ToolValues | None`): In a tool's panel, its own values,
      shown beside the defaults (#735); `None` for an outline.
    """

    # Method `ValuesTable.__init__()`:
    def __init__(
        self,
        drawing: Drawing,
        view: OutlineView,
        *,
        save: Callable[[], None],
        show_message: Callable[[], None],
        arm: Callable[[str | None], None],
    ) -> None:
        """Make the table, its tabs and its problem line (#213).

        Arguments:
        * `drawing` (`Drawing`): The outline.
        * `view` (`OutlineView`): The drawing area.
        * `save` (`Callable[[], None]`): Saves the outline.
        * `show_message` (`Callable[[], None]`): Shows the messages.
        * `arm` (`Callable[[str | None], None]`): Arms a fillet letter.
        """
        super().__init__()
        self.drawing: Drawing = drawing
        self.view: OutlineView = view
        self.save: Callable[[], None] = save
        self.show_message: Callable[[], None] = show_message
        self.arm: Callable[[str | None], None] = arm
        self.read_only: bool = False
        self.tool: ToolValues | None = None
        self.table: QTableWidget = QTableWidget(0, len(COLUMNS))
        self.problems: QLabel = QLabel("")
        self.renaming: dict[int, str] = {}
        self.letter_lines: list[str] = []
        self.tabs: QTabBar = QTabBar()
        self.new_fillet: QPushButton = QPushButton("New Fillet Dimension")
        self.polygon_table: PolygonsTable = PolygonsTable(self)

        # The tabs over the table, the problems under it (#141).
        self.table.setHorizontalHeaderLabels([title for title, _ in COLUMNS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setItemDelegate(LiveDelegate(self))
        # One click on a cell edits it, so typing goes into the cell:
        # a key typed onto a cell not being edited half-started an edit
        # and could fire a button's key (`n` of `in`: [Dimension]).
        triggers: type[QAbstractItemView.EditTrigger] = (
            QAbstractItemView.EditTrigger
        )
        self.table.setEditTriggers(
            triggers.CurrentChanged
            | triggers.SelectedClicked
            | triggers.DoubleClicked
            | triggers.EditKeyPressed
        )
        self.problems.setWordWrap(True)
        self.problems.setStyleSheet(f"color: {theme.colors().problem}")
        stack: QVBoxLayout = QVBoxLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab("Dimensions")
        self.tabs.addTab("Fillets")
        self.tabs.addTab("Polygons")
        self.tabs.currentChanged.connect(self.show_rows)
        self.new_fillet.clicked.connect(self.add_fillet)
        self.new_fillet.setVisible(False)
        self.polygon_table.setVisible(False)
        stack.addWidget(self.tabs)
        stack.addWidget(self.table)
        stack.addWidget(self.polygon_table)
        stack.addWidget(self.new_fillet, 0, Qt.AlignmentFlag.AlignLeft)
        stack.addWidget(self.problems)

        # A click on a row arms it in [Fillets]; pointing at a row
        # lights its letter's uses (#224), leaving the table puts
        # them out.
        self.table.itemChanged.connect(self.letter_edited)
        self.table.cellClicked.connect(self.row_clicked)
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self.hover_row)
        self.table.viewport().installEventFilter(self)

    # Method `ValuesTable.eventFilter()`:
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Put the lit letter out when the pointer leaves the table.

        Arguments:
        * `watched` (`QObject`): The table's viewport.
        * `event` (`QEvent`): What happened to it.

        Returns:
        * (`bool`): Never taken: `False`.
        """
        if (
            watched is self.table.viewport()
            and event.type() == QEvent.Type.Leave
        ):
            self.view.light_letter("")
        return False

    # Method `ValuesTable.hover_row()`:
    def hover_row(self, row: int, _column: int) -> None:
        """Light the uses of the letter pointed at (#224).

        Arguments:
        * `row` (`int`): The table row.
        """
        self.view.light_letter(
            ""
            if row < LETTER_ROW
            else self.drawing.letters[row - LETTER_ROW].letter
        )

    # Method `ValuesTable.frame_row()`:
    def frame_row(self, corner: int) -> None:
        """Make the row of the letter rounding a corner pointed at bold
        (#224); every other row plain.

        Arguments:
        * `corner` (`int`): The corner, or -1.
        """
        letter: str = self.view.fillets().get(corner, "")
        self.table.blockSignals(True)
        index: int
        each: Letter
        for index, each in enumerate(self.drawing.letters):
            column: int
            for column in range(len(COLUMNS)):
                item: QTableWidgetItem | None = self.table.item(
                    LETTER_ROW + index, column
                )
                if item is not None:
                    font: QFont = item.font()
                    font.setBold(bool(letter) and each.letter == letter)
                    item.setFont(font)
        self.table.blockSignals(False)

    # Method `ValuesTable.row_clicked()`:
    def row_clicked(self, row: int, _column: int) -> None:
        """A click on a [Fillets] row arms it, or disarms it if armed
        (#214).

        Arguments:
        * `row` (`int`): The table row.
        """
        if self.tabs.currentIndex() != FILLETS_TAB:
            return
        letter: str = (
            ""
            if row < LETTER_ROW
            else self.drawing.letters[row - LETTER_ROW].letter
        )
        self.arm(None if letter == self.view.armed else letter)

    # Method `ValuesTable.light_armed()`:
    def light_armed(self) -> None:
        """Select the armed letter's row, and only it."""
        self.table.clearSelection()
        armed: str | None = self.view.armed
        if armed is None:
            return
        rows: list[int] = [0] + [
            LETTER_ROW + index
            for index, letter in enumerate(self.drawing.letters)
            if letter.letter == armed
        ]
        self.table.selectRow(rows[-1] if armed else 0)

    # Method `ValuesTable.show_rows()`:
    def show_rows(self) -> None:
        """Show every letter in [Dimensions], only the fillet radii in
        [Fillets], with [New Fillet Dimension] there (#213, #214)."""
        fillets: bool = (
            self.tool is None and self.tabs.currentIndex() == FILLETS_TAB
        )
        self.table.setRowHidden(0, not fillets)
        index: int
        letter: Letter
        for index, letter in enumerate(self.drawing.letters):
            self.table.setRowHidden(
                LETTER_ROW + index, fillets and not letter.fillet
            )
        self.new_fillet.setVisible(fillets)
        # In [Fillets] a click arms a row (#214), so a cell is edited
        # only by a double click there.
        triggers: type[QAbstractItemView.EditTrigger] = (
            QAbstractItemView.EditTrigger
        )
        locked: bool = (
            not self.tool.editing if self.tool is not None else self.read_only
        )
        self.table.setEditTriggers(
            triggers.NoEditTriggers
            if locked
            else triggers.DoubleClicked | triggers.EditKeyPressed
            if fillets
            else triggers.CurrentChanged
            | triggers.SelectedClicked
            | triggers.DoubleClicked
            | triggers.EditKeyPressed
        )
        if not fillets:
            self.arm(None)

        # [Polygons] shows its own table in place of the letters'.
        polygons: bool = (
            self.tool is None and self.tabs.currentIndex() == POLYGONS_TAB
        )
        self.table.setVisible(not polygons)
        self.polygon_table.setVisible(polygons)
        if polygons:
            self.polygon_table.fill()

    # Method `ValuesTable.add_fillet()`:
    def add_fillet(self) -> None:
        """[New Fillet Dimension]: a new letter, checked "Fillet",
        ready to be named (#214)."""
        self.drawing.letters.append(
            replace(
                next_letter(self.drawing.letters),
                name="Fillet radius",
                fillet=True,
            )
        )
        self.fill_table()
        self.table.setCurrentCell(len(self.drawing.letters), 1)

    # Method `ValuesTable.fill_table()`:
    def fill_table(self) -> None:
        """Show every letter, a row each, its problems marked.

        No cell is left current: one would be edited at once (a click
        edits), taking the keys the buttons answer to.
        """
        if self.tool is not None:
            self.fill_tool_table(self.tool)
            return
        self.table.blockSignals(True)
        self.renaming.clear()
        self.table.setRowCount(LETTER_ROW + len(self.drawing.letters))
        column: int
        text: str
        for column, text in enumerate(NO_FILLET):
            fixed: QTableWidgetItem = QTableWidgetItem(text)
            fixed.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(0, column, fixed)
        index: int
        letter: Letter
        for index, letter in enumerate(self.drawing.letters):
            attribute: str
            for column, (_, attribute) in enumerate(COLUMNS):
                self.table.setItem(
                    LETTER_ROW + index, column, self.cell(letter, attribute)
                )
        self.table.setCurrentCell(-1, -1)
        self.table.blockSignals(False)
        self.show_rows()
        self.light_armed()
        self.view.setFocus()
        self.check_letters()

    # Method `ValuesTable.show_tool()`:
    def show_tool(self, tool: ToolValues) -> None:
        """Show a tool's own values beside the defaults (#735).

        Arguments:
        * `tool` (`ToolValues`): The tool's values, and how to write
          them.
        """
        self.tool = tool
        self.tabs.hide()
        self.table.setColumnCount(len(TOOL_COLUMNS))
        self.table.setHorizontalHeaderLabels(list(TOOL_COLUMNS))
        self.fill_table()

    # Method `ValuesTable.fill_tool_table()`:
    def fill_tool_table(self, tool: ToolValues) -> None:
        """Show each letter: its name, its default, this tool's value.

        Only a value given (not a formula's) may be typed in, and only
        while the tool may be changed.

        Arguments:
        * `tool` (`ToolValues`): The tool's values.
        """
        self.table.blockSignals(True)
        self.table.setRowCount(LETTER_ROW + len(self.drawing.letters))
        self.table.setRowHidden(0, True)
        index: int
        letter: Letter
        for index, letter in enumerate(self.drawing.letters):
            texts: tuple[str, ...] = (
                letter.letter,
                letter.name,
                f"= {letter.formula}"
                if letter.formula
                else tool.defaults.get(letter.letter, ""),
                letter.default
                if letter.formula
                else tool.values.get(letter.letter, ""),
            )
            column: int
            text: str
            for column, text in enumerate(texts):
                item: QTableWidgetItem = QTableWidgetItem(text)
                if column != TOOL_VALUE or letter.formula:
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(LETTER_ROW + index, column, item)
        self.table.setCurrentCell(-1, -1)
        self.table.blockSignals(False)
        self.show_rows()

    # Method `ValuesTable.cell()`:
    @staticmethod
    def cell(letter: Letter, attribute: str) -> QTableWidgetItem:
        """Return a letter's cell: its text, or for "Fillet" a check
        box that a click flips, never edited as text (#213).  A formula
        letter's value cell shows `= ` and its formula (#430).

        Arguments:
        * `letter` (`Letter`): The letter.
        * `attribute` (`str`): Its field shown (see `COLUMNS`).

        Returns:
        * (`QTableWidgetItem`): The cell.
        """
        if attribute == "default" and letter.formula:
            return QTableWidgetItem(f"= {letter.formula}")
        if attribute == "scope":
            return QTableWidgetItem(scope_of(letter))
        if attribute != "fillet":
            return QTableWidgetItem(getattr(letter, attribute))
        item: QTableWidgetItem = QTableWidgetItem()
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
        )
        item.setCheckState(
            Qt.CheckState.Checked if letter.fillet else Qt.CheckState.Unchecked
        )
        return item

    # Method `ValuesTable.new_letter()`:
    def new_letter(self) -> None:
        """Add a row for the first free letter, ready to be named; in
        [Fillets], a fillet radius (#214)."""
        if self.tabs.currentIndex() == FILLETS_TAB:
            self.add_fillet()
            return
        self.drawing.letters.append(next_letter(self.drawing.letters))
        self.fill_table()
        self.table.setCurrentCell(len(self.drawing.letters), 1)

    # Method `ValuesTable.letter_edited()`:
    def letter_edited(self, item: QTableWidgetItem) -> None:
        """Keep a finished cell's text in its letter, then check them.

        Arguments:
        * `item` (`QTableWidgetItem`): The cell.
        """
        if item.row() < LETTER_ROW:
            return
        if self.tool is not None:
            self.tool_edited(self.tool, item)
            return
        if COLUMNS[item.column()][1] == "fillet":
            letter: Letter = self.drawing.letters[item.row() - LETTER_ROW]
            checked: bool = item.checkState() == Qt.CheckState.Checked
            if not checked and self._uses(letter.letter, fillets=True):
                # Still a fillet radius somewhere (#225): stays checked.
                self.view.message = (
                    f"{letter.letter} rounds "
                    f"{self._uses(letter.letter, fillets=True)}: "
                    "it stays a fillet radius."
                )
                self.table.blockSignals(True)
                item.setCheckState(Qt.CheckState.Checked)
                self.table.blockSignals(False)
                self.view.light_letter(letter.letter)  # Its uses (#245).
                self.show_message()
                return
            letter.fillet = checked
            self.check_letters()
            self.save()
        else:
            self.keep(item.row(), item.column(), item.text())

    # Method `ValuesTable.keep_scope()`:
    def keep_scope(self, letter: Letter, scope: str) -> None:
        """Set who sees a letter (#783b): `outline` (or nothing),
        `internal`, or a polygon's name; anything else is refused,
        saying why, and the cell shows the scope kept.

        Arguments:
        * `letter` (`Letter`): The letter.
        * `scope` (`str`): The scope typed.
        """
        polygons: list[str] = [
            polygon.name for polygon in self.drawing.polygons
        ]
        if scope in ("", OUTLINE_SCOPE, INTERNAL_SCOPE):
            letter.polygon = ""
            letter.internal = scope == INTERNAL_SCOPE
        elif scope in polygons:
            letter.polygon = scope
            letter.internal = True
        else:
            self.view.message = (
                f"{scope!r} is not {OUTLINE_SCOPE}, {INTERNAL_SCOPE} or a"
                f" polygon ({', '.join(polygons)})."
            )
        self.fill_table()
        self.show_message()
        self.save()

    # Method `ValuesTable.tool_edited()`:
    def tool_edited(self, tool: ToolValues, item: QTableWidgetItem) -> None:
        """Write a tool's finished value into its file (#736), then
        draw and show it, or say why not.

        Arguments:
        * `tool` (`ToolValues`): The tool's values.
        * `item` (`QTableWidgetItem`): The cell.
        """
        if item.column() != TOOL_VALUE:
            return
        letter: Letter = self.drawing.letters[item.row() - LETTER_ROW]
        text: str = item.text().strip()
        problem: str = tool.save(letter.letter, text)
        if not problem:
            tool.values[letter.letter] = text
            tool.redraw()
        self.fill_table()
        self.problems.setText(problem)

    # Method `ValuesTable.delete()`:
    def delete(self) -> None:
        """[Delete]: the selected corners and dimensions; with none,
        the letter armed in [Fillets] or the table's current row,
        refused while it is in use, its uses named (#215)."""
        view: OutlineView = self.view
        if view.chosen_points or view.chosen_dimensions:
            view.delete_selected()
            return
        letter: str = ""
        row: int = self.table.currentRow()
        if self.tabs.currentIndex() == FILLETS_TAB and view.armed:
            letter = view.armed
        elif row >= LETTER_ROW:
            letter = self.drawing.letters[row - LETTER_ROW].letter
        if not letter:
            view.delete_selected()  # Says what to select.
            return
        used: str = self._uses(letter)
        if used:
            view.light_letter(letter)  # Its uses shown (#245).
            view.message = f"{letter} is used by {used}: not deleted."
            view.scene().update()
            self.show_message()
            return
        view.history.remember(self.drawing.snapshot())
        self.drawing.letters[:] = [
            each for each in self.drawing.letters if each.letter != letter
        ]
        if self.drawing.note_radius == letter:
            self.drawing.note_radius = ""
        view.armed = None
        view.message = ""
        self.fill_table()
        self.save()

    # Method `ValuesTable._uses()`:
    def _uses(self, letter: str, fillets: bool = False) -> str:
        """Return what uses a letter, in words ("" for nothing).

        Arguments:
        * `letter` (`str`): The letter.
        * `fillets` (`bool`): Only its fillets.

        Returns:
        * (`str`): E.g. "2 fillets and 1 dimension".
        """
        rounds: int = sum(
            1
            for dimension in self.drawing.dimensions
            if dimension.letter == letter and dimension.kind == RADIUS
        )
        sizes: int = (
            0
            if fillets
            else sum(
                1
                for dimension in self.drawing.dimensions
                if dimension.letter == letter and dimension.kind != RADIUS
            )
        )
        words: list[str] = [
            f"{count} {name}{'' if count == 1 else 's'}"
            for count, name in ((rounds, "fillet"), (sizes, "dimension"))
            if count
        ]
        return " and ".join(words)

    # Method `ValuesTable.keep()`:
    def keep(self, row: int, column: int, text: str) -> None:
        """Keep a cell's text in its letter, then check the letters.

        A value starting `=` makes a formula letter (#430); any other
        makes it a letter given a value.  Formula letters' values are
        worked out again after every change.

        Arguments:
        * `row` (`int`): The letter's table row (see `LETTER_ROW`).
        * `column` (`int`): The cell's column (see `COLUMNS`).
        * `text` (`str`): The cell's text so far.
        """
        if self.tool is not None:
            letter_of: Letter = self.drawing.letters[row - LETTER_ROW]
            cell: QTableWidgetItem | None = self.table.item(row, column)
            if cell is not None:
                cell.setToolTip(self.tool.check(letter_of.letter, text))
            return
        attribute: str = COLUMNS[column][1]
        letter: Letter = self.drawing.letters[row - LETTER_ROW]
        kept: str = text.strip()
        if attribute == "scope":
            self.keep_scope(letter, kept)
            return
        if attribute == "letter":
            self.rename(row, kept)
            refresh_formulas(self.drawing.letters)
            self.check_letters()
            self.save()
            return
        if attribute == "default":
            letter.formula = kept[1:].strip() if kept.startswith("=") else ""
            if letter.formula:
                kept = ""
        setattr(letter, attribute, kept)
        refresh_formulas(self.drawing.letters)
        self.check_letters()
        self.save()

    # Method `ValuesTable.rename()`:
    def rename(self, row: int, name: str) -> None:
        """Rename a letter, and everything that uses it with it (#441):
        its dimensions, holes, the fillets' note letter and the
        formulas that name it.  Its uses follow only a good name, one
        not taken (`letter_problem()`), so that typing `OAL` through
        `O` and `OA`, or a name half typed, never leaves them blank.

        Arguments:
        * `row` (`int`): The letter's table row (see `LETTER_ROW`).
        * `name` (`str`): Its new name, as typed so far.
        """
        index: int = row - LETTER_ROW
        letter: Letter = self.drawing.letters[index]
        carried: str = self.renaming.get(row, letter.letter)
        letter.letter = name
        taken: bool = any(
            other.letter.lower() == name.lower()
            for place, other in enumerate(self.drawing.letters)
            if place != index
        )
        if taken or letter_problem(self.drawing.letters, index):
            self.renaming[row] = carried
            return
        self.renaming.pop(row, None)
        if carried == name:
            return
        dimension: Dimension
        for dimension in self.drawing.dimensions:
            if dimension.letter == carried:
                dimension.letter = name
        hole: Hole
        for hole in self.drawing.holes:
            if hole.letter == carried:
                hole.letter = name
        if self.drawing.note_radius == carried:
            self.drawing.note_radius = name
        pattern: re.Pattern[str] = re.compile(rf"\b{re.escape(carried)}\b")
        other: Letter
        for other in self.drawing.letters:
            if other.formula:
                other.formula = pattern.sub(name, other.formula)

    # Method `ValuesTable.check_letters()`:
    def check_letters(self) -> None:
        """Mark each bad letter or default, and show the first problem."""
        self.table.blockSignals(True)
        bad: QColor = QColor(theme.colors().bad)
        problems: list[str] = []
        row: int
        letter: Letter
        trouble: dict[str, str] = self.fillet_trouble()
        for row, letter in enumerate(self.drawing.letters):
            kinds: set[str] = {
                "angle" if dimension.kind == ANGLE else "length"
                for dimension in self.drawing.dimensions
                if dimension.letter == letter.letter
            }
            found: str
            column: int
            for found, column in (
                (letter_problem(self.drawing.letters, row), 0),
                (
                    formula_problem(self.drawing.letters, row)
                    or value_problem(letter.default)
                    or use_problem(letter.letter, letter.default, kinds)
                    or trouble.get(letter.letter, ""),
                    2,
                ),
                (fillet_kind_problem(letter, kinds), 3),
            ):
                cell: QTableWidgetItem | None = self.table.item(
                    LETTER_ROW + row, column
                )
                if cell is not None:
                    cell.setBackground(bad if found else QColor(0, 0, 0, 0))
                    # A good formula letter's tip is its value (#430).
                    cell.setToolTip(
                        found
                        or (
                            f"= {letter.default}"
                            if column == 2 and letter.formula
                            else ""
                        )
                    )
                if found:
                    # A message naming its letter first is not given it
                    # twice (#143).
                    problems.append(
                        found
                        if found.startswith(f"{letter.letter} ")
                        else f"{letter.letter}: {found}"
                    )
        self.table.blockSignals(False)
        self.letter_lines = problems
        self.show_message()

    # Method `ValuesTable.fillet_trouble()`:
    def fillet_trouble(self) -> dict[str, str]:
        """Find the fillets too big for their edges (#127), mark them
        in the drawing, and return each one's problem by letter.

        Returns:
        * (`dict[str, str]`): The first problem of each fillet letter.
        """
        self.view.trouble = fillet_problems(
            self.drawing.points,
            self.drawing.letters,
            self.drawing.dimensions,
            self.drawing.loops(),
        )
        self.view.follow()  # The drawing follows the values (#148).
        letters: dict[int, str] = {
            dimension.start: dimension.letter
            for dimension in self.drawing.dimensions
            if dimension.kind == RADIUS
        }
        trouble: dict[str, str] = {}
        corner: int
        message: str
        for corner, message in self.view.trouble.items():
            trouble.setdefault(letters[corner], message)
        return trouble
