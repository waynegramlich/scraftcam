"""Following up a controller template's change (`T.osiade~5.1.9` #142).

A machine holds its own copy of a controller template (#141).  When
someone changes a template, the GUI shows them, at once and in the
template's panel, each machine made from it and its value of each
field that changed: one that still held the old value can be
updated ([Update], or [Update All]); one with a value of its own is
shown beside the new one, to update or keep.  Nothing is left for
the operator: a machine's own panel never shows a mark.

* `follow_ups()`: what changed, machine by machine.
* `update_machine()`: writes a new value into a machine's copy.
* `FollowUpView`: the list, with its buttons.
"""

import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..packages import require
from ..shops import HEADER
from .fields import read_item, write_item
from .theme import colors

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtWidgets import (  # noqa: E402
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order

# The keys a template change is not followed up for: its header (its
# name, kind, language, version and notes).
SKIPPED: frozenset[str] = frozenset(header.key for header in HEADER)

# How much of a value a line shows.
SHOWN: int = 40


# Class `FollowUp`:
@dataclass(frozen=True, slots=True)
class FollowUp:
    """One machine's value of one field a template change changed.

    Attributes:
    * `machine` (`str`): The machine's name.
    * `path` (`Path`): Its file.
    * `key` (`str`): The field's key, in its `[controller]`.
    * `new` (`object`): The template's new value (`None`: removed).
    * `own` (`object`): The machine's value (`None`: it has none).
    * `stale` (`bool`): True when the machine held the template's old
      value, so it can simply be updated.

    Constructor:
    * `FollowUp(machine, path, key, new, own, stale)`
    """

    # Constructor arguments:
    machine: str = field(init=True)
    path: Path = field(init=True)
    key: str = field(init=True)
    new: object = field(init=True)
    own: object = field(init=True)
    stale: bool = field(init=True)


# Function `is_template()`:
def is_template(path: Path) -> bool:
    """Tell whether a file is a shop's controller template.

    Arguments:
    * `path` (`Path`): The file.

    Returns:
    * (`bool`): True for a `.toml` in `controllers/` beside a
      `shop.toml`.
    """
    return (
        path.suffix == ".toml"
        and path.parent.name == "controllers"
        and (path.parent.parent / "shop.toml").is_file()
    )


# Function `follow_ups()`:
def follow_ups(
    template: Path, old: dict[str, object], new: dict[str, object]
) -> list[FollowUp]:
    """Return what a template change means for the machines made from it.

    Arguments:
    * `template` (`Path`): The template's file, in `controllers/`.
    * `old` (`dict[str, object]`): The template before.
    * `new` (`dict[str, object]`): The template now.

    Returns:
    * (`list[FollowUp]`): One per machine made from it (its copy's
      `template` names it) and changed field whose value differs from
      the new one, machine by machine.
    """
    # The fields that changed.
    keys: list[str] = sorted(
        key
        for key in set(old) | set(new)
        if key not in SKIPPED and old.get(key) != new.get(key)
    )
    name: object = new.get("name", old.get("name"))
    if not keys:
        return []

    # Each machine made from it, and its value of each.
    found: list[FollowUp] = []
    path: Path
    for path in sorted((template.parent.parent / "machines").glob("*.toml")):
        item: dict[str, object] = read_item(path)[0]
        copy: object = item.get("controller")
        if not isinstance(copy, dict) or copy.get("template") != name:
            continue
        key: str
        for key in keys:
            own: object = copy.get(key)
            if own != new.get(key):
                found.append(
                    FollowUp(
                        str(item.get("name", path.stem)),
                        path,
                        key,
                        new.get(key),
                        own,
                        own == old.get(key),
                    )
                )
    return found


# Function `update_machine()`:
def update_machine(follow_up: FollowUp) -> None:
    """Give a machine's copy the template's new value of a field.

    Arguments:
    * `follow_up` (`FollowUp`): The machine and the field.

    Raises:
    * `OSError`: If the file can not be read or written.
    * `tomllib.TOMLDecodeError`: If it no longer reads.
    """
    with follow_up.path.open("rb") as file:
        item: dict[str, object] = tomllib.load(file)
    copy: object = item.get("controller")
    if not isinstance(copy, dict):
        return
    if follow_up.new is None:
        copy.pop(follow_up.key, None)
    else:
        copy[follow_up.key] = follow_up.new
    write_item(follow_up.path, item)


# Function `shown()`:
def shown(value: object) -> str:
    """Return a value as a line shows it: short, on one line.

    Arguments:
    * `value` (`object`): The value, or `None` for none.

    Returns:
    * (`str`): E.g. `"linuxcnc"`, or `(none)`.
    """
    if value is None:
        return "(none)"
    text: str = " ".join(str(value).split())
    return repr(text if len(text) <= SHOWN else text[: SHOWN - 3] + "...")


# Class `FollowUpView`:
class FollowUpView(QWidget):
    """The machines a template change touches, with what to do (#142).

    Attributes:
    * `follow_ups` (`list[FollowUp]`): What it shows, in order.
    * `states` (`list[QLabel]`): Each one's state: what to do, or
      "updated" or "kept".
    * `buttons` (`list[list[QPushButton]]`): Each one's buttons.
    * `say` (`Callable[[str], None]`): Reports a problem.
    """

    def __init__(
        self, follow_ups_found: list[FollowUp], say: Callable[[str], None]
    ) -> None:
        """Make the list.

        Arguments:
        * `follow_ups_found` (`list[FollowUp]`): What to show.
        * `say` (`Callable[[str], None]`): Reports a problem.
        """
        super().__init__()
        self.follow_ups: list[FollowUp] = follow_ups_found
        self.say: Callable[[str], None] = say
        self.states: list[QLabel] = []
        self.buttons: list[list[QPushButton]] = []
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        heading: QLabel = QLabel(
            "This template changed.  The machines made from it:"
        )
        heading.setStyleSheet("font-weight: bold")
        layout.addWidget(heading)
        grid_widget: QWidget = QWidget()
        grid: QGridLayout = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        number: int
        follow_up: FollowUp
        for number, follow_up in enumerate(follow_ups_found):
            line: QLabel = QLabel(
                f"{follow_up.machine}: {follow_up.key}"
                + ("" if follow_up.stale else f" = {shown(follow_up.own)}")
            )
            state: QLabel = QLabel(
                "had the old value"
                if follow_up.stale
                else f"its own value; the template's: {shown(follow_up.new)}"
            )
            state.setStyleSheet(f"color: {colors().quiet}")
            update: QPushButton = QPushButton("Update")
            update.clicked.connect(self.doer(number, keep=False))
            row: list[QPushButton] = [update]
            grid.addWidget(line, number, 0)
            grid.addWidget(state, number, 1)
            grid.addWidget(update, number, 2)
            if not follow_up.stale:
                keep: QPushButton = QPushButton("Keep")
                keep.clicked.connect(self.doer(number, keep=True))
                grid.addWidget(keep, number, 3)
                row.append(keep)
            self.states.append(state)
            self.buttons.append(row)
        grid.setColumnStretch(1, 1)
        layout.addWidget(grid_widget)

        # [Update All], for those that had the old value.
        if sum(follow_up.stale for follow_up in follow_ups_found) > 1:
            every: QPushButton = QPushButton("Update All with the old value")
            every.clicked.connect(self.update_stale)
            layout.addWidget(every)

    def doer(self, number: int, *, keep: bool) -> Callable[[], None]:
        """Return what a line's [Update] or [Keep] calls.

        Arguments:
        * `number` (`int`): The line.
        * `keep` (`bool`): True for [Keep].

        Returns:
        * (`Callable[[], None]`): Updates or keeps that one.
        """

        # Function `done()`:
        def done() -> None:
            """Update or keep the one line."""
            self.settle(number, keep=keep)

        return done

    def settle(self, number: int, *, keep: bool) -> None:
        """Update one machine's field, or keep its own value.

        Arguments:
        * `number` (`int`): The line.
        * `keep` (`bool`): True to keep the machine's own value.
        """
        if not keep:
            try:
                update_machine(self.follow_ups[number])
            except (OSError, tomllib.TOMLDecodeError) as error:
                self.say(f"{self.follow_ups[number].path}: {error}")
                return
        self.states[number].setText("kept" if keep else "updated")
        button: QPushButton
        for button in self.buttons[number]:
            button.setEnabled(False)

    def update_stale(self) -> None:
        """Update every machine that had the old value ([Update All])."""
        number: int
        follow_up: FollowUp
        for number, follow_up in enumerate(self.follow_ups):
            if follow_up.stale and self.buttons[number][0].isEnabled():
                self.settle(number, keep=False)
