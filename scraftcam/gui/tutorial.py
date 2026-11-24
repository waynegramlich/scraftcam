"""Tutorials: a recording played in the outline editor (#19).

`--tutorial FILE` opens the recording's starting outline with the
narration panel at the bottom; with `--headless` too it runs every
step and checks each state instead, as the tests do.  The editor is
passed in, never imported: run with `-m`, its module is `__main__`.
"""

from __future__ import annotations

import typing

from scraftcam.exposed.steps import Player, Recording, View
from scraftcam.gui import outline_exposed
from scraftcam.gui.narration import NarrationPanel
from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtWidgets import QApplication, QLayout  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order

if typing.TYPE_CHECKING:
    from scraftcam.gui.outline_editor import OutlineEditor

# The window size every replay sees (#498).
SIZE: tuple[int, int] = (1280, 800)


def start(editor: OutlineEditor, recording: Recording) -> Player:
    """Make the player of `recording`'s steps on `editor`.

    Arguments:
    * `editor` (`OutlineEditor`):
        The editor, open on the recording's starting outline.
    * `recording` (`Recording`):
        The steps.

    Returns:
    * (`Player`): its player, before the first step.
    """
    # The steps reach the editor by its handle, as over MCP.
    outline_exposed.EDITORS.add(editor)
    handle: str = outline_exposed.HANDLES.handle(editor)

    def depth() -> int:
        """Give the editor's undo depth."""
        return len(editor.view.history.done)

    def place(shown: View) -> None:
        """Show the editor at a step's recorded view (#566)."""
        outline_exposed.place_view(editor.view, shown)

    return Player(
        recording, {"editor": handle}, depth, editor.view.undo, place
    )


def show_panel(editor: OutlineEditor, recording: Recording) -> None:
    """Put the narration panel at the bottom of `editor`.

    Arguments:
    * `editor` (`OutlineEditor`):
        The editor, open on the recording's starting outline.
    * `recording` (`Recording`):
        The steps.
    """
    layout: QLayout | None = editor.layout()
    if layout is not None:
        layout.addWidget(NarrationPanel(start(editor, recording)))


def mismatches(editor: OutlineEditor, recording: Recording) -> list[str]:
    """Run every step on `editor` (offscreen), checking each state.

    Arguments:
    * `editor` (`OutlineEditor`):
        The editor, open on the recording's starting outline.
    * `recording` (`Recording`):
        The steps.

    Returns:
    * (`list[str]`): a message per step whose state differs.
    """
    # Its window (itself, or the panel's window it sits in, #593)
    # shown at the one size and fitted, as a user would first see it.
    editor.window().resize(*SIZE)
    editor.window().show()
    editor.view.fit()
    QApplication.processEvents()
    return start(editor, recording).mismatches()
