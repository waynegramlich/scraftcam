#!/usr/bin/env python3
"""The 2D outline editor (`T.prg~5.1.9.2`): chunk 1.

A window with X and Y axes, an origin square, a grid that gets finer
as one zooms in (#12, #13), and an outline whose corners are pull
squares, dragged and snapped to the grid (Shift drags freely).  Each
edge ends in a small arrowhead showing the winding, counterclockwise
(#4).  The wheel zooms about the pointer (#3); dragging the origin or
empty space pans the view (#6).  A mode bar across the top (#11) has
a keyed button for each action, no menus: [Move (M)], [Add (A)] (a
corner after the clicked one, splitting the edge leaving it) and
[Delete (D)] are the modes; [Grid (G)], [Snap (S)] and [Fit (F)];
[Undo (Ctrl+Z)] and [Redo (Ctrl+Shift+Z)] (#18), a whole drag being
one change.

The scene is in unitless drawing steps (letters give the real sizes,
#15), Y up.  Run alone: `python3 -m scraftcam.gui.outline_editor`.
"""

import math
import sys
from dataclasses import dataclass, field

from ..packages import require

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QPointF, QRect, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractButton,
    QApplication,
    QButtonGroup,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyleOptionGraphicsItem,
    QVBoxLayout,
    QWidget,
)

from . import theme  # noqa: E402
from .window import make_application  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order

# Screen sizes, in pixels: a pull square's side, an arrowhead's length,
# the outline's and the thin lines' widths (#26), and the least gap
# between minor grid lines.
SQUARE_PIXELS: float = 9.0
ARROW_PIXELS: float = 9.0
THICK_PIXELS: float = 2.0
THIN_PIXELS: float = 1.0
GRID_PIXELS: float = 12.0

# Every `MAJOR_EVERY`th grid line is drawn darker.
MAJOR_EVERY: int = 5

# How far one wheel notch (120 eighths of a degree) zooms, and the
# zoom's limits (pixels per drawing step).
ZOOM_PER_NOTCH: float = 1.25
ZOOM_LIMITS: tuple[float, float] = (1e-3, 1e5)

# The modes: what a click on a pull square does.
MOVE: str = "move"
ADD: str = "add"
DELETE: str = "delete"

# An outline has at least this many corners.
LEAST_CORNERS: int = 3

# The first outline: a triangle around the origin, counterclockwise.
TRIANGLE: tuple[tuple[float, float], ...] = (
    (-4.0, -3.0),
    (4.0, -3.0),
    (0.0, 4.0),
)


# Function `grid_step()`:
def grid_step(pixels_per_step: float) -> float:
    """Return the finest grid step at least `GRID_PIXELS` apart.

    Steps are 1, 2 or 5 times a power of ten, so they read well.

    Arguments:
    * `pixels_per_step` (`float`): The zoom, in pixels per drawing step.

    Returns:
    * (`float`): The grid step, in drawing steps.
    """
    least: float = GRID_PIXELS / pixels_per_step
    power: float = 10.0 ** math.floor(math.log10(least))
    factor: float
    for factor in (1.0, 2.0, 5.0, 10.0):
        if factor * power >= least * (1.0 - 1e-9):
            return factor * power
    return 10.0 * power  # pragma: no cover (the loop always returns)


# Function `snap()`:
def snap(point: QPointF, step: float) -> QPointF:
    """Return `point` moved to the nearest grid crossing.

    Arguments:
    * `point` (`QPointF`): The point, in drawing steps.
    * `step` (`float`): The grid step.

    Returns:
    * (`QPointF`): The snapped point.
    """
    return QPointF(
        round(point.x() / step) * step, round(point.y() / step) * step
    )


# Function `triangle()`:
def triangle() -> list[tuple[float, float]]:
    """Return a fresh copy of the first outline, `TRIANGLE`."""
    return list(TRIANGLE)


# Class `Drawing`:
@dataclass(slots=True)
class Drawing:
    """The outline being drawn, as corner positions in drawing steps.

    Attributes:
    * `points` (`list[tuple[float, float]]`):
      The corners, in order, counterclockwise.

    Constructor:
    * `Drawing(points)`
    """

    # Constructor arguments:
    points: list[tuple[float, float]] = field(
        init=True, default_factory=triangle
    )


