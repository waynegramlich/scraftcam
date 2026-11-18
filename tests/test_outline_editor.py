"""Tests of `scraftcam.gui.outline_editor`, chunk 1 (offscreen)."""

import unittest
from typing import TYPE_CHECKING

from scraftcam.gui import outline_editor
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


class EditorTest(unittest.TestCase):
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
        self.assertEqual(buttons["Move"].text(), "Move (M)")
        self.assertEqual(buttons["Snap"].shortcut().toString(), "S")

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
        """[Add] splits the edge after a corner; [Delete] stops at 3."""
        view = self.editor.view
        buttons = self.editor.buttons
        buttons["Add"].click()
        self.assertEqual(view.mode, outline_editor.ADD)
        view.add_after(2)
        self.assertEqual(view.drawing.points[3], (-2.0, 0.5))
        self.assertEqual(len(view.squares), 4)
        self.assertEqual(view.squares[3].index, 3)
        buttons["Delete"].click()
        self.assertEqual(view.mode, outline_editor.DELETE)
        view.delete(0)
        self.assertEqual(view.drawing.points[0], (4.0, -3.0))
        view.delete(0)
        self.assertIn("at least 3", view.message)
        self.assertEqual(len(view.drawing.points), 3)
        qt_app.process_events()
        self.assertIn("at least 3", self.editor.status.text())
        buttons["Move"].click()
        self.assertEqual(view.mode, outline_editor.MOVE)
        self.assertEqual(self.editor.status.text(), "")

    def test_clicks(self) -> None:
        """A click on a square adds or deletes, as the mode says."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        view = self.editor.view

        def click(index: int) -> None:
            """Click the middle of a corner's square."""
            where: QPoint = view.mapFromScene(view.squares[index].pos())
            QTest.mouseClick(
                view.viewport(), Qt.MouseButton.LeftButton, pos=where
            )

        self.editor.buttons["Add"].click()
        click(0)
        self.assertEqual(len(view.drawing.points), 4)
        self.editor.buttons["Delete"].click()
        click(1)
        self.assertEqual(len(view.drawing.points), 3)
        self.editor.buttons["Move"].click()
        click(0)
        self.assertEqual(len(view.drawing.points), 3)

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

    def test_paints(self) -> None:
        """The view draws, grid on and off, with no error."""
        view = self.editor.view
        self.assertFalse(view.grab().isNull())
        view.grid_shown = False
        self.assertFalse(view.grab().isNull())
        view.restyle()


if __name__ == "__main__":
    unittest.main()
