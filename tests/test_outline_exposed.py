"""Tests for `scraftcam.gui.outline_exposed`: the outline editor's
functions reached over MCP (#S3), called in process."""

import unittest

from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError
from scraftcam.gui import outline_exposed
from scraftcam.gui.outline_editor import Drawing, OutlineEditor
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

    def test_not_an_editor(self) -> None:
        """A handle that is not an open editor is refused."""
        with self.assertRaisesRegex(ExposedError, "is not a handle"):
            exposed.call("state", {"editor": "OutlineEditor 2"})
        outline_exposed.HANDLES.handle(self)
        with self.assertRaisesRegex(ExposedError, "not an outline editor"):
            exposed.call("state", {"editor": "TestOutlineExposed 1"})

    def test_gestures(self) -> None:
        """A click chooses a corner, a drag moves one, Ctrl+Z undoes."""
        exposed.call("editors", {})
        self.editor.resize(1280, 800)
        self.editor.show()
        self.editor.view.fit()
        qt_app.process_events()
        handle: dict[str, object] = {"editor": "OutlineEditor 1"}
        text: object = exposed.call("click", {**handle, "x": -4, "y": -3})
        self.assertIn("chosen corners: [0]", str(text))
        text = exposed.call(
            "drag", {**handle, "x": 0, "y": 4, "to_x": 1, "to_y": 6}
        )
        self.assertIn("  2: (1, 6)", str(text))
        self.assertIn("undo depth: 1", str(text))
        text = exposed.call("press", {**handle, "keys": "Ctrl+Z"})
        self.assertIn("  2: (0, 4)", str(text))
        with self.assertRaisesRegex(ExposedError, "names no keys"):
            exposed.call("press", {**handle, "keys": ""})


if __name__ == "__main__":
    unittest.main()