# Class `History`:
@dataclass(slots=True)
class History:
    """The corners before each change, for undo and redo (#18).

    Attributes (alphabetized):
    * `done` (`list[list[tuple[float, float]]]`):
      The corners before each change done, the latest last.
    * `undone` (`list[list[tuple[float, float]]]`):
      The corners before each change undone, the latest last.

    Constructor:
    * `History()`
    """

    # Remaining attributes (alphabetized):
    done: list[list[tuple[float, float]]] = field(
        init=False, default_factory=list
    )
    undone: list[list[tuple[float, float]]] = field(
        init=False, default_factory=list
    )

    # Method `History.remember()`:
    def remember(self, before: list[tuple[float, float]]) -> None:
        """Keep the corners from before a change; nothing to redo now.

        Arguments:
        * `before` (`list[tuple[float, float]]`): The corners.
        """
        self.done.append(list(before))
        self.undone.clear()

    # Method `History.undo()`:
    def undo(
        self, now: list[tuple[float, float]]
    ) -> list[tuple[float, float]] | None:
        """Return the corners before the last change (`None`: none).

        Arguments:
        * `now` (`list[tuple[float, float]]`): The corners now, kept
          for redo.

        Returns:
        * (`list[tuple[float, float]] | None`): The corners to show.
        """
        if not self.done:
            return None
        self.undone.append(list(now))
        return self.done.pop()

    # Method `History.redo()`:
    def redo(
        self, now: list[tuple[float, float]]
    ) -> list[tuple[float, float]] | None:
        """Return the corners after the last undone change.

        Arguments:
        * `now` (`list[tuple[float, float]]`): The corners now, kept
          for undo.

        Returns:
        * (`list[tuple[float, float]] | None`):
          The corners to show (`None`: nothing to redo).
        """
        if not self.undone:
            return None
        self.done.append(list(now))
        return self.undone.pop()


# Class `PullSquare`:
class PullSquare(QGraphicsRectItem):
    """A corner's square, the same size on screen at any zoom.

    In [Move] it is dragged, moving its corner, snapped to the grid
    when [Snap] is on and Shift is not held.  In [Add] or [Delete] a
    click adds a corner after it or deletes its corner.

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its corner's index in the drawing.
    * `before` (`list[tuple[float, float]]`):
      The corners when a drag began (empty between drags).
    """

    # Method `PullSquare.__init__()`:
    def __init__(self, editor: "OutlineView", index: int) -> None:
        """Make the square of one corner.

        Arguments:
        * `editor` (`OutlineView`): The view it is drawn in.
        * `index` (`int`): Its corner's index in the drawing.
        """
        half: float = SQUARE_PIXELS / 2.0
        super().__init__(-half, -half, SQUARE_PIXELS, SQUARE_PIXELS)
        self.editor: OutlineView = editor
        self.index: int = index
        self.before: list[tuple[float, float]] = []

        # Placed before it sends its moves, so placing it never snaps
        # its corner.
        self.setPos(*editor.drawing.points[index])
        flags: type[QGraphicsItem.GraphicsItemFlag] = (
            QGraphicsItem.GraphicsItemFlag
        )
        self.setFlag(flags.ItemIgnoresTransformations)
        self.setFlag(flags.ItemIsMovable)
        self.setFlag(flags.ItemSendsGeometryChanges)
        self.setZValue(2.0)

    # Method `PullSquare.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Add or delete in those modes; else start a drag."""
        if self.editor.mode == ADD:
            self.editor.add_after(self.index)
            event.accept()
        elif self.editor.mode == DELETE:
            self.editor.delete(self.index)
            event.accept()
        else:
            self.before = list(self.editor.drawing.points)
            super().mousePressEvent(event)

    # Method `PullSquare.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """End a drag: remember it, if it moved the corner."""
        super().mouseReleaseEvent(event)
        if self.before and self.before != self.editor.drawing.points:
            self.editor.history.remember(self.before)
        self.before = []

    # Method `PullSquare.itemChange()`:
    def itemChange(
        self, change: QGraphicsItem.GraphicsItemChange, value: object
    ) -> object:
        """Snap a move, and move the corner with it."""
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and isinstance(value, QPointF)
        ):
            free: bool = not self.editor.snap_on or bool(
                QApplication.keyboardModifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )
            moved: QPointF = value if free else snap(value, self.editor.step())
            self.editor.drawing.points[self.index] = (moved.x(), moved.y())
            self.editor.outline.refresh()
            return moved
        return super().itemChange(change, value)


