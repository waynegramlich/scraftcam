"""Tests of `scraftcam.gui.outline_editor`, chunk 1 (offscreen)."""

import unittest
from typing import TYPE_CHECKING

from scraftcam.gui import outline_editor
from scraftcam.gui.dimensions import HORIZONTAL, LENGTH, VERTICAL, Dimension
from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_editor import Drawing, OutlineEditor
from tests import qt_app

# Only for the type: `PySide6` is on `sys.path` once `tests` is in.
if TYPE_CHECKING:
    from PySide6.QtWidgets import QTableWidgetItem


# Function `cell()`:
def cell(editor: OutlineEditor, row: int, column: int) -> "QTableWidgetItem":
    """Return a cell of the letters' table (it must be there)."""
    item: QTableWidgetItem | None = editor.table.item(row, column)
    assert item is not None
    return item


class GridTest(unittest.TestCase):
    """Grid steps and snapping."""

    def test_grid_step(self) -> None:
        """Steps are 1, 2 or 5 times ten to a power, finer zoomed in."""
        self.assertEqual(outline_editor.grid_step(12.0), 1.0)
        self.assertEqual(outline_editor.grid_step(10.0), 2.0)
        self.assertEqual(outline_editor.grid_step(3.0), 5.0)
        self.assertAlmostEqual(outline_editor.grid_step(120.0), 0.1)
        self.assertAlmostEqual(outline_editor.grid_step(1e4), 2e-3)

    def test_snap(self) -> None:
        """A point goes to the nearest crossing."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        from PySide6.QtCore import (  # pylint: disable=import-outside-toplevel
            QPointF,
        )

        snapped: QPointF = outline_editor.snap(QPointF(1.26, -0.74), 0.5)
        self.assertEqual((snapped.x(), snapped.y()), (1.5, -0.5))

    def test_arrowhead(self) -> None:
        """An arrowhead's tip is the edge's end; none on a dot."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        from PySide6.QtCore import (  # pylint: disable=import-outside-toplevel
            QPointF,
        )

        path = outline_editor.arrowhead(QPointF(0, 0), QPointF(4, 0), 1.0)
        self.assertEqual(path.boundingRect().right(), 4.0)
        self.assertAlmostEqual(path.boundingRect().left(), 3.0)
        dot = outline_editor.arrowhead(QPointF(1, 1), QPointF(1, 1), 1.0)
        self.assertTrue(dot.isEmpty())


