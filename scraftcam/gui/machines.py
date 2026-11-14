"""The machines: a machine's controls, and the `machines/` summary.

* `MachineControl`: a machine's controls, as the GUI knows them (the
  HMI is one); `Due`: when it next needs its operator.
* `MachineTab`: a machine panel's header, its name over a `DueBar`,
  the bar that fills as the operator's next task comes (#102).
* `MachinesView`: what a panel shows for the shop's `machines/`
  directory (`T.osiade~5.1.9` #134): three lines per CNC machine (its
  kind, controller and state; a detail or two; its bar), a line per
  other machine, and the next tools to fetch across all machines.
  A machine's name button shows its own panel (#135).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..packages import require
from ..shops import not_initialized
from .fields import read_item
from .theme import colors
from .tree import ERROR, Node

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QGridLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

# A machine's bar: its steps, its least width (pixels), how many
# minutes count as soon, and soon's color (#102).
BAR_STEPS: int = 1000
BAR_WIDTH: int = 140
SOON: float = 1.0
SOON_COLOR: str = "#e0a000"
FILL_COLOR: str = "#3d7fd6"


# Class `MachineControl`:
@dataclass(frozen=True, slots=True)
class MachineControl:
    """A machine's controls, as a panel shows them (step 5, #52).

    The HMI (`scraftcam.hmi.lcnc_hmi.HMI`) is one; the GUI knows it
    only through these, so that it needs no LinuxCNC to start.

    Attributes:
    * `name` (`str`): The machine's name, as its file's `name`.
    * `widget` (`QWidget`): The controls, filling the panel (#59).
    * `busy` (`Callable[[], str]`): Why nothing may close yet (the
      machine runs, or its spindle is on), or `""` (#56).
    * `stop` (`Callable[[], None]`): Stops the machine at once.
    * `on_minimal` (`Callable[[Callable[[bool], None]], None]`): Hands
      the controls what to call when they go minimal (True) or full
      (False), so the window can shrink with them (#94).
    * `due` (`Callable[[], Due | None]`): When the operator is next
      needed (#102); `None` with no program.

    Constructor:
    * `MachineControl(name, widget, busy, stop, on_minimal, due)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    widget: QWidget = field(init=True)
    busy: Callable[[], str] = field(init=True)
    stop: Callable[[], None] = field(init=True)
    on_minimal: Callable[[Callable[[bool], None]], None] = field(init=True)
    due: Callable[[], "Due | None"] = field(init=True)


# Class `Due`:
@dataclass(frozen=True, slots=True)
class Due:
    """When a machine next needs its operator (#102, #103).

    Attributes:
    * `what` (`str`): What then: a tool (`T05`), or `end`.
    * `left` (`float`): Minutes until then (0 when waiting now).
    * `span` (`float`): Minutes from the one before to it.
    * `waiting` (`bool`): True when it waits for the operator now.

    Constructor:
    * `Due(what, left, span, waiting)`
    """

    # Constructor arguments:
    what: str = field(init=True)
    left: float = field(init=True)
    span: float = field(init=True)
    waiting: bool = field(init=True)


# Class `MachineItem`:
@dataclass(frozen=True, slots=True)
class MachineItem:
    """One machine file of `machines/`, as the summary shows it (#134).

    Attributes:
    * `name` (`str`): Its `name`, or its file's stem.
    * `kind` (`str`): Its `machine` (`mill`, `router`, ...), or "".
    * `controller` (`str`): Its controller, or "" for a machine that
      is not CNC.
    * `details` (`str`): A detail or two, by kind (#137), or its
      notes' first line.
    * `error` (`str`): Why its file does not read, or "".
    * `missing` (`tuple[str, ...]`): The fields it needs to run that it
      does not have yet (#145).

    Constructor:
    * `MachineItem(name, kind, controller, details, error, missing)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    kind: str = field(init=True)
    controller: str = field(init=True)
    details: str = field(init=True)
    error: str = field(init=True)
    missing: tuple[str, ...] = field(init=True)


# Function `minutes()`:
def minutes(amount: float) -> str:
    """Return minutes as `M:SS`.

    Arguments:
    * `amount` (`float`): The minutes.

    Returns:
    * (`str`): E.g. `3:42`.
    """
    seconds: int = max(round(amount * 60.0), 0)
    return f"{seconds // 60}:{seconds % 60:02d}"


# Function `is_machines_directory()`:
def is_machines_directory(node: Node) -> bool:
    """Tell whether an item is a shop's `machines/` directory.

    Arguments:
    * `node` (`Node`): The item.

    Returns:
    * (`bool`): True for `machines/` beside a `shop.toml`.
    """
    return (
        node.path.name == "machines"
        and node.path.is_dir()
        and (node.path.parent / "shop.toml").is_file()
    )


# Function `machine_item()`:
def machine_item(node: Node) -> MachineItem:
    """Read one machine file for the summary.

    Arguments:
    * `node` (`Node`): The file's item.

    Returns:
    * (`MachineItem`): What the summary shows of it.
    """
    # A file that does not read: its name and why.
    path: Path = node.path
    item: dict[str, object]
    problem: str
    item, problem = read_item(path) if node.kind != ERROR else ({}, "")
    if node.kind == ERROR or problem:
        return MachineItem(path.stem, "", "", "", node.error or problem, ())

    # Its name, kind and controller.
    name: str = str(item.get("name", path.stem))
    kind: str = str(item.get("machine", ""))
    own: object = item.get("controller", "")
    controller: str = str(
        own.get("name", "") if isinstance(own, dict) else own
    )

    # A detail or two by kind (#137): a mill's or router's spindle and
    # carousel; any other's notes.
    details: str = ""
    spindle: object = item.get("spindle")
    if kind in ("mill", "router") and isinstance(spindle, dict):
        parts: list[str] = [
            str(spindle[key])
            for key in ("interface", "max_rpm")
            if key in spindle
        ]
        carousel: object = item.get("carousel")
        if isinstance(carousel, dict) and "slots" in carousel:
            parts.append(f"{carousel['slots']} slot carousel")
        details = ", ".join(parts)
    if not details:
        details = str(item.get("notes", "")).strip().split("\n", maxsplit=1)[0]
    missing: tuple[str, ...] = tuple(not_initialized(item, "machine"))
    return MachineItem(name, kind, controller, details, "", missing)


# Function `fetch_list()`:
def fetch_list(controls: list[MachineControl]) -> list[str]:
    """Return the next tools to fetch, across all machines (#134).

    Arguments:
    * `controls` (`list[MachineControl]`): The machines connected.

    Returns:
    * (`list[str]`): Soonest first, e.g. "T05 for Shop mill, now" or
      "T02 for Shop mill, in 3:42".
    """
    wanted: list[tuple[float, str]] = []
    control: MachineControl
    for control in controls:
        due: Due | None = control.due()
        if due is None or due.what == "end":
            continue
        when: str = "now" if due.waiting else f"in {minutes(due.left)}"
        wanted.append(
            (
                0.0 if due.waiting else due.left,
                f"{due.what} for {control.name}, {when}",
            )
        )
    return [text for _left, text in sorted(wanted)]


# Class `DueBar`:
class DueBar(QProgressBar):
    """A bar that fills as a machine's operator's next task comes (#102).

    It fills, from black, as the next task (a tool or carousel change,
    #136) comes, and is full when it is due; it starts again from
    black after it (#106).  Its text is the time left.  The urgency
    shows in marks as well as color, for operators who are color
    blind: "3:42"; within `SOON` minutes, amber, "▲ 0:40"; waiting now,
    red and blinking, "■ NOW".
    """

    def __init__(self) -> None:
        """Make an empty bar."""
        super().__init__()
        self.setRange(0, BAR_STEPS)
        self.setTextVisible(True)
        self.setMinimumWidth(BAR_WIDTH)

    def show_due(self, due: Due | None, blink: bool) -> None:
        """Show when the operator is next needed.

        Arguments:
        * `due` (`Due | None`): When; `None` with no program.
        * `blink` (`bool`): Which half of a blink this is.
        """
        if due is None:
            self.setValue(0)
            self.setFormat("no program")
            self.setStyleSheet("")
            return
        color: str
        if due.waiting:
            self.setValue(BAR_STEPS)
            self.setFormat("■ NOW")
            color = colors().problem if blink else colors().quiet
        else:
            done: float = 1.0 - min(max(due.left / due.span, 0.0), 1.0)
            self.setValue(round(done * BAR_STEPS))
            soon: bool = due.left <= SOON
            self.setFormat(f"{'▲ ' if soon else ''}{minutes(due.left)}")
            color = SOON_COLOR if soon else FILL_COLOR
        self.setToolTip(
            "Until the end" if due.what == "end" else f"Until {due.what}"
        )
        self.setStyleSheet(
            "QProgressBar { background: black; color: white;"
            " text-align: center; }"
            f" QProgressBar::chunk {{ background: {color}; }}"
        )


# Class `MachineTab`:
class MachineTab(QWidget):
    """A machine panel's header: its name over its bar (#102, #135).

    Attributes:
    * `meter` (`DueBar`): The time to the operator's next task.
    """

    def __init__(self, name: str) -> None:
        """Make the header.

        Arguments:
        * `name` (`str`): The machine's name.
        """
        super().__init__()
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)
        label: QLabel = QLabel(name)
        label.setStyleSheet("font-weight: bold")
        layout.addWidget(label)
        self.meter: DueBar = DueBar()
        layout.addWidget(self.meter)

    def show_due(self, due: Due | None, blink: bool) -> None:
        """Show when the operator is next needed.

        Arguments:
        * `due` (`Due | None`): When; `None` with no program.
        * `blink` (`bool`): Which half of a blink this is.
        """
        self.meter.show_due(due, blink)


# Class `MachinesView`:
class MachinesView(QWidget):
    """The `machines/` summary (#134), brought up to date by `refresh()`.

    A machine each, in tree order, CNC machines first: a CNC machine
    takes three lines (its name button, kind, controller and state;
    its details; its next task's bar), any other one line.  Then the
    next tools to fetch, across all machines.

    Attributes:
    * `bars` (`dict[str, DueBar]`): Each CNC machine's bar, by name.
    * `controls` (`Callable[[], list[MachineControl]]`): The machines
      connected, in every window.
    * `fetch` (`QLabel`): The next tools to fetch.
    * `items` (`list[MachineItem]`): The machine files, in tree order.
    * `states` (`dict[str, QLabel]`): Each CNC machine's first line
      after its name, by name.
    """

    def __init__(
        self,
        node: Node,
        controls: Callable[[], list[MachineControl]],
        open_machine: Callable[[str], None],
    ) -> None:
        """Make the summary of a `machines/` directory.

        Arguments:
        * `node` (`Node`): The directory.
        * `controls` (`Callable[[], list[MachineControl]]`): Gives the
          machines connected.
        * `open_machine` (`Callable[[str], None]`): Shows a machine's
          own panel, by name (its name button, #135).
        """
        super().__init__()
        self.controls: Callable[[], list[MachineControl]] = controls
        self.items: list[MachineItem] = [
            machine_item(child)
            for child in node.children
            if child.path.suffix == ".toml"
        ]
        self.bars: dict[str, DueBar] = {}
        self.states: dict[str, QLabel] = {}
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # The CNC machines, then the others; then the tools to fetch.
        item: MachineItem
        for item in self.items:
            if item.controller:
                layout.addWidget(self.cnc_block(item, open_machine))
        for item in self.items:
            if not item.controller:
                layout.addWidget(other_line(item))
        if not self.items:
            layout.addWidget(QLabel("No machines yet."))
        layout.addWidget(heading("Tools to fetch"))
        self.fetch: QLabel = QLabel()
        layout.addWidget(self.fetch)
        layout.addStretch(1)
        self.refresh(False)

    def cnc_block(
        self, item: MachineItem, open_machine: Callable[[str], None]
    ) -> QWidget:
        """Return a CNC machine's three lines.

        Arguments:
        * `item` (`MachineItem`): The machine.
        * `open_machine` (`Callable[[str], None]`): Shows a machine's
          own panel, by name.

        Returns:
        * (`QWidget`): Its name button and state, its details, and its
          next task's bar.
        """
        block: QWidget = QWidget()
        grid: QGridLayout = QGridLayout(block)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setVerticalSpacing(1)
        button: QPushButton = QPushButton(item.name)
        button.setToolTip(f"Show the {item.name}'s own panel")
        button.clicked.connect(_opener(open_machine, item.name))
        state: QLabel = QLabel()
        details: QLabel = QLabel(item.details)
        details.setStyleSheet(f"color: {colors().quiet}")
        meter: DueBar = DueBar()
        grid.addWidget(button, 0, 0)
        grid.addWidget(state, 0, 1)
        grid.addWidget(details, 1, 1)
        grid.addWidget(meter, 2, 1, Qt.AlignmentFlag.AlignLeft)
        grid.setColumnStretch(1, 1)
        self.states[item.name] = state
        self.bars[item.name] = meter
        return block

    def refresh(self, blink: bool) -> None:
        """Show each machine's state and bar, and the tools to fetch.

        Arguments:
        * `blink` (`bool`): Which half of a blink this is.
        """
        controls: list[MachineControl] = self.controls()
        connected: dict[str, MachineControl] = {
            control.name: control for control in controls
        }
        item: MachineItem
        for item in self.items:
            if not item.controller:
                continue
            control: MachineControl | None = connected.get(item.name)
            reason: str = "" if control is None else control.busy()
            state: str = (
                "not initialized yet"
                if control is None and item.missing
                else "not connected"
                if control is None
                else "running"
                if reason
                else "ready"
            )
            label: QLabel = self.states[item.name]
            label.setText(f"{item.kind}, {item.controller}: {state}")
            label.setToolTip(reason)
            meter: DueBar = self.bars[item.name]
            if control is None:
                meter.show_due(None, blink)
                meter.setFormat("not connected")
            else:
                meter.show_due(control.due(), blink)
        fetches: list[str] = fetch_list(controls)
        self.fetch.setText("\n".join(fetches) if fetches else "None.")


# Function `other_line()`:
def other_line(item: MachineItem) -> QLabel:
    """Return a line for a machine that is not CNC, or does not read.

    Arguments:
    * `item` (`MachineItem`): The machine.

    Returns:
    * (`QLabel`): "NAME (KIND): DETAILS", or its problem, in red.
    """
    line: QLabel
    if item.error:
        line = QLabel(f"{item.name} (error): {item.error}")
        line.setStyleSheet(f"color: {colors().problem}")
    else:
        kind: str = f" ({item.kind})" if item.kind else ""
        line = QLabel(f"{item.name}{kind}: {item.details}")
    line.setWordWrap(True)
    return line


# Function `heading()`:
def heading(text: str) -> QLabel:
    """Return a section's heading.

    Arguments:
    * `text` (`str`): The heading.

    Returns:
    * (`QLabel`): It, bold.
    """
    label: QLabel = QLabel(text)
    label.setStyleSheet("font-weight: bold")
    return label


# Function `_opener()`:
def _opener(
    open_machine: Callable[[str], None], name: str
) -> Callable[[], None]:
    """Return what [Open] calls for one machine.

    Arguments:
    * `open_machine` (`Callable[[str], None]`): Shows a machine.
    * `name` (`str`): The machine's name.

    Returns:
    * (`Callable[[], None]`): Shows that machine.
    """

    # Function `opened()`:
    def opened() -> None:
        """Show the machine."""
        open_machine(name)

    return opened