# Class `OutlineItem`:
class OutlineItem(QGraphicsItem):
    """The outline: thick edges, each ending in a small arrowhead.

    Attributes:
    * `drawing` (`Drawing`): What it draws.
    """

    # Method `OutlineItem.__init__()`:
    def __init__(self, drawing: Drawing) -> None:
        """Make the outline of a drawing.

        Arguments:
        * `drawing` (`Drawing`): What it draws.
        """
        super().__init__()
        self.drawing: Drawing = drawing
        self.setZValue(1.0)

    # Method `OutlineItem.refresh()`:
    def refresh(self) -> None:
        """Draw again after the corners moved."""
        self.prepareGeometryChange()
        self.update()

    # Method `OutlineItem.boundingRect()`:
    def boundingRect(self) -> QRectF:
        """Return a box around the corners, with room for the arrows."""
        xs: list[float] = [x for x, _ in self.drawing.points]
        ys: list[float] = [y for _, y in self.drawing.points]
        box: QRectF = QRectF(
            min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        )
        margin: float = 0.05 * max(box.width(), box.height(), 1.0)
        return box.adjusted(-margin, -margin, margin, margin)

    # Method `OutlineItem.paint()`:
    def paint(
        self,
        painter: QPainter,
        _option: QStyleOptionGraphicsItem,
        _widget: QWidget | None = None,
    ) -> None:
        """Draw the edges, then an arrowhead at the end of each."""
        # Pens are cosmetic: their widths are pixels at any zoom.
        ink: QColor = QColor(theme.colors().ink)
        pen: QPen = QPen(ink, THICK_PIXELS)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        corners: list[QPointF] = [
            QPointF(x, y) for x, y in self.drawing.points
        ]
        painter.drawPolygon(QPolygonF(corners))

        # Each arrowhead is `ARROW_PIXELS` long on screen, pointing
        # along its edge into the corner it ends at.
        scale: float = painter.worldTransform().m11()
        length: float = ARROW_PIXELS / max(abs(scale), 1e-12)
        painter.setBrush(ink)
        index: int
        for index, end in enumerate(corners):
            start: QPointF = corners[index - 1]
            painter.drawPath(arrowhead(start, end, length))


# Function `arrowhead()`:
def arrowhead(start: QPointF, end: QPointF, length: float) -> QPainterPath:
    """Return a closed arrowhead at `end` of the edge from `start`.

    Arguments:
    * `start` (`QPointF`): Where the edge starts.
    * `end` (`QPointF`): Where it ends, the arrow's tip.
    * `length` (`float`): The arrowhead's length, in drawing steps.

    Returns:
    * (`QPainterPath`): The arrowhead (empty for a zero length edge).
    """
    path: QPainterPath = QPainterPath()
    dx: float = end.x() - start.x()
    dy: float = end.y() - start.y()
    edge: float = math.hypot(dx, dy)
    if edge == 0.0:
        return path
    ux: float = dx / edge
    uy: float = dy / edge
    back: QPointF = QPointF(end.x() - ux * length, end.y() - uy * length)
    side: QPointF = QPointF(-uy * length / 3.0, ux * length / 3.0)
    path.moveTo(end)
    path.lineTo(back + side)
    path.lineTo(back - side)
    path.closeSubpath()
    return path