# Each test is a public method, and the editor has many features.
class EditorTest(unittest.TestCase):  # pylint: disable=too-many-public-methods
    """The window: squares, dragging, zoom, keys, drawing."""

    def setUp(self) -> None:
        """Make an editor on the first triangle."""
        self.editor: OutlineEditor = OutlineEditor()
        self.editor.show()
        qt_app.process_events()

    def tearDown(self) -> None:
        """Close the editor."""
        self.editor.close()
        self.editor.deleteLater()
        qt_app.process_events()

    def test_triangle(self) -> None:
        """A counterclockwise triangle around the origin, one square each."""
        points: list[tuple[float, float]] = Drawing().points
        area: float = 0.5 * sum(
            x0 * y1 - x1 * y0
            for (x0, y0), (x1, y1) in zip(
                points, points[1:] + points[:1], strict=True
            )
        )
        self.assertGreater(area, 0.0)
        self.assertEqual(len(self.editor.view.squares), 3)
        self.assertIsNot(Drawing().points, Drawing().points)

    def test_drag_snaps(self) -> None:
        """Moving a square snaps it and moves its corner."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        from PySide6.QtCore import (  # pylint: disable=import-outside-toplevel
            QPointF,
        )

        view = self.editor.view
        square = view.squares[0]
        step: float = view.step()
        square.setPos(QPointF(-4.0 + 0.3 * step, -3.0 - 0.6 * step))
        self.assertAlmostEqual(square.pos().x(), -4.0)
        self.assertAlmostEqual(square.pos().y(), -3.0 - step)
        self.assertEqual(view.drawing.points[0], (-4.0, -3.0 - step))

    def test_zoom_and_keys(self) -> None:
        """The wheel zooms in and out, within limits; F fits; G grid."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtTest import QTest

        view = self.editor.view
        view.fit()
        before: float = view.zoom()
        center = QPointF(view.viewport().rect().center())

        def wheel(notches: int) -> None:
            """Turn the wheel by `notches` over the view's middle."""
            event: QWheelEvent = QWheelEvent(
                center,
                view.mapToGlobal(center),
                QPoint(0, 0),
                QPoint(0, 120 * notches),
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
                Qt.ScrollPhase.NoScrollPhase,
                False,
            )
            view.wheelEvent(event)

        wheel(1)
        self.assertAlmostEqual(view.zoom(), before * 1.25)
        wheel(-1000)
        self.assertAlmostEqual(view.zoom(), outline_editor.ZOOM_LIMITS[0])

        buttons = self.editor.buttons
        buttons["Fit"].click()
        self.assertAlmostEqual(view.zoom(), before, places=3)
        buttons["Grid"].click()
        self.assertFalse(view.grid_shown)
        buttons["Grid"].click()
        self.assertTrue(view.grid_shown)
        self.assertEqual(buttons["Delete"].text(), "Delete (Del)")
        self.assertEqual(self.editor.keys["Snap"].key().toString(), "S")

        # The keys work (`G` hides the grid, then shows it again).
        self.editor.activateWindow()
        qt_app.process_events()
        QTest.keyClick(view, Qt.Key.Key_G)
        self.assertFalse(view.grid_shown)
        QTest.keyClick(view, Qt.Key.Key_G)
        self.assertTrue(view.grid_shown)

    def test_snap_off(self) -> None:
        """With [Snap] off, a square goes exactly where it is put."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        from PySide6.QtCore import (  # pylint: disable=import-outside-toplevel
            QPointF,
        )

        self.editor.buttons["Snap"].click()
        self.assertFalse(self.editor.view.snap_on)
        square = self.editor.view.squares[1]
        square.setPos(QPointF(4.123, -3.0))
        self.assertAlmostEqual(square.pos().x(), 4.123)

    def test_add_and_delete(self) -> None:
        """Adding splits the edge after a corner; deleting stops at 3."""
        view = self.editor.view
        view.add_after(2)
        self.assertEqual(view.drawing.points[3], (-2.0, 0.5))
        self.assertEqual(len(view.squares), 4)
        self.assertEqual(view.squares[3].index, 3)
        view.delete(0)
        self.assertEqual(view.drawing.points[0], (4.0, -3.0))
        view.delete(0)
        self.assertIn("at least 3", view.message)
        self.assertEqual(len(view.drawing.points), 3)
        qt_app.process_events()
        self.assertIn("at least 3", self.editor.status.text())

    def test_selection(self) -> None:
        """Each click adds to the selection; empty space clears it."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtTest import QTest

        view = self.editor.view

        def click(where: QPointF) -> None:
            """Click the view at a scene point."""
            QTest.mouseClick(
                view.viewport(),
                Qt.MouseButton.LeftButton,
                pos=view.mapFromScene(where),
            )
            QTest.qWait(1)

        click(view.squares[0].pos())
        self.assertEqual(view.chosen_points, [0])
        click(view.squares[1].pos())
        click(view.origin.pos())
        click(view.squares[1].pos())
        self.assertEqual(view.chosen_points, [0, -1, 1])
        click(QPointF(3.0, 3.0))
        self.assertEqual(view.chosen_points, [])

    def test_delete_selected(self) -> None:
        """[Delete] removes the selection, letters too, as one change."""
        view = self.editor.view
        buttons = self.editor.buttons
        buttons["Delete"].click()
        self.assertIn("Select corners", view.message)
        view.select_point(0)
        buttons["Delete"].click()
        self.assertIn("at least 3", view.message)
        view.add_after(2)
        view.dimension_between(-1, 1)
        view.dimension_between(-1, 3)
        self.assertEqual(len(view.drawing.letters), 2)
        view.select_dimension(0)
        view.select_point(3)
        buttons["Delete"].click()
        self.assertEqual(view.drawing.dimensions, [])
        self.assertEqual(view.drawing.letters, [])
        self.assertEqual(len(view.drawing.points), 3)
        self.assertEqual(self.editor.table.rowCount(), 0)
        view.undo()
        self.assertEqual(len(view.drawing.dimensions), 2)
        self.assertEqual(self.editor.table.rowCount(), 2)

    def test_delete_after_drag(self) -> None:
        """A dimension dragged by its circle, then deleted, is gone
        from the scene's index too (a segmentation fault once)."""
        from PySide6.QtCore import QPoint, Qt  # pylint: disable=C0415
        from PySide6.QtTest import QTest  # pylint: disable=C0415

        view = self.editor.view
        view.dimension_between(-1, 1)
        qt_app.process_events()
        view.grab()
        port = view.viewport()
        start: QPoint = view.mapFromScene(view.circles[0].scenePos())
        end: QPoint = start + QPoint(20, 30)
        QTest.mousePress(port, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(port, start + QPoint(10, 15))
        QTest.mouseMove(port, end)
        QTest.mouseRelease(port, Qt.MouseButton.LeftButton, pos=end)
        qt_app.process_events()
        view.grab()
        self.assertEqual(view.chosen_dimensions, [0])
        self.editor.buttons["Delete"].click()
        self.assertEqual(view.drawing.dimensions, [])
        qt_app.process_events()
        self.assertFalse(view.grab().isNull())
        QTest.mouseClick(port, Qt.MouseButton.LeftButton, pos=end)

    def test_corner_tips(self) -> None:
        """Each square tells its formulas; a chosen circle is lit."""
        view = self.editor.view
        self.assertEqual(view.squares[1].toolTip(), "(X-Floating, Y-Floating)")
        view.dimension_between(-1, 1)
        tip: str = view.squares[1].toolTip()
        letter: str = view.drawing.dimensions[0].letter
        self.assertIn(letter, tip)
        self.assertEqual(tip.count("Floating"), 1)
        self.assertIn("(0, 0)", view.origin.toolTip())
        view.clear_selection()
        ring = view.circles[0].pen().color()
        view.select_dimension(0)
        self.assertNotEqual(view.circles[0].pen().color(), ring)
        self.assertEqual(
            view.circles[0].pen().color(), view.palette().highlight().color()
        )

    def test_cycle_kind(self) -> None:
        """[Dim. Kind] turns the selected dimensions horizontal <->
        vertical, as one change, keeping them selected."""
        view = self.editor.view
        button = self.editor.buttons["Dim. Kind"]
        self.assertIn("\u21bb", button.text())
        button.click()
        self.assertIn("Select dimensions", view.message)
        view.dimension_between(-1, 1)
        self.assertEqual(view.chosen_dimensions, [0])
        kind: str = view.drawing.dimensions[0].kind
        seen: list[str] = [kind]
        for _ in range(3):
            button.click()
            seen.append(view.drawing.dimensions[0].kind)
            self.assertEqual(view.chosen_dimensions, [0])
            self.assertFalse(view.grab().isNull())
        self.assertEqual(set(seen), {HORIZONTAL, LENGTH, VERTICAL})
        self.assertEqual(seen[3], kind)

        # Each kind keeps its own place (#29).
        dimension = view.drawing.dimensions[0]
        dimension.offset, dimension.along = -7.0, 0.25
        button.click()
        dimension = view.drawing.dimensions[0]
        dimension.offset, dimension.along = 3.0, 0.75
        for _ in range(3):
            button.click()
        dimension = view.drawing.dimensions[0]
        self.assertEqual((dimension.offset, dimension.along), (3.0, 0.75))
        for _ in range(2):
            button.click()
        dimension = view.drawing.dimensions[0]
        self.assertEqual((dimension.offset, dimension.along), (-7.0, 0.25))
        for _ in range(6):
            view.undo()
        view.undo()
        self.assertEqual(view.drawing.dimensions[0].kind, seen[2])

    def test_length(self) -> None:
        """A length runs beside its points, the circle moving it."""
        from PySide6.QtCore import QPoint, QPointF, Qt  # pylint: disable=C0415
        from PySide6.QtTest import QTest  # pylint: disable=C0415

        view = self.editor.view
        view.dimension_between(0, 1)
        dimension = view.drawing.dimensions[0]
        dimension.kind = LENGTH
        dimension.offset = 2.0
        view.make_squares()
        first, second, start, end = view.measures[0].ends()
        self.assertAlmostEqual(
            QPointF.dotProduct(end - start, start - first), 0.0
        )
        self.assertEqual(end - start, second - first)
        self.assertFalse(view.grab().isNull())
        port = view.viewport()
        at: QPoint = view.mapFromScene(view.circles[0].scenePos())
        QTest.mousePress(port, Qt.MouseButton.LeftButton, pos=at)
        QTest.mouseMove(port, at + QPoint(30, 40))
        QTest.mouseRelease(
            port, Qt.MouseButton.LeftButton, pos=at + QPoint(30, 40)
        )
        self.assertNotEqual(dimension.offset, 2.0)
        self.assertEqual(len(view.history.done), 2)
        dimension.offset = view.offset_for(LENGTH, 0, 1)
        self.assertNotEqual(dimension.offset, 0.0)
        self.assertEqual(
            outline_editor.left_of(QPointF(0.0, 0.0)), QPointF(0.0, 0.0)
        )

    def test_undo_redo(self) -> None:
        """Undo and redo go back and forth; a new change ends redo."""
        view = self.editor.view
        buttons = self.editor.buttons
        first: list[tuple[float, float]] = list(view.drawing.points)
        qt_app.process_events()
        self.assertFalse(buttons["Undo"].isEnabled())
        view.add_after(0)
        added: list[tuple[float, float]] = list(view.drawing.points)
        view.delete(3)
        qt_app.process_events()
        self.assertTrue(buttons["Undo"].isEnabled())
        buttons["Undo"].click()
        self.assertEqual(view.drawing.points, added)
        buttons["Undo"].click()
        self.assertEqual(view.drawing.points, first)
        self.assertEqual(len(view.squares), 3)
        view.undo()
        self.assertEqual(view.drawing.points, first)
        qt_app.process_events()
        self.assertTrue(buttons["Redo"].isEnabled())
        buttons["Redo"].click()
        self.assertEqual(view.drawing.points, added)
        view.delete(1)
        self.assertEqual(view.history.undone, [])
        view.redo()
        self.assertEqual(len(view.drawing.points), 3)
        self.assertEqual(buttons["Redo"].text(), "Redo (Ctrl+Shift+Z)")

    def test_drag_is_one_change(self) -> None:
        """A whole drag is one change; a click moving nothing is none."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        view = self.editor.view
        first: list[tuple[float, float]] = list(view.drawing.points)
        where: QPoint = view.mapFromScene(view.squares[0].pos())
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=where)
        self.assertEqual(view.history.done, [])
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=where)
        for step in range(1, 6):
            QTest.mouseMove(view.viewport(), where + QPoint(20 * step, 0))
        QTest.mouseRelease(
            view.viewport(),
            Qt.MouseButton.LeftButton,
            pos=where + QPoint(100, 0),
        )
        self.assertNotEqual(view.drawing.points, first)
        self.assertEqual(len(view.history.done), 1)
        view.undo()
        self.assertEqual(view.drawing.points, first)

    def test_letters_table(self) -> None:
        """[New Letter] adds a row; edits are kept and checked."""
        editor = self.editor
        self.assertEqual(editor.table.rowCount(), 0)
        self.assertEqual(editor.buttons["New Letter"].text(), "New Letter (L)")
        editor.buttons["New Letter"].click()
        editor.buttons["New Letter"].click()
        self.assertEqual(editor.table.rowCount(), 2)
        self.assertEqual(cell(editor, 1, 0).text(), "B")
        cell(editor, 0, 1).setText("Overall width")
        self.assertEqual(editor.drawing.letters[0].name, "Overall width")
        cell(editor, 1, 0).setText(" a ")
        self.assertEqual(editor.drawing.letters[1].letter, "a")
        self.assertIn("only in case", editor.status.text())
        self.assertIn("only in case", cell(editor, 1, 0).toolTip())
        cell(editor, 1, 0).setText("H")
        self.assertEqual(editor.status.text(), "")
        cell(editor, 1, 2).setText("2")
        self.assertIn("H: '2' is not a value", editor.status.text())
        cell(editor, 1, 2).setText("2-1/4 in")
        self.assertEqual(editor.status.text(), "")
        self.assertEqual(cell(editor, 1, 2).toolTip(), "")

    def test_live_typing(self) -> None:
        """Each keystroke in a cell is kept and checked at once."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QLineEdit

        editor = self.editor
        editor.buttons["New Letter"].click()
        editor.table.editItem(cell(editor, 0, 2))
        qt_app.process_events()
        entry: object = editor.table.focusWidget()
        assert isinstance(entry, QLineEdit)
        entry.selectAll()
        QTest.keyClicks(entry, "6")
        self.assertEqual(editor.drawing.letters[0].default, "6")
        self.assertIn("is not a value", editor.status.text())
        self.assertIn("is not a value", entry.toolTip())
        QTest.keyClicks(entry, " in")
        self.assertEqual(editor.drawing.letters[0].default, "6 in")
        self.assertEqual(editor.status.text(), "")
        self.assertEqual(entry.styleSheet(), "")

    def test_dimension_selected(self) -> None:
        """[Dimension] with two points clicked before, around or after."""
        editor = self.editor
        view = editor.view
        dimension = editor.buttons["Dimension"]

        # C1, C2, D.
        view.select_point(0)
        view.select_point(1)
        dimension.click()
        first = view.drawing.dimensions[0]
        self.assertEqual((first.letter, first.kind), ("A", "horizontal"))
        self.assertEqual(cell(editor, 0, 0).text(), "A")
        self.assertNotIn(1, view.solution.x)  # Not tied to the origin.

        # D, C1, C2.
        dimension.click()
        qt_app.process_events()
        self.assertIn("Click two points", editor.status.text())
        view.select_point(-1)
        self.assertIn("second point", view.message)
        view.select_point(2)
        second = view.drawing.dimensions[1]
        self.assertEqual((second.letter, second.kind), ("B", "vertical"))
        self.assertEqual(str(view.solution.y[2]), "B")
        self.assertFalse(view.grab().isNull())

        # C1, D, C2; then empty space stops the waiting.
        view.add_after(2)
        view.select_point(-1)
        dimension.click()
        self.assertTrue(view.wanted)
        view.select_point(3)
        self.assertEqual(len(view.drawing.dimensions), 3)
        dimension.click()
        view.clear_selection()
        view.select_point(0)
        self.assertEqual(len(view.drawing.dimensions), 3)

        # Two points in one place are refused.
        view.drawing.points[1] = view.drawing.points[0]
        view.select_point(0)
        view.select_point(1)
        dimension.click()
        self.assertIn("same place", view.message)

    def test_drag_dimension(self) -> None:
        """The circle moves letter and line; a line click selects."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtTest import QTest

        view = self.editor.view
        view.add_dimension(Dimension("W", HORIZONTAL, 0, 1, -5.0))
        circle = view.circles[0]
        self.assertEqual((circle.pos().x(), circle.pos().y()), (0.0, -5.0))
        grab: QPoint = view.mapFromScene(circle.pos())
        target: QPoint = view.mapFromScene(QPointF(6.1, -7.1))
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=grab)
        QTest.mouseMove(view.viewport(), grab + QPoint(5, 5))
        QTest.mouseMove(view.viewport(), target)
        QTest.mouseRelease(
            view.viewport(), Qt.MouseButton.LeftButton, pos=target
        )
        dimension = view.drawing.dimensions[0]
        steps: float = dimension.offset / view.step()
        self.assertAlmostEqual(steps, round(steps))
        self.assertLess(dimension.offset, -6.0)
        self.assertGreater(dimension.along, 1.0)  # Past the arrowhead.
        self.assertFalse(view.grab().isNull())
        self.assertEqual(len(view.history.done), 2)
        view.undo()
        self.assertEqual(view.drawing.dimensions[0].offset, -5.0)
        self.assertEqual(view.drawing.dimensions[0].along, 0.5)
        line: QPoint = view.mapFromScene(QPointF(-2.0, -5.0))
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=line)
        self.assertEqual(view.chosen_dimensions, [0])
        self.assertEqual(view.drawing.dimensions[0].offset, -5.0)
        self.assertTrue(view.measures[0].shape().contains(QPointF(1.0, -5.0)))

    def test_edge_handles(self) -> None:
        """A handle's drag pulls out a snapped corner; a click does not."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        view = self.editor.view
        self.assertEqual(len(view.handles), 3)
        handle = view.handles[0]
        self.assertEqual((handle.pos().x(), handle.pos().y()), (0.0, -3.0))
        self.assertTrue(handle.isVisible())
        where: QPoint = view.mapFromScene(handle.pos())
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=where)
        self.assertEqual(len(view.drawing.points), 3)
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=where)
        QTest.mouseMove(view.viewport(), where + QPoint(0, 30))
        QTest.mouseMove(view.viewport(), where + QPoint(0, 60))
        QTest.mouseRelease(
            view.viewport(),
            Qt.MouseButton.LeftButton,
            pos=where + QPoint(0, 60),
        )
        self.assertEqual(len(view.drawing.points), 4)
        x: float
        y: float
        x, y = view.drawing.points[1]
        self.assertLess(y, -3.0)
        self.assertAlmostEqual(y / view.step(), round(y / view.step()))
        self.assertEqual(len(view.handles), 4)
        view.undo()
        self.assertEqual(len(view.drawing.points), 3)
        # Zoomed far out, the edges are too short for handles.
        view.scale(1e-3, 1e-3)
        view.place_handles()
        self.assertFalse(view.handles[0].isVisible())
        self.assertEqual(x, 0.0)

    def test_given_letters(self) -> None:
        """A drawing's letters are shown, problems marked at once."""
        drawing: Drawing = Drawing(
            letters=[Letter("W", "Width", "6 in"), Letter("pi", "", "x")]
        )
        editor: OutlineEditor = OutlineEditor(drawing)
        self.assertEqual(cell(editor, 0, 2).text(), "6 in")
        self.assertIn("pi: 'pi' is kept", editor.status.text())
        editor.close()
        editor.deleteLater()

    def test_pan(self) -> None:
        """Dragging empty space pans; the pointer is an arrow after."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtTest import QTest

        view = self.editor.view
        empty: QPoint = view.mapFromScene(QPointF(3.0, 3.0))
        before: QPointF = view.mapToScene(empty)
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=empty)
        self.assertEqual(
            view.viewport().cursor().shape(), Qt.CursorShape.ClosedHandCursor
        )
        QTest.mouseMove(view.viewport(), empty + QPoint(40, 0))
        QTest.mouseRelease(
            view.viewport(),
            Qt.MouseButton.LeftButton,
            pos=empty + QPoint(40, 0),
        )
        self.assertLess(view.mapToScene(empty).x(), before.x())
        self.assertEqual(
            view.viewport().cursor().shape(), Qt.CursorShape.ArrowCursor
        )

    def test_paints(self) -> None:
        """The view draws, grid on and off, with no error."""
        view = self.editor.view
        self.assertFalse(view.grab().isNull())
        view.grid_shown = False
        self.assertFalse(view.grab().isNull())
        view.restyle()


if __name__ == "__main__":
    unittest.main()
