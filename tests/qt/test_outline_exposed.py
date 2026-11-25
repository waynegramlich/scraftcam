"""Tests for `scraftcam.gui.outline_exposed`: the outline editor's
functions reached over MCP (#S3), called in process."""

import tempfile
import unittest
from pathlib import Path

from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError
from scraftcam.gui import outline_exposed
from scraftcam.gui.outline_editor import Drawing, OutlineEditor, ViewTab
from tests import qt_app


class TestOutlineExposed(unittest.TestCase):
    """The editors are listed by handle and described as text."""

    def setUp(self) -> None:
        """Start each test with fresh handles and one new editor."""
        outline_exposed.HANDLES.reset()
        outline_exposed.EDITORS.clear()
        self.editor: OutlineEditor = OutlineEditor(Drawing())
        outline_exposed.EDITORS.add(self.editor)
        qt_app.process_events()

    def tearDown(self) -> None:
        """Delete the editor."""
        self.editor.deleteLater()
        qt_app.process_events()

    def test_editors(self) -> None:
        """The open editor has the first handle."""
        self.assertEqual(exposed.call("editors", {}), ["OutlineEditor 1"])

    def test_state(self) -> None:
        """A new editor's state is the triangle, nothing chosen."""
        exposed.call("editors", {})
        text: object = exposed.call("state", {"editor": "OutlineEditor 1"})
        self.assertIsInstance(text, str)
        lines: list[str] = str(text).splitlines()
        self.assertEqual(
            lines[:6],
            [
                "file: (new)",
                "revolve: False",
                "corners:",
                "  0: (-4, -3)",
                "  1: (4, -3)",
                "  2: (0, 4)",
            ],
        )
        self.assertIn("chosen corners: []", lines)
        self.assertEqual(lines[-1], "undo depth: 0")

    def test_tab(self) -> None:
        """[Drawing] and [Edit] are chosen as a user chooses them; a
        greyed one is refused, saying why (`T.toasl~6.8` #755)."""
        handle: str = "OutlineEditor 1"
        exposed.call("editors", {})
        exposed.call("tab", {"editor": handle, "name": "Drawing"})
        self.assertIs(self.editor.tab(), ViewTab.DRAWING)
        self.assertTrue(self.editor.read_only)
        exposed.call("tab", {"editor": handle, "name": "Edit"})
        self.assertFalse(self.editor.read_only)
        with self.assertRaisesRegex(ExposedError, "no tab"):
            exposed.call("tab", {"editor": handle, "name": "Overview"})
        self.editor.set_read_only(True)
        with self.assertRaisesRegex(ExposedError, "greyed: This outline"):
            exposed.call("tab", {"editor": handle, "name": "Edit"})

    def test_not_an_editor(self) -> None:
        """A handle that is not an open editor is refused."""
        with self.assertRaisesRegex(ExposedError, "is not a handle"):
            exposed.call("state", {"editor": "OutlineEditor 2"})
        outline_exposed.HANDLES.handle(self)
        with self.assertRaisesRegex(ExposedError, "not an outline editor"):
            exposed.call("state", {"editor": "TestOutlineExposed 1"})

    def test_gestures(self) -> None:
        """A click chooses a corner, a drag moves one, [Undo] undoes."""
        exposed.call("editors", {})
        self.editor.resize(1280, 800)
        self.editor.show()
        self.editor.view.fit()
        qt_app.process_events()
        handle: dict[str, object] = {"editor": "OutlineEditor 1"}
        text: object = exposed.call("click", {**handle, "target": "Vertex 0"})
        self.assertIn("chosen corners: [0]", str(text))
        text = exposed.call(
            "drag", {**handle, "target": "Vertex 2", "to": "(1, 6)"}
        )
        self.assertIn("  2: (1, 6)", str(text))
        self.assertIn("undo depth: 1", str(text))
        text = exposed.call("button", {**handle, "word": "Undo"})
        self.assertIn("  2: (0, 4)", str(text))
        # A target must be what is there now (#550).
        with self.assertRaisesRegex(ExposedError, "there are 3 vertices"):
            exposed.call("click", {**handle, "target": "Vertex 5"})
        with self.assertRaisesRegex(ExposedError, "is not what is there"):
            exposed.call("click", {**handle, "target": "background (0, 4)"})
        with self.assertRaisesRegex(ExposedError, "not revolved"):
            exposed.call("click", {**handle, "target": "Mirror 1"})
        with self.assertRaisesRegex(ExposedError, "is not `Vertex N`"):
            exposed.call("click", {**handle, "target": "Corner 1"})

    def test_screenshot(self) -> None:
        """A picture of the window is written where it says (#567)."""
        exposed.call("editors", {})
        self.editor.resize(1280, 800)
        self.editor.show()
        qt_app.process_events()
        handle: dict[str, object] = {"editor": "OutlineEditor 1"}
        kept: Path = outline_exposed.SHOTS
        with tempfile.TemporaryDirectory() as directory:
            outline_exposed.SHOTS = Path(directory)
            try:
                made: Path = Path(
                    str(exposed.call("screenshot", {**handle, "name": "a"}))
                )
                self.assertEqual(made, Path(directory) / "a.png")
                self.assertTrue(made.read_bytes().startswith(b"\x89PNG"))
                with self.assertRaisesRegex(ExposedError, "plain file"):
                    exposed.call("screenshot", {**handle, "name": "../b"})
            finally:
                outline_exposed.SHOTS = kept

    def test_resize(self) -> None:
        """`resize` sizes the window and fits; silly sizes refused."""
        exposed.call("editors", {})
        handle: dict[str, object] = {"editor": "OutlineEditor 1"}
        exposed.call("resize", {**handle, "width": 640, "height": 900})
        self.assertEqual(self.editor.window().size().height(), 900)
        with self.assertRaises(ExposedError):
            exposed.call("resize", {**handle, "width": 10, "height": 900})


if __name__ == "__main__":
    unittest.main()
