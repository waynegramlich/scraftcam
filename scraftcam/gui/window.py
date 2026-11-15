"""A window of the GUI: the top line, the action rows and the panels.

From the top down (`T.osiade~5.1.9` #82):

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

With `--port`, `CommandServer` answers the command port (`port.py`,
#96): `status` (what the windows show), `press` (a top line button,
as a person would; `params`: `button`, and `window`, from 0) and
`new_shop` (makes a shop, as `NewShopDialog` would; `params`:
`directory`, `name`, `units`, `machines`) and `quit` (closes every
window, unless one refuses).
"""

import functools
import os
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import FrameType

from ..packages import require
from . import port, theme
from .app import (
    MACHINE_KINDS,
    MANUAL_PREFIX,
    NEW_MACHINE_KINDS,
    NEW_SHOP_DIRECTORY,
    UNIT_LABELS,
    UNITS,
    App,
    Message,
    controller_templates,
)
from .editor import HINT, editor_command
from .fields import shop_units
from .machines import (
    MachineControl,
    is_active,
    is_machines_directory,
    machine_item,
)
from .port import Method, PortError, text_param
from .theme import colors
from .tree import Node, edit_path
from .views import Panel, TreeView, TreeWatcher, entry_text, splitter

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import (  # noqa: E402
    QCoreApplication,
    QEvent,
    QMessageLogContext,
    QObject,
    QSize,
    Qt,
    QTimer,
    QtMsgType,
    QUrl,
    qInstallMessageHandler,
)
from PySide6.QtGui import QCloseEvent, QDesktopServices  # noqa: E402
from PySide6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

# The top line's button that closes the program (#114, #156).
EXIT: str = "Exit Program"

# A new window's size (#109): small, so SolidCraft fits beside it.
WIDTH: int = 720
HEIGHT: int = 480


# What Qt's offscreen platform says each time a window is shown; it
# means nothing here, so `use_headless()` drops it.
OFFSCREEN_NOISE: str = "This plugin does not support propagateSizeHints()"

# The least width of `NewShopDialog`'s directory, in pixels.
DIRECTORY_WIDTH: int = 360

# The most of the window's width the tree takes when it is fitted to
# its labels (#22); the user can drag it wider.
TREE_MOST: float = 0.5

# How long `quit` waits, so its answer is sent before the GUI closes.
QUIT_DELAY_MS: int = 200

# How often the GUI looks for a signal to close, while it waits for
# the machines to stop (milliseconds, #56).
STOP_MS: int = 250

# Every open window, oldest first (the command port's `window`).
WINDOWS: list["Window"] = []


