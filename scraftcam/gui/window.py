"""A window of the GUI: the top line, the action rows and the panels.

From the top down (`T.g~6` #82):

* The top line: [Stop All] (always first and shown: greyed while no
  machine runs, red, bold and boxed while any does, #2, #100),
  [Tree] (shows or hides the tree, on the left edge, #70), the shop's
  and the design's names, the latest message (red for a problem,
  #95), [+ Panel] and [x].
* The action rows of the item selected (#73, #75); for now only
  [New Shop], while there is no shop, which opens `NewShopDialog`
  (#97, #98; it also opens by itself when the GUI starts with no
  shop, unless headless).
* The panels, side by side, with a splitter between them; [+ Panel]
  adds one (#94).

Each window draws from the one `App` (`app.py`), and redraws whenever
it changes, so all of the windows agree (#3).  A window that controls
a running machine refuses to close (#67).

With `--mcp PORT`, `run()` serves MCP on that port, with the GUI's
functions (`window_exposed.py`, #577, #585).
"""

import functools
import importlib
import os
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, Protocol

from ..packages import require
from ..shops import CATALOG_PAGES

# Only for its type: imported when a catalog is opened (#68), since it
# fetches the PDF packages.
if TYPE_CHECKING:
    from ..catalog.catxtract import App as Pages
from . import prompt, theme
from .app import (
    MACHINE_KINDS,
    MANUAL_PREFIX,
    NEW_MACHINE_KINDS,
    NEW_SHOP_DIRECTORY,
    UNIT_LABELS,
    UNITS,
    App,
    Message,
    add_ignores,
    controller_templates,
    ignores_needed,
    pdf_pages,
)
from .editor import HINT, editor_command
from .fields import shop_units
from .layout import read_layout, save_layout
from .machines import (
    MachineControl,
    is_active,
    is_catalogs_directory,
    is_machines_directory,
    machine_item,
)
from .theme import colors
from .tree import SHOP, Node, edit_path
from .views import (
    Panel,
    TreeView,
    TreeWatcher,
    narrow,
    splitter,
)

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import (  # noqa: E402
    QCoreApplication,
    QEvent,
    QObject,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import (  # noqa: E402
    QCloseEvent,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QResizeEvent,
    QScreen,
)
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

# The top line's button that closes the program (#114, #156).
EXIT: str = "Exit"

# [Stop All]'s room beyond its text, in pixels: twice its running
# look's padding (10) and border (3), and a little more.
STOP_ROOM: int = 2 * 10 + 2 * 3 + 6

# A new window's size (#109): small, so SolidCraft fits beside it.
WIDTH: int = 720
HEIGHT: int = 480


# The least width of `NewShopDialog`'s directory, in pixels.
DIRECTORY_WIDTH: int = 360

# The most of the window's width the tree takes when it is fitted to
# its labels (#22); the user can drag it wider.
TREE_MOST: float = 0.5

# How long `fit_width()` waits for the window's new width (ms).
FIT_MS: int = 1000

# How long `quit` waits, so its answer is sent before the GUI closes.
QUIT_DELAY_MS: int = 200

# How often the GUI looks for a signal to close, while it waits for
# the machines to stop (milliseconds, #56).
STOP_MS: int = 250

# Every open window, oldest first (the command port's `window`).
WINDOWS: list["Window"] = []

# What connects a machine by name (`run()`'s `connect`), if anything.
CONNECT: list[Callable[[str], MachineControl | None]] = []

# The `catxtract` windows open, by their `catalog.toml`: one each, in
# a window of its own, as a page needs all the screen it can get
# (`T.c~6.3` #68).
CATALOG_WINDOWS: dict[str, "Pages"] = {}

# [New Window] (#200).
NEW_WINDOW: str = "New Window"


# Function `make_application()`:
def make_application(*, headless: bool) -> QApplication:
    """Make the one `QApplication`, or return the one already made.

    Arguments:
    * `headless` (`bool`): True to draw offscreen
      (`prompt.use_headless()`).

    Returns:
    * (`QApplication`): The application.
    """
    if headless:
        prompt.use_headless()
    existing: object = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication(sys.argv[:1])


# Function `redraw_windows()`:
def redraw_windows() -> None:
    """Draw every window again, in the scheme now in use (#24)."""
    widget: QWidget
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, Window):
            widget.tree.version = -1
            widget.redraw()
            panel: Panel
            for panel in widget.panels:
                panel.restyle()


# Function `delete_windows()`:
def delete_windows() -> None:
    """Close and delete every top level widget, now.

    A widget whose signals are connected to its own methods is kept
    alive by them until Python exits; PySide then deletes what is
    left in no safe order, and with many widgets left (as the tests
    leave) that can crash Python after everything has passed.  Called
    before that (`atexit`), this deletes them in Qt's own order.
    """
    application: object = QApplication.instance()
    if not isinstance(application, QApplication):
        return
    top: QWidget
    for top in application.topLevelWidgets():
        top.close()
        top.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


# Function `run()`:
def run(
    model: App,
    *,
    headless: bool,
    mcp_port: int,
    makers: "MachineMakers | None" = None,
    first_panel: "FirstPanel | None" = None,
) -> int:
    """Show the first window, and run Qt until the last one closes.

    Arguments:
    * `model` (`App`): What every window shows.
    * `headless` (`bool`): True to draw offscreen.
    * `mcp_port` (`int`): The MCP port, or 0 for none.
    * `first_panel` (`FirstPanel | None`): What the first panel
      opens (`outline_panel.OutlinePanel`: an outline, a tutorial, a
      recording, #S5); it may stop at once (a tutorial checked
      headless), and it finishes once Qt does.
    * `makers` (`MachineMakers | None`): What makes machines'
      controls (their HMIs): the first window's, once Qt is up (step
      5, #53), and any the user opens later (#607).

    Returns:
    * (`int`): Qt's exit code, 0 normally, or 1 when the port can
      not be opened.
    """
    application: QApplication = make_application(headless=headless)
    CONNECT.clear()
    if makers is not None:
        CONNECT.append(makers.connect)
    theme.follow(application, redraw_windows)
    first: Window = Window(model)
    first.show()
    watcher: TreeWatcher = TreeWatcher(model)
    if makers is not None and makers.first is not None:
        control: MachineControl | None = makers.first("")
        if control is not None:
            first.connect_machine(control)
    restore_layout(first)
    stopper: Stopper = Stopper()

    # The first panel's editor (#S5); a tutorial checked headless stops.
    if first_panel is not None:
        checked: int | None = first_panel.open(first)
        if checked is not None:
            model.forget(watcher.follow)
            return checked

    # No shop: offer to make one (#97), when someone can answer.
    elif model.shop is None and not headless:
        first.new_shop()

    # MCP, if asked for: each call runs on Qt's main thread (#577).
    if mcp_port:
        # The MCP server is imported only when it is asked for.
        # pylint: disable=import-outside-toplevel
        from ..exposed import qt_runner, server

        # pylint: enable=import-outside-toplevel
        # Importing it registers its functions; by name, since it
        # imports this module (no cycle at load time).
        importlib.import_module(f"{__package__}.window_exposed")
        try:
            server.serve(mcp_port, server.Server(qt_runner.QtRunner()))
        except OSError as error:
            print(f"Can not open port {mcp_port}: {error}", file=sys.stderr)
            return 1
        print(f"MCP on http://127.0.0.1:{mcp_port}{server.PATH}", flush=True)

    # Until the last window closes, with the trees watched.
    status: int = int(application.exec())
    model.forget(watcher.follow)
    del stopper
    if first_panel is not None:
        first_panel.finish()
    return status


