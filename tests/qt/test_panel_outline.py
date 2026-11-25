"""Tests of a tool panel's [Outline] tab (`T.og~6.9` #578, #587)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from scraftcam.exposed import steps
from scraftcam.gui import outline_exposed, tutorial
from scraftcam.gui.outline_editor import Drawing, OutlineEditor, ViewTab
from scraftcam.gui.outline_file import outline_text
from scraftcam.gui.outline_letters import ToolValues
from scraftcam.gui.tree import FILE, Node
from scraftcam.gui.tree import OUTLINE as OUTLINE_KIND
from scraftcam.gui.views import Panel, item_text, outline_of
from scraftcam.shops import EXAMPLE_SHOP
from tests import qt_app

# The example shop's tools, an end mill and its kind's outline.
TOOLS: Path = EXAMPLE_SHOP / "tools/end_mills"
TOOL: str = "1_4_in_2_flute_carbide_end_mill.toml"
OTHER_TOOL: str = "1_2_in_2_flute_carbide_end_mill.toml"
OUTLINE: str = "end_mill.outline.toml"

# The kept recordings (`tests/qt/test_steps.py` replays them alone).
RECORDINGS: Path = Path(__file__).resolve().parents[1] / "steps"


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
        """[Outline] shows; a tool's panel never changes the outline,
        only the tool's values (#590, `T.toasl~6.8` #735, #736)."""
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
        # why; in a tool's panel it does so even with changes allowed
        # (#736), when only the tool's values may be typed in; in the
        # outline's own panel (#730), the same drag moves it.
        self.panel.resize(1000, 800)
        self.panel.show()
        self.panel.tabs.setCurrentWidget(editor)
        qt_app.process_events()
        editor.view.fit()
        handle: str = outline_exposed.HANDLES.handle(editor)
        before: list[tuple[float, float]] = list(editor.drawing.points)
        outline_exposed.drag(handle, "Vertex V2", to="(1, 1)")
        self.assertEqual(editor.drawing.points, before)
        self.assertIn("Only this tool's values", editor.status.text())

        self.panel.set_editing(True)
        self.assertTrue(editor.read_only)
        tool: ToolValues | None = editor.letters.tool
        assert tool is not None
        self.assertTrue(tool.editing)
        outline_exposed.drag(handle, "Vertex V2", to="(1, 1)")
        self.assertEqual(editor.drawing.points, before)
        own: Panel = Panel(2)
        self.addCleanup(own.deleteLater)
        outline: Path = self.directory / OUTLINE
        own.show_node(Node("end_mill", OUTLINE_KIND, outline, ""), "in")
        opened: OutlineEditor | None = own.outline
        assert opened is not None

        # It opens on [Drawing], look only; [Edit] changes it, with
        # no [Allow Changes] (#755, #758).
        self.assertIs(opened.tab(), ViewTab.DRAWING)
        self.assertTrue(opened.read_only)
        self.assertFalse(own.edit_row.isVisibleTo(own))
        opened.show_tab(ViewTab.EDIT)
        self.assertFalse(opened.read_only)
        self.assertTrue(opened.button_actions["Delete"].isEnabled())

        # The same item again keeps its editor; another loses it.
        self.panel.show_node(Node(TOOL, FILE, self.tool, ""), "in")
        self.assertIs(self.panel.outline, editor)
        other: Path = self.directory / "plain.toml"
        other.write_text('name = "x"\n', encoding="utf-8")
        self.panel.show_node(Node(other.name, FILE, other, ""), "in")
        self.assertIsNone(self.panel.outline)
        self.assertEqual(self.panel.tabs.count(), 1)

    def test_outline_text(self) -> None:
        """An outline item's text is its file, never Python's parse of
        it (#760: "syntax error at line 52")."""
        outline: Path = self.directory / OUTLINE
        node: Node = Node("end_mill", OUTLINE_KIND, outline, "")
        self.assertEqual(item_text(node), outline.read_text(encoding="utf-8"))

    def test_outline_link(self) -> None:
        """A tool's [Outline] has no [Edit]: a link opens its kind's
        outline (`T.toasl~6.8` #757)."""
        self.panel.show_node(Node(TOOL, FILE, self.tool, ""), "in")
        self.panel.show()
        editor: OutlineEditor | None = self.panel.outline
        assert editor is not None
        self.panel.tabs.setCurrentWidget(editor)
        qt_app.process_events()
        edit: int = list(ViewTab).index(ViewTab.EDIT)
        self.assertFalse(editor.tab_bar.isTabVisible(edit))
        self.assertTrue(editor.outline_link.isVisible())
        self.assertIn("Edit the End mill outline", editor.outline_link.text())
        opened_paths: list[str] = []
        self.panel.open_path = opened_paths.append
        editor.follow_outline_link("edit")
        self.assertEqual(opened_paths, [str(self.directory / OUTLINE)])

    def test_same_panel(self) -> None:
        """One panel: a tool, its kind's outline, another tool; each
        gets its own editor, though the file is the same (#750,
        #751)."""
        shutil.copy(TOOLS / OTHER_TOOL, self.directory)
        outline: Path = self.directory / OUTLINE
        self.panel.show_node(Node(TOOL, FILE, self.tool, ""), "in")
        first: OutlineEditor | None = self.panel.outline
        assert first is not None
        self.assertIsNotNone(first.letters.tool)

        # The outline itself: no tool's values, and it may be changed.
        self.panel.show_node(Node("end_mill", OUTLINE_KIND, outline, ""), "in")
        shape: OutlineEditor | None = self.panel.outline
        assert shape is not None
        shape.show_tab(ViewTab.EDIT)
        self.assertIsNot(shape, first)
        self.assertIsNone(shape.letters.tool)
        self.assertFalse(shape.read_only)

        # Another tool shows its own values.
        other: Path = self.directory / OTHER_TOOL
        self.panel.show_node(Node(OTHER_TOOL, FILE, other, ""), "in")
        second: OutlineEditor | None = self.panel.outline
        assert second is not None
        tool: ToolValues | None = second.letters.tool
        assert tool is not None
        self.assertEqual(tool.values["D"], "1/2 in")

    def test_tool_table(self) -> None:
        """One table: default and this tool's value; an edit writes
        only the tool's file, and a bad one is refused (#735, #736)."""
        outline: Path = self.directory / OUTLINE
        kept: str = outline.read_text(encoding="utf-8")
        self.panel.show_node(Node(TOOL, FILE, self.tool, ""), "in")
        editor: OutlineEditor | None = self.panel.outline
        assert editor is not None
        table: QTableWidget = editor.letters.table

        # Function `cell()`:
        def cell(row: int, column: int) -> QTableWidgetItem:
            """Return a cell of the table, which must be there."""
            item: QTableWidgetItem | None = table.item(row, column)
            assert item is not None
            return item

        # Function `header()`:
        def header(column: int) -> str:
            """Return a column's title."""
            item: QTableWidgetItem | None = table.horizontalHeaderItem(column)
            assert item is not None
            return item.text()

        self.assertEqual(
            [header(column) for column in range(table.columnCount())],
            ["Letter", "Name", "Default", "This tool"],
        )
        rows: dict[str, tuple[str, str]] = {}
        row: int
        for row in range(1, table.rowCount()):
            rows[cell(row, 0).text()] = (
                cell(row, 2).text(),
                cell(row, 3).text(),
            )
        self.assertEqual(rows["D"], ("1/4 in", "1/4 in"))
        self.assertEqual(rows["LOC"][0], "3/4 in")
        self.assertNotIn("D", [r.schema.short for r in self.panel.rows])

        # [Allow Changes], then a new diameter: in the tool's file
        # only; an angle for a length is refused.
        self.panel.set_editing(True)
        d_row: int = 1 + [
            letter.letter for letter in editor.drawing.letters
        ].index("D")
        cell(d_row, 3).setText("3/8 in")
        self.assertIn('D = "3/8 in"', self.tool.read_text(encoding="utf-8"))
        self.assertEqual(outline.read_text(encoding="utf-8"), kept)
        cell(d_row, 3).setText("90 deg")
        self.assertTrue(editor.letters.problems.text())
        self.assertIn('D = "3/8 in"', self.tool.read_text(encoding="utf-8"))

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
        """Every `tests/steps/*.steps.md` matches in an outline's panel."""

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
                # The outline's own panel (#730): a tool's never
                # changes its outline (#736).
                panel.show_node(
                    Node("end_mill", OUTLINE_KIND, directory / OUTLINE, ""),
                    "in",
                )
                editor: OutlineEditor | None = panel.outline
                assert editor is not None
                editor.show_tab(ViewTab.EDIT)
                panel.tabs.setCurrentWidget(editor)
                self.assertEqual(tutorial.mismatches(editor, recording), [])
                panel.deleteLater()
                qt_app.process_events()


if __name__ == "__main__":
    unittest.main()
