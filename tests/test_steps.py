"""Tests for recordings (`scraftcam.exposed.steps`), the narration
panel and tutorials: every `tests/steps/*.steps.toml` is replayed."""

import dataclasses
import tempfile
import unittest
from pathlib import Path

from scraftcam import __version__
from scraftcam.exposed import steps
from scraftcam.exposed.exposed import ExposedError
from scraftcam.exposed.steps import Recording
from scraftcam.gui import outline_exposed, tutorial
from scraftcam.gui.narration import NarrationPanel
from scraftcam.gui.outline_editor import (
    Drawing,
    OutlineEditor,
    drawing_from_text,
)
from scraftcam.gui.recorder import Recorder
from tests import qt_app

# The recordings kept as tests and tutorials.
RECORDINGS: Path = Path(__file__).parent / "steps"

# The first tutorial, used for the player's own tests.
FIRST: Path = RECORDINGS / "move_a_corner.steps.toml"


def editor_for(recording: Recording) -> OutlineEditor:
    """Make an editor on `recording`'s starting outline, with fresh
    handles."""
    outline_exposed.HANDLES.reset()
    outline_exposed.EDITORS.clear()
    drawing: Drawing = (
        drawing_from_text(recording.outline)
        if recording.outline
        else Drawing()
    )
    return OutlineEditor(drawing)


class TestRecordings(unittest.TestCase):
    """Each kept recording replays with every state as recorded."""

    def test_every_recording(self) -> None:
        """Every `tests/steps/*.steps.toml` matches."""
        paths: list[Path] = sorted(RECORDINGS.glob("*.steps.toml"))
        self.assertTrue(paths)
        path: Path
        for path in paths:
            with self.subTest(recording=path.name):
                recording: Recording = steps.load(path)
                editor: OutlineEditor = editor_for(recording)
                self.assertEqual(tutorial.mismatches(editor, recording), [])
                editor.deleteLater()
                qt_app.process_events()

    def test_mismatch_reported(self) -> None:
        """A step whose state differs is named, with both states."""
        recording: Recording = steps.load(FIRST)
        changed: steps.Step = dataclasses.replace(
            recording.steps[0], state="something else"
        )
        recording = dataclasses.replace(
            recording, steps=(changed, *recording.steps[1:])
        )
        editor: OutlineEditor = editor_for(recording)
        found: list[str] = tutorial.mismatches(editor, recording)
        self.assertEqual(len(found), 1)
        self.assertIn("step 1 (click): expected\nsomething else", found[0])
        editor.deleteLater()
        qt_app.process_events()

    def test_written_back(self) -> None:
        """A recording written out reads back the same."""
        recording: Recording = steps.load(FIRST)
        text: str = steps.recording_text(recording)
        self.assertEqual(steps.recording_from_text(text), recording)
        odd: Recording = Recording(
            "Quotes ''' and \"",
            "",
            (steps.Step("press", {"keys": "a'''b", "n": [1, 2.5, True]}),),
        )
        self.assertEqual(
            steps.recording_from_text(steps.recording_text(odd)),
            dataclasses.replace(odd, version=__version__),
        )

    def test_bad_files(self) -> None:
        """A file that is not a recording is refused, saying why."""
        cases: tuple[tuple[str, str], ...] = (
            ("format = 2", "format 2, not 1"),
            ("format = 1\nsteps = 3", "not a list"),
            ("format = 1\n[[steps]]\nnarration = 'x'", "has no `call`"),
            ("format = 1\n[[steps]]\ncall = 'a'\narguments = 1", "table"),
            ("format = = 1", "f.toml"),
        )
        text: str
        message: str
        for text, message in cases:
            with (
                self.subTest(text=text),
                self.assertRaisesRegex(ExposedError, message),
            ):
                steps.recording_from_text(text, "f.toml")


class TestRecorder(unittest.TestCase):
    """What a user does is written as steps that replay the same."""

    def test_record_then_replay(self) -> None:
        """A click, a drag, a shortcut and a button, recorded."""
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtTest import QTest

        # The user's gestures, as Qt events on a recorded editor.
        editor: OutlineEditor = editor_for(Recording("", "", ()))
        editor.resize(*tutorial.SIZE)
        editor.show()
        editor.view.fit()
        qt_app.process_events()
        with tempfile.TemporaryDirectory() as directory:
            path: Path = Path(directory) / "made.steps.toml"
            Recorder(editor, path, "Made by doing")
            port = editor.view.viewport()

            def pixel(x: float, y: float) -> QPoint:
                """Give the pixel showing a drawing point."""
                return editor.view.mapFromScene(QPointF(x, y))

            left: Qt.MouseButton = Qt.MouseButton.LeftButton
            QTest.mouseClick(port, left, pos=pixel(-4, -3))
            QTest.mousePress(port, left, pos=pixel(0, 4))
            QTest.mouseMove(port, pixel(0.5, 5))
            QTest.mouseMove(port, pixel(1, 6))
            QTest.mouseRelease(port, left, pos=pixel(1, 6))
            qt_app.process_events()
            QTest.keyClick(
                editor.view, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier
            )
            qt_app.process_events()
            editor.buttons["Grid"].click()
            qt_app.process_events()

            # Written as four steps, which replay with the same states.
            made: Recording = steps.load(path)
            editor.deleteLater()
        calls: list[str] = [step.call for step in made.steps]
        self.assertEqual(calls, ["click", "drag", "press", "button"])
        self.assertEqual(made.steps[2].arguments, {"keys": "Ctrl+Z"})
        self.assertEqual(made.steps[3].arguments, {"word": "Grid"})
        again: OutlineEditor = editor_for(made)
        self.assertEqual(tutorial.mismatches(again, made), [])
        again.deleteLater()
        qt_app.process_events()


class TestPanel(unittest.TestCase):
    """[Forward] runs a step; [Backward] undoes it."""

    def test_forward_and_backward(self) -> None:
        """The drag is run, then undone back to where it started."""
        recording: Recording = steps.load(FIRST)
        editor: OutlineEditor = editor_for(recording)
        editor.resize(*tutorial.SIZE)
        editor.show()
        editor.view.fit()
        qt_app.process_events()
        panel: NarrationPanel = NarrationPanel(
            tutorial.start(editor, recording)
        )
        self.assertFalse(panel.backward.isEnabled())
        panel.forward.click()
        panel.forward.click()
        self.assertEqual(editor.view.drawing.points[2], (1.0, 6.0))
        self.assertEqual(panel.lines.currentRow(), 2)
        panel.backward.click()
        self.assertEqual(editor.view.drawing.points[2], (0.0, 4.0))
        self.assertEqual(panel.player.done, 1)
        panel.forward.click()
        panel.forward.click()
        self.assertFalse(panel.forward.isEnabled())
        with self.assertRaisesRegex(ExposedError, "every step"):
            panel.player.forward()
        panel.deleteLater()
        editor.deleteLater()
        qt_app.process_events()


if __name__ == "__main__":
    unittest.main()
