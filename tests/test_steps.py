"""Tests for recordings (`scraftcam.exposed.steps`), the narration
panel and tutorials: every `tests/steps/*.steps.md` is replayed."""

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
FIRST: Path = RECORDINGS / "move_a_corner.steps.md"


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
        """Every `tests/steps/*.steps.md` matches."""
        paths: list[Path] = sorted(RECORDINGS.glob("*.steps.md"))
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
        """A step whose state differs is named, with only the lines
        that changed (#552)."""
        recording: Recording = steps.load(FIRST)
        changed: steps.Step = dataclasses.replace(
            recording.steps[0],
            state=recording.steps[0].state.replace(
                "chosen corners: [0]", "chosen corners: [1]"
            ),
        )
        recording = dataclasses.replace(
            recording, steps=(changed, *recording.steps[1:])
        )
        editor: OutlineEditor = editor_for(recording)
        found: list[str] = tutorial.mismatches(editor, recording)
        self.assertEqual(len(found), 1)
        lines: list[str] = found[0].splitlines()
        self.assertEqual(lines[0], "step 1: click Vertex 0")
        self.assertTrue(lines[1].startswith("  * Click the lower left"))
        # Only the line that changed.
        self.assertEqual(
            lines[2:], ["  -chosen corners: [1]", "  +chosen corners: [0]"]
        )
        editor.deleteLater()
        qt_app.process_events()

    def test_failed_step_reported(self) -> None:
        """A step that fails ends the run, named with its error."""
        recording: Recording = steps.load(FIRST)
        gone: steps.Step = dataclasses.replace(
            recording.steps[0], arguments={"target": "Vertex 9"}
        )
        recording = dataclasses.replace(
            recording, steps=(gone, *recording.steps[1:])
        )
        editor: OutlineEditor = editor_for(recording)
        found: list[str] = tutorial.mismatches(editor, recording)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("step 1: click Vertex 9\n"))
        self.assertIn("failed: no Vertex 9: there are 3 vertices", found[0])
        editor.deleteLater()
        qt_app.process_events()

    def test_written_back(self) -> None:
        """A recording written out reads back the same."""
        recording: Recording = steps.load(FIRST)
        text: str = steps.recording_markdown(recording)
        self.assertEqual(steps.recording_from_markdown(text), recording)
        self.assertEqual(text, FIRST.read_text(encoding="utf-8"))
        odd: Recording = Recording(
            "Odd Values",
            "An introduction,\nover two lines.",
            "",
            (
                steps.Step("button", {"word": "a, b"}, "Two\nlines.", "x"),
                steps.Step("", {}, "Only to read.", "", "## A Section"),
                steps.Step(
                    "drag",
                    {"target": "background (1.5, -2)", "to": "(3, 4)"},
                    "A drag.",
                    "",
                    "",
                    12.5,
                    (40.0, 1.25, -0.5),
                ),
            ),
        )
        again: Recording = steps.recording_from_markdown(
            steps.recording_markdown(odd)
        )
        self.assertEqual(again, dataclasses.replace(odd, version=__version__))
        self.assertIn(
            "<!-- do: drag background (1.5, -2) -> (3, 4) -->",
            steps.recording_markdown(odd),
        )

    def test_bad_files(self) -> None:
        """A file that is not a recording is refused, saying why."""
        end: str = "\n<!-- recording\nformat = 2\n-->\n"
        cases: tuple[tuple[str, str], ...] = (
            ("# T\n", "no closing"),
            ("# T\n\n<!-- recording\nformat = 1\n-->\n", "format 1, not 2"),
            (
                "* a\n  <!-- do: button A -->\n  <!-- do: button B -->" + end,
                r"f.md:3: a second `do:`",
            ),
            ("* a\n  <!-- do: fly 1 -->" + end, r"f.md:2: .*fly"),
            ("* a\n  <!-- do: button A, B -->" + end, "takes 1 values, not 2"),
            ("x\n<!-- recording\nformat = = 2\n-->\n", "recording:"),
        )
        text: str
        message: str
        for text, message in cases:
            with (
                self.subTest(text=text),
                self.assertRaisesRegex(ExposedError, message),
            ):
                steps.recording_from_markdown(text, "f.md")
        with self.assertRaisesRegex(ExposedError, "ends a comment"):
            steps.recording_markdown(
                Recording(
                    "T",
                    "",
                    "",
                    (steps.Step("button", {"word": "A"}, "", "a --> b"),),
                )
            )


