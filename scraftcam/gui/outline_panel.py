"""The outline editor in the GUI's first panel (`T.og~6.9` #S5).

What `scraftcam.run` does with the outline editor's old command line
(the standalone editor is gone, #599):

* `--outline [FILE]`: edits an outline file, saving every change (a
  new one starts as the triangle); with no file, a new outline kept
  nowhere.
* `--tutorial FILE`: plays a recording (`NAME.steps.md`) with its
  narration panel, its outline its own and never saved (#595); with
  `--headless` too, checks every step instead.
* `--record [FILE]`: records what the user does as steps (#21), and
  what they say (#532) unless `--no-speech`, turned into each step's
  draft once the GUI closes.
"""

from __future__ import annotations

import sys
import time
import typing
from dataclasses import dataclass, field
from pathlib import Path

from scraftcam.exposed import steps
from scraftcam.exposed.exposed import ExposedError
from scraftcam.exposed.steps import Recording
from scraftcam.gui import outline_exposed, tutorial
from scraftcam.gui.outline_editor import (
    Drawing,
    OutlineEditor,
    drawing_from,
    drawing_from_text,
)
from scraftcam.gui.outline_file import OutlineError
from scraftcam.gui.recorder import Recorder
from scraftcam.shops import is_read_only
from scraftcam.speech import gain_problems

if typing.TYPE_CHECKING:
    from scraftcam.gui.views import Panel
    from scraftcam.gui.window import Window

# What a bare `--outline` gives: a new outline, kept in no file.
NEW_OUTLINE: Path = Path()

# What an outline in the package says when it is opened (#683).
READ_ONLY_OUTLINE: str = (
    "This outline is in the example shop, which is read only: "
    "[Copy Shop] makes one of your own"
)

# Where `--record` writes when no file is named (#503).
RECORDINGS: Path = Path.home() / ".scraftcam" / "recordings"


# Function `record_path()`:
def record_path(record: Path, path: Path | None) -> Path:
    """Give the file `--record` writes.

    Arguments:
    * `record` (`Path`): What `--record` named: a file, or a
      directory (`RECORDINGS` when nothing was named).
    * `path` (`Path | None`): The outline file edited, if any.

    Returns:
    * (`Path`): A named file as is; in a directory, a new file
      named after the outline and the time (`end_mill_2026-11-23_
      14-37-31.steps.md`).
    """
    if not record.is_dir() and record != RECORDINGS:
        return record
    stem: str = path.name.split(".")[0] if path is not None else "new"
    stamp: str = time.strftime("%Y-%m-%d_%H-%M-%S")
    return record / f"{stem}_{stamp}.steps.md"


# Class `OutlinePanel`:
@dataclass(slots=True)
class OutlinePanel:
    """What the first panel shows of the outline editor, if anything.

    Constructor:
    * `OutlinePanel(outline, tutorial, record, speech, headless)`

    Attributes:
    * `outline` (`Path | None`): `--outline`: the file to edit.
    * `tutorial` (`Path | None`): `--tutorial`: the recording to play.
    * `record` (`Path | None`): `--record`: the file (or directory)
      to record into.
    * `speech` (`bool`): False for `--no-speech`.
    * `headless` (`bool`): `--headless`: a tutorial is checked.
    * `recorder` (`Recorder | None`): The recorder, once started.
    """

    # Constructor arguments:
    outline: Path | None = field(init=True)
    tutorial: Path | None = field(init=True)
    record: Path | None = field(init=True)
    speech: bool = field(init=True)
    headless: bool = field(init=True)

    # Remaining attributes (alphabetized):
    recorder: Recorder | None = field(init=False, default=None)

    def wanted(self) -> bool:
        """Tell whether any outline option was given.

        Returns:
        * (`bool`): True when the first panel holds an editor.
        """
        return (
            self.outline is not None
            or self.tutorial is not None
            or self.record is not None
        )

    def open(self, top: Window) -> int | None:
        """Open the editor in `top`'s current panel.

        Arguments:
        * `top` (`Window`): The window.

        Returns:
        * (`int | None`): An exit status to stop with: a tutorial
          checked headless (0 when every step matches, 1 otherwise,
          the mismatches printed), or 1 when a file cannot be read;
          `None` to run on.
        """
        # The drawing: the tutorial's own, the file's, or a triangle.
        recording: Recording | None = None
        drawing: Drawing = Drawing()
        source: Path | None = self.tutorial or self.outline
        try:
            if self.tutorial is not None:
                recording = steps.load(self.tutorial)
                if recording.outline:
                    drawing = drawing_from_text(
                        recording.outline, str(self.tutorial)
                    )
            elif self.outline not in (None, NEW_OUTLINE):
                assert self.outline is not None
                if self.outline.exists():
                    drawing = drawing_from(self.outline)
        except (OSError, OutlineError, ExposedError) as error:
            print(error, file=sys.stderr)
            return 1

        # Fresh handles, as every replay starts; then the editor in
        # the panel (a tutorial's outline is never saved).
        outline_exposed.HANDLES.reset()
        path: Path | None = (
            None
            if recording is not None or self.outline == NEW_OUTLINE
            else self.outline
        )
        editor: OutlineEditor = OutlineEditor(drawing, path=path)
        panel: Panel = top.panels[top.current]
        title: str = "New outline"
        if recording is not None:
            title = f"Tutorial: {recording.title or source}"
        elif path is not None:
            title = f"Outline: {path.name}"

        # One in the package (the example shop's) is read only, but
        # for `.allow_edits` (`T.toasl~6.8` #683, #717).
        locked: bool = path is not None and is_read_only(path)
        if locked:
            title += " (read only)"
        panel.hold_editor(editor, title)
        if locked:
            editor.set_read_only(True)
            top.model.say(READ_ONLY_OUTLINE)
        outline_exposed.EDITORS.add(editor)
        editor.view.fit()

        # A tutorial: checked offscreen, or shown with its panel (#19).
        if recording is not None:
            if self.headless:
                found: list[str] = tutorial.mismatches(editor, recording)
                print("\n\n".join(found) or f"{source}: all match")
                return 1 if found else 0
            tutorial.show_panel(editor, recording)
            return None

        # Recording what the user does, and says (#21, #532).
        if self.record is not None:
            self.recorder = self.start_recording(editor, path)
        return None

    def start_recording(
        self, editor: OutlineEditor, path: Path | None
    ) -> Recorder:
        """Start `--record`, with the microphone unless `--no-speech`.

        Arguments:
        * `editor` (`OutlineEditor`): The editor to record.
        * `path` (`Path | None`): The outline file edited, if any.

        Returns:
        * (`Recorder`): The recorder.
        """
        # Warn of a microphone that will sound buried in hiss (#537).
        assert self.record is not None
        record: Path = record_path(self.record, path)
        title: str = record.name.split(".")[0].rsplit("_", 2)[0]
        if self.speech:
            problem: str
            for problem in gain_problems():
                print(f"Warning: {problem}", file=sys.stderr)
        named: str = title.replace("_", " ").capitalize()
        recorder: Recorder
        try:
            recorder = Recorder(editor, record, named, speech=self.speech)
        except OSError as error:
            print(f"No speech: {error}", file=sys.stderr)
            recorder = Recorder(editor, record, named)
        talk: str = "; talk as you go" if recorder.microphone else ""
        print(f"Recording into {record}{talk}", flush=True)
        return recorder

    def finish(self) -> None:
        """Once the GUI has closed, turn a recording's speech into
        its steps' drafts, and say where it went."""
        if self.recorder is not None:
            print(self.recorder.finish())