# Class `CatalogPanel`:
class CatalogPanel:
    """`--pages CATALOG`: the first panel opens a catalog's pages (#600).

    Attributes:
    * `catalog` (`Path`): The catalog's `catalog.toml`.
    """

    def __init__(self, catalog: Path) -> None:
        """Remember the catalog.

        Arguments:
        * `catalog` (`Path`): Its `catalog.toml`.
        """
        self.catalog: Path = catalog

    def open(self, top: "Window") -> int | None:
        """Select the catalog in the tree, and press [Open Pages].

        Arguments:
        * `top` (`Window`): The window.

        Returns:
        * (`int | None`): 1 when the shop has no such catalog, else
          `None`.
        """
        item: QTreeWidgetItem | None = top.tree.item_at_path(
            self.catalog.resolve()
        )
        if item is None:
            print(f"No catalog {self.catalog} in the shop", file=sys.stderr)
            return 1
        top.select_item(item)
        top.open_pages(top.panels[top.current])
        return None

    def finish(self) -> None:
        """Nothing to finish: the pages are saved as they close."""


# Class `MachineMakers`:
@dataclass(frozen=True, slots=True)
class MachineMakers:
    """What makes machines' controls, by machine name ("" for the
    program's machine); each reports its own failure and gives `None`.

    Constructor:
    * `MachineMakers(first, connect)`

    Attributes:
    * `first` (`Callable[[str], MachineControl | None] | None`): The
      first window's machine (`--program`, `--hmi`), if any.
    * `connect` (`Callable[[str], MachineControl | None]`): A machine
      the user opens that is not connected (#607).
    """

    # Constructor arguments:
    first: Callable[[str], MachineControl | None] | None = field(init=True)
    connect: Callable[[str], MachineControl | None] = field(init=True)


# Class `FirstPanel`:
class FirstPanel(Protocol):
    """What `run()` opens in the first panel, and finishes after Qt."""

    def open(self, top: "Window") -> int | None:
        """Open it in `top`'s current panel.

        Arguments:
        * `top` (`Window`): The window.

        Returns:
        * (`int | None`): An exit status to stop with, or `None`.
        """

    def finish(self) -> None:
        """Finish, once Qt has stopped."""


# The guide in the first panel at start, after the shop and the NC
# program (#139).
GUIDE: tuple[str, ...] = (
    "",
    (
        "1. [Tree] toggles the visibility of the tree hierarchy panel to"
        " the left."
    ),
    "",
    (
        "2. A shop may have several machines from the same vendor that"
        " are running the same controller software.  To simplify things,"
        " the vendor CNC controller software can be configured once here."
    ),
    "",
    "3. [Stop All] is always shown, and stops every CNC machine at once.",
    "",
    "4. Click a tree item to see it here.",
)


# Function `show_rows_buttons()`:
def show_rows_buttons() -> None:
    """Bring every row's panel buttons up to date."""
    top: Window
    for top in WINDOWS:
        top.show_panel_buttons()


# Function `close_rows()`:
def close_rows() -> None:
    """Close every row ([Exit], #184), the newest first."""
    top: Window
    for top in reversed(list(WINDOWS)):
        top.close()


# Function `index_start()`:
def index_start(item: dict[str, object]) -> int:
    """Return the PDF page a catalog's index starts on (#63, #66).

    Arguments:
    * `item` (`dict[str, object]`): The catalog, as read.

    Returns:
    * (`int`): Its first index page plus `page_offset`, counting
      from 1; 0 when it has no index pages.
    """
    ranges: object = item.get("index_pages")
    if not isinstance(ranges, list) or not ranges:
        return 0
    first: object = ranges[0]
    page: object = first[0] if isinstance(first, list) else first
    offset: object = item.get("page_offset", 0)
    if not isinstance(page, int) or not isinstance(offset, int):
        return 0
    return page + offset


# Function `close_catalogs()`:
def close_catalogs() -> None:
    """Close every `catxtract` window, each saving its page (#68)."""
    pages: Pages
    for pages in list(CATALOG_WINDOWS.values()):
        pages.close()
    CATALOG_WINDOWS.clear()


# Function `restore_layout()`:
def restore_layout(first: "Window") -> None:
    """Bring back the layout kept for the shop, if any (#186, #187).

    Arguments:
    * `first` (`Window`): The first row, made at start; the others
      are made here.
    """
    model: App = first.model
    if not model.keep_layout or model.shop is None:
        return
    rows: list[dict[str, object]] = read_layout(model.shop)
    index: int
    row: dict[str, object]
    for index, row in enumerate(rows):
        top: Window = first if index == 0 else Window(model)
        top.restore(row)
        top.show()


# Function `machine_controls()`:
def machine_controls() -> list[MachineControl]:
    """Return every machine connected, in every window (#134).

    Returns:
    * (`list[MachineControl]`): Their controls, window by window.
    """
    return [machine for top in WINDOWS for machine in top.machines]


# Class `Stopper`:
class Stopper(QObject):
    """Closes the GUI on a `SIGTERM` or `SIGINT`, never mid-cut (#56).

    The signal stops every machine at once; the windows close once
    each is stopped with its spindle off.  Python sees a signal only
    when Python runs, so a timer looks every `STOP_MS`.

    Attributes:
    * `asked` (`bool`): True once a signal has come.
    * `timer` (`QTimer`): Looks for it.
    """

    def __init__(self) -> None:
        """Catch the signals, and start looking."""
        super().__init__()
        self.asked: bool = False
        signal.signal(signal.SIGTERM, self.catch)
        signal.signal(signal.SIGINT, self.catch)
        self.timer: QTimer = QTimer(self)
        self.timer.setInterval(STOP_MS)
        self.timer.timeout.connect(self.look)
        self.timer.start()

    def catch(self, _number: int, _frame: FrameType | None) -> None:
        """Note the signal, and stop the machines at once.

        Arguments:
        * `_number` (`int`): The signal (ignored).
        * `_frame` (`FrameType | None`): Where Python was (ignored).
        """
        self.asked = True
        top: Window
        for top in WINDOWS:
            machine: MachineControl
            for machine in top.machines:
                if machine.busy():
                    machine.stop()

    def look(self) -> None:
        """Close every window, once asked and nothing is busy."""
        if self.asked and not any(top.busy() for top in WINDOWS):
            close_all()