class TestRecorder(unittest.TestCase):
    """What a user does is written as steps that replay the same."""

    def test_record_then_replay(self) -> None:
        """A click, a drag and two buttons, recorded."""
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtTest import QTest

        # The user's gestures, as Qt events on a recorded editor.
        editor: OutlineEditor = editor_for(Recording("", "", "", ()))
        editor.resize(*tutorial.SIZE)
        editor.show()
        editor.view.fit()
        qt_app.process_events()
        with tempfile.TemporaryDirectory() as directory:
            path: Path = Path(directory) / "made.steps.md"
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
            editor.buttons["Undo"].click()
            qt_app.process_events()
            editor.buttons["Grid"].click()
            qt_app.process_events()

            # Written as four steps, which replay with the same states.
            made: Recording = steps.load(path)
            editor.deleteLater()
        calls: list[str] = [step.call for step in made.steps]
        self.assertEqual(calls, ["click", "drag", "button", "button"])
        self.assertEqual(made.steps[0].arguments, {"target": "Vertex 0"})
        self.assertEqual(
            made.steps[1].arguments, {"target": "Vertex 2", "to": "(1, 6)"}
        )
        self.assertEqual(made.steps[2].arguments, {"word": "Undo"})
        self.assertEqual(made.steps[3].arguments, {"word": "Grid"})
        times: list[float] = [step.time for step in made.steps]
        self.assertTrue(all(when >= 0 for when in times))
        self.assertEqual(times, sorted(times))
        self.assertEqual(len(made.steps[0].view), 3)
        self.assertEqual(made.steps[0].view, made.steps[1].view)
        again: OutlineEditor = editor_for(made)
        self.assertEqual(tutorial.mismatches(again, made), [])
        again.deleteLater()
        qt_app.process_events()


class TestView(unittest.TestCase):
    """Each step's view is restored before it is replayed (#566)."""

    def test_place_view(self) -> None:
        """A view placed reads back; a bad one is refused."""
        editor: OutlineEditor = editor_for(Recording("", "", "", ()))
        editor.resize(*tutorial.SIZE)
        editor.show()
        editor.view.fit()
        qt_app.process_events()
        zoom: float = outline_exposed.view_of(editor.view)[0]
        wanted: tuple[float, float, float] = (zoom * 2.5, 1.0, 2.0)
        outline_exposed.place_view(editor.view, wanted)
        got: tuple[float, float, float] = outline_exposed.view_of(editor.view)
        self.assertAlmostEqual(got[0], wanted[0], places=6)
        # The view sits on whole pixels: the centre is within 1.5.
        pixel: float = 1.5 / wanted[0]
        self.assertAlmostEqual(got[1], 1.0, delta=pixel)
        self.assertAlmostEqual(got[2], 2.0, delta=pixel)
        with self.assertRaises(ExposedError):
            outline_exposed.place_view(editor.view, (0.0, 1.0, 2.0))
        editor.deleteLater()
        qt_app.process_events()

    def test_replay_restores_view(self) -> None:
        """A step recorded zoomed in is replayed zoomed in."""
        recording: Recording = steps.load(FIRST)
        first: steps.Step = recording.steps[0]
        editor: OutlineEditor = editor_for(recording)
        editor.resize(*tutorial.SIZE)
        editor.show()
        editor.view.fit()
        qt_app.process_events()
        zoom: float = outline_exposed.view_of(editor.view)[0] * 1.5
        zoomed: Recording = dataclasses.replace(
            recording,
            steps=(dataclasses.replace(first, view=(zoom, 0.0, 0.0)),),
        )
        player: steps.Player = tutorial.start(editor, zoomed)
        player.forward()
        self.assertAlmostEqual(editor.view.zoom(), zoom, places=6)
        editor.deleteLater()
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