# Function `use_headless()`:
def use_headless() -> None:
    """Draw offscreen from now on (tests, and `--headless`).

    It must be called before the `QApplication` is made.
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    qInstallMessageHandler(qt_message)


# Function `qt_message()`:
def qt_message(
    _kind: QtMsgType, _context: QMessageLogContext, message: str
) -> None:
    """Write a message from Qt, less `OFFSCREEN_NOISE`.

    Arguments:
    * `_kind` (`QtMsgType`): Debug, warning and so on (ignored).
    * `_context` (`QMessageLogContext`): Where it came from (ignored).
    * `message` (`str`): The message.
    """
    if message != OFFSCREEN_NOISE:
        print(message, file=sys.stderr)


# Function `make_application()`:
def make_application(*, headless: bool) -> QApplication:
    """Make the one `QApplication`, or return the one already made.

    Arguments:
    * `headless` (`bool`): True to draw offscreen (`use_headless()`).

    Returns:
    * (`QApplication`): The application.
    """
    if headless:
        use_headless()
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
    command_port: int,
    machine: Callable[[], MachineControl | None] | None = None,
) -> int:
    """Show the first window, and run Qt until the last one closes.

    Arguments:
    * `model` (`App`): What every window shows.
    * `headless` (`bool`): True to draw offscreen.
    * `command_port` (`int`): The command port, or 0 for none.
    * `machine` (`Callable[[], MachineControl | None] | None`): Makes
      a machine's controls for the first window's panel (step 5,
      #53), once Qt is up; it reports its own failure and gives
      `None`.

    Returns:
    * (`int`): Qt's exit code, 0 normally, or 1 when the port can
      not be opened.
    """
    application: QApplication = make_application(headless=headless)
    theme.follow(application, redraw_windows)
    first: Window = Window(model)
    first.show()
    watcher: TreeWatcher = TreeWatcher(model)
    if machine is not None:
        control: MachineControl | None = machine()
        if control is not None:
            first.connect_machine(control)
    stopper: Stopper = Stopper()

    # No shop: offer to make one (#97), when someone can answer.
    if model.shop is None and not headless:
        first.new_shop()

    # The command port, if asked for.
    if command_port:
        server: CommandServer = CommandServer(model)
        if not server.listen_local(command_port):
            print(
                f"Can not open port {command_port}: {server.errorString()}",
                file=sys.stderr,
            )
            return 1

    # Until the last window closes, with the trees watched.
    status: int = int(application.exec())
    model.forget(watcher.follow)
    del stopper
    return status


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


# Class `DetachedWindow`:
class DetachedWindow(QWidget):
    """A window holding one detached panel (#157).

    Closing it (its title bar's close) is [Close Panel]: an active
    machine is asked to stop first.

    Attributes:
    * `panel` (`Panel`): The panel.
    * `on_close` (`Callable[[], None]`): What closing it calls.
    """

    def __init__(self, panel: Panel, on_close: Callable[[], None]) -> None:
        """Make the window, holding the panel.

        Arguments:
        * `panel` (`Panel`): The panel.
        * `on_close` (`Callable[[], None]`): What closing it calls.
        """
        super().__init__()
        self.panel: Panel = panel
        self.on_close: Callable[[], None] = on_close
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(panel)

    def closeEvent(  # pylint: disable=invalid-name
        self, event: QCloseEvent
    ) -> None:
        """Close the panel as [Close Panel] does, not the window itself.

        Arguments:
        * `event` (`QCloseEvent`): The close; ignored, as
          `on_close()` takes the window away once the panel may go.
        """
        event.ignore()
        self.on_close()


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
    * `new_machine_row` (`QWidget`): The action row with [New
      Machine], for `machines/` (#141).
    * `new_shop_row` (`QWidget`): The action row with [New Shop].
    * `panels` (`list[Panel]`): The panels, left to right.
    * `detached` (`list[DetachedWindow]`): The panels detached into
      windows of their own (#157); tree clicks never go to them.
    * `closing` (`list[Panel]`): Panels told to close whose machine
      is still stopping; each closes once it has stopped (#156).
    * `exiting` (`bool`): True once [Exit Program] has stopped the
      machines; the window closes once every one has stopped.
    * `machines` (`list[MachineControl]`): The machines connected to
      this window, each shown in a panel only once it is clicked
      (#135).
    * `splitter` (`QSplitter`): The tree, then the panels.
    * `tree` (`TreeView`): The shop's and the design's files.
    * `current` (`int`): The current panel's index (#122).
    * `machine_timer` (`QTimer`): Keeps [Stop All] and the machine
      tabs' bars up to date.
    * `blink` (`bool`): Which half of a blink it is (a waiting
      machine's bar).
    """

    def __init__(self, model: App, controls: set[str] | None = None) -> None:
        """Make a window, with one empty panel, and show what it shows.

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
        self.add_button(top, EXIT, self.exit_program)

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

        # The tree on the left, then the panels; the first is current.
        self.splitter: QSplitter = splitter(Qt.Orientation.Horizontal)
        self.tree: TreeView = TreeView()
        self.tree.itemClicked.connect(self.select_item)
        self.tree.itemExpanded.connect(self.tree_opened)
        self.tree.itemCollapsed.connect(self.tree_opened)
        self.splitter.addWidget(self.tree)
        self.panels: list[Panel] = []
        self.detached: list[DetachedWindow] = []
        self.closing: list[Panel] = []
        self.exiting: bool = False
        self.machines: list[MachineControl] = []
        self.current: int = 0
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
        # guide (#139).
        model.listen(self.redraw)
        self.redraw()
        self.panels[0].show_guide(self.guide_text())
        WINDOWS.append(self)

    def add_button(
        self, line: QHBoxLayout, label: str, action: Callable[[], object]
    ) -> None:
        """Add a button to the top line.

        Arguments:
        * `line` (`QHBoxLayout`): The top line.
        * `label` (`str`): The button's label.
        * `action` (`Callable[[], object]`): What a press calls.
        """
        button: QPushButton = QPushButton(label)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(action)
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
        """Add an empty panel on the right ([+ Panel]); it is current."""
        panel: Panel = Panel(len(self.panels) + 1)
        panel.controls = machine_controls
        panel.open_machine = self.open_machine
        panel.say = functools.partial(self.model.say, problem=True)
        panel.edit_file = functools.partial(self.edit, panel)
        panel.close_panel = functools.partial(self.close_panel, panel)
        panel.detach_panel = functools.partial(self.detach_panel, panel)
        panel.clicked.connect(functools.partial(self.make_current, panel))
        self.panels.append(panel)
        self.splitter.addWidget(panel)
        self.make_current(panel)
        self.show_close_buttons()

    def show_close_buttons(self) -> None:
        """Show [Close Panel] on every panel but a last one (#156)."""
        panel: Panel
        for panel in self.panels:
            panel.close_button.setVisible(len(self.panels) > 1)

    def close_panel(self, panel: Panel) -> None:
        """Close a panel ([Close Panel], #156).

        An active machine's panel asks to stop it first, and closes
        once it has stopped; any other closes at once.  A machine's
        controls stay connected, to be opened again.

        Arguments:
        * `panel` (`Panel`): The panel.
        """
        holder: DetachedWindow | None = self.holder(panel)
        if holder is None and len(self.panels) < 2:
            return
        stopping: bool = panel in self.closing
        if panel.machines and is_active(panel.machines[0]) and not stopping:
            machine: MachineControl = panel.machines[0]
            answer: QMessageBox.StandardButton = QMessageBox.question(
                self,
                "Close Panel",
                f"{machine.name} is running.  Stop it before closing its "
                "panel?",
            )
            if answer != QMessageBox.StandardButton.Yes:
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
        if holder is not None:
            self.detached.remove(holder)
            holder.deleteLater()
            return
        self.panels.remove(panel)
        panel.hide()
        panel.setParent(None)
        panel.deleteLater()
        self.make_current(self.panels[min(self.current, len(self.panels) - 1)])
        self.show_close_buttons()

    def holder(self, panel: Panel) -> "DetachedWindow | None":
        """Return the window a detached panel is in (#157).

        Arguments:
        * `panel` (`Panel`): The panel.

        Returns:
        * (`DetachedWindow | None`): Its window, or None if it is in
          this one.
        """
        return next(
            (held for held in self.detached if held.panel is panel), None
        )

    def all_panels(self) -> list[Panel]:
        """Return the panels, detached ones last (#157).

        Returns:
        * (`list[Panel]`): Every panel of this window.
        """
        return self.panels + [held.panel for held in self.detached]

    def detach_panel(self, panel: Panel) -> None:
        """Detach a panel into a window of its own, or reattach it (#157).

        A detached panel keeps what it shows; [Reattach] puts it back as
        the rightmost panel.

        Arguments:
        * `panel` (`Panel`): The panel.
        """
        # Back in: the rightmost panel.
        holder: DetachedWindow | None = self.holder(panel)
        if holder is not None:
            self.detached.remove(holder)
            self.panels.append(panel)
            self.splitter.addWidget(panel)
            panel.detach_button.setText("Detach")
            holder.deleteLater()
            self.make_current(panel)
            self.show_close_buttons()
            return

        # Out: a panel is left behind for the tree's clicks.
        if len(self.panels) < 2:
            self.add_panel()
        self.panels.remove(panel)
        size: QSize = panel.size()
        holder = DetachedWindow(
            panel, functools.partial(self.close_panel, panel)
        )
        holder.setWindowTitle(f"scraftcam: {panel.title.text()}")
        holder.resize(size)
        holder.show()
        self.detached.append(holder)
        panel.detach_button.setText("Reattach")
        panel.close_button.show()
        panel.set_current(False)
        self.make_current(self.panels[min(self.current, len(self.panels) - 1)])
        self.show_close_buttons()

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

        The current one, unless it controls an active machine (#58,
        #154); then the first that does not, or a new one.  A panel
        whose machine is not active gives it up.

        Returns:
        * (`Panel`): The panel.
        """
        panel: Panel = self.panels[self.current]
        if not panel.machines or not is_active(panel.machines[0]):
            panel.drop_machine()
            return panel
        for panel in self.panels:
            if not panel.machines or not is_active(panel.machines[0]):
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
                    top.free_panel().show_machine(machine)
                    top.to_front(self)
                    return
        self.model.say(
            f"The {name} is not connected (LinuxCNC is the only "
            "controller so far)"
        )

    def to_front(self, clicked: "Window") -> None:
        """Bring this window to the front, unless it was clicked in.

        Arguments:
        * `clicked` (`Window`): The window clicked in.
        """
        if self is not clicked:
            self.raise_()
            self.activateWindow()

    def busy(self) -> str:
        """Say why this window may not close, if it may not (#56, #67).

        Returns:
        * (`str`): The first machine's reason, or the model's (a
          running machine), or "" when it may close.
        """
        machine: MachineControl
        for machine in self.machines:
            reason: str = machine.busy()
            if reason:
                return reason
        return self.model.close_refusal(self.controls)

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
        """Bring [Stop All] and each machine tab's bar up to date."""
        self.blink = not self.blink
        self.show_stop_all()
        panel: Panel
        for panel in self.all_panels():
            panel.show_dues(self.blink)

        # What was told to close once its machines stopped (#156).
        for panel in list(self.closing):
            if not any(machine.busy() for machine in panel.machines):
                self.close_panel(panel)
        if self.exiting and not self.busy():
            self.exiting = False
            self.close()

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
        dialog.open()

    def new_machine(self) -> None:
        """Ask about the new machine, and make it ([New Machine], #141)."""
        dialog: NewMachineDialog = NewMachineDialog(self, self.model)
        dialog.open()

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

    def closeEvent(  # pylint: disable=invalid-name
        self, event: QCloseEvent
    ) -> None:
        """Close, unless this window controls a running machine (#67).

        (Qt's name for it; [x] and the window's own close come here.)

        Arguments:
        * `event` (`QCloseEvent`): Accepted, or ignored with the
          reason on the top line.
        """
        # The title bar's close asks, as [Exit Program] does (#15).
        refusal: str = self.busy()
        if refusal and event.spontaneous() and self.ask_to_stop():
            refusal = self.busy()
        if refusal:
            self.model.say(refusal, problem=True)
            event.ignore()
            return

        # Closed, and its detached panels with it (#157).
        self.model.forget(self.redraw)
        if self in WINDOWS:
            WINDOWS.remove(self)
        holder: DetachedWindow
        for holder in self.detached:
            holder.deleteLater()
        self.detached = []
        event.accept()

    def exit_program(self) -> None:
        """Close the window ([Exit Program], #156), asking to stop first.

        With machines running: "Stop them all and exit?"; once they
        have stopped with their spindles off, it closes.
        """
        if self.busy() and not self.ask_to_stop():
            return
        self.close()

    def ask_to_stop(self) -> bool:
        """Ask to stop every running machine before exiting (#13).

        Returns:
        * (`bool`): True if the user said to stop them (and they were
          told to stop).
        """
        names: list[str] = [
            machine.name for machine in machine_controls() if machine.busy()
        ] + sorted(self.model.running)
        running: str = " and ".join(names) or "A machine"
        verb: str = "are" if len(names) > 1 else "is"
        answer: QMessageBox.StandardButton = QMessageBox.question(
            self,
            EXIT,
            f"{running} {verb} running.  Stop them all and exit?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        self.stop_all()
        if self.busy():
            self.exiting = True
            self.model.say(
                "Stopping every machine: scraftcam exits once they have "
                "stopped."
            )
        return True


# Class `CommandServer`:
class CommandServer(QTcpServer):
    """The command port (`port.py`): one JSON line in, one out.

    Attributes:
    * `model` (`App`): What every window shows.
    * `methods` (`dict[str, Method]`): The port's methods, by name.
    """

    def __init__(self, model: App) -> None:
        """Make the server; `listen()` opens its port.

        Arguments:
        * `model` (`App`): What every window shows.
        """
        super().__init__()
        self.model: App = model
        self.methods: dict[str, Method] = {
            "new_shop": self.new_shop,
            "press": self.press,
            "quit": self.quit,
            "select": self.select,
            "status": self.status,
            "tree": self.tree,
        }
        self.newConnection.connect(self.accept)

    def listen_local(self, number: int) -> bool:
        """Listen on a port of 127.0.0.1 only.

        Arguments:
        * `number` (`int`): The port, or 0 for any free one
          (`serverPort()` says which).

        Returns:
        * (`bool`): True when it listens.
        """
        return bool(
            self.listen(
                QHostAddress(QHostAddress.SpecialAddress.LocalHost), number
            )
        )

    def accept(self) -> None:
        """Take each new connection, and answer its lines."""
        while self.hasPendingConnections():
            socket: QTcpSocket = self.nextPendingConnection()
            socket.readyRead.connect(functools.partial(self.answer, socket))
            socket.disconnected.connect(socket.deleteLater)

    def answer(self, socket: QTcpSocket) -> None:
        """Answer every whole line a connection has sent.

        Arguments:
        * `socket` (`QTcpSocket`): The connection.
        """
        while socket.canReadLine():
            line: str = bytes(socket.readLine().data()).decode()
            reply_line: str = port.reply(line, self.methods)
            socket.write((reply_line + "\n").encode())
            socket.flush()

    @staticmethod
    def window(params: dict[str, object]) -> "Window":
        """Return the window a request names (`window`, from 0).

        Arguments:
        * `params` (`dict[str, object]`): The request's parameters.

        Returns:
        * (`Window`): The window.

        Raises:
        * `PortError`: If there is no such window.
        """
        index: object = params.get("window", 0)
        if not isinstance(index, int) or not 0 <= index < len(WINDOWS):
            raise PortError(f"no window {index}", port.INVALID_PARAMS)
        return WINDOWS[index]

    def status(self, _params: dict[str, object]) -> object:
        """Return what the windows show (`status`).

        Arguments:
        * `_params` (`dict[str, object]`): None needed.

        Returns:
        * (`object`): The model's state, and each window's.
        """
        model: App = self.model
        latest: Message = model.latest()
        return {
            "title": model.title(),
            "shop": model.shop_title,
            "design": model.design_title(),
            "message": latest.text,
            "problem": latest.problem,
            "running": sorted(model.running),
            "windows": [
                {
                    "buttons": [
                        label
                        for label, button in top.buttons.items()
                        if not button.isHidden()
                    ],
                    "tree": not top.tree.isHidden(),
                    "panels": len(top.panels),
                }
                for top in WINDOWS
            ],
        }

    def press(self, params: dict[str, object]) -> object:
        """Press a top line button, as a person would (`press`).

        Arguments:
        * `params` (`dict[str, object]`): `button` (its label) and
          `window` (from 0; 0 if not given).

        Returns:
        * (`object`): "pressed LABEL".

        Raises:
        * `PortError`: If there is no such button, or it is hidden.
        """
        top: Window = self.window(params)
        label: str = text_param(params, "button")
        button: QPushButton | None = top.buttons.get(label)
        if button is None:
            raise PortError(
                f"no button `{label}`; there are: {', '.join(top.buttons)}",
                port.INVALID_PARAMS,
            )
        if button.isHidden() or not button.isEnabled():
            raise PortError(f"`{label}` is not showing")
        button.click()
        return f"pressed {label}"

    def new_shop(self, params: dict[str, object]) -> object:
        """Make a new shop, as `NewShopDialog` would (`new_shop`).

        Arguments:
        * `params` (`dict[str, object]`): `directory`, `name`, `units`
          (strings) and `machines` (a list of kinds' keys).

        Returns:
        * (`object`): The new `shop.toml`'s path.

        Raises:
        * `PortError`: If an answer is not allowed, or it can not be
          written.
        """
        machines: object = params.get("machines", [])
        if not isinstance(machines, list) or not all(
            isinstance(kind, str) for kind in machines
        ):
            raise PortError(
                "`machines` must be a list of strings", port.INVALID_PARAMS
            )
        try:
            shop: Path = self.model.new_shop(
                Path(text_param(params, "directory")),
                text_param(params, "name"),
                text_param(params, "units"),
                [str(kind) for kind in machines],
            )
        except (ValueError, OSError) as error:
            raise PortError(str(error)) from error
        return str(shop)

    def tree(self, params: dict[str, object]) -> object:
        """Return what a window's tree shows (`tree`).

        Arguments:
        * `params` (`dict[str, object]`): `window` (from 0; 0 if not
          given).

        Returns:
        * (`object`): Per root, its label, then a list per child.
        """
        return self.window(params).tree.labels()

    def select(self, params: dict[str, object]) -> object:
        """Click a tree item, as a person would (`select`).

        Arguments:
        * `params` (`dict[str, object]`): `path` (the item's file or
          directory) and `window` (from 0; 0 if not given).

        Returns:
        * (`object`): What the current panel shows: `label`, `fields`
          (each field row's key and what its entry holds) and `text`.

        Raises:
        * `PortError`: If no item has that path.
        """
        top: Window = self.window(params)
        path: str = text_param(params, "path")
        item: QTreeWidgetItem | None = top.tree.item_at_path(
            Path(path).resolve()
        )
        if item is None:
            raise PortError(f"no item for {path}", port.INVALID_PARAMS)
        top.select_item(item)
        panel: Panel = top.panels[top.current]
        fields: dict[str, str] = {
            key: entry_text(entry) for key, entry in panel.entries.items()
        }
        return {
            "label": panel.title.text(),
            "fields": fields,
            "text": panel.text.toPlainText(),
        }

    def quit(self, _params: dict[str, object]) -> object:
        """Close every window, unless one refuses (`quit`).

        The windows close `QUIT_DELAY_MS` after the answer is sent.

        Arguments:
        * `_params` (`dict[str, object]`): None needed.

        Returns:
        * (`object`): "quitting".

        Raises:
        * `PortError`: If a window controls a running machine.
        """
        top: Window
        for top in WINDOWS:
            refusal: str = top.busy()
            if refusal:
                raise PortError(refusal)
        QTimer.singleShot(QUIT_DELAY_MS, close_all)
        return "quitting"


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
        chosen: str = QFileDialog.getExistingDirectory(
            self,
            "The shop's directory",
            str(start),
            QFileDialog.Option.ShowDirsOnly
            | QFileDialog.Option.DontUseNativeDialog,
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
