"""Tests of a tool panel's [Outline] tab (`T.og~6.9` #578, #587)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from scraftcam.exposed import steps
from scraftcam.gui import outline_exposed, tutorial
from scraftcam.gui.outline_editor import Drawing, OutlineEditor
from scraftcam.gui.outline_file import outline_text
from scraftcam.gui.tree import FILE, Node
from scraftcam.gui.views import Panel, outline_of
from tests import qt_app

# The example shop's tools, an end mill and its kind's outline.
TOOLS: Path = Path(__file__).resolve().parent.parent / "examples/shop/tools"
TOOL: str = "1_4_in_2_flute_carbide_end_mill.toml"
OUTLINE: str = "end_mill.outline.toml"

# The kept recordings (`tests/test_steps.py` replays them alone).
RECORDINGS: Path = Path(__file__).resolve().parent / "steps"


class OutlineTabTest(unittest.TestCase):
    """A tool's panel shows its kind's outline in an editor."""

    def setUp(self) -> None:
        """A copy of the tool and its outline (the editor saves)."""
        # `enterContext()` closes it: pylint does not know that.
        # pylint: disable-next=consider-using-with
        made: str = self.enterContext(tempfile.TemporaryDirectory())
        self.directory: Path = Path(made)
        shutil.copy(TOOLS / TOOL, self.directory)
        shutil.copy(TOOLS / OUTLINE, self.directory)
        self.tool: Path = self.directory / TOOL
        self.panel: Panel = Panel(1)
        self.addCleanup(self.panel.deleteLater)

    def test_outline_of(self) -> None:
        """The kind names the file beside the item; none, no file."""
        self.assertEqual(
            outline_of(self.tool, {"kind": "end_mill"}),
            self.directory / OUTLINE,
        )
        self.assertIsNone(outline_of(self.tool, {"kind": "drill"}))
        self.assertIsNone(outline_of(self.tool, {}))

    def test_tab(self) -> None:
        """[Outline] shows, read only until [Allow Changes] (#590)."""
        self.panel.show_node(Node(TOOL, FILE, self.tool, ""), "in")
        qt_app.process_events()
        self.assertEqual(self.panel.tabs.count(), 2)
        self.assertEqual(self.panel.tabs.tabText(1), "Outline")
        editor: OutlineEditor | None = self.panel.outline
        assert editor is not None
        self.assertIn(editor, set(outline_exposed.EDITORS))
        self.assertTrue(editor.read_only)
        self.assertTrue(editor.isEnabled())
        self.assertFalse(editor.button_actions["Delete"].isEnabled())
        self.assertTrue(editor.button_actions["Fit"].isEnabled())

        # Read only, a drag (over MCP, #579) leaves the corner, and says
        # why; with changes allowed, the same drag moves it.
        self.panel.resize(1000, 800)
        self.panel.show()
        self.panel.tabs.setCurrentWidget(editor)
        qt_app.process_events()
        editor.view.fit()
        handle: str = outline_exposed.HANDLES.handle(editor)
        before: list[tuple[float, float]] = list(editor.drawing.points)
        outline_exposed.drag(handle, "Vertex 1", to="(1, 1)")
        self.assertEqual(editor.drawing.points, before)
        self.assertIn("Allow Changes", editor.status.text())
        self.panel.set_editing(True)
        self.assertFalse(editor.read_only)
        outline_exposed.drag(handle, "Vertex 1", to="(1, 1)")
        self.assertNotEqual(editor.drawing.points, before)
        self.assertTrue(editor.button_actions["Delete"].isEnabled())

        # The same item again keeps its editor; another loses it.
        self.panel.show_node(Node(TOOL, FILE, self.tool, ""), "in")
        self.assertIs(self.panel.outline, editor)
        other: Path = self.directory / "plain.toml"
        other.write_text('name = "x"\n', encoding="utf-8")
        self.panel.show_node(Node(other.name, FILE, other, ""), "in")
        self.assertIsNone(self.panel.outline)
        self.assertEqual(self.panel.tabs.count(), 1)

    def test_hold_editor(self) -> None:
        """A tutorial's editor, on no file, goes when an item shows."""

        held: OutlineEditor = OutlineEditor(Drawing())
        self.panel.hold_editor(held, "Tutorial: x")
        self.assertIs(self.panel.outline, held)
        self.assertFalse(held.read_only)
        self.assertEqual(self.panel.title.text(), "Tutorial: x")
        other: Path = self.directory / "plain.toml"
        other.write_text('name = "x"\n', encoding="utf-8")
        self.panel.show_node(Node(other.name, FILE, other, ""), "in")
        self.assertIsNone(self.panel.outline)


class ReplayInPanelTest(unittest.TestCase):
    """Each kept recording replays in a panel's editor (#579, #593)."""

    def test_every_recording(self) -> None:
        """Every `tests/steps/*.steps.md` matches in a tool's panel."""

        paths: list[Path] = sorted(RECORDINGS.glob("*.steps.md"))
        self.assertTrue(paths)
        path: Path
        for path in paths:
            with (
                self.subTest(recording=path.name),
                tempfile.TemporaryDirectory() as made,
            ):
                # The tool, its kind's outline the recording's start.
                recording: steps.Recording = steps.load(path)
                directory: Path = Path(made)
                shutil.copy(TOOLS / TOOL, directory)
                (directory / OUTLINE).write_text(
                    recording.outline or outline_text(Drawing()),
                    encoding="utf-8",
                )

                # Fresh handles, as a replay starts; changes allowed.
                outline_exposed.HANDLES.reset()
                outline_exposed.EDITORS.clear()
                panel: Panel = Panel(1)
                panel.show_node(Node(TOOL, FILE, directory / TOOL, ""), "in")
                panel.set_editing(True)
                editor: OutlineEditor | None = panel.outline
                assert editor is not None
                panel.tabs.setCurrentWidget(editor)
                self.assertEqual(tutorial.mismatches(editor, recording), [])
                panel.deleteLater()
                qt_app.process_events()


if __name__ == "__main__":
    unittest.main()