# Class `Window`:
# A window holds a widget for each thing it shows, and a method for
# each button and each thing it follows.
# pylint: disable-next=too-many-instance-attributes,too-many-public-methods
class Window(QWidget):
    """One window of the GUI.

    Attributes:
    * `model` (`App`): What every window shows.
    * `controls` (`set[str]`): The machines this window controls.
    * `buttons` (`dict[str, QPushButton]`): The top line's buttons,
      by label (for the command port's `press`).
    * `message_label` (`QLabel`): The latest message.
    * `action_rows` (`QWidget`): The action rows.
    * `new_catalog_row` (`QWidget`): The action row with [New
      Catalog], for `catalogs/` and the shop (`T.c~6.3` #61).
    * `new_machine_row` (`QWidget`): The action row with [New
      Machine], for `machines/` (#141).
    * `new_shop_row` (`QWidget`): The action row with [New Shop].
    * `panels` (`list[Panel]`): The panels, left to right.
    * `closing` (`list[Panel]`): Panels told to close whose machine
      is still stopping; each closes once it has stopped (#156).
    * `machines` (`list[MachineControl]`): The machines connected to
      this window, each shown in a panel only once it is clicked
      (#135).
    * `splitter` (`QSplitter`): The tree, then the panels.
    * `tree` (`TreeView`): The shop's and the design's files.
    * `current` (`int`): The current panel's index (#122).
    * `wanted` (`list[int]`): The splitter's sizes `fit_width()`
      wants once the window has its new width, or empty.
    * `machine_timer` (`QTimer`): Keeps [Stop All] and the machine
      tabs' bars up to date.
    * `blink` (`bool`): Which half of a blink it is (a waiting
      machine's bar).
    """

    def __init__(self, model: App, controls: set[str] | None = None) -> None:
        """Make a window (a PanelRow, #184), and show what it shows.

        Arguments:
        * `model` (`App`): What every window shows.
        * `controls` (`set[str] | None`): The machines this window
          controls, if any.
        """
        super().__init__()
        self.model: App = model
        self.controls: set[str] = set() if controls is None else controls
        self.buttons: dict[str, QPushButton] = {}
        self.resize(WIDTH, HEIGHT)

        # The top line, left to right.
        top: QHBoxLayout = QHBoxLayout()
        self.add_button(top, "Stop All", self.stop_all)
        self.add_button(top, "Tree", self.toggle_tree)
        self.message_label: QLabel = QLabel()
        self.message_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        top.addWidget(self.message_label, 1)
        self.add_button(top, "+ Panel", self.add_panel)
        self.add_button(top, NEW_WINDOW, self.new_window)
        self.add_button(top, EXIT, self.exit_program)
        self.explain_top_line()

        # The action rows, under the top line: [New Shop], while there
        # is no shop; [New Machine], for `machines/`.  [Enable
        # Editing] and [Edit TOML File] are in each panel (#153).
        self.action_rows: QWidget = QWidget()
        rows: QVBoxLayout = QVBoxLayout(self.action_rows)
        rows.setContentsMargins(0, 0, 0, 0)
        self.new_shop_row: QWidget = self.action_row(
            rows, QLabel("No shop yet:"), "New Shop", self.new_shop
        )
        self.new_machine_row: QWidget = self.action_row(
            rows, QLabel("machines/:"), "New Machine", self.new_machine
        )
        self.new_catalog_row: QWidget = self.action_row(
            rows, QLabel("catalogs/:"), "New Catalog", self.new_catalog
        )

        # The tree on the left, then the panels; the first is current.
        self.splitter: QSplitter = splitter(Qt.Orientation.Horizontal)
        self.tree: TreeView = TreeView()
        self.tree.itemClicked.connect(self.select_item)
        self.tree.itemExpanded.connect(self.tree_opened)
        self.tree.itemCollapsed.connect(self.tree_opened)
        self.splitter.addWidget(self.tree)
        self.panels: list[Panel] = []
        self.closing: list[Panel] = []
        self.machines: list[MachineControl] = []
        self.current: int = 0
        self.wanted: list[int] = []
        self.add_panel()
        tree_width: int = int(WIDTH * TREE_MOST)
        self.splitter.setSizes([tree_width, WIDTH - tree_width])

        # The bands, top to bottom.
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.action_rows)
        layout.addWidget(self.splitter, 1)

        # [Stop All] follows the machines, which change on their own.
        self.blink: bool = False
        self.machine_timer: QTimer = self.watch_machines()

        # Redraw whenever the model changes, starting now, with the
        # guide (#139); [New Window] takes it away (#200).
        model.listen(self.redraw)
        self.redraw()
        self.panels[0].show_guide(self.guide_text())
        WINDOWS.append(self)
        show_rows_buttons()

    def explain_top_line(self) -> None:
        """Give the top line's short buttons tooltips and room (#197).

        [Stop All] gets room for its bold, boxed look while a machine
        runs (#199): `show_stop_all()`'s padding and border.
        """
        self.buttons["+ Panel"].setToolTip("Add a new panel on the right")
        self.buttons[NEW_WINDOW].setToolTip(
            "Open another window, its panel filled from its tree"
        )
        self.buttons[EXIT].setToolTip("Stop and close every window")
        stop: QPushButton = self.buttons["Stop All"]
        bold: QFont = QFont(stop.font())
        bold.setBold(True)
        stop.setMaximumWidth(
            QFontMetrics(bold).horizontalAdvance("Stop All") + STOP_ROOM
        )

    def add_button(
        self, line: QHBoxLayout, label: str, action: Callable[[], object]
    ) -> None:
        """Add a button to the top line, as wide as its text (#196).

        Arguments:
        * `line` (`QHBoxLayout`): The top line.
        * `label` (`str`): The button's label.
        * `action` (`Callable[[], object]`): What a press calls.
        """
        button: QPushButton = QPushButton(label)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(action)
        narrow(button)
        line.addWidget(button)
        self.buttons[label] = button

    def action_row(
        self,
        rows: QVBoxLayout,
        label: QLabel,
        button: str,
        action: Callable[[], object],
    ) -> QWidget:
        """Add an action row: a label, then a button.

        Arguments:
        * `rows` (`QVBoxLayout`): The action rows.
        * `label` (`QLabel`): What the row is about.
        * `button` (`str`): The button's label.
        * `action` (`Callable[[], object]`): What a press calls.

        Returns:
        * (`QWidget`): The row.
        """
        row: QWidget = QWidget()
        line: QHBoxLayout = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(label)
        self.add_button(line, button, action)
        line.addStretch(1)
        rows.addWidget(row)
        return row

    def redraw(self) -> None:
        """Show what the model holds now."""
        model: App = self.model
        self.setWindowTitle(model.title())
        latest: Message = model.latest()
        self.message_label.setText(latest.text)
        self.message_label.setToolTip(latest.text)
        problem: str = colors().problem
        self.message_label.setStyleSheet(
            f"color: {problem}" if latest.problem else ""
        )
        self.show_stop_all()
        self.new_shop_row.setVisible(model.shop is None)
        self.buttons["New Shop"].setVisible(model.shop is None)

        # The tree, when it was read again, and the panels' items;
        # then the selected item's action row.
        if self.tree.version != model.tree_version:
            roots: list[Node] = [
                root
                for root in (model.shop_root, model.design_root)
                if root is not None
            ]
            first: bool = self.tree.version < 0
            self.tree.fill(roots, model.tree_version)
            if first:
                self.fit_tree()
            panel: Panel
            for panel in self.panels:
                if panel.node is not None:
                    node: Node | None = self.tree.nodes.get(
                        str(panel.node.path)
                    )
                    if node is not None:
                        panel.show_node(
                            node,
                            shop_units(model.shop),
                            created=str(node.path) in model.created,
                        )
        self.show_actions()

    def toggle_tree(self) -> None:
        """Show the tree if it is hidden, or hide it ([Tree])."""
        # Hide it; or show it, fitted to its labels.
        if not self.tree.isHidden():
            self.tree.hide()
            return
        self.tree.show()
        self.fit_tree()

    def tree_opened(self, _item: QTreeWidgetItem) -> None:
        """Fit the tree again when a branch opens or closes (#43)."""
        self.fit_tree()

    def fit_tree(self) -> None:
        """Make the tree as wide as its labels; the panels share the rest.

        No more than `TREE_MOST` of the width (#22).
        """
        sizes: list[int] = self.splitter.sizes()
        total: int = sum(sizes) or WIDTH
        tree_width: int = min(self.tree.wanted_width(), int(total * TREE_MOST))
        rest: int = max(1, len(sizes) - 1)
        self.splitter.setSizes(
            [tree_width] + [(total - tree_width) // rest] * (len(sizes) - 1)
        )

    def add_panel(self) -> None:
        """Add an empty panel on the right ([+ Panel]); it is current.

        The window widens by the new panel, as wide as the others are
        on average (#180); the first panel only fills the window.
        """
        # The widths wanted: the others as they are, then the new one.
        sizes: list[int] = self.splitter.sizes()
        widths: list[int] = sizes[1:]
        if widths:
            sizes.append(sum(widths) // len(widths))

        # The panel.
        panel: Panel = Panel(len(self.panels) + 1)
        self.adopt(panel)
        if widths:
            self.fit_width(sizes)
        self.make_current(panel)
        show_rows_buttons()

    def adopt(self, panel: Panel) -> None:
        """Make a panel this row's, on its right (#184).

        Arguments:
        * `panel` (`Panel`): The panel, new or from another row.
        """
        panel.controls = machine_controls
        panel.open_machine = self.open_machine
        panel.say = functools.partial(self.model.say, problem=True)
        panel.edit_file = functools.partial(self.edit, panel)
        panel.open_pages = functools.partial(self.open_pages, panel)
        panel.close_panel = functools.partial(self.close_panel, panel)
        panel.move_panel = functools.partial(self.move_panel, panel)
        panel.clicked.connect(functools.partial(self.make_current, panel))
        self.panels.append(panel)
        self.splitter.addWidget(panel)

    def new_window(self) -> None:
        """Open another window ([New Window], #200).

        It has one empty panel and its tree, to be filled from it.
        """
        top: Window = Window(self.model)
        top.panels[0].hide_guide()
        top.show()

    def fit_width(self, sizes: list[int]) -> None:
        """Make the window as wide as the tree and panels want (#177-#180).

        So adding or closing a panel keeps the
        other panels' widths, and the total width on the screen.  A
        maximized or full screen window keeps its size, and the panels
        share it; the window never grows past the screen, nor shrinks
        below what it needs.

        Arguments:
        * `sizes` (`list[int]`): The splitter's sizes wanted: the
          tree's (0 when hidden), then each panel's.
        """
        # The splitter's sizes now, shared in today's width; again once
        # the window has its new width (`resizeEvent()`).  The width is
        # found once Qt has laid out the panels again (its minimum).
        self.splitter.setSizes(sizes)
        if self.isMaximized() or self.isFullScreen():
            return
        self.wanted = sizes
        QTimer.singleShot(0, self.resize_to_wanted)

    def resize_to_wanted(self) -> None:
        """Resize the window for the sizes `fit_width()` wanted."""
        sizes: list[int] = self.wanted
        if not sizes:
            return
        shown: int = sum(1 for size in sizes if size > 0)
        handles: int = self.splitter.handleWidth() * max(0, shown - 1)
        frame: int = self.width() - self.splitter.width()
        width: int = sum(sizes) + handles + frame
        screen: QScreen | None = self.screen()
        if screen is not None:
            width = min(width, screen.availableGeometry().width())
        width = max(width, self.minimumSizeHint().width())
        self.resize(width, self.height())

        # The compositor may refuse; forget the sizes wanted soon.
        QTimer.singleShot(FIT_MS, self.forget_wanted)

    def forget_wanted(self) -> None:
        """Forget the sizes `fit_width()` wanted, once they are set."""
        self.wanted = []

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Give the panels the widths `fit_width()` wanted (#177-#180).

        Arguments:
        * `event` (`QResizeEvent`): The resize.
        """
        super().resizeEvent(event)
        if self.wanted:
            QTimer.singleShot(0, self.set_wanted)

    def set_wanted(self) -> None:
        """Set the splitter's sizes to those wanted, once."""
        if self.wanted:
            self.splitter.setSizes(self.wanted)
            self.wanted = []

    def show_panel_buttons(self) -> None:
        """Show each panel's buttons as its place allows.

        [Close] on every panel but a last one (#156); [<] greyed on
        the leftmost, [>] on the rightmost (#174).
        """
        many: bool = len(self.panels) > 1
        last: int = len(self.panels) - 1
        index: int
        panel: Panel
        for index, panel in enumerate(self.panels):
            panel.close_button.setVisible(many)
            panel.left_button.setEnabled(index > 0)
            panel.right_button.setEnabled(index < last)

    def move_panel(self, panel: Panel, step: int) -> None:
        """Move a panel one place left or right (#174).

        Its width goes with it, and it stays current if it was.

        Arguments:
        * `panel` (`Panel`): The panel.
        * `step` (`int`): -1 (left) or 1 (right).
        """
        # Only a panel of this window, never past either end.
        if panel not in self.panels:
            return
        index: int = self.panels.index(panel)
        other: int = index + step
        if not 0 <= other < len(self.panels):
            return

        # The splitter holds the tree first, so panel `i` is at `i + 1`.
        current: Panel = self.panels[self.current]
        sizes: list[int] = self.splitter.sizes()
        sizes[index + 1], sizes[other + 1] = sizes[other + 1], sizes[index + 1]
        self.panels[index], self.panels[other] = (
            self.panels[other],
            self.panels[index],
        )
        self.splitter.insertWidget(other + 1, panel)
        self.splitter.setSizes(sizes)
        self.make_current(current)
        show_rows_buttons()

    def close_panel(self, panel: Panel) -> None:
        """Close a panel ([Close Panel], #156).

        An active machine's panel asks to stop it first, and closes
        once it has stopped; any other closes at once.  A machine's
        controls stay connected, to be opened again.

        Arguments:
        * `panel` (`Panel`): The panel.
        """
        if len(self.panels) < 2:
            return
        stopping: bool = panel in self.closing
        if panel.machines and is_active(panel.machines[0]) and not stopping:
            machine: MachineControl = panel.machines[0]
            # Asked in the panel itself (#606).
            if not prompt.ask_yes_no(
                panel,
                "Close Panel",
                f"{machine.name} is running.  Stop it before closing its "
                "panel?",
            ):
                return
            machine.stop()
            if machine.busy():
                self.model.say(
                    f"Stopping {machine.name}: its panel closes once it "
                    "has stopped."
                )
                if panel not in self.closing:
                    self.closing.append(panel)
                return
        if panel in self.closing:
            self.closing.remove(panel)
        panel.drop_machine()
        if panel not in self.panels:
            return
        sizes: list[int] = self.splitter.sizes()
        del sizes[self.panels.index(panel) + 1]
        self.panels.remove(panel)
        panel.hide()
        panel.setParent(None)
        panel.deleteLater()
        self.fit_width(sizes)
        self.make_current(self.panels[min(self.current, len(self.panels) - 1)])
        show_rows_buttons()

    def all_panels(self) -> list[Panel]:
        """Return this row's panels (#184).

        Returns:
        * (`list[Panel]`): Its panels, left to right.
        """
        return list(self.panels)

    def make_current(self, panel: Panel) -> None:
        """Make a panel the current one: the next item shows there.

        Arguments:
        * `panel` (`Panel`): The panel.
        """
        self.current = self.panels.index(panel)
        other: Panel
        for other in self.panels:
            other.set_current(other is panel)
        self.show_actions()

    def select_item(self, item: QTreeWidgetItem) -> None:
        """Show a tree item in the current panel (#122).

        Arguments:
        * `item` (`QTreeWidgetItem`): The item clicked.
        """
        node: Node | None = self.tree.node_of(item)
        if node is not None:
            name: str = self.connected_name(node)
            if name:
                self.open_machine(name)
            else:
                self.free_panel().show_node(
                    node,
                    shop_units(self.model.shop),
                    created=str(node.path) in self.model.created,
                )
        self.show_actions()

    def connected_name(self, node: Node) -> str:
        """Return the name of the connected machine an item is, if any.

        Arguments:
        * `node` (`Node`): A tree item.

        Returns:
        * (`str`): The machine's name, when the item is a machine's
          file in `machines/` and that machine is connected; or "".
        """
        parent: Node | None = self.tree.nodes.get(str(node.path.parent))
        if parent is None or not is_machines_directory(parent):
            return ""
        name: str = machine_item(node).name
        connected: bool = any(
            machine.name == name for machine in machine_controls()
        )
        return name if connected else ""

    def guide_text(self) -> str:
        """Return the guide shown at start (#139).

        Returns:
        * (`str`): The shop, the NC program, and what to do first.
        """
        lines: list[str] = [f"Shop: {self.model.shop_title}"]
        if self.model.program:
            lines.append(f"NC program: {Path(self.model.program).name}")
        lines.extend(GUIDE)
        return "\n".join(lines)

    def connect_machine(self, machine: MachineControl) -> None:
        """Hold a machine's controls, shown once it is clicked (#135).

        Arguments:
        * `machine` (`MachineControl`): The controls.
        """
        self.machines.append(machine)

    def free_panel(self) -> Panel:
        """Return the panel a click shows an item in, and make it current.

        The current one, unless it is pinned (#201; an active
        machine's is, #58, #154); then the first that is not, or a new
        one on the right.  A panel showing a machine gives it up.

        Returns:
        * (`Panel`): The panel.
        """
        panel: Panel = self.panels[self.current]
        if not panel.is_pinned():
            panel.drop_machine()
            return panel
        for panel in self.panels:
            if not panel.is_pinned():
                self.make_current(panel)
                panel.drop_machine()
                return panel
        self.add_panel()
        return self.panels[self.current]

    def open_machine(self, name: str) -> None:
        """Show a machine's own panel (#134, #135).

        A machine already shown: its panel becomes the current one, in
        whichever window holds it.  One connected but not shown yet:
        shown in the panel a click uses.  One not connected is only
        said to be so.

        Arguments:
        * `name` (`str`): The machine's name.
        """
        top: Window
        machine: MachineControl
        for top in WINDOWS:
            panel: Panel
            for panel in top.all_panels():
                if any(machine.name == name for machine in panel.machines):
                    top.make_current(panel)
                    top.to_front(self)
                    return
        for top in WINDOWS:
            for machine in top.machines:
                if machine.name == name:
                    top.free_panel().show_machine(
                        machine, top.machine_label(name)
                    )
                    top.to_front(self)
                    return
        # Not connected: connect it (#607), one LinuxCNC simulator so
        # far (`T.rslsao~5.8`).
        if not CONNECT:
            self.model.say(f"The {name} is not connected")
            return
        if machine_controls():
            self.model.say(
                f"The {name} is not connected: one LinuxCNC simulator "
                "so far, and it is in use",
                problem=True,
            )
            return
        control: MachineControl | None = CONNECT[0](name)
        if control is None:
            return
        self.connect_machine(control)
        self.open_machine(name)

    def machine_label(self, name: str) -> str:
        """Return a machine's file's label in the tree (#183).

        Arguments:
        * `name` (`str`): The machine's name.

        Returns:
        * (`str`): Its label, e.g. "Shop mill (file)", or "" when no
          file in `machines/` names it.
        """
        node: Node
        for node in self.tree.nodes.values():
            parent: Node | None = self.tree.nodes.get(str(node.path.parent))
            if (
                parent is not None
                and is_machines_directory(parent)
                and not node.children
                and machine_item(node).name == name
            ):
                return node.label()
        return ""

    def to_front(self, clicked: "Window | None") -> None:
        """Bring this window to the front, unless it was clicked in.

        Arguments:
        * `clicked` (`Window | None`): The window clicked in, or
          `None` (always to the front).
        """
        if self is not clicked:
            self.raise_()
            self.activateWindow()

    def busy(self) -> str:
        """Say why this window may not close, if it may not (#56, #67).

        A row with other rows left answers only for the machines in
        its panels (#184); the last one for all.

        Returns:
        * (`str`): The first machine's reason, or the model's (a
          running machine), or "" when it may close.
        """
        # Its panels' machines; the last row answers for every one.
        others: bool = any(top is not self for top in WINDOWS)
        machines: list[MachineControl] = [
            machine for panel in self.panels for machine in panel.machines
        ]
        if not others:
            machines += self.machines
        machine: MachineControl
        for machine in machines:
            reason: str = machine.busy()
            if reason:
                return reason
        return "" if others else self.model.close_refusal(self.controls)

    def show_actions(self) -> None:
        """Show the action rows of the current panel's item (#73)."""
        node: Node | None = (
            self.panels[self.current].node if self.panels else None
        )

        # [New Machine], for `machines/`: grey, saying why, with no
        # controller template (#141).
        machines: bool = node is not None and is_machines_directory(node)
        self.new_machine_row.setVisible(machines)
        self.buttons["New Machine"].setVisible(machines)
        templates: bool = self.model.shop is not None and bool(
            controller_templates(self.model.shop)
        )
        self.buttons["New Machine"].setEnabled(templates)
        self.buttons["New Machine"].setToolTip(
            "Make a machine, with its own copy of a controller template"
            if templates
            else "First put a controller template in controllers/"
        )

        # [New Catalog], for `catalogs/` and the shop itself, since a
        # shop has no `catalogs/` until its first (`T.c~6.3` #61).
        catalogs: bool = node is not None and (
            node.kind == SHOP or is_catalogs_directory(node)
        )
        self.new_catalog_row.setVisible(catalogs)
        self.buttons["New Catalog"].setVisible(catalogs)
        self.buttons["New Catalog"].setToolTip(
            "Add a vendor's catalog: its PDF, copied or linked"
        )

    def open_pages(self, panel: Panel) -> None:
        """Open a panel's catalog in `catxtract` ([Open Pages], #68).

        In the panel's [Pages] tab (#600), at its first index page
        (else where `catxtract` starts); one already open is shown.

        Arguments:
        * `panel` (`Panel`): The panel whose button was pressed.
        """
        # The catalog, and its PDF in `pages/`.
        if panel.node is None or panel.item.get("kind") != "catalog":
            return
        path: Path = panel.node.path
        found: Pages | None = CATALOG_WINDOWS.get(str(path))
        if found is not None and not found.closed:
            panel.show_pages(found)
            return
        item: dict[str, object] = panel.item
        pages: Path = path.parent / CATALOG_PAGES
        pdf: Path = pages / str(item.get("pdf", ""))
        if not pdf.is_file():
            self.model.say(
                f"{pdf} is missing: put the PDF, or a link to it, there",
                problem=True,
            )
            return

        # Imported here: it fetches the PDF packages on first use.
        # pylint: disable-next=import-outside-toplevel
        from ..catalog.catxtract import App as Opened

        opened: Pages = Opened(pdf, pages)
        opened.setWindowTitle(f"catxtract: {item.get('name', path.parent)}")
        start: int = index_start(item)
        if 1 <= start <= len(opened.doc):
            opened.page_no = start - 1
            opened.show_page()
        CATALOG_WINDOWS[str(path)] = opened
        panel.show_pages(opened)

    def edit(self, panel: Panel) -> None:
        """Open a panel's file in an editor ([Edit TOML File], #124).

        Arguments:
        * `panel` (`Panel`): The panel whose button was pressed.
        """
        # The file.
        node: Node | None = panel.node
        path: Path | None = None if node is None else edit_path(node)
        if path is None:
            return

        # `VISUAL`, `EDITOR` in a terminal, or why not.
        command: list[str]
        problem: str
        command, problem = editor_command(path, os.environ, shutil.which)
        if problem:
            self.model.say(problem, problem=True)
            return
        if command:
            try:
                # The program runs on its own; nothing waits for it.
                subprocess.Popen(  # pylint: disable=consider-using-with
                    command, start_new_session=True
                )
            except OSError as error:
                self.model.say(f"{command[0]}: {error}", problem=True)
            return

        # Neither: the desktop's default, with the hint once a session.
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self.model.say(f"No editor opened {path}.", problem=True)
        elif not self.model.editor_hinted:
            self.model.editor_hinted = True
            self.model.say(HINT)

    def stop_all(self) -> None:
        """Stop every machine ([Stop All]), each of its panels' too."""
        top: Window
        for top in WINDOWS:
            machine: MachineControl
            for machine in top.machines:
                machine.stop()
        self.model.stop_all()

    def running(self) -> bool:
        """Tell whether any machine runs (or is paused, or turns).

        Returns:
        * (`bool`): True if one of any window's machines is busy
          (`MachineControl.busy()`), or the model has one running.
        """
        return bool(self.model.running) or any(
            machine.busy() for machine in machine_controls()
        )

    def watch_machines(self) -> QTimer:
        """Start following the machines, every `STOP_MS`.

        Returns:
        * (`QTimer`): The timer, running.
        """
        timer: QTimer = QTimer(self)
        timer.setInterval(STOP_MS)
        timer.timeout.connect(self.follow_machines)
        timer.start()
        return timer

    def follow_machines(self) -> None:
        """Bring [Stop All], each machine tab's bar, and the active
        machines' tree items (#610) up to date."""
        self.blink = not self.blink
        self.show_stop_all()
        self.show_active()
        panel: Panel
        for panel in self.all_panels():
            panel.show_dues(self.blink)
            panel.show_pin()

        # What was told to close once its machines stopped (#156).
        for panel in list(self.closing):
            if not any(machine.busy() for machine in panel.machines):
                self.close_panel(panel)

        # The layout, kept on every change (#187), by the first row.
        if (
            self.model.keep_layout
            and self.model.shop is not None
            and WINDOWS
            and WINDOWS[0] is self
        ):
            save_layout(self.model.shop, [top.snapshot() for top in WINDOWS])

    def restore(self, row: dict[str, object]) -> None:
        """Lay this row out as a layout kept it (#186).

        Its panels show what they showed, read only; a machine is only
        shown, never started; anything gone is skipped quietly
        (#187).

        Arguments:
        * `row` (`dict[str, object]`): The row's snapshot.
        """
        # The panels, then the tree, then the sizes.
        widths: list[int] = self.restore_panels(row.get("panels"))
        opened: object = row.get("opened")
        if isinstance(opened, list):
            self.tree.open_items([str(path) for path in opened])
        tree: bool = row.get("tree") is not False
        self.tree.setVisible(tree)
        tree_width: object = row.get("tree_width")
        width: object = row.get("width")
        height: object = row.get("height")

        # The widths kept win over those [+ Panel] wanted, now and once
        # the window has its size (`resizeEvent()`).
        if isinstance(tree_width, int) and len(widths) == len(self.panels):
            self.wanted = [tree_width if tree else 0] + widths
            self.splitter.setSizes(self.wanted)
        if isinstance(width, int) and isinstance(height, int):
            self.resize(width, height)

    def restore_panels(self, panels: object) -> list[int]:
        """Show the panels a layout kept, left to right (#186).

        Arguments:
        * `panels` (`object`): The kept panels (a list of `dict`s).

        Returns:
        * (`list[int]`): The widths of the panels restored.
        """
        widths: list[int] = []
        if not isinstance(panels, list):
            return widths
        kept: object
        for kept in panels:
            if not isinstance(kept, dict):
                continue

            # What it showed, if it is still there.
            node: Node | None = self.tree.nodes.get(str(kept.get("path")))
            name: object = kept.get("machine")
            machine: MachineControl | None = next(
                (
                    control
                    for control in machine_controls()
                    if control.name == name
                ),
                None,
            )
            if (node is None and "path" in kept) or (
                machine is None and "machine" in kept
            ):
                continue

            # A panel for it: the first one there, then new ones.
            if widths:
                self.add_panel()
            panel: Panel = self.panels[-1]
            if machine is not None:
                panel.show_machine(machine, self.machine_label(machine.name))
            elif node is not None:
                panel.show_node(node, shop_units(self.model.shop))
            panel.pinned = kept.get("pinned") is True
            panel.show_pin()
            width: object = kept.get("width")
            widths.append(width if isinstance(width, int) else panel.width())
        self.make_current(self.panels[0])
        return widths

    def snapshot(self) -> dict[str, object]:
        """Return what the layout keeps of this row (#186).

        Returns:
        * (`dict[str, object]`): Its size; its tree (shown, width,
          open paths); its panels, left to right, each with its width,
          `pinned` (#201) and what it shows: `path` (an item),
          `machine` (a name), or neither (the guide or nothing).
        """
        sizes: list[int] = self.splitter.sizes()
        panels: list[dict[str, object]] = []
        index: int
        panel: Panel
        for index, panel in enumerate(self.panels):
            shown: dict[str, object] = {
                "width": sizes[index + 1],
                "pinned": panel.pinned,
            }
            if panel.machines:
                shown["machine"] = panel.machines[0].name
            elif panel.node is not None:
                shown["path"] = str(panel.node.path)
            panels.append(shown)
        return {
            "width": self.width(),
            "height": self.height(),
            "tree": not self.tree.isHidden(),
            "tree_width": sizes[0],
            "opened": self.tree.opened(),
            "panels": panels,
        }

    def show_stop_all(self) -> None:
        """Make [Stop All] stand out while any machine runs (#100).

        Not by color alone (some operators are color blind): it is
        also enabled, bold and heavily boxed only then.
        """
        button: QPushButton = self.buttons["Stop All"]
        active: bool = self.running()
        button.setEnabled(active)
        button.setStyleSheet(
            f"QPushButton {{ color: white; background: {colors().problem};"
            " font-weight: bold; border: 3px solid black;"
            " padding: 3px 10px; }"
            if active
            else ""
        )

    def new_shop(self) -> None:
        """Ask about the new shop, and make it ([New Shop])."""
        dialog: NewShopDialog = NewShopDialog(self, self.model)
        prompt.show_in(self.panels[self.current], dialog)

    def new_machine(self) -> None:
        """Ask about the new machine, and make it ([New Machine], #141)."""
        dialog: NewMachineDialog = NewMachineDialog(self, self.model)
        prompt.show_in(self.panels[self.current], dialog)

    def new_catalog(self) -> None:
        """Ask about the new catalog, and make it ([New Catalog])."""
        dialog: NewCatalogDialog = NewCatalogDialog(self, self.model)
        prompt.show_in(self.panels[self.current], dialog)

    def offer_ignores(self) -> None:
        """Offer to keep catalogs' `pages/` out of version control (#51)."""
        if self.model.shop is None:
            return
        needed: list[tuple[Path, str]] = ignores_needed(self.model.shop.parent)
        if not needed:
            return
        lines: str = "\n".join(f"{path}:  {line}" for path, line in needed)
        if not prompt.ask_yes_no(
            self.panels[self.current],
            "Keep the PDFs out of version control?",
            "A catalog's PDF and its pages are never under version "
            f"control.  Add these lines?\n\n{lines}",
        ):
            self.model.say("Not added: " + lines.replace("\n", "; "))
            return
        try:
            add_ignores(needed)
        except OSError as error:
            self.model.say(str(error), problem=True)

    def show_created(self, path: Path) -> None:
        """Show an item just made, editing enabled (#140).

        Arguments:
        * `path` (`Path`): Its file.
        """
        self.redraw()
        node: Node | None = self.tree.nodes.get(str(path))
        if node is not None:
            self.free_panel().show_node(
                node, shop_units(self.model.shop), created=True
            )
            self.show_actions()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Close, unless this window controls a running machine (#67).

        (Qt's name for it; [x] and the window's own close come here.)

        Arguments:
        * `event` (`QCloseEvent`): Accepted, or ignored with the
          reason on the top line.
        """
        # Refused while a machine is active, naming each one and why,
        # their windows brought forward; no question (#606, #611).
        refusal: str = self.busy()
        if refusal:
            refuse_exit(self.model)
            event.ignore()
            return

        # Closed; its machines go to the oldest row left (#184).
        self.model.forget(self.redraw)
        if self in WINDOWS:
            WINDOWS.remove(self)
        if WINDOWS:
            WINDOWS[0].machines += self.machines
            WINDOWS[0].controls |= self.controls
            self.machines = []
            self.controls = set()
        else:
            close_catalogs()
        show_rows_buttons()
        event.accept()

    def exit_program(self) -> None:
        """Close every window ([Exit], #156), unless a machine is
        active: then say which, and why, and show them (#611)."""
        if active_reasons():
            refuse_exit(self.model)
            return
        close_rows()

    def show_active(self) -> None:
        """Keep this window's active machines in sight (#610).

        While one of its panels' machines is active, its tree is
        shown and [Tree] greyed, and those machines' items are drawn
        as [Stop All] is while one runs.
        """
        names: set[str] = {
            machine.name
            for panel in self.panels
            for machine in panel.machines
            if machine.busy()
        }
        if names and self.tree.isHidden():
            self.toggle_tree()
        self.buttons["Tree"].setEnabled(not names)
        self.tree.mark_active(names)


# Function `active_reasons()`:
def active_reasons() -> list[str]:
    """Say why each active machine stops scraftcam closing (#611).

    Returns:
    * (`list[str]`): A reason per active machine, in every window
      ("The Shop mill's spindle is on: stop it first"); empty when
      none is active.
    """
    reasons: list[str] = [
        reason
        for reason in (machine.busy() for machine in machine_controls())
        if reason
    ]
    if WINDOWS:
        reasons += [
            f"{name} is running" for name in sorted(WINDOWS[0].model.running)
        ]
    return reasons


# Function `refuse_exit()`:
def refuse_exit(model: App) -> None:
    """Refuse to close: name every active machine and why, on the
    message line, and bring their windows forward (#611).

    Arguments:
    * `model` (`App`): What every window shows.
    """
    reasons: list[str] = active_reasons()
    model.say("Stop first: " + "; ".join(reasons), problem=True)
    top: Window
    for top in WINDOWS:
        if any(
            machine.busy()
            for panel in top.panels
            for machine in panel.machines
        ):
            top.show_active()
            top.raise_()
            top.activateWindow()


# Function `close_all()`:
def close_all() -> None:
    """Close every window, newest first."""
    top: Window
    for top in reversed(list(WINDOWS)):
        top.close()


# Class `NewShopDialog`:
class NewShopDialog(QDialog):
    """The questions for a new shop (#98, #104).

    Where it goes (`shop/` under the current directory, unless
    changed), its name, its units, and a check box for each kind of
    machine (`MACHINE_KINDS`; those `scraftcam` can not drive yet say
    so).  [Create], beside the name, stays grey until there is one.

    Attributes:
    * `model` (`App`): What every window shows.
    * `directory` (`QLineEdit`): Where the shop goes.
    * `name` (`QLineEdit`): The shop's name.
    * `units` (`QComboBox`): The units it prefers.
    * `kinds` (`dict[str, QCheckBox]`): A check box per kind, by key.
    * `buttons` (`QDialogButtonBox`): [Cancel].
    * `make_button` (`QPushButton`): [Create], beside the name.
    """

    def __init__(self, parent: QWidget, model: App) -> None:
        """Make the dialog; `open()` shows it.

        Arguments:
        * `parent` (`QWidget`): The window it belongs to.
        * `model` (`App`): What every window shows.
        """
        super().__init__(parent)
        self.model: App = model
        self.setWindowTitle("New Shop")
        form: QFormLayout = QFormLayout(self)

        # Where, with [Browse...] to choose another directory.
        self.directory: QLineEdit = QLineEdit(
            str(Path.cwd() / NEW_SHOP_DIRECTORY)
        )
        self.directory.setMinimumWidth(DIRECTORY_WIDTH)
        browse: QPushButton = QPushButton("Browse...")
        browse.clicked.connect(self.browse)
        where: QHBoxLayout = QHBoxLayout()
        where.addWidget(self.directory, 1)
        where.addWidget(browse)
        form.addRow("Directory:", where)

        # The name, with [Create] beside it (#116; Enter presses it),
        # grey until there is a name.
        self.name: QLineEdit = QLineEdit()
        self.name.setPlaceholderText("e.g. Home shop")
        self.name.textChanged.connect(self.check)
        self.make_button: QPushButton = QPushButton("Create")
        self.make_button.setDefault(True)
        self.make_button.clicked.connect(self.make_shop)
        named: QHBoxLayout = QHBoxLayout()
        named.addWidget(self.name, 1)
        named.addWidget(self.make_button)
        form.addRow("Name:", named)

        # The units.
        self.units: QComboBox = QComboBox()
        unit: str
        for unit in UNITS:
            self.units.addItem(UNIT_LABELS[unit], unit)
        form.addRow("Units:", self.units)

        # A check box per kind of machine: computer controlled ones,
        # then manual ones (for prep work).
        form.addRow(QLabel("Which machines does the shop have?"))
        form.addRow(QLabel("Computer controlled:"))
        self.kinds: dict[str, QCheckBox] = {}
        kind: str
        label: str
        ready: bool
        for kind, label, ready in MACHINE_KINDS:
            if kind.startswith(MANUAL_PREFIX) and not any(
                key.startswith(MANUAL_PREFIX) for key in self.kinds
            ):
                form.addRow(QLabel("Manual, for prep work:"))
            box: QCheckBox = QCheckBox(
                label if ready else f"{label} (not supported yet)"
            )
            box.setChecked(kind == "cnc_mill")
            form.addRow(box)
            self.kinds[kind] = box

        # [Cancel].
        self.buttons: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        self.check()

    def check(self) -> None:
        """Grey [Create], saying why, until there is a name."""
        named: bool = bool(self.name.text().strip())
        self.make_button.setEnabled(named)
        self.make_button.setToolTip("" if named else "Give the shop a name.")

    def browse(self) -> None:
        """Choose the shop's directory ([Browse...]).

        Qt's own dialog, not the desktop's: KDE's, opened from this
        dialog, did not show (#117).  It starts in the nearest
        directory that exists.
        """
        start: Path = Path(self.directory.text().strip()).expanduser()
        while not start.is_dir() and start != start.parent:
            start = start.parent
        chosen: str = prompt.ask_directory(
            self, "The shop's directory", str(start)
        )
        if chosen:
            self.directory.setText(chosen)

    def make_shop(self) -> None:
        """Make the shop ([Create]); on a problem, say so and stay."""
        machines: list[str] = [
            kind for kind, box in self.kinds.items() if box.isChecked()
        ]
        try:
            self.model.new_shop(
                Path(self.directory.text().strip()).expanduser(),
                self.name.text(),
                str(self.units.currentData()),
                machines,
            )
        except (ValueError, OSError) as error:
            self.model.say(str(error), problem=True)
            return
        self.accept()


# Class `NewCatalogDialog`:
class NewCatalogDialog(QDialog):
    """The questions for a new catalog (`T.c~6.3` #61).

    Its vendor, its edition, its PDF, and whether the PDF is copied
    into the catalog's `pages/` or linked to.  [Create] stays grey
    until all three are given.

    Attributes:
    * `model` (`App`): What every window shows.
    * `vendor` (`QLineEdit`): Who publishes it.
    * `edition` (`QLineEdit`): Which edition.
    * `pdf` (`QLineEdit`): The PDF's file.
    * `how` (`QComboBox`): Link or copy (its data: True to link).
    * `make_button` (`QPushButton`): [Create].
    * `buttons` (`QDialogButtonBox`): [Cancel].
    """

    def __init__(self, parent: "Window", model: App) -> None:
        """Make the dialog; `open()` shows it.

        Arguments:
        * `parent` (`Window`): The window it belongs to.
        * `model` (`App`): What every window shows.
        """
        super().__init__(parent)
        self.model: App = model
        self.setWindowTitle("New Catalog")
        form: QFormLayout = QFormLayout(self)

        # The vendor, with [Create] beside it, and the edition.
        self.vendor: QLineEdit = QLineEdit()
        self.vendor.setPlaceholderText("e.g. Shars")
        self.vendor.textChanged.connect(self.check)
        self.make_button: QPushButton = QPushButton("Create")
        self.make_button.setDefault(True)
        self.make_button.clicked.connect(self.make_catalog)
        named: QHBoxLayout = QHBoxLayout()
        named.addWidget(self.vendor, 1)
        named.addWidget(self.make_button)
        form.addRow("Vendor:", named)
        self.edition: QLineEdit = QLineEdit()
        self.edition.setPlaceholderText("e.g. 2026")
        self.edition.textChanged.connect(self.check)
        form.addRow("Edition:", self.edition)

        # The PDF, with [Choose...], and how it gets into `pages/`.
        self.pdf: QLineEdit = QLineEdit()
        self.pdf.setPlaceholderText("The catalog's PDF")
        self.pdf.textChanged.connect(self.check)
        choose: QPushButton = QPushButton("Choose...")
        choose.clicked.connect(self.choose_pdf)
        chosen: QHBoxLayout = QHBoxLayout()
        chosen.addWidget(self.pdf, 1)
        chosen.addWidget(choose)
        form.addRow("PDF:", chosen)
        self.how: QComboBox = QComboBox()
        self.how.addItem("Link to it", True)
        self.how.addItem("Copy it", False)
        form.addRow("Into pages/:", self.how)

        # [Cancel].
        self.buttons: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        self.check()

    def pdf_path(self) -> Path:
        """Return the PDF as typed or chosen.

        Returns:
        * (`Path`): Its file, `~` expanded.
        """
        return Path(self.pdf.text().strip()).expanduser()

    def check(self) -> None:
        """Grey [Create], saying why, until all three are given."""
        pdf: bool = bool(self.pdf.text().strip()) and self.pdf_path().is_file()
        missing: list[str] = [
            what
            for what, given in (
                ("a vendor", bool(self.vendor.text().strip())),
                ("an edition", bool(self.edition.text().strip())),
                ("a PDF", pdf),
            )
            if not given
        ]
        self.make_button.setEnabled(not missing)
        self.make_button.setToolTip(
            "Give it " + ", ".join(missing) + "." if missing else ""
        )

    def choose_pdf(self) -> None:
        """Choose the PDF ([Choose...]), with Qt's own dialog (#117)."""
        chosen: str = prompt.ask_open_file(
            self,
            "The catalog's PDF",
            "PDF files (*.pdf *.PDF)",
            str(Path.home()),
        )
        if chosen:
            self.pdf.setText(chosen)

    def make_catalog(self) -> None:
        """Make the catalog ([Create]); on a problem, say so and stay."""
        try:
            pdf: Path = self.pdf_path()
            path: Path = self.model.new_catalog(
                self.vendor.text(),
                self.edition.text(),
                pdf,
                link=bool(self.how.currentData()),
                pages=pdf_pages(pdf),
            )
        except (ValueError, OSError) as error:
            self.model.say(str(error), problem=True)
            return
        self.accept()
        parent: QObject | None = self.parent()
        if isinstance(parent, Window):
            parent.offer_ignores()
            parent.show_created(path)


# Class `NewMachineDialog`:
class NewMachineDialog(QDialog):
    """The questions for a new machine (#141).

    Its name, its kind, and the controller template it gets its own
    copy of.  [Create] stays grey until there is a name.

    Attributes:
    * `model` (`App`): What every window shows.
    * `name` (`QLineEdit`): The machine's name.
    * `kind` (`QComboBox`): Its kind (`NEW_MACHINE_KINDS`).
    * `template` (`QComboBox`): The controller template.
    * `make_button` (`QPushButton`): [Create].
    * `buttons` (`QDialogButtonBox`): [Cancel].
    """

    def __init__(self, parent: "Window", model: App) -> None:
        """Make the dialog; `open()` shows it.

        Arguments:
        * `parent` (`Window`): The window it belongs to.
        * `model` (`App`): What every window shows.
        """
        super().__init__(parent)
        self.model: App = model
        self.setWindowTitle("New Machine")
        form: QFormLayout = QFormLayout(self)

        # The name, with [Create] beside it, grey until there is one.
        self.name: QLineEdit = QLineEdit()
        self.name.setPlaceholderText("e.g. Shop lathe")
        self.name.textChanged.connect(self.check)
        self.make_button: QPushButton = QPushButton("Create")
        self.make_button.setDefault(True)
        self.make_button.clicked.connect(self.make_machine)
        named: QHBoxLayout = QHBoxLayout()
        named.addWidget(self.name, 1)
        named.addWidget(self.make_button)
        form.addRow("Name:", named)

        # The kind, and the template.
        self.kind: QComboBox = QComboBox()
        kind: str
        for kind in NEW_MACHINE_KINDS:
            self.kind.addItem(kind, kind)
        form.addRow("Kind:", self.kind)
        self.template: QComboBox = QComboBox()
        if model.shop is not None:
            name: str
            for name in controller_templates(model.shop):
                self.template.addItem(name, name)
        form.addRow("Controller template:", self.template)

        # [Cancel].
        self.buttons: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        self.check()

    def check(self) -> None:
        """Grey [Create], saying why, until there is a name."""
        named: bool = bool(self.name.text().strip())
        self.make_button.setEnabled(named)
        self.make_button.setToolTip(
            "" if named else "Give the machine a name."
        )

    def make_machine(self) -> None:
        """Make the machine ([Create]); on a problem, say so and stay."""
        try:
            path: Path = self.model.new_machine(
                self.name.text(),
                str(self.kind.currentData()),
                str(self.template.currentData()),
            )
        except (ValueError, OSError) as error:
            self.model.say(str(error), problem=True)
            return
        self.accept()
        parent: QObject | None = self.parent()
        if isinstance(parent, Window):
            parent.show_created(path)