# Class `OutlineView`:
# A view holds the drawing's state as well as its items.
class OutlineView(  # pylint: disable=too-many-instance-attributes
    QGraphicsView
):
    """The drawing area: grid, axes, origin, outline and squares.

    Attributes:
    * `drawing` (`Drawing`): The outline being drawn.
    * `grid_shown` (`bool`): Whether the grid is drawn.
    * `history` (`History`): What undo and redo go back and forth in.
    * `message` (`str`): The last refusal, for the mode bar.
    * `mode` (`str`): `MOVE`, `ADD` or `DELETE`.
    * `origin` (`QGraphicsRectItem`): The origin's square.
    * `outline` (`OutlineItem`): The outline.
    * `snap_on` (`bool`): Whether drags snap to the grid.
    * `squares` (`list[PullSquare]`): The corners' squares.
    """

    # Method `OutlineView.__init__()`:
    def __init__(self, drawing: Drawing) -> None:
        """Make the view of a drawing, fitted to it.

        Arguments:
        * `drawing` (`Drawing`): The outline being drawn.
        """
        super().__init__()
        self.drawing: Drawing = drawing
        self.grid_shown: bool = True
        self.history: History = History()
        self.message: str = ""
        self.mode: str = MOVE
        self.snap_on: bool = True
        scene: QGraphicsScene = QGraphicsScene(self)
        scene.setSceneRect(QRectF(-1e6, -1e6, 2e6, 2e6))
        self.setScene(scene)

        # Y up; zoom about the pointer; drag empty space to pan.
        self.scale(1.0, -1.0)
        anchor: QGraphicsView.ViewportAnchor = (
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setTransformationAnchor(anchor)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

        # The origin's square does not move: dragging it pans (#6).
        half: float = SQUARE_PIXELS / 2.0
        self.origin: QGraphicsRectItem = QGraphicsRectItem(
            -half, -half, SQUARE_PIXELS, SQUARE_PIXELS
        )
        self.origin.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        scene.addItem(self.origin)

        # The outline, then a square on each corner.
        self.outline: OutlineItem = OutlineItem(drawing)
        scene.addItem(self.outline)
        self.squares: list[PullSquare] = []
        self.make_squares()
        self.resize(800, 600)
        self.fit()

    # Method `OutlineView.make_squares()`:
    def make_squares(self) -> None:
        """Put a square on each corner, in place of any there were."""
        square: PullSquare
        for square in self.squares:
            self.scene().removeItem(square)
        self.squares = []
        index: int
        for index in range(len(self.drawing.points)):
            square = PullSquare(self, index)
            self.scene().addItem(square)
            self.squares.append(square)
        self.outline.refresh()
        self.restyle()

    # Method `OutlineView.add_after()`:
    def add_after(self, index: int) -> None:
        """Add a corner in the middle of the edge leaving a corner.

        Arguments:
        * `index` (`int`): The corner the edge leaves.
        """
        points: list[tuple[float, float]] = self.drawing.points
        x0: float
        y0: float
        x1: float
        y1: float
        x0, y0 = points[index]
        x1, y1 = points[(index + 1) % len(points)]
        self.history.remember(points)
        points.insert(index + 1, ((x0 + x1) / 2.0, (y0 + y1) / 2.0))
        self.message = ""
        self.make_squares()

    # Method `OutlineView.delete()`:
    def delete(self, index: int) -> None:
        """Delete a corner, unless only `LEAST_CORNERS` are left.

        Arguments:
        * `index` (`int`): The corner.
        """
        if len(self.drawing.points) <= LEAST_CORNERS:
            self.message = (
                f"An outline needs at least {LEAST_CORNERS} corners."
            )
            return
        self.history.remember(self.drawing.points)
        del self.drawing.points[index]
        self.message = ""
        self.make_squares()

    # Method `OutlineView.undo()`:
    def undo(self) -> None:
        """Go back to the corners before the last change, if any."""
        self.show_points(self.history.undo(self.drawing.points))

    # Method `OutlineView.redo()`:
    def redo(self) -> None:
        """Do the last undone change again, if any."""
        self.show_points(self.history.redo(self.drawing.points))

    # Method `OutlineView.show_points()`:
    def show_points(self, points: list[tuple[float, float]] | None) -> None:
        """Show these corners (`None`: leave things as they are).

        Arguments:
        * `points` (`list[tuple[float, float]] | None`): The corners.
        """
        if points is not None:
            self.drawing.points[:] = points
            self.message = ""
            self.make_squares()

    # Method `OutlineView.restyle()`:
    def restyle(self) -> None:
        """Color everything for the scheme in use (light or dark)."""
        scheme: theme.Colors = theme.colors()
        self.setBackgroundBrush(QColor(scheme.paper))
        pen: QPen = QPen(QColor(scheme.ink), THIN_PIXELS)
        pen.setCosmetic(True)
        self.origin.setPen(pen)
        self.origin.setBrush(QColor(scheme.ink))
        square: PullSquare
        for square in self.squares:
            square.setPen(pen)
            square.setBrush(QColor(scheme.paper))
        self.viewport().update()

    # Method `OutlineView.zoom()`:
    def zoom(self) -> float:
        """Return the zoom, in pixels per drawing step."""
        return abs(self.transform().m11())

    # Method `OutlineView.step()`:
    def step(self) -> float:
        """Return the grid step at the current zoom."""
        return grid_step(self.zoom())

    # Method `OutlineView.fit()`:
    def fit(self) -> None:
        """Fit the outline (and the origin) in the window."""
        box: QRectF = self.outline.boundingRect().united(
            QRectF(-1.0, -1.0, 2.0, 2.0)
        )
        self.fitInView(box, Qt.AspectRatioMode.KeepAspectRatio)

    # Method `OutlineView.wheelEvent()`:
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom about the pointer, within `ZOOM_LIMITS`."""
        notches: float = event.angleDelta().y() / 120.0
        factor: float = ZOOM_PER_NOTCH**notches
        low: float
        high: float
        low, high = ZOOM_LIMITS
        wanted: float = min(max(self.zoom() * factor, low), high)
        factor = wanted / self.zoom()
        self.scale(factor, factor)
        event.accept()

    # Method `OutlineView.toggle_grid()`:
    def toggle_grid(self) -> None:
        """Show the grid, or hide it."""
        self.grid_shown = not self.grid_shown
        self.viewport().update()

    # Method `OutlineView.drawBackground()`:
    def drawBackground(
        self, painter: QPainter, exposed: QRectF | QRect
    ) -> None:
        """Draw the paper, the grid (if shown) and the axes."""
        super().drawBackground(painter, exposed)
        rect: QRectF = QRectF(exposed)
        scheme: theme.Colors = theme.colors()
        pen: QPen = QPen(QColor(scheme.quiet), THIN_PIXELS)
        pen.setCosmetic(True)

        # The grid under the axes.
        if self.grid_shown:
            self.draw_grid(painter, rect, pen)

        # The axes, through the origin, past the window's edges.
        pen.setColor(QColor(scheme.ink))
        painter.setPen(pen)
        painter.drawLine(QPointF(rect.left(), 0.0), QPointF(rect.right(), 0.0))
        painter.drawLine(QPointF(0.0, rect.top()), QPointF(0.0, rect.bottom()))

    # Method `OutlineView.draw_grid()`:
    def draw_grid(self, painter: QPainter, rect: QRectF, pen: QPen) -> None:
        """Draw the grid lines crossing `rect`.

        Minor lines are faint, every `MAJOR_EVERY`th one less so.

        Arguments:
        * `painter` (`QPainter`): What draws.
        * `rect` (`QRectF`): The part of the scene to draw.
        * `pen` (`QPen`): A thin cosmetic pen, recolored here.
        """
        step: float = self.step()
        scheme: theme.Colors = theme.colors()
        minor: QColor = QColor(scheme.quiet)
        minor.setAlphaF(0.2)
        major: QColor = QColor(scheme.quiet)
        major.setAlphaF(0.45)

        # Vertical lines, then horizontal ones.
        line: int
        for line in range(
            math.floor(rect.left() / step), math.ceil(rect.right() / step) + 1
        ):
            pen.setColor(major if line % MAJOR_EVERY == 0 else minor)
            painter.setPen(pen)
            x: float = line * step
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for line in range(
            math.floor(rect.top() / step), math.ceil(rect.bottom() / step) + 1
        ):
            pen.setColor(major if line % MAJOR_EVERY == 0 else minor)
            painter.setPen(pen)
            y: float = line * step
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))


# Class `OutlineEditor`:
class OutlineEditor(QWidget):
    """The editor's window: the mode bar over the drawing area.

    Attributes:
    * `buttons` (`dict[str, QPushButton]`):
      The mode bar's buttons, by their word (`"Move"`, `"Grid"`, ...).
    * `drawing` (`Drawing`): The outline being drawn.
    * `modes` (`QButtonGroup`): [Move], [Add] and [Delete], one down.
    * `status` (`QLabel`): The last refusal, at the bar's end.
    * `view` (`OutlineView`): The drawing area.
    """

    # Method `OutlineEditor.__init__()`:
    def __init__(self, drawing: Drawing | None = None) -> None:
        """Make the window.

        Arguments:
        * `drawing` (`Drawing | None`):
          The outline to edit (the first triangle when `None`).
        """
        super().__init__()
        self.drawing: Drawing = Drawing() if drawing is None else drawing
        self.setWindowTitle("Outline Editor")
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view: OutlineView = OutlineView(self.drawing)

        # The mode bar: each button shows its key (#20).
        mode_bar: QHBoxLayout = QHBoxLayout()
        layout.addLayout(mode_bar)
        layout.addWidget(self.view)
        self.buttons: dict[str, QPushButton] = {}
        self.modes: QButtonGroup = QButtonGroup(self)
        word: str
        key: str
        for word, key in (
            ("Move", "M"),
            ("Add", "A"),
            ("Delete", "D"),
            ("Grid", "G"),
            ("Snap", "S"),
            ("Fit", "F"),
            ("Undo", "Ctrl+Z"),
            ("Redo", "Ctrl+Shift+Z"),
        ):
            button: QPushButton = QPushButton(f"{word} ({key})")
            button.setShortcut(key)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            mode_bar.addWidget(button)
            self.buttons[word] = button
        for word in ("Move", "Add", "Delete"):
            self.buttons[word].setCheckable(True)
            self.modes.addButton(self.buttons[word])
        self.buttons["Move"].setChecked(True)
        self.modes.buttonClicked.connect(self.choose_mode)
        for word in ("Grid", "Snap"):
            self.buttons[word].setCheckable(True)
            self.buttons[word].setChecked(True)
        self.buttons["Grid"].clicked.connect(self.view.toggle_grid)
        self.buttons["Snap"].clicked.connect(self.toggle_snap)
        self.buttons["Fit"].clicked.connect(self.view.fit)
        self.buttons["Undo"].clicked.connect(self.view.undo)
        self.buttons["Redo"].clicked.connect(self.view.redo)
        self.status: QLabel = QLabel("")
        mode_bar.addWidget(self.status, 1)
        self.view.scene().changed.connect(self.show_message)
        self.show_message()
        self.resize(800, 600)

    # Method `OutlineEditor.choose_mode()`:
    def choose_mode(self, button: QAbstractButton) -> None:
        """Make the clicked mode button's mode the view's.

        Arguments:
        * `button` (`QAbstractButton`): [Move], [Add] or [Delete].
        """
        word: str
        for word, mode in (("Move", MOVE), ("Add", ADD), ("Delete", DELETE)):
            if button is self.buttons[word]:
                self.view.mode = mode
        self.view.message = ""
        self.show_message()

    # Method `OutlineEditor.toggle_snap()`:
    def toggle_snap(self) -> None:
        """Turn snapping on or off, as [Snap] now shows."""
        self.view.snap_on = self.buttons["Snap"].isChecked()

    # Method `OutlineEditor.show_message()`:
    def show_message(self, *_regions: object) -> None:
        """Show the view's last refusal (or nothing) in the mode bar.

        [Undo] and [Redo] are enabled only when there is something to
        undo or redo.
        """
        history: History = self.view.history
        self.buttons["Undo"].setEnabled(bool(history.done))
        self.buttons["Redo"].setEnabled(bool(history.undone))
        self.status.setText(self.view.message)
        self.status.setStyleSheet(f"color: {theme.colors().problem}")


# Function `main()`:
def main() -> None:
    """Show the editor until its window is closed."""
    application: QApplication = make_application(headless=False)
    editor: OutlineEditor = OutlineEditor()
    theme.follow(application, editor.view.restyle)
    editor.show()
    editor.view.fit()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
