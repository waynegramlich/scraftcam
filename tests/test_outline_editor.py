"""Tests of `scraftcam.gui.outline_editor`, chunk 1 (offscreen)."""

import unittest
from typing import TYPE_CHECKING

from scraftcam.gui import outline_editor
from scraftcam.gui.dimensions import (
    ANGLE,
    HORIZONTAL,
    LENGTH,
    ORIGIN,
    VERTICAL,
    X_AXIS,
    Y_AXIS,
    Dimension,
)
from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_editor import Drawing, OutlineEditor
from scraftcam.gui.outline_file import outline_text
from tests import qt_app

# Only for the type: `PySide6` is on `sys.path` once `tests` is in.
if TYPE_CHECKING:
    from PySide6.QtWidgets import QTableWidgetItem


# Function `cell()`:
def cell(editor: OutlineEditor, row: int, column: int) -> "QTableWidgetItem":
    """Return a letter's cell (`row` counts letters, past the fixed
    "No fillet" row; it must be there)."""
    item: QTableWidgetItem | None = editor.table.item(
        outline_editor.LETTER_ROW + row, column
    )
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
        self.assertEqual(self.editor.table.rowCount(), 1)
        view.undo()
        self.assertEqual(len(view.drawing.dimensions), 2)
        self.assertEqual(self.editor.table.rowCount(), 3)

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
        # Selected circles and squares are filled, not colored (#129).
        none = view.circles[0].brush().style().__class__.NoBrush
        view.clear_selection()
        self.assertEqual(view.circles[0].brush().style(), none)
        self.assertEqual(view.squares[1].brush().style(), none)
        view.select_dimension(0)
        view.select_point(1)
        self.assertNotEqual(view.circles[0].brush().style(), none)
        self.assertNotEqual(view.squares[1].brush().style(), none)
        self.assertEqual(view.squares[0].pen().widthF(), 3.0)

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

    def test_select_edge(self) -> None:
        """A click on an edge's circle selects the edge, lit; a drag
        does not; empty space clears it."""
        from PySide6.QtCore import QPoint, Qt  # pylint: disable=C0415
        from PySide6.QtTest import QTest  # pylint: disable=C0415

        view = self.editor.view
        port = view.viewport()
        none = view.handles[1].brush().style()
        at: QPoint = view.mapFromScene(view.handles[1].scenePos())
        QTest.mouseClick(port, Qt.MouseButton.LeftButton, pos=at)
        self.assertEqual(view.chosen_edges, [1])
        self.assertNotEqual(view.handles[1].brush().style(), none)
        view.select_edge(2)
        view.select_edge(1)
        self.assertEqual(view.chosen_edges, [2, 1])
        view.clear_selection()
        self.assertEqual(view.chosen_edges, [])
        self.assertEqual(view.handles[1].brush().style(), none)

    def test_angle(self) -> None:
        """[Angle] between two edges: an arc, its letter in degrees;
        refused for too few edges or parallel ones."""
        from PySide6.QtCore import QPointF  # pylint: disable=C0415

        view = self.editor.view
        button = self.editor.buttons["Dimension"]
        view.select_edge(0)
        view.select_edge(1)
        button.click()
        self.assertEqual(len(view.drawing.dimensions), 1)
        self.assertEqual(view.drawing.dimensions[0].kind, ANGLE)
        self.assertTrue(view.drawing.letters[-1].default.endswith(" deg"))
        self.assertFalse(view.grab().isNull())
        self.assertFalse(view.measures[0].shape().isEmpty())
        self.assertFalse(view.measures[0].boundingRect().isEmpty())
        circle = view.circles[0]
        circle.drag_angle(view.drawing.dimensions[0], QPointF(9.0, 9.0))
        self.assertGreater(view.drawing.dimensions[0].offset, 0.0)
        self.editor.buttons["Dim. Kind"].click()
        self.assertEqual(view.drawing.dimensions[0].kind, ANGLE)
        view.drawing.points[:] = [(0, 0), (4, 0), (4, 2), (0, 2)]
        view.make_squares()
        view.select_edge(0)
        view.select_edge(2)
        button.click()
        self.assertIn("parallel", view.message)
        self.assertFalse(view.grab().isNull())
        corners = [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)]
        self.assertEqual(outline_editor.middle_rays(corners, 0, 2), (1, -1))
        arc = outline_editor.edge_arc(corners, 0, 2, (1, -1))
        assert arc is not None
        self.assertAlmostEqual(arc[2], 90.0)
        self.assertIsNone(
            outline_editor.middle_rays(view.drawing.points, 0, 2)
        )

    def test_angle_sector_fixed(self) -> None:
        """An angle is positive whichever edge is clicked first, and
        stays under 180 degrees as corners move (#57, #68)."""
        view = self.editor.view
        tip = [(0.0, 0.0), (2.0, 1.2), (2.0, 8.0), (-2.0, 8.0), (-2.0, 1.2)]
        for first, second in ((4, 0), (0, 4)):
            view.drawing.points[:] = tip
            view.drawing.dimensions.clear()
            view.drawing.letters.clear()
            view.make_squares()
            view.select_edge(first)
            view.select_edge(second)
            self.editor.buttons["Dimension"].click()
            self.assertEqual(view.drawing.letters[-1].default, "118 deg")

        # A corner swung around (#68): the arc follows the drawing,
        # always on the side under 180 degrees.
        dimension = view.drawing.dimensions[0]
        x: float
        for x in (3.0, 1.0, -3.0, -1.0):
            view.drawing.points[0] = (x, 3.0 if x > 0.0 else -3.0)
            view.follow()
            arc = outline_editor.angle_arc(view.drawing.points, dimension)
            assert arc is not None
            self.assertLess(arc[2], 180.0)
            self.assertFalse(view.grab().isNull())

    def test_angle_edges_change(self) -> None:
        """An angle keeps to its edges as corners come and go (#45)."""
        drawing: Drawing = Drawing()
        drawing.points[:] = [(0, 0), (4, 0), (4, 4), (0, 4), (-2, 2)]
        drawing.dimensions.append(Dimension("A", ANGLE, 0, 2))

        # A corner splitting an edge before the second: it shifts.
        drawing.insert(2, (4, 2))
        self.assertEqual(
            (drawing.dimensions[0].start, drawing.dimensions[0].end), (0, 3)
        )

        # The first edge's far corner gone: the edge reaches on.
        drawing.remove(1)
        self.assertEqual(
            (drawing.dimensions[0].start, drawing.dimensions[0].end), (0, 2)
        )

        # A corner an edge leaves gone: the angle goes with it.
        drawing.remove(2)
        self.assertEqual(drawing.dimensions, [])

    def test_letter_uses(self) -> None:
        """A letter whose value does not fit its dimension is red."""
        view = self.editor.view
        view.select_edge(0)
        view.select_edge(1)
        self.editor.buttons["Dimension"].click()
        self.editor.check_letters()
        self.assertEqual(self.editor.problems.text(), "")
        view.drawing.letters[0].default = "2 in"
        self.editor.check_letters()
        self.assertIn("measures an angle", self.editor.problems.text())

    def test_axis_angle(self) -> None:
        """A click on an axis selects it; an angle from it to an edge:
        half a drill point (#59, #63, #65); the arc keeps its letter
        (#76)."""
        from PySide6.QtCore import QPoint, QPointF, Qt  # pylint: disable=C0415
        from PySide6.QtTest import QTest  # pylint: disable=C0415

        view = self.editor.view
        view.drawing.points[:] = [(0.0, 0.0), (2.0, 1.2), (2.0, 8.0), (-1, 8)]
        view.make_squares()
        view.fit()
        port = view.viewport()
        at: QPoint = view.mapFromScene(QPointF(0.0, 4.0))
        QTest.mouseClick(port, Qt.MouseButton.LeftButton, pos=at)
        self.assertEqual(view.chosen_edges, [Y_AXIS])
        self.assertFalse(view.grab().isNull())
        view.select_edge(0)
        self.editor.buttons["Dimension"].click()
        self.assertEqual(view.drawing.letters[-1].default, "59 deg")
        self.assertFalse(view.grab().isNull())
        dimension = view.drawing.dimensions[0]
        view.circles[0].drag_angle(dimension, QPointF(9.0, -9.0))
        self.assertTrue(0.0 <= dimension.along <= 1.0)
        view.select_edge(X_AXIS)
        view.select_edge(Y_AXIS)
        self.editor.buttons["Dimension"].click()
        self.assertIn("pick an edge", view.message)
        view.clear_selection()
        far: QPoint = view.mapFromScene(QPointF(5.0, 5.0))
        self.assertEqual(view.axis_at(far), ORIGIN)

    def test_dimension_from_axis(self) -> None:
        """An axis and a corner, then [Dimension]: measured across the
        axis from the origin (#80)."""
        view = self.editor.view
        view.select_edge(X_AXIS)
        view.select_point(2)
        self.editor.buttons["Dimension"].click()
        dimension = view.drawing.dimensions[-1]
        self.assertEqual(
            (dimension.kind, dimension.start, dimension.end),
            (VERTICAL, ORIGIN, 2),
        )
        view.clear_selection()
        view.select_point(1)
        view.select_edge(Y_AXIS)
        self.editor.buttons["Dimension"].click()
        self.assertEqual(view.drawing.dimensions[-1].kind, HORIZONTAL)

    def test_revolve(self) -> None:
        """[Revolve]: refused left of the Y axis; on, it keeps drags at
        X >= 0; undone as one change, the button following (#32)."""
        from PySide6.QtCore import QPointF  # pylint: disable=C0415

        view = self.editor.view
        button = self.editor.buttons["Revolve"]
        button.click()
        self.assertFalse(view.drawing.revolve)
        self.assertIn("X >= 0", view.message)
        view.drawing.points[:] = [(0.0, 0.0), (2.0, 1.2), (2.0, 8.0), (0, 8)]
        view.make_squares()
        button.click()
        self.assertTrue(view.drawing.revolve)
        self.assertTrue(button.isChecked())
        self.assertFalse(view.grab().isNull())
        self.assertLess(view.outline.boundingRect().left(), -1.9)
        view.squares[1].setPos(QPointF(-3.0, 1.0))
        self.assertEqual(view.drawing.points[1][0], 0.0)
        view.undo()
        self.assertFalse(view.drawing.revolve)
        self.editor.show_message()
        self.assertFalse(button.isChecked())

    def test_file(self) -> None:
        """An editor on a file rewrites it after each change, and reads
        back the same drawing (#90, #97)."""
        import tempfile  # pylint: disable=C0415
        from pathlib import Path  # pylint: disable=C0415

        with tempfile.TemporaryDirectory() as folder:
            path: Path = Path(folder) / "drill.outline.toml"
            editor: OutlineEditor = OutlineEditor(path=path)
            self.assertIn("drill.outline.toml", editor.windowTitle())
            # A new file is written at once, holding the triangle.
            editor.save()
            self.assertTrue(path.exists())
            editor.view.add_after(0)
            editor.show_message()
            self.assertTrue(path.exists())
            drawing = outline_editor.drawing_from(path)
            self.assertEqual(drawing.points, editor.drawing.points)
            editor.view.dimension_between(-1, 1)
            editor.keep(outline_editor.LETTER_ROW, 2, "3 in")
            self.assertEqual(
                outline_editor.drawing_from(path).letters[0].default, "3 in"
            )
            again: OutlineEditor = OutlineEditor(
                outline_editor.drawing_from(path), path=path
            )
            self.assertEqual(again.saved, path.read_text(encoding="utf-8"))
            self.assertEqual(outline_editor.file_text(None), "")
            editor.close()
            again.close()

    def test_fillet(self) -> None:
        """Fillets by the note letter, made the first time; each change
        is one undo step (#116)."""
        view = self.editor.view
        self.assertNotIn("Fillet", self.editor.buttons)
        self.assertIn("(Home)", self.editor.buttons["Fit"].text())
        view.drawing.points[:] = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0, 4)]
        view.make_squares()
        view.set_fillets([1, 2], outline_editor.NOTE_CHOICE)
        self.assertEqual(view.drawing.note_radius, "UDF")
        self.assertEqual(view.drawing.letters[0].letter, "UDF")
        self.assertEqual(view.drawing.letters[0].default, "1/16 in")
        radii = outline_editor.fillet_radii(view.drawing)
        self.assertEqual(sorted(radii), [1, 2])
        self.assertAlmostEqual(radii[1], 0.8)

        # The drawn size follows the corners (#121).
        view.drawing.points[2] = (6.0, 2.0)
        self.assertAlmostEqual(
            outline_editor.fillet_radii(view.drawing)[1], 0.4
        )
        view.drawing.points[2] = (6.0, 4.0)

        ends = outline_editor.fillet_ends(view.drawing)
        self.assertEqual(ends[0][0], ends[0][1])
        self.assertAlmostEqual(ends[1][0].x(), 5.2)
        self.assertAlmostEqual(ends[1][1].y(), 0.8)
        box = outline_editor.rounded_path(view.drawing, ends).boundingRect()
        self.assertAlmostEqual(box.right(), 6.0, places=6)
        self.assertFalse(view.grab().isNull())
        # No fillet on corner 1: sharp again.
        view.set_fillets([1], "")
        self.assertEqual(
            sorted(outline_editor.fillet_radii(view.drawing)), [2]
        )
        self.editor.buttons["Dim. Kind"].click()
        view.undo()
        view.undo()
        self.assertEqual(view.drawing.note_radius, "")
        self.assertEqual(outline_editor.fillet_radii(view.drawing), {})

    def test_fillet_scale(self) -> None:
        """Once the drawing has a scale, a fillet is its value to scale,
        and follows a changed value (#142.3)."""
        view = self.editor.view
        view.drawing.points[:] = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0, 4)]
        view.make_squares()
        view.set_fillets([1], outline_editor.NOTE_CHOICE)
        view.drawing.scale = 0.5
        self.assertAlmostEqual(
            outline_editor.fillet_radii(view.drawing)[1], 25.4 / 32
        )
        view.drawing.letters[0].default = "1/8 in"
        view.follow()
        self.assertAlmostEqual(
            outline_editor.fillet_radii(view.drawing)[1], 25.4 / 16
        )

    def test_fillets_tab(self) -> None:
        """[Fillets] shows "No fillet" and only the letters checked
        "Fillet", with [New Fillet Dimension] (#213, #214, #219)."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        from PySide6.QtCore import Qt  # pylint: disable=C0415

        editor = self.editor
        hidden = editor.table.isRowHidden
        editor.drawing.letters[:] = [
            Letter("W", "Width", "6 in", ""),
            Letter("R2", "Big", "1/4 in", "", fillet=True),
        ]
        editor.fill_table()
        self.assertEqual(
            [hidden(row) for row in range(3)], [True, False, False]
        )
        self.assertTrue(editor.new_fillet.isHidden())
        editor.tabs.setCurrentIndex(outline_editor.FILLETS_TAB)
        self.assertEqual(
            [hidden(row) for row in range(3)], [False, True, False]
        )
        fixed = editor.table.item(0, 4)
        assert fixed is not None
        self.assertEqual(fixed.text(), "(No Edit Allowed)")
        self.assertFalse(fixed.flags() & Qt.ItemFlag.ItemIsEditable)
        self.assertFalse(editor.new_fillet.isHidden())
        editor.new_fillet.click()
        self.assertEqual(editor.drawing.letters[-1].letter, "A")
        self.assertTrue(editor.drawing.letters[-1].fillet)
        self.assertFalse(hidden(3))
        editor.buttons["New Letter"].click()
        self.assertTrue(editor.drawing.letters[-1].fillet)
        self.assertNotIn("No fillet", outline_text(editor.drawing))
        editor.tabs.setCurrentIndex(outline_editor.DIMENSIONS_TAB)
        self.assertFalse(hidden(1))

    def test_arm_and_paint(self) -> None:
        """A [Fillets] row clicked arms its letter: it fillets the
        corners selected (#218), then each corner clicked, one undo
        step each (#223); "No fillet" makes them sharp; clicking the
        row again, empty space or [Dimensions] disarms (#214)."""
        editor = self.editor
        view = editor.view
        view.drawing.points[:] = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0, 4)]
        view.drawing.letters[:] = [
            Letter("R2", "Big", "1/4 in", "", fillet=True)
        ]
        view.make_squares()
        editor.fill_table()
        editor.tabs.setCurrentIndex(outline_editor.FILLETS_TAB)
        view.select_point(1)
        editor.row_clicked(1, 1)
        self.assertEqual(view.armed, "R2")
        self.assertEqual(view.fillets(), {1: "R2"})
        self.assertIn("by R2", editor.status.text())
        self.assertEqual(editor.table.selectedItems()[0].row(), 1)
        done = len(view.history.done)
        view.squares[2].paint_fillet()
        self.assertEqual(view.fillets(), {1: "R2", 2: "R2"})
        self.assertEqual(len(view.history.done), done + 1)
        editor.row_clicked(0, 1)
        self.assertEqual(view.armed, "")
        view.squares[2].paint_fillet()
        self.assertEqual(view.fillets(), {})
        self.assertIn("sharp", editor.status.text())
        editor.row_clicked(0, 1)
        self.assertIsNone(view.armed)
        editor.row_clicked(1, 1)
        view.clear_selection()
        self.assertIsNone(view.armed)
        editor.row_clicked(1, 1)
        editor.tabs.setCurrentIndex(outline_editor.DIMENSIONS_TAB)
        self.assertIsNone(view.armed)
        self.assertEqual(editor.status.text(), "")
        # Undone: R2 armed again on corner 1, then the sharp corner 2.
        view.undo()
        self.assertEqual(view.fillets(), {})
        view.undo()
        self.assertEqual(view.fillets(), {2: "R2"})

    def test_fillet_too_big(self) -> None:
        """A fillet too big for its edges is red in the table, under it,
        and on its corner (#127, #139, #141)."""
        view = self.editor.view
        view.drawing.points[:] = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0, 4)]
        view.make_squares()
        view.dimension_between(-1, 1, HORIZONTAL)
        view.dimension_between(-1, 2, VERTICAL)
        view.drawing.letters[0].default = "1 in"
        view.drawing.letters[1].default = "1/2 in"
        view.clear_selection()
        view.set_fillets([2], outline_editor.NOTE_CHOICE)
        self.editor.check_letters()
        self.assertEqual(view.trouble, {})
        self.assertEqual(self.editor.problems.text(), "")
        view.drawing.letters[2].default = "3/4 in"
        self.editor.check_letters()
        self.assertEqual(sorted(view.trouble), [2])
        self.assertIn(
            "UDF need 3/4 in of a 1/2 in edge.",
            self.editor.problems.text(),
        )
        self.assertNotIn("UDF: UDF", self.editor.problems.text())
        self.assertEqual(view.squares[2].pen().color().name(), "#c00000")
        self.assertFalse(view.grab().isNull())

    def test_click_and_type(self) -> None:
        """One click on a Value cell edits it; what is typed sticks and
        fires no button's key (`n` of `in` is [Dimension]'s)."""
        from PySide6.QtCore import Qt  # pylint: disable=C0415
        from PySide6.QtTest import QTest  # pylint: disable=C0415
        from PySide6.QtWidgets import QApplication  # pylint: disable=C0415

        view = self.editor.view
        table = self.editor.table
        view.dimension_between(-1, 1)
        qt_app.process_events()
        spot = table.visualRect(
            table.model().index(outline_editor.LETTER_ROW, 2)
        ).center()
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=spot)
        qt_app.process_events()
        line = QApplication.focusWidget()
        assert line is not None
        QTest.keyClick(line, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClicks(line, "3/4 in")
        QTest.keyClick(line, Qt.Key.Key_Return)
        qt_app.process_events()
        self.assertEqual(view.drawing.letters[0].default, "3/4 in")
        self.assertEqual(cell(self.editor, 0, 2).text(), "3/4 in")
        self.assertEqual(len(view.drawing.dimensions), 1)

        # A new dimension refills the table: no cell left being edited,
        # so the buttons' keys still work.
        view.dimension_between(-1, 2)
        qt_app.process_events()
        self.assertNotEqual(
            table.state(), table.state().__class__.EditingState
        )

    def test_follows_values(self) -> None:
        """The drawing follows the table's values, to a scale chosen
        once; a bad value keeps the last good shape (#148, #154)."""
        from PySide6.QtCore import QPointF  # pylint: disable=C0415

        editor = self.editor
        view = editor.view
        view.drawing.points[:] = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0, 4)]
        view.make_squares()
        view.dimension_between(-1, 1, HORIZONTAL)
        view.dimension_between(-1, 2, VERTICAL)
        editor.keep(outline_editor.LETTER_ROW, 2, "1 in")
        editor.keep(outline_editor.LETTER_ROW + 1, 2, "1/2 in")
        self.assertAlmostEqual(view.drawing.points[2][0] / 2.0, 3.0)
        self.assertAlmostEqual(view.drawing.points[2][1], 3.0)
        scale: float = view.drawing.scale
        editor.keep(outline_editor.LETTER_ROW, 2, "2 in")
        self.assertAlmostEqual(view.drawing.points[1][0], 12.0)
        self.assertAlmostEqual(view.drawing.points[3][1], 3.0)
        self.assertEqual(view.drawing.scale, scale)
        self.assertEqual(view.squares[1].pos().x(), view.drawing.points[1][0])
        for bad in ("-2 in", "0 in", "2 i"):
            editor.keep(outline_editor.LETTER_ROW, 2, bad)
            self.assertAlmostEqual(view.drawing.points[1][0], 12.0)
        self.assertIn("A: '2 i' is not a value", editor.problems.text())

        # A fixed coordinate does not move when dragged (#152 to come).
        view.squares[1].setPos(view.squares[1].pos() + QPointF(5.0, 0.0))
        self.assertAlmostEqual(view.drawing.points[1][0], 12.0)

    def test_hide(self) -> None:
        """[Hide], then a wide drag over the shank: a strip hiding a
        stretch of height, shown in the overview; refused over a
        corner; undone as one change (#164, #165, #168)."""
        from PySide6.QtCore import QPointF, Qt  # pylint: disable=C0415
        from PySide6.QtTest import QTest  # pylint: disable=C0415

        editor = self.editor
        view = editor.view
        view.drawing.points[:] = [(0.0, 0.0), (2.0, 1.2), (2.0, 8.0), (0, 8)]
        view.make_squares()
        view.fit()
        port = view.viewport()

        # Function `drag()`:
        def drag(start: QPointF, end: QPointF) -> None:
            """Drag from one scene point to another."""
            editor.buttons["Hide"].click()
            QTest.mousePress(
                port, Qt.MouseButton.LeftButton, pos=view.mapFromScene(start)
            )
            QTest.mouseMove(port, view.mapFromScene(end))
            QTest.mouseRelease(
                port, Qt.MouseButton.LeftButton, pos=view.mapFromScene(end)
            )

        drag(QPointF(-1.0, 3.0), QPointF(3.0, 6.0))
        self.assertTrue(view.overview)
        self.assertEqual(len(view.drawing.hides), 1)
        hide = view.drawing.hides[0]
        self.assertEqual((hide.axis, hide.below, hide.above), (1, 1, 2))
        editor.show_message()
        self.assertTrue(editor.buttons["Overview"].isChecked())
        self.assertFalse(view.grab().isNull())
        drag(QPointF(-1.0, 0.5), QPointF(3.0, 2.0))
        self.assertIn("corner", view.message)
        self.assertEqual(len(view.drawing.hides), 1)
        editor.buttons["Overview"].click()
        self.assertFalse(view.overview)
        view.undo()
        self.assertEqual(view.drawing.hides, [])

    def test_strip_circles(self) -> None:
        """A strip's side circles resize it, its middle one moves it;
        not over a corner; only in the overview; one change (#173)."""
        from PySide6.QtCore import (  # pylint: disable=C0415
            QPoint,
            QPointF,
            QRectF,
            Qt,
        )
        from PySide6.QtTest import QTest  # pylint: disable=C0415

        from scraftcam.gui.hides import (  # pylint: disable=C0415
            across,
            strip,
        )

        view = self.editor.view
        view.drawing.points[:] = [(0.0, 0.0), (2.0, 1.2), (2.0, 8.0), (0, 8)]
        view.make_squares()
        view.lay_hide(QRectF(-1.0, 3.0, 4.0, 3.0))
        self.assertEqual(len(view.grips), 5)
        self.assertFalse(view.grips[0].isVisible())
        view.toggle_overview()
        view.fit()
        self.assertTrue(view.grips[0].isVisible())
        port = view.viewport()

        # Function `drag()`:
        def drag(grip: int, to: QPointF) -> None:
            """Drag one circle to a scene point."""
            start: QPoint = view.mapFromScene(view.grips[grip].scenePos())
            QTest.mousePress(port, Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseMove(port, view.mapFromScene(to))
            QTest.mouseRelease(
                port, Qt.MouseButton.LeftButton, pos=view.mapFromScene(to)
            )

        drag(1, QPointF(1.0, 7.0))  # The high side up to 7.
        self.assertAlmostEqual(
            strip(view.drawing.points, view.drawing.hides[0])[1], 7.0
        )
        drag(1, QPointF(1.0, 9.0))  # Past the top corner: refused.
        self.assertIn("corner", view.message)
        self.assertAlmostEqual(
            strip(view.drawing.points, view.drawing.hides[0])[1], 7.0
        )
        drag(4, QPointF(1.0, 4.0))  # The middle (5) down by 1.
        self.assertEqual(
            strip(view.drawing.points, view.drawing.hides[0]), (2.0, 6.0)
        )

        # The left and right sides: out is fine, into the part not.
        drag(3, QPointF(5.0, 4.0))  # The right side out to 5.
        self.assertEqual(
            across(view.drawing.points, view.drawing.hides[0])[1], 5.0
        )
        drag(2, QPointF(1.0, 4.0))  # The left side into the part.
        self.assertIn("reach past", view.message)
        view.undo()
        view.undo()
        self.assertAlmostEqual(
            strip(view.drawing.points, view.drawing.hides[0])[1], 7.0
        )

    def test_drag_across_axes(self) -> None:
        """A corner drags onto an axis and on across it; one fixed by
        a dimension stays (#176)."""
        from PySide6.QtCore import QPointF  # pylint: disable=C0415

        view = self.editor.view
        square = view.squares[0]
        x: float
        for x in (0.0, -2.0, 3.0):
            square.setPos(QPointF(x, -3.0))
            self.assertAlmostEqual(view.drawing.points[0][0], x)
        square.setPos(QPointF(3.0, 0.0))
        square.setPos(QPointF(3.0, 2.0))
        self.assertAlmostEqual(view.drawing.points[0][1], 2.0)
        view.dimension_between(-1, 0, HORIZONTAL)
        square.setPos(QPointF(-4.0, 2.0))
        self.assertAlmostEqual(view.drawing.points[0][1], 2.0)
        self.assertNotAlmostEqual(view.drawing.points[0][0], -4.0)

    def test_working_view(self) -> None:
        """Out of the overview, a strip's stretch is cut out: the piece
        past it drawn closer by the stretch less the gap; the view is
        for looking (#170, #171)."""
        from PySide6.QtCore import QRectF  # pylint: disable=C0415

        view = self.editor.view
        view.drawing.points[:] = [(0.0, 0.0), (2.0, 1.2), (2.0, 40), (0, 40)]
        view.make_squares()
        view.lay_hide(QRectF(-1.0, 5.0, 4.0, 30.0))
        self.assertEqual(view.drawing.hides[0].axis, 1)
        self.assertFalse(view.overview)
        self.assertFalse(view.isInteractive())
        gap: float = outline_editor.GAP_PIXELS / view.zoom()
        pieces = view.cut_offsets(1)
        self.assertEqual(len(pieces), 2)
        self.assertAlmostEqual(pieces[0][2], 0.0)
        self.assertAlmostEqual(pieces[1][2], -(30.0 - gap))
        self.assertEqual(view.cut_offsets(0), [(-1e6, 1e6, 0.0)])
        self.assertAlmostEqual(
            outline_editor.shift_at(pieces, 38.0), pieces[1][2]
        )
        self.assertFalse(view.grab().isNull())

        # A dimension across the cut: an S on each side, the same shape
        # (#185).
        view.dimension_between(-1, 2, VERTICAL)
        self.assertFalse(view.grab().isNull())
        below = view.ess(1, 5.0, 4.0)
        above = view.ess(1, 6.0, 4.0)

        # Its middle exactly at the line's end (#188).
        self.assertAlmostEqual(below.boundingRect().center().y(), 5.0)
        self.assertAlmostEqual(above.boundingRect().center().y(), 6.0)
        self.assertAlmostEqual(below.boundingRect().center().x(), 4.0)
        self.assertAlmostEqual(
            below.boundingRect().width(), above.boundingRect().width()
        )

        # It lies across the line: wider than it is tall (#187).
        self.assertGreater(
            below.boundingRect().width(), below.boundingRect().height()
        )
        view.toggle_overview()
        self.assertTrue(view.isInteractive())

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
        self.assertEqual(editor.table.rowCount(), 1)
        self.assertEqual(editor.buttons["New Letter"].text(), "New Letter (L)")
        editor.buttons["New Letter"].click()
        editor.buttons["New Letter"].click()
        self.assertEqual(editor.table.rowCount(), 3)
        self.assertEqual(cell(editor, 1, 0).text(), "B")
        cell(editor, 0, 1).setText("Overall width")
        self.assertEqual(editor.drawing.letters[0].name, "Overall width")
        cell(editor, 1, 0).setText(" a ")
        self.assertEqual(editor.drawing.letters[1].letter, "a")
        self.assertIn("only in case", editor.problems.text())
        self.assertIn("only in case", cell(editor, 1, 0).toolTip())
        cell(editor, 1, 0).setText("H")
        self.assertEqual(editor.problems.text(), "")
        cell(editor, 1, 2).setText("2")
        self.assertIn("H: '2' is not a value", editor.problems.text())
        cell(editor, 1, 2).setText("2-1/4 in")
        self.assertEqual(editor.problems.text(), "")
        self.assertEqual(cell(editor, 1, 2).toolTip(), "")

    def test_fillet_column(self) -> None:
        """The "Fillet" check box marks a fillet radius (#213)."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtCore import Qt

        editor = self.editor
        editor.buttons["New Letter"].click()
        box: QTableWidgetItem = cell(editor, 0, 3)
        self.assertEqual(box.text(), "")
        self.assertFalse(box.flags() & Qt.ItemFlag.ItemIsEditable)
        self.assertEqual(box.checkState(), Qt.CheckState.Unchecked)
        box.setCheckState(Qt.CheckState.Checked)
        self.assertTrue(editor.drawing.letters[0].fillet)
        self.assertEqual(editor.problems.text(), "")
        cell(editor, 0, 2).setText("30 deg")
        self.assertIn("a fillet radius is a length", editor.problems.text())
        self.assertIn("a fillet radius", cell(editor, 0, 3).toolTip())
        cell(editor, 0, 3).setCheckState(Qt.CheckState.Unchecked)
        self.assertFalse(editor.drawing.letters[0].fillet)
        self.assertEqual(editor.problems.text(), "")
        editor.view.note_letter()
        self.assertTrue(editor.drawing.letters[-1].fillet)

    def test_live_typing(self) -> None:
        """Each keystroke in a cell is kept and checked at once."""
        # (`PySide6` is on `sys.path` only once `tests` is imported.)
        # pylint: disable=import-outside-toplevel
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QLineEdit

        editor = self.editor
        editor.buttons["New Letter"].click()
        # [New Letter] edits the Name cell; on to the Value cell.
        editor.table.setCurrentCell(1, 2)
        qt_app.process_events()
        entry: object = editor.table.focusWidget()
        assert isinstance(entry, QLineEdit)
        entry.selectAll()
        QTest.keyClicks(entry, "6")
        self.assertEqual(editor.drawing.letters[0].default, "6")
        self.assertIn("is not a value", editor.problems.text())
        self.assertIn("is not a value", entry.toolTip())
        QTest.keyClicks(entry, " in")
        self.assertEqual(editor.drawing.letters[0].default, "6 in")
        self.assertEqual(editor.problems.text(), "")
        self.assertEqual(entry.styleSheet(), "")

    def test_dimension_from_selection(self) -> None:
        """[Dimension] works from what is selected (#234): one edge
        gives its length (#231), one corner the angle there (#232),
        an axis and an edge an angle; [Angle] is gone."""
        view = self.editor.view
        button = self.editor.buttons["Dimension"]
        self.assertNotIn("Angle", self.editor.buttons)
        view.select_edge(0)
        button.click()
        made = view.drawing.dimensions[-1]
        self.assertEqual((made.kind, made.start, made.end), (LENGTH, 0, 1))
        view.clear_selection()
        view.select_point(1)
        button.click()
        made = view.drawing.dimensions[-1]
        self.assertEqual((made.kind, {made.start, made.end}), (ANGLE, {0, 1}))
        view.clear_selection()
        view.select_edge(X_AXIS)
        view.select_edge(1)
        button.click()
        made = view.drawing.dimensions[-1]
        self.assertEqual(made.kind, ANGLE)
        self.assertIn(X_AXIS, (made.start, made.end))
        self.assertEqual(len(view.drawing.dimensions), 3)

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
        self.assertIn("two points", editor.status.text())
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
        self.assertIn("pi: 'pi' is kept", editor.problems.text())
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
