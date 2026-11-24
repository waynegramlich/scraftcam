"""The GUI's functions reached over MCP (`T.og~6.9` #577, #585).

Importing this module registers them; `window.run()` does so when
`scraftcam.run` is given `--mcp PORT`.  They replace the old JSON
line command port (`CommandServer`, `port.py`).  Every one runs on
Qt's main thread (the server's `QtRunner` sees to that), and names a
window by its place in `window.WINDOWS`, from 0.
"""

from __future__ import annotations

from pathlib import Path

from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError
from scraftcam.gui import window
from scraftcam.gui.app import App, Message
from scraftcam.gui.views import Panel, entry_text
from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QPushButton, QTreeWidgetItem  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order


# Function `_window()`:
def _window(number: int) -> window.Window:
    """Return the window numbered `number`, from 0.

    Arguments:
    * `number` (`int`): The window's place in `window.WINDOWS`.

    Returns:
    * (`window.Window`): The window.

    Raises:
    * `ExposedError`: If there is no such window.
    """
    if not 0 <= number < len(window.WINDOWS):
        raise ExposedError(
            f"no window {number}; there are {len(window.WINDOWS)}"
        )
    return window.WINDOWS[number]


# Function `_model()`:
def _model() -> App:
    """Return what every window shows.

    Returns:
    * (`App`): The model, from the first window.
    """
    return _window(0).model


# Function `status()`:
@exposed.reads
def status() -> dict[str, object]:
    """Tell what the windows show.

    Returns:
    * (`dict[str, object]`): The title, shop, design, latest message
      (and whether it is a problem), the machines running, and per
      window its top line buttons showing, whether its tree shows,
      and its number of panels.
    """
    model: App = _model()
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
            for top in window.WINDOWS
        ],
    }


# Function `top_button()`:
@exposed.changes
def top_button(label: str, window_number: int = 0) -> str:
    """Press the `label` button on window `window_number`'s top line.

    Arguments:
    * `label` (`str`): The button's label (e.g. "Tree").
    * `window_number` (`int`): The window, from 0.

    Returns:
    * (`str`): "pressed LABEL".

    Raises:
    * `ExposedError`: If there is no such button, or it is hidden or
      greyed.
    """
    top: window.Window = _window(window_number)
    button: QPushButton | None = top.buttons.get(label)
    if button is None:
        raise ExposedError(
            f"no button `{label}`; there are: {', '.join(top.buttons)}"
        )
    if button.isHidden() or not button.isEnabled():
        raise ExposedError(f"`{label}` is not showing")
    button.click()
    return f"pressed {label}"


# Function `new_shop()`:
@exposed.changes
def new_shop(
    directory: str, name: str, units: str, machines: list[str]
) -> str:
    """Make the shop `name` in `directory`, as [New Shop] would.

    Arguments:
    * `directory` (`str`): Where the shop goes.
    * `name` (`str`): The shop's name.
    * `units` (`str`): Its units (a key of `app.UNITS`).
    * `machines` (`list[str]`): The kinds of machine it has (keys of
      `app.MACHINE_KINDS`).

    Returns:
    * (`str`): The new `shop.toml`'s path.

    Raises:
    * `ExposedError`: If an answer is not allowed, or it can not be
      written.
    """
    try:
        shop: Path = _model().new_shop(
            Path(directory), name, units, list(machines)
        )
    except (ValueError, OSError) as error:
        raise ExposedError(str(error)) from error
    return str(shop)


# Function `tree()`:
@exposed.reads
def tree(window_number: int = 0) -> list[object]:
    """Tell what window `window_number`'s tree shows.

    Arguments:
    * `window_number` (`int`): The window, from 0.

    Returns:
    * (`list[object]`): Per root, its label, then a list per child.
    """
    return _window(window_number).tree.labels()


# Function `select()`:
@exposed.changes
def select(path: str, window_number: int = 0) -> dict[str, object]:
    """Click the tree item for `path` in window `window_number`.

    Arguments:
    * `path` (`str`): The item's file or directory.
    * `window_number` (`int`): The window, from 0.

    Returns:
    * (`dict[str, object]`): What the current panel then shows:
      `label`, `fields` (each field row's key and what its entry
      holds) and `text`.

    Raises:
    * `ExposedError`: If no item has that path.
    """
    top: window.Window = _window(window_number)
    item: QTreeWidgetItem | None = top.tree.item_at_path(Path(path).resolve())
    if item is None:
        raise ExposedError(f"no item for {path}")
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


# Function `panel_tab()`:
@exposed.changes
def panel_tab(label: str, window_number: int = 0) -> str:
    """Show the `label` tab of window `window_number`'s current panel.

    Arguments:
    * `label` (`str`): The tab's label (e.g. "Outline", "Fields").
    * `window_number` (`int`): The window, from 0.

    Returns:
    * (`str`): "showing LABEL".

    Raises:
    * `ExposedError`: If the current panel has no such tab.
    """
    top: window.Window = _window(window_number)
    panel: Panel = top.panels[top.current]
    labels: list[str] = [
        panel.tabs.tabText(index) for index in range(panel.tabs.count())
    ]
    if label not in labels:
        raise ExposedError(f"no tab `{label}`; there are: {', '.join(labels)}")
    panel.tabs.setCurrentIndex(labels.index(label))
    return f"showing {label}"


# Function `open_machine()`:
@exposed.changes
def open_machine(name: str, window_number: int = 0) -> dict[str, object]:
    """Open the machine `name`'s panel, connecting it if it is not
    (#607), as clicking it in the machines list does.

    Arguments:
    * `name` (`str`): The machine's name (e.g. "Shop mill").
    * `window_number` (`int`): The window, from 0.

    Returns:
    * (`dict[str, object]`): `status()` afterwards (its message says
      why, when it could not be connected).
    """
    _window(window_number).open_machine(name)
    return status()


# Function `to_front()`:
@exposed.changes
def to_front(window_number: int = 0) -> str:
    """Bring window `window_number` to the front of the screen.

    Arguments:
    * `window_number` (`int`): The window, from 0.

    Returns:
    * (`str`): "in front".
    """
    top: window.Window = _window(window_number)
    top.showNormal()
    top.raise_()
    top.activateWindow()
    return "in front"


# Function `quit_all()`:
@exposed.changes
def quit_all() -> str:
    """Close every window, unless one controls a running machine.

    The windows close `window.QUIT_DELAY_MS` after the answer is
    sent, so that the answer gets out.

    Returns:
    * (`str`): "quitting".

    Raises:
    * `ExposedError`: If a window refuses (its machine runs).
    """
    top: window.Window
    for top in window.WINDOWS:
        refusal: str = top.busy()
        if refusal:
            raise ExposedError(refusal)
    QTimer.singleShot(window.QUIT_DELAY_MS, window.close_all)
    return "quitting"
