#!/usr/bin/env python3
"""The 2D outline editor (`T.prg~5.1.9.2`).

A window with X and Y axes, an origin square, a grid that gets finer
as one zooms in (#12, #13), and an outline whose corners are pull
squares, dragged and snapped to the grid (Shift drags freely).  Each
edge ends in a small arrowhead showing the winding, counterclockwise
(#4).  The wheel zooms about the pointer (#3); dragging the origin or
empty space pans the view (#6).  There are no modes (#58): dragging
moves (a corner, a dimension's line); each click adds to the
selection (empty space clears it), and the bar's buttons act on it.
[Dimension (N)] takes the last two points clicked, before or after
it is pressed, in any order (#60).
The bar has a keyed button for each action, no menus (#11): [Grid
(G)], [Snap (S)], [Delete (Del)], [Dimension (N)] (the two selected
points), [Dim. Kind \u21bb (K)] (horizontal, length, vertical),
[Angle (A)] (between the last two edges clicked),
[Fit (F)],
[Undo (Ctrl+Z)] and [Redo
(Ctrl+Shift+Z)] (#18), a whole drag being one change, [New Letter
(L)].  Below the drawing, past a bar dragged up and down, the
letters' table (#27): letter, long name, default value with its
unit, help, each kept and checked at every keystroke.

The scene is in unitless drawing steps (letters give the real sizes,
#15), Y up.  Run alone: `python3 -m scraftcam.gui.outline_editor`.
"""

import math
import sys
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..packages import require

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import (  # noqa: E402
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
)
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
    QShortcut,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionGraphicsItem,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import theme  # noqa: E402
from .dimensions import (  # noqa: E402
    ANGLE,
    AXES,
    HORIZONTAL,
    LENGTH,
    NEXT_KIND,
    ORIGIN,
    VERTICAL,
    X_AXIS,
    Y_AXIS,
    Dimension,
    Formula,
    Solution,
    solve,
)
from .letters import (  # noqa: E402
    Letter,
    letter_problem,
    next_letter,
    use_problem,
    value_problem,
)
from .outline_file import (  # noqa: E402
    Outline,
    OutlineError,
    outline_from_text,
    outline_text,
)
from .window import make_application  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order

# Screen sizes, in pixels: a pull square's side, an arrowhead's length,
# the outline's and the thin lines' widths (#26), and the least gap
# between minor grid lines.
SQUARE_PIXELS: float = 9.0
ARROW_PIXELS: float = 9.0

# How many straight pieces draw an angle's arc.
ARC_STEPS: int = 48

THICK_PIXELS: float = 2.0
THIN_PIXELS: float = 1.0
GRID_PIXELS: float = 12.0

# Every `MAJOR_EVERY`th grid line is drawn darker.
MAJOR_EVERY: int = 5

# How far one wheel notch (120 eighths of a degree) zooms, and the
# zoom's limits (pixels per drawing step).
ZOOM_PER_NOTCH: float = 1.25
ZOOM_LIMITS: tuple[float, float] = (1e-3, 1e5)

# The letters' table: its columns, each with its `Letter` field.
COLUMNS: tuple[tuple[str, str], ...] = (
    ("Letter", "letter"),
    ("Name", "name"),
    ("Default", "default"),
    ("Help", "help"),
)

# A dimension's extension lines run this far past its line, and its
# letter sits this far from it (pixels); the letters' size (points).
OVERSHOOT_PIXELS: float = 4.0
LETTER_GAP_PIXELS: float = 4.0
LETTER_POINTS: int = 11

# An edge handle's size, and the least length on screen of an edge
# that shows one (pixels).
HANDLE_PIXELS: float = 9.0
HANDLE_EDGE_PIXELS: float = 3.0 * SQUARE_PIXELS

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


# Class `Snapshot`:
@dataclass(frozen=True, slots=True)
class Snapshot:
    """A drawing's corners and dimensions at one time, for undo.

    Attributes:
    * `points` (`tuple[tuple[float, float], ...]`): The corners.
    * `dimensions` (`tuple[Dimension, ...]`): Copies of the dimensions.
    * `letters` (`tuple[Letter, ...]`): Copies of the letters.
    * `revolve` (`bool`): Whether it is revolved (#32).

    Constructor:
    * `Snapshot(points, dimensions, letters, revolve)`
    """

    # Constructor arguments:
    points: tuple[tuple[float, float], ...] = field(init=True)
    dimensions: tuple[Dimension, ...] = field(init=True)
    letters: tuple[Letter, ...] = field(init=True)
    revolve: bool = field(init=True, default=False)


# Class `Drawing`:
@dataclass(slots=True)
class Drawing:
    """The outline being drawn, as corner positions in drawing steps.

    Attributes:
    * `points` (`list[tuple[float, float]]`):
      The corners, in order, counterclockwise.
    * `letters` (`list[Letter]`): The letters naming its sizes.
    * `dimensions` (`list[Dimension]`): The dimensions, by letter.
    * `revolve` (`bool`): Whether it is revolved about the Y axis
      (#32): a round tool, drawn at X >= 0 only.

    Constructor:
    * `Drawing(points, letters, dimensions, revolve)`
    """

    # Constructor arguments:
    points: list[tuple[float, float]] = field(
        init=True, default_factory=triangle
    )
    letters: list[Letter] = field(init=True, default_factory=list)
    dimensions: list[Dimension] = field(init=True, default_factory=list)
    revolve: bool = field(init=True, default=False)

    # Method `Drawing.snapshot()`:
    def snapshot(self) -> Snapshot:
        """Return the corners and dimensions as they are now."""
        return Snapshot(
            tuple(self.points),
            tuple(replace(dimension) for dimension in self.dimensions),
            tuple(replace(letter) for letter in self.letters),
            self.revolve,
        )

    # Method `Drawing.restore()`:
    def restore(self, snapshot: Snapshot) -> None:
        """Go back to a snapshot's corners and dimensions.

        Arguments:
        * `snapshot` (`Snapshot`): What to go back to.
        """
        self.points[:] = snapshot.points
        self.dimensions[:] = [
            replace(dimension) for dimension in snapshot.dimensions
        ]
        self.letters[:] = [replace(letter) for letter in snapshot.letters]
        self.revolve = snapshot.revolve

    # Method `Drawing.follow_angles()`:
    def follow_angles(self) -> None:
        """Turn each angle to the side its edges are drawn on (#68):
        rays toward the edges' middles, measured counterclockwise from
        the edge that makes it under 180 degrees.  Parallel edges
        keep their rays."""
        dimension: Dimension
        for dimension in self.dimensions:
            if dimension.kind != ANGLE:
                continue
            rays: tuple[int, int] | None = middle_rays(
                self.points, dimension.start, dimension.end
            )
            if rays is None:
                continue
            dimension.rays = rays
            arc: tuple[QPointF, float, float] | None = angle_arc(
                self.points, dimension
            )
            if arc is not None and arc[2] > 180.0:
                dimension.start, dimension.end = dimension.end, dimension.start
                dimension.rays = (rays[1], rays[0])

    # Method `Drawing.insert()`:
    def insert(self, index: int, point: tuple[float, float]) -> None:
        """Insert a corner; the dimensions keep to their corners.

        Arguments:
        * `index` (`int`): Where the new corner goes.
        * `point` (`tuple[float, float]`): The new corner.
        """
        self.points.insert(index, point)
        dimension: Dimension
        for dimension in self.dimensions:
            if dimension.start >= index:
                dimension.start += 1
            if dimension.end >= index:
                dimension.end += 1

    # Method `Drawing.remove()`:
    def remove(self, index: int) -> None:
        """Remove a corner, with the dimensions that measure it.

        Arguments:
        * `index` (`int`): The corner.
        """
        del self.points[index]
        self.dimensions[:] = [
            dimension
            for dimension in self.dimensions
            if index not in (dimension.start, dimension.end)
        ]
        dimension: Dimension
        for dimension in self.dimensions:
            if dimension.start > index:
                dimension.start -= 1
            if dimension.end > index:
                dimension.end -= 1


# Class `History`:
@dataclass(slots=True)
class History:
    """The drawing before each change, for undo and redo (#18).

    Attributes (alphabetized):
    * `done` (`list[Snapshot]`):
      The drawing before each change done, the latest last.
    * `undone` (`list[Snapshot]`):
      The drawing before each change undone, the latest last.

    Constructor:
    * `History()`
    """

    # Remaining attributes (alphabetized):
    done: list[Snapshot] = field(init=False, default_factory=list)
    undone: list[Snapshot] = field(init=False, default_factory=list)

    # Method `History.remember()`:
    def remember(self, before: Snapshot) -> None:
        """Keep the drawing from before a change; nothing to redo now.

        Arguments:
        * `before` (`Snapshot`): The drawing.
        """
        self.done.append(before)
        self.undone.clear()

    # Method `History.undo()`:
    def undo(self, now: Snapshot) -> Snapshot | None:
        """Return the drawing before the last change (`None`: none).

        Arguments:
        * `now` (`Snapshot`): The drawing now, kept for redo.

        Returns:
        * (`Snapshot | None`): The drawing to show.
        """
        if not self.done:
            return None
        self.undone.append(now)
        return self.done.pop()

    # Method `History.redo()`:
    def redo(self, now: Snapshot) -> Snapshot | None:
        """Return the drawing after the last undone change.

        Arguments:
        * `now` (`Snapshot`): The drawing now, kept for undo.

        Returns:
        * (`Snapshot | None`):
          The drawing to show (`None`: nothing to redo).
        """
        if not self.undone:
            return None
        self.done.append(now)
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
    * `before` (`Snapshot | None`):
      The drawing when a drag began (`None` between drags).
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
        self.before: Snapshot | None = None

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
        """Select its corner, then start a drag."""
        self.editor.select_point(self.index)
        self.before = self.editor.drawing.snapshot()
        super().mousePressEvent(event)

    # Method `PullSquare.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """End a drag: remember it, if it moved the corner."""
        super().mouseReleaseEvent(event)
        if self.before is not None and self.before.points != tuple(
            self.editor.drawing.points
        ):
            self.editor.history.remember(self.before)
        self.before = None

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
            if self.editor.drawing.revolve and moved.x() < 0.0:
                moved.setX(0.0)  # A revolved outline keeps to X >= 0.
            self.editor.drawing.points[self.index] = (moved.x(), moved.y())
            self.editor.outline.refresh()
            self.editor.follow()
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
        if self.drawing.revolve:
            xs += [-x for x in xs]
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

        # Revolved: the other half, mirrored, faint and dashed.
        if self.drawing.revolve:
            ghost: QPen = QPen(QColor(theme.colors().quiet), THIN_PIXELS)
            ghost.setCosmetic(True)
            ghost.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(ghost)
            painter.drawPolygon(
                QPolygonF([QPointF(-x, y) for x, y in self.drawing.points])
            )
            painter.setPen(pen)

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


# Function `crossing()`:
def crossing(
    points: list[tuple[float, float]], first: int, second: int
) -> QPointF | None:
    """Return where two edges' lines cross.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `first` (`int`): The corner the first edge leaves.
    * `second` (`int`): The corner the second edge leaves.

    Returns:
    * (`QPointF | None`): The crossing; `None` for parallel edges.
    """
    a0: QPointF = edge_start(points, first)
    da: QPointF = edge_way(points, first)
    b0: QPointF = edge_start(points, second)
    db: QPointF = edge_way(points, second)
    cross: float = da.x() * db.y() - da.y() * db.x()
    if abs(cross) <= PARALLEL * max(
        math.hypot(da.x(), da.y()) * math.hypot(db.x(), db.y()), 1e-300
    ):
        return None
    gap: QPointF = b0 - a0
    return a0 + da * ((gap.x() * db.y() - gap.y() * db.x()) / cross)


# Function `edge_start()`:
def edge_start(points: list[tuple[float, float]], edge: int) -> QPointF:
    """Return the corner an edge leaves (the origin, for an axis).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `edge` (`int`): The corner the edge leaves, or an axis.

    Returns:
    * (`QPointF`): The point.
    """
    if edge in AXES:
        return QPointF(0.0, 0.0)
    return QPointF(*points[edge])


# Function `edge_way()`:
def edge_way(points: list[tuple[float, float]], edge: int) -> QPointF:
    """Return an edge's direction, from the corner it leaves (+X or
    +Y, for an axis).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `edge` (`int`): The corner the edge leaves, or an axis.

    Returns:
    * (`QPointF`): The next corner less this one.
    """
    if edge == X_AXIS:
        return QPointF(1.0, 0.0)
    if edge == Y_AXIS:
        return QPointF(0.0, 1.0)
    return QPointF(*points[(edge + 1) % len(points)]) - QPointF(*points[edge])


# Function `middle_rays()`:
def middle_rays(
    points: list[tuple[float, float]], first: int, second: int
) -> tuple[int, int] | None:
    """Return the rays from two edges' crossing toward their middles,
    each `1` along its edge's direction or `-1` against it (#53).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `first` (`int`): The corner the first edge leaves.
    * `second` (`int`): The corner the second edge leaves.

    Returns:
    * (`tuple[int, int] | None`): The two rays; `None` for parallel
      edges.
    """
    center: QPointF | None = crossing(points, first, second)
    if center is None:
        return None
    signs: list[int] = []
    edge: int
    other: int
    for edge, other in ((first, second), (second, first)):
        # An axis's ray points toward the other edge's side (#65).
        middle: QPointF = (
            edge_start(points, other) + edge_way(points, other) / 2
            if edge in AXES
            else edge_start(points, edge) + edge_way(points, edge) / 2
        )
        toward: float = QPointF.dotProduct(
            middle - center, edge_way(points, edge)
        )
        signs.append(1 if toward >= 0.0 else -1)
    return signs[0], signs[1]


# Function `edge_arc()`:
def edge_arc(
    points: list[tuple[float, float]],
    first: int,
    second: int,
    rays: tuple[int, int],
) -> tuple[QPointF, float, float] | None:
    """Return an angle's arc: where two edges' lines cross, and the
    turn counterclockwise from the first ray to the second.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `first` (`int`): The corner the first edge leaves.
    * `second` (`int`): The corner the second edge leaves.
    * `rays` (`tuple[int, int]`): Each ray along (`1`) or against
      (`-1`) its edge's direction.

    Returns:
    * (`tuple[QPointF, float, float] | None`): The crossing, the first
      ray's direction and the turn to the second ray (degrees, 0 to
      360, counterclockwise); `None` for parallel edges.
    """
    center: QPointF | None = crossing(points, first, second)
    if center is None:
        return None
    start: float = direction(edge_way(points, first) * rays[0])
    turn: float = direction(edge_way(points, second) * rays[1]) - start
    return center, start, turn % 360.0


# Function `angle_arc()`:
def angle_arc(
    points: list[tuple[float, float]], dimension: Dimension
) -> tuple[QPointF, float, float] | None:
    """Return an angle dimension's arc (see `edge_arc()`).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `dimension` (`Dimension`): The angle.

    Returns:
    * (`tuple[QPointF, float, float] | None`): As `edge_arc()`.
    """
    return edge_arc(points, dimension.start, dimension.end, dimension.rays)


# Function `direction()`:
def direction(way: QPointF) -> float:
    """Return a direction's angle from +X, in degrees.

    Arguments:
    * `way` (`QPointF`): The direction.

    Returns:
    * (`float`): Counterclockwise positive, -180 to 180.
    """
    return math.degrees(math.atan2(way.y(), way.x()))


# Function `left_of()`:
def left_of(way: QPointF) -> QPointF:
    """Return the unit vector a quarter turn counterclockwise from a
    direction (`(0, 0)` for none).

    Arguments:
    * `way` (`QPointF`): The direction.

    Returns:
    * (`QPointF`): One unit long, to its left (Y up).
    """
    length: float = (way.x() ** 2 + way.y() ** 2) ** 0.5
    if length == 0.0:
        return QPointF(0.0, 0.0)
    return QPointF(-way.y() / length, way.x() / length)


# Two edges closer to parallel than this (the sine of the angle
# between them) have no angle (#40).
PARALLEL: float = 1e-6


# Class `EdgeHandle`:
class EdgeHandle(QGraphicsEllipseItem):
    """A small hollow circle in the middle of an edge (#59).

    Dragged, it pulls out a new corner there, snapped as corners are,
    the whole drag one change; a click that does not move selects
    the edge (for [Angle], #S2).

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): The corner its edge leaves.
    * `before` (`Snapshot | None`): The drawing when a drag began.
    * `added` (`int`): The new corner's index during a drag (`-1`
      before the pointer moves).
    """

    # Method `EdgeHandle.__init__()`:
    def __init__(self, editor: "OutlineView", index: int) -> None:
        """Make the handle of one edge.

        Arguments:
        * `editor` (`OutlineView`): The view it is drawn in.
        * `index` (`int`): The corner its edge leaves.
        """
        half: float = HANDLE_PIXELS / 2.0
        super().__init__(-half, -half, HANDLE_PIXELS, HANDLE_PIXELS)
        self.editor: OutlineView = editor
        self.index: int = index
        self.before: Snapshot | None = None
        self.added: int = -1
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setZValue(1.5)

    # Method `EdgeHandle.place()`:
    def place(self) -> None:
        """Sit in the middle of its edge; hidden if the edge is short."""
        points: list[tuple[float, float]] = self.editor.drawing.points
        x0: float
        y0: float
        x1: float
        y1: float
        x0, y0 = points[self.index]
        x1, y1 = points[(self.index + 1) % len(points)]
        self.setPos((x0 + x1) / 2.0, (y0 + y1) / 2.0)
        length: float = (
            (x1 - x0) ** 2 + (y1 - y0) ** 2
        ) ** 0.5 * self.editor.zoom()
        self.setVisible(length >= HANDLE_EDGE_PIXELS)

    # Method `EdgeHandle.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Get ready to pull out a corner."""
        self.before = self.editor.drawing.snapshot()
        self.added = -1
        event.accept()

    # Method `EdgeHandle.mouseMoveEvent()`:
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Pull out the new corner (made at the first move)."""
        where: QPointF = event.scenePos()
        free: bool = not self.editor.snap_on or bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        if not free:
            where = snap(where, self.editor.step())
        if self.editor.drawing.revolve and where.x() < 0.0:
            where.setX(0.0)  # A revolved outline keeps to X >= 0.
        if self.added < 0:
            self.added = self.index + 1
            self.editor.drawing.insert(self.added, (where.x(), where.y()))
        self.editor.drawing.points[self.added] = (where.x(), where.y())
        self.setPos(where)
        self.editor.outline.refresh()
        measure: DimensionItem
        for measure in self.editor.measures:
            measure.prepareGeometryChange()
            measure.update()

    # Method `EdgeHandle.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, _event: QGraphicsSceneMouseEvent) -> None:
        """End the pull: remember it, and give the corner its square;
        or, if it never moved, select the edge."""
        if self.before is not None and self.added >= 0:
            self.editor.history.remember(self.before)
            self.before = None
            self.editor.make_squares()
        elif self.before is not None:
            self.editor.select_edge(self.index)
        self.before = None


# Class `DimensionHandle`:
class DimensionHandle(QGraphicsEllipseItem):
    """A dimension's small hollow circle, beside its letter (#63).

    Dragged along the line it moves the letter (past the arrowheads
    too); across the line it moves the line; snapped as corners are,
    the whole drag one change.

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its dimension's index in the drawing.
    * `before` (`Snapshot | None`): The drawing when a drag began.
    """

    # Method `DimensionHandle.__init__()`:
    def __init__(self, editor: "OutlineView", index: int) -> None:
        """Make the circle of one dimension.

        Arguments:
        * `editor` (`OutlineView`): The view it is drawn in.
        * `index` (`int`): Its dimension's index in the drawing.
        """
        half: float = HANDLE_PIXELS / 2.0
        super().__init__(-half, -half, HANDLE_PIXELS, HANDLE_PIXELS)
        self.editor: OutlineView = editor
        self.index: int = index
        self.before: Snapshot | None = None
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setZValue(1.5)

    # Method `DimensionHandle.place()`:
    def place(self) -> None:
        """Sit on the line, where the letter is."""
        self.setPos(self.editor.measures[self.index].at())

    # Method `DimensionHandle.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Select the dimension; get ready to move it."""
        self.editor.select_dimension(self.index)
        self.before = self.editor.drawing.snapshot()
        event.accept()

    # Method `DimensionHandle.mouseMoveEvent()`:
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Move the letter along the line, and the line across."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        where: QPointF = event.scenePos()
        free: bool = not self.editor.snap_on or bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        if not free:
            where = snap(where, self.editor.step())
        measure: DimensionItem = self.editor.measures[self.index]
        start: QPointF
        end: QPointF
        measure.prepareGeometryChange()
        if dimension.kind == ANGLE:
            self.drag_angle(dimension, where)
            measure.update()
            self.place()
            return
        _, _, start, end = measure.ends()
        if dimension.kind == HORIZONTAL:
            dimension.offset = where.y()
            span: float = end.x() - start.x()
            if span != 0.0:
                dimension.along = (where.x() - start.x()) / span
        elif dimension.kind == LENGTH:
            # Along the slant moves the letter; across it, the line.
            first: QPointF = self.editor.point(dimension.start)
            way: QPointF = self.editor.point(dimension.end) - first
            square: float = QPointF.dotProduct(way, way)
            if square != 0.0:
                dimension.along = (
                    QPointF.dotProduct(where - first, way) / square
                )
                dimension.offset = QPointF.dotProduct(
                    where - first, left_of(way)
                )
        else:
            dimension.offset = where.x()
            span = end.y() - start.y()
            if span != 0.0:
                dimension.along = (where.y() - start.y()) / span
        measure.update()
        self.place()

    # Method `DimensionHandle.drag_angle()`:
    def drag_angle(self, dimension: Dimension, where: QPointF) -> None:
        """Move an angle's letter around its arc, and the arc in and
        out (its radius).

        Arguments:
        * `dimension` (`Dimension`): The angle.
        * `where` (`QPointF`): The pointer, in the scene.
        """
        arc: tuple[QPointF, float, float] | None = angle_arc(
            self.editor.drawing.points, dimension
        )
        if arc is None:
            return
        center: QPointF
        start: float
        turn: float
        center, start, turn = arc
        out: QPointF = where - center
        radius: float = math.hypot(out.x(), out.y())
        if radius == 0.0 or turn == 0.0:
            return
        dimension.offset = radius
        past: float = math.degrees(math.atan2(out.y(), out.x())) - start
        past = (past - turn / 2.0 + 180.0) % 360.0 - 180.0 + turn / 2.0
        # The letter stays on the arc, between its arrowheads (#76).
        dimension.along = min(max(past / turn, 0.0), 1.0)

    # Method `DimensionHandle.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, _event: QGraphicsSceneMouseEvent) -> None:
        """End a drag: remember it, if it moved the dimension."""
        if self.before is not None and self.before.dimensions != tuple(
            self.editor.drawing.dimensions
        ):
            self.editor.history.remember(self.before)
        self.before = None


# Class `DimensionItem`:
class DimensionItem(QGraphicsItem):
    """A dimension: thin extension lines, a line with an arrowhead at
    each end, and its letter (#26).

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its dimension's index in the drawing.

    A click on its line selects it; its `DimensionHandle` moves it.
    """

    # Method `DimensionItem.__init__()`:
    def __init__(self, editor: "OutlineView", index: int) -> None:
        """Make the item of one dimension.

        Arguments:
        * `editor` (`OutlineView`): The view it is drawn in.
        * `index` (`int`): Its dimension's index in the drawing.
        """
        super().__init__()
        self.editor: OutlineView = editor
        self.index: int = index
        self.setZValue(0.5)

    # Method `DimensionItem.ends()`:
    def ends(self) -> tuple[QPointF, QPointF, QPointF, QPointF]:
        """Return its two points, then its line's two ends."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        first: QPointF = self.editor.point(dimension.start)
        second: QPointF = self.editor.point(dimension.end)
        if dimension.kind == LENGTH:
            # Parallel to the line between the points, `offset` aside.
            aside: QPointF = left_of(second - first) * dimension.offset
            return first, second, first + aside, second + aside
        if dimension.kind == HORIZONTAL:
            return (
                first,
                second,
                QPointF(first.x(), dimension.offset),
                QPointF(second.x(), dimension.offset),
            )
        return (
            first,
            second,
            QPointF(dimension.offset, first.y()),
            QPointF(dimension.offset, second.y()),
        )

    # Method `DimensionItem.shape()`:
    def shape(self) -> QPainterPath:
        """Return a band along its line, `SQUARE_PIXELS` wide, so only
        a click near the line grabs it."""
        path: QPainterPath = QPainterPath()
        if self.index >= len(self.editor.drawing.dimensions):
            return path
        if self.editor.drawing.dimensions[self.index].kind == ANGLE:
            path = self.arc_path()
        else:
            start: QPointF
            end: QPointF
            _, _, start, end = self.ends()
            path.moveTo(start)
            path.lineTo(end)
        stroker: QPainterPathStroker = QPainterPathStroker()
        stroker.setWidth(SQUARE_PIXELS / max(self.editor.zoom(), 1e-12))
        return stroker.createStroke(path)

    # Method `DimensionItem.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Select the dimension (its circle moves it, #64)."""
        self.editor.select_dimension(self.index)
        event.accept()

    # Method `DimensionItem.at()`:
    def at(self) -> QPointF:
        """Return the point of its line where the letter sits."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        if dimension.kind == ANGLE:
            return self.arc_point(dimension.along)
        start: QPointF
        end: QPointF
        _, _, start, end = self.ends()
        return start + (end - start) * dimension.along

    # Method `DimensionItem.boundingRect()`:
    def boundingRect(self) -> QRectF:
        """Return a box around its lines, with room for the letter."""
        # Qt may ask while the item is being removed, its dimension
        # already gone (an undo).
        if self.index >= len(self.editor.drawing.dimensions):
            return QRectF()
        margin: float = 40.0 / max(self.editor.zoom(), 1e-12)
        if self.editor.drawing.dimensions[self.index].kind == ANGLE:
            # Its arc, and the extension lines out to it.
            return (
                self.arc_path()
                .boundingRect()
                .united(self.reach_path().boundingRect())
                .adjusted(-margin, -margin, margin, margin)
            )
        corners: tuple[QPointF, QPointF, QPointF, QPointF] = self.ends()
        xs: list[float] = [corner.x() for corner in corners]
        ys: list[float] = [corner.y() for corner in corners]
        return QRectF(
            min(xs) - margin,
            min(ys) - margin,
            max(xs) - min(xs) + 2.0 * margin,
            max(ys) - min(ys) + 2.0 * margin,
        )

    # Method `DimensionItem.paint()`:
    def paint(
        self,
        painter: QPainter,
        _option: QStyleOptionGraphicsItem,
        _widget: QWidget | None = None,
    ) -> None:
        """Draw the extension lines, the line, its arrows and letter."""
        # Thin cosmetic lines, red for a dimension one too many.
        extra: bool = self.index in self.editor.solution.extra
        ink: QColor = QColor(
            theme.colors().problem if extra else theme.colors().ink
        )
        if self.index in self.editor.chosen_dimensions:
            ink = self.editor.palette().highlight().color()
        pen: QPen = QPen(ink, THIN_PIXELS)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(ink)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale: float = max(abs(painter.worldTransform().m11()), 1e-12)
        if self.editor.drawing.dimensions[self.index].kind == ANGLE:
            self.paint_angle(painter, scale)
            return
        first: QPointF
        second: QPointF
        start: QPointF
        end: QPointF
        first, second, start, end = self.ends()

        # Each extension line runs from its point a little past the
        # dimension line.
        point: QPointF
        foot: QPointF
        for point, foot in ((first, start), (second, end)):
            past: QPointF = foot - point
            length: float = (past.x() ** 2 + past.y() ** 2) ** 0.5
            if length > 0.0:
                past = past * (OVERSHOOT_PIXELS / scale / length)
            painter.drawLine(point, foot + past)

        # The line, an arrowhead at each end pointing out to its
        # extension line.
        painter.drawLine(start, end)
        self.draw_reach(painter, start, end)
        arrow: float = ARROW_PIXELS / scale
        painter.drawPath(arrowhead(end, start, arrow))
        painter.drawPath(arrowhead(start, end, arrow))

        self.draw_letter(painter, start, end)

    # Method `DimensionItem.arc_point()`:
    def arc_point(self, share: float) -> QPointF:
        """Return a point of an angle's arc (the crossing, for
        parallel edges).

        Arguments:
        * `share` (`float`): How far along the arc, 0 at the first
          edge, 1 at the second.

        Returns:
        * (`QPointF`): The point.
        """
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        arc: tuple[QPointF, float, float] | None = angle_arc(
            self.editor.drawing.points, dimension
        )
        if arc is None:
            return edge_start(self.editor.drawing.points, dimension.start)
        center: QPointF
        start: float
        turn: float
        center, start, turn = arc
        angle: float = math.radians(start + turn * share)
        return center + QPointF(math.cos(angle), math.sin(angle)) * (
            dimension.offset
        )

    # Method `DimensionItem.arc_path()`:
    def arc_path(self) -> QPainterPath:
        """Return an angle's arc as a path (empty for parallel edges)."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        path: QPainterPath = QPainterPath()
        if angle_arc(self.editor.drawing.points, dimension) is None:
            return path
        path.moveTo(self.arc_point(0.0))
        step: int
        for step in range(1, ARC_STEPS + 1):
            path.lineTo(self.arc_point(step / ARC_STEPS))
        return path

    # Method `DimensionItem.reach_path()`:
    def reach_path(self) -> QPainterPath:
        """Return an angle's extension lines: along each edge's line,
        from the edge's far end out to the arc, where the arc is past
        it."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        points: list[tuple[float, float]] = self.editor.drawing.points
        path: QPainterPath = QPainterPath()
        arc: tuple[QPointF, float, float] | None = angle_arc(points, dimension)
        if arc is None:
            return path
        center: QPointF = arc[0]
        edge: int
        share: float
        for edge, share in ((dimension.start, 0.0), (dimension.end, 1.0)):
            if edge in AXES:
                continue  # Drawn right across the window already.
            tip: QPointF = self.arc_point(share)
            ray: QPointF = tip - center
            ends: list[QPointF] = [
                QPointF(*points[edge]),
                QPointF(*points[(edge + 1) % len(points)]),
            ]
            reach: float = max(
                QPointF.dotProduct(end - center, ray) for end in ends
            ) / max(QPointF.dotProduct(ray, ray), 1e-24)
            if reach < 1.0:
                path.moveTo(center + ray * max(reach, 0.0))
                path.lineTo(tip)
        return path

    # Method `DimensionItem.paint_angle()`:
    def paint_angle(self, painter: QPainter, scale: float) -> None:
        """Draw an angle: its arc with an arrowhead at each end, the
        extension lines out to it, and its letter.

        Arguments:
        * `painter` (`QPainter`): What draws, pen and brush set.
        * `scale` (`float`): Pixels per drawing step.
        """
        arc: QPainterPath = self.arc_path()
        if arc.isEmpty():
            return
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(arc)
        painter.drawPath(self.reach_path())
        painter.setBrush(painter.pen().color())
        arrow: float = ARROW_PIXELS / scale
        near: float = 1.0 / ARC_STEPS
        painter.drawPath(
            arrowhead(self.arc_point(near), self.arc_point(0.0), arrow)
        )
        painter.drawPath(
            arrowhead(self.arc_point(1.0 - near), self.arc_point(1.0), arrow)
        )
        self.draw_letter(painter, self.at(), self.at())

    # Method `DimensionItem.draw_reach()`:
    def draw_reach(
        self, painter: QPainter, start: QPointF, end: QPointF
    ) -> None:
        """Draw the line on past an arrowhead, out to a letter there.

        Arguments:
        * `painter` (`QPainter`): What draws, in scene coordinates.
        * `start` (`QPointF`): One end of the dimension line.
        * `end` (`QPointF`): The other end.
        """
        along: float = self.editor.drawing.dimensions[self.index].along
        if along < 0.0:
            painter.drawLine(start, self.at())
        elif along > 1.0:
            painter.drawLine(end, self.at())

    # Method `DimensionItem.draw_letter()`:
    def draw_letter(
        self, painter: QPainter, start: QPointF, end: QPointF
    ) -> None:
        """Draw the letter, upright, beside its point of the line, on
        the side `letter_side()` gives.

        Arguments:
        * `painter` (`QPainter`): What draws, in scene coordinates.
        * `start` (`QPointF`): One end of the dimension line.
        * `end` (`QPointF`): The other end.
        """
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        world: QTransform = painter.worldTransform()
        middle: QPointF = world.map(start + (end - start) * dimension.along)
        side: QPointF = self.letter_side(world) * (
            LETTER_POINTS + LETTER_GAP_PIXELS
        )
        painter.save()
        painter.resetTransform()
        font: QFont = QFont("sans-serif", LETTER_POINTS)
        font.setBold(True)
        painter.setFont(font)
        box: QRectF = QRectF(middle.x() - 50.0, middle.y() - 40.0, 100.0, 80.0)
        box.translate(side)
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, dimension.letter)
        painter.restore()

    # Method `DimensionItem.letter_side()`:
    def letter_side(self, world: QTransform) -> QPointF:
        """Return which way, on screen, the letter sits from its line.

        Horizontal and vertical ones go away from the outline's
        middle, so the letter stays off the outline; a length goes on
        the side its line was moved to.

        Arguments:
        * `world` (`QTransform`): The scene to screen transform.

        Returns:
        * (`QPointF`): A unit vector in screen pixels (Y down).
        """
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        xs: list[float] = [x for x, _ in self.editor.drawing.points]
        ys: list[float] = [y for _, y in self.editor.drawing.points]
        if dimension.kind == HORIZONTAL:
            below: bool = dimension.offset < (min(ys) + max(ys)) / 2.0
            return QPointF(0.0, 1.0 if below else -1.0)
        if dimension.kind == ANGLE:
            arc: tuple[QPointF, float, float] | None = angle_arc(
                self.editor.drawing.points, dimension
            )
            if arc is None:
                return QPointF(0.0, 0.0)
            out_of: QPointF = world.map(self.at()) - world.map(arc[0])
            length: float = math.hypot(out_of.x(), out_of.y())
            return out_of / length if length > 0.0 else out_of
        if dimension.kind == LENGTH:
            way: QPointF = world.map(
                self.editor.point(dimension.end)
            ) - world.map(self.editor.point(dimension.start))
            # The screen's Y is down: flip, turn left, flip back.
            out: QPointF = left_of(QPointF(way.x(), -way.y()))
            sign: float = 1.0 if dimension.offset >= 0.0 else -1.0
            return QPointF(out.x(), -out.y()) * sign
        left: bool = dimension.offset < (min(xs) + max(xs)) / 2.0
        return QPointF(-1.0 if left else 1.0, 0.0)


# Class `OutlineView`:
# A view holds the drawing's state as well as its items, and Qt's
# event handlers count as public methods.
# pylint: disable-next=too-many-instance-attributes,too-many-public-methods
class OutlineView(QGraphicsView):
    """The drawing area: grid, axes, origin, outline and squares.

    Attributes:
    * `drawing` (`Drawing`): The outline being drawn.
    * `grid_shown` (`bool`): Whether the grid is drawn.
    * `history` (`History`): What undo and redo go back and forth in.
    * `message` (`str`): The last refusal, for the mode bar.
    * `chosen_points` (`list[int]`):
      The selected points (`ORIGIN` or corners), in the order clicked.
    * `chosen_dimensions` (`list[int]`): The selected dimensions.
    * `chosen_edges` (`list[int]`): The selected edges (by the corner
      each leaves), in the order clicked.
    * `wanted` (`bool`): Whether [Dimension] waits for points.
    * `pan_from` (`QPoint | None`):
      Where the pointer was, while empty space is dragged.
    * `letters_changed` (`Callable[[], None]`):
      Called after a new dimension adds a letter (the window sets it).
    * `released` (`Callable[[], None]`):
      Called after a mouse button comes up (the window saves).
    * `origin` (`QGraphicsRectItem`): The origin's square.
    * `outline` (`OutlineItem`): The outline.
    * `snap_on` (`bool`): Whether drags snap to the grid.
    * `squares` (`list[PullSquare]`): The corners' squares.
    * `measures` (`list[DimensionItem]`): The dimensions' items.
    * `handles` (`list[EdgeHandle]`): The edges' handles.
    * `circles` (`list[DimensionHandle]`): The dimensions' circles.
    * `solution` (`Solution`): The corners' formulas, and what is
      amiss.
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
        self.chosen_points: list[int] = []
        self.chosen_dimensions: list[int] = []
        self.chosen_edges: list[int] = []
        self.wanted: bool = False
        self.letters_changed: Callable[[], None] = self.update
        self.released: Callable[[], None] = self.update
        self.snap_on: bool = True
        scene: QGraphicsScene = QGraphicsScene(self)
        scene.setSceneRect(QRectF(-1e6, -1e6, 2e6, 2e6))
        # No spatial index: a deletion changes the boxes of the items
        # it removes, so an index loses them and keeps a dangling
        # pointer (a segmentation fault after a dimension's drag).  A
        # drawing has only a few dozen items.
        scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        self.setScene(scene)

        # Y up; zoom about the pointer; drag empty space to pan.
        self.scale(1.0, -1.0)
        anchor: QGraphicsView.ViewportAnchor = (
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setTransformationAnchor(anchor)
        # Panned by hand (`pan_from`), so the pointer stays an arrow
        # for aiming; a closed hand only while panning (#55).
        self.pan_from: QPoint | None = None
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
        self.handles: list[EdgeHandle] = []
        self.circles: list[DimensionHandle] = []
        self.measures: list[DimensionItem] = []
        self.solution: Solution = solve(drawing.points, drawing.dimensions)
        self.make_squares()
        self.resize(800, 600)
        self.fit()

    # Method `OutlineView.make_squares()`:
    def make_squares(self) -> None:
        """Put a square on each corner, in place of any there were.

        The selection is cleared, as the indices may have changed.
        """
        self.chosen_points = []
        self.chosen_dimensions = []
        self.chosen_edges = []
        square: PullSquare
        for square in self.squares:
            self.scene().removeItem(square)
        self.squares = []
        index: int
        for index in range(len(self.drawing.points)):
            square = PullSquare(self, index)
            self.scene().addItem(square)
            self.squares.append(square)
        handle: EdgeHandle
        for handle in self.handles:
            self.scene().removeItem(handle)
        self.handles = [
            EdgeHandle(self, index)
            for index in range(len(self.drawing.points))
        ]
        for handle in self.handles:
            self.scene().addItem(handle)
        measure: DimensionItem
        for measure in self.measures:
            self.scene().removeItem(measure)
        self.measures = [
            DimensionItem(self, index)
            for index in range(len(self.drawing.dimensions))
        ]
        for measure in self.measures:
            self.scene().addItem(measure)
        circle: DimensionHandle
        for circle in self.circles:
            self.scene().removeItem(circle)
        self.circles = [
            DimensionHandle(self, index)
            for index in range(len(self.drawing.dimensions))
        ]
        for circle in self.circles:
            self.scene().addItem(circle)
        self.outline.refresh()
        self.follow()

    # Method `OutlineView.point()`:
    def point(self, which: int) -> QPointF:
        """Return a point of a dimension, as drawn.

        Arguments:
        * `which` (`int`): `ORIGIN` or a corner's index.

        Returns:
        * (`QPointF`): Where it is.
        """
        if which == ORIGIN:
            return QPointF(0.0, 0.0)
        return QPointF(*self.drawing.points[which])

    # Method `OutlineView.select_point()`:
    def select_point(self, which: int) -> None:
        """Add a point to the selection (as the latest, if it was in).

        When [Dimension] is waiting for points and two are now
        selected, the dimension is made.

        Arguments:
        * `which` (`int`): `ORIGIN` or a corner's index.
        """
        if which in self.chosen_points:
            self.chosen_points.remove(which)
        self.chosen_points.append(which)
        self.message = ""
        if self.wanted:
            self.dimension_selected()
        self.restyle()

    # Method `OutlineView.select_dimension()`:
    def select_dimension(self, index: int) -> None:
        """Add a dimension to the selection.

        Arguments:
        * `index` (`int`): The dimension.
        """
        if index not in self.chosen_dimensions:
            self.chosen_dimensions.append(index)
        self.message = ""
        self.restyle()

    # Method `OutlineView.select_edge()`:
    def select_edge(self, index: int) -> None:
        """Add an edge to the selection (as the latest, if it was in).

        Arguments:
        * `index` (`int`): The corner the edge leaves.
        """
        if index in self.chosen_edges:
            self.chosen_edges.remove(index)
        self.chosen_edges.append(index)
        self.message = ""
        self.restyle()

    # Method `OutlineView.clear_selection()`:
    def clear_selection(self) -> None:
        """Select nothing, and stop waiting for points to dimension."""
        self.chosen_points = []
        self.chosen_dimensions = []
        self.chosen_edges = []
        self.wanted = False
        self.restyle()

    # Method `OutlineView.dimension_between()`:
    def dimension_between(
        self, first: int, second: int, kind: str = ""
    ) -> None:
        """Add a dimension with a new letter between two points.

        Unless given, it is horizontal when the points are further
        apart in X than in Y, else vertical; its line sits two grid
        steps past them.

        Arguments:
        * `first` (`int`): `ORIGIN` or a corner's index.
        * `second` (`int`): The other point.
        * `kind` (`str`): `HORIZONTAL` or `VERTICAL`; empty to choose.
        """
        start: QPointF = self.point(first)
        end: QPointF = self.point(second)
        across: float = abs(end.x() - start.x())
        up: float = abs(end.y() - start.y())
        if not kind:
            kind = HORIZONTAL if across >= up else VERTICAL
        letter: Letter = next_letter(self.drawing.letters)
        self.history.remember(self.drawing.snapshot())
        self.drawing.letters.append(letter)
        self.drawing.dimensions.append(
            Dimension(
                letter.letter,
                kind,
                first,
                second,
                self.offset_for(kind, first, second),
            )
        )
        self.message = ""
        self.make_squares()
        # Selected, so [Dim. Kind] acts on it straight away.
        self.chosen_dimensions = [len(self.drawing.dimensions) - 1]
        self.restyle()
        self.letters_changed()

    # Method `OutlineView.offset_for()`:
    def offset_for(self, kind: str, first: int, second: int) -> float:
        """Return where a new dimension's line goes: two grid steps
        below its points (horizontal), right of them (vertical), or
        aside from them, away from the outline (length).

        Arguments:
        * `kind` (`str`): `HORIZONTAL`, `VERTICAL` or `LENGTH`.
        * `first` (`int`): `ORIGIN` or a corner's index.
        * `second` (`int`): The other point.

        Returns:
        * (`float`): The line's Y (horizontal) or X (vertical).
        """
        start: QPointF = self.point(first)
        end: QPointF = self.point(second)
        gap: float = 2.0 * self.step()
        if kind == HORIZONTAL:
            return min(start.y(), end.y()) - gap
        if kind == LENGTH:
            # On the side away from the outline's middle.
            xs: list[float] = [x for x, _ in self.drawing.points]
            ys: list[float] = [y for _, y in self.drawing.points]
            middle: QPointF = QPointF(
                (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
            )
            away: QPointF = (start + end) / 2.0 - middle
            left: float = QPointF.dotProduct(away, left_of(end - start))
            return gap if left >= 0.0 else -gap
        return max(start.x(), end.x()) + gap

    # Method `OutlineView.cycle_kind()`:
    def cycle_kind(self) -> None:
        """[Dim. Kind]: turn each selected dimension to its next kind
        (horizontal, length, vertical, then horizontal again), as one
        change.  Each kind keeps its own place: the line and letter go
        back to where they were last time it was that kind, or the
        first time to where a new one would go (#29)."""
        if not self.chosen_dimensions:
            self.message = "Select dimensions to change their kind."
            self.scene().update()
            return
        self.history.remember(self.drawing.snapshot())
        index: int
        for index in self.chosen_dimensions:
            dimension: Dimension = self.drawing.dimensions[index]
            if dimension.kind == ANGLE:
                continue  # Its four arcs: not yet.
            self.measures[index].prepareGeometryChange()
            kind: str = NEXT_KIND[dimension.kind]
            dimension.become(
                kind, self.offset_for(kind, dimension.start, dimension.end)
            )
        self.message = ""
        chosen: list[int] = list(self.chosen_dimensions)
        self.make_squares()
        self.chosen_dimensions = chosen
        self.restyle()

    # Method `OutlineView.mousePressEvent()`:
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Select the origin or clear the selection, then pan, when
        no corner or dimension takes the press."""
        super().mousePressEvent(event)
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.scene().mouseGrabberItem() is None
        ):
            axis: int = self.axis_at(event.position().toPoint())
            if self.origin in self.items(event.position().toPoint()):
                self.select_point(ORIGIN)
            elif axis in AXES:
                self.select_edge(axis)
            else:
                self.clear_selection()
            self.pan_from = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)

    # Method `OutlineView.axis_at()`:
    def axis_at(self, where: QPoint) -> int:
        """Return the axis a click is on, within half a square.

        Arguments:
        * `where` (`QPoint`): The click, in the view.

        Returns:
        * (`int`): `X_AXIS`, `Y_AXIS`, or `ORIGIN` for neither.
        """
        point: QPointF = self.mapToScene(where)
        near: float = SQUARE_PIXELS / 2.0 / max(self.zoom(), 1e-12)
        if abs(point.y()) <= near:
            return X_AXIS
        if abs(point.x()) <= near:
            return Y_AXIS
        return ORIGIN

    # Method `OutlineView.mouseMoveEvent()`:
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """While panning, move the view with the pointer."""
        if self.pan_from is None:
            super().mouseMoveEvent(event)
            return
        moved: QPoint = event.position().toPoint() - self.pan_from
        self.pan_from = event.position().toPoint()
        horizontal = self.horizontalScrollBar()
        vertical = self.verticalScrollBar()
        horizontal.setValue(horizontal.value() - moved.x())
        vertical.setValue(vertical.value() - moved.y())

    # Method `OutlineView.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """End a pan (the pointer an arrow again), or pass it on; then
        tell the window (a drag may have ended)."""
        if self.pan_from is not None:
            self.pan_from = None
            self.viewport().unsetCursor()
            return
        super().mouseReleaseEvent(event)
        self.released()

    # Method `OutlineView.mouseDoubleClickEvent()`:
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Take a quick second click as a click, so none is lost."""
        self.mousePressEvent(event)

    # Method `OutlineView.add_dimension()`:
    def add_dimension(self, dimension: Dimension) -> None:
        """Add a dimension (undone as one change).

        Arguments:
        * `dimension` (`Dimension`): The new dimension.
        """
        self.history.remember(self.drawing.snapshot())
        self.drawing.dimensions.append(dimension)
        self.make_squares()

    # Method `OutlineView.follow()`:
    def follow(self) -> None:
        """Solve again, then draw the dimensions and squares to match."""
        self.solution = solve(self.drawing.points, self.drawing.dimensions)
        measure: DimensionItem
        for measure in self.measures:
            measure.prepareGeometryChange()
        self.drawing.follow_angles()
        for measure in self.measures:
            measure.update()
        self.place_handles()
        self.restyle()

    # Method `OutlineView.place_handles()`:
    def place_handles(self) -> None:
        """Put each edge's handle in its middle (shown if long enough)."""
        handle: EdgeHandle
        for handle in self.handles:
            handle.place()
        circle: DimensionHandle
        for circle in self.circles:
            circle.place()

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
        self.history.remember(self.drawing.snapshot())
        self.drawing.insert(index + 1, ((x0 + x1) / 2.0, (y0 + y1) / 2.0))
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
        self.history.remember(self.drawing.snapshot())
        self.drawing.remove(index)
        self.message = ""
        self.make_squares()

    # Method `OutlineView.delete_selected()`:
    def delete_selected(self) -> None:
        """Delete the selected corners and dimensions, as one change.

        A letter goes with its dimension, unless another one still
        uses it.  An outline keeps at least `LEAST_CORNERS` corners.
        """
        corners: list[int] = sorted(
            (point for point in self.chosen_points if point != ORIGIN),
            reverse=True,
        )
        if not corners and not self.chosen_dimensions:
            self.message = "Select corners or dimensions to delete."
            self.scene().update()
            return
        if len(self.drawing.points) - len(corners) < LEAST_CORNERS:
            self.message = (
                f"An outline needs at least {LEAST_CORNERS} corners."
            )
            self.scene().update()
            return
        self.history.remember(self.drawing.snapshot())
        gone: set[str] = {
            self.drawing.dimensions[index].letter
            for index in self.chosen_dimensions
        }
        index: int
        for index in sorted(self.chosen_dimensions, reverse=True):
            del self.drawing.dimensions[index]
        for index in corners:
            gone |= {
                dimension.letter
                for dimension in self.drawing.dimensions
                if index in (dimension.start, dimension.end)
            }
            self.drawing.remove(index)
        used: set[str] = {
            dimension.letter for dimension in self.drawing.dimensions
        }
        self.drawing.letters[:] = [
            letter
            for letter in self.drawing.letters
            if letter.letter not in gone or letter.letter in used
        ]
        self.message = ""
        self.make_squares()
        self.letters_changed()

    # Method `OutlineView.dimension_selected()`:
    def dimension_selected(self) -> None:
        """Dimension the last two points clicked, in that order.

        With fewer, wait for the rest: the next clicks make it.  An
        axis and a corner (#80): a dimension from the axis, that is,
        from the origin across it (vertical from the X axis).
        """
        axes: list[int] = [edge for edge in self.chosen_edges if edge in AXES]
        corners: list[int] = [
            point for point in self.chosen_points if point != ORIGIN
        ]
        if axes and corners and len(self.chosen_points) < 2:
            self.wanted = False
            self.dimension_between(
                ORIGIN,
                corners[-1],
                VERTICAL if axes[-1] == X_AXIS else HORIZONTAL,
            )
            return
        if len(self.chosen_points) < 2:
            self.wanted = True
            self.message = (
                "Click a second point."
                if self.chosen_points
                else "Click two points to dimension."
            )
            self.scene().update()
            return
        self.wanted = False
        first: int
        second: int
        first, second = self.chosen_points[-2:]
        if self.point(first) == self.point(second):
            self.message = "Those two points are in the same place."
            self.scene().update()
            return
        self.dimension_between(first, second)

    # Method `OutlineView.angle_selected()`:
    def angle_selected(self) -> None:
        """[Angle]: an angle between the last two edges clicked, its
        letter's default the angle as drawn, to a whole degree."""
        if len(self.chosen_edges) < 2:
            self.message = "Click two edges' circles for an angle."
            self.scene().update()
            return
        first: int
        second: int
        first, second = self.chosen_edges[-2:]
        if first in AXES and second in AXES:
            self.message = "The axes are 90 deg apart: pick an edge."
            self.scene().update()
            return
        rays: tuple[int, int] | None = middle_rays(
            self.drawing.points, first, second
        )
        if rays is None:
            self.message = "Those edges are parallel: no angle."
            self.scene().update()
            return

        # The rays toward the edges' middles fix the sector (#53);
        # measured counterclockwise from the edge that makes it under
        # 180 degrees, so the value is positive (#57).
        arc: tuple[QPointF, float, float] | None = edge_arc(
            self.drawing.points, first, second, rays
        )
        assert arc is not None  # Not parallel: `rays` were found.
        turn: float = arc[2]
        if turn > 180.0:
            first, second = second, first
            rays = (rays[1], rays[0])
            turn = 360.0 - turn
        # The arc halfway to the nearer edge's middle.
        reach: float = min(
            math.hypot(middle.x(), middle.y())
            for middle in (
                edge_start(self.drawing.points, edge)
                + edge_way(self.drawing.points, edge) / 2.0
                - arc[0]
                for edge in (first, second)
                if edge not in AXES
            )
        )
        letter: Letter = replace(
            next_letter(self.drawing.letters), default=f"{round(turn)} deg"
        )
        self.history.remember(self.drawing.snapshot())
        self.drawing.letters.append(letter)
        self.drawing.dimensions.append(
            Dimension(
                letter.letter,
                ANGLE,
                first,
                second,
                max(reach / 2.0, 2.0 * self.step()),
                rays=rays,
            )
        )
        self.message = ""
        self.make_squares()
        self.chosen_dimensions = [len(self.drawing.dimensions) - 1]
        self.restyle()
        self.letters_changed()

    # Method `OutlineView.toggle_revolve()`:
    def toggle_revolve(self) -> None:
        """[Revolve]: turn revolving about the Y axis on or off, as one
        change; refused while a corner is left of the axis."""
        if not self.drawing.revolve and any(
            x < 0.0 for x, _ in self.drawing.points
        ):
            self.message = (
                "A revolved outline is drawn at X >= 0: move the "
                "corners left of the Y axis first."
            )
            self.scene().update()
            return
        self.history.remember(self.drawing.snapshot())
        self.drawing.revolve = not self.drawing.revolve
        self.message = ""
        self.outline.refresh()
        self.resetCachedContent()
        self.follow()

    # Method `OutlineView.undo()`:
    def undo(self) -> None:
        """Go back to the corners before the last change, if any."""
        self.show_snapshot(self.history.undo(self.drawing.snapshot()))

    # Method `OutlineView.redo()`:
    def redo(self) -> None:
        """Do the last undone change again, if any."""
        self.show_snapshot(self.history.redo(self.drawing.snapshot()))

    # Method `OutlineView.show_snapshot()`:
    def show_snapshot(self, snapshot: Snapshot | None) -> None:
        """Show a snapshot (`None`: leave things as they are).

        Arguments:
        * `snapshot` (`Snapshot | None`): The drawing to show.
        """
        if snapshot is not None:
            self.drawing.restore(snapshot)
            self.message = ""
            self.make_squares()
            self.letters_changed()

    # Method `OutlineView.restyle()`:
    def restyle(self) -> None:
        """Color everything for the scheme in use (light or dark)."""
        scheme: theme.Colors = theme.colors()
        self.setBackgroundBrush(QColor(scheme.paper))
        pen: QPen = QPen(QColor(scheme.ink), THIN_PIXELS)
        pen.setCosmetic(True)
        chosen: QPen = QPen(self.palette().highlight().color(), 3.0)
        chosen.setCosmetic(True)
        self.origin.setPen(chosen if ORIGIN in self.chosen_points else pen)
        self.origin.setBrush(QColor(scheme.ink))
        # A square is yellow (a warning) while its corner is not
        # dimensioned yet (once there are dimensions at all).
        missing: set[int] = {
            corner
            for corner, _ in self.solution.missing(len(self.drawing.points))
        }
        square: PullSquare
        for square in self.squares:
            square.setPen(
                chosen if square.index in self.chosen_points else pen
            )
            loose: bool = bool(self.drawing.dimensions) and (
                square.index in missing
            )
            square.setBrush(QColor(scheme.warning if loose else scheme.paper))
            square.setToolTip(self.corner_tip(square.index))
        self.origin.setToolTip("The origin: (0, 0)")
        # Hollow, so the edge shows through (#60), in ink to be seen; a
        # selected dimension's circle as a selected square.
        ring: QPen = QPen(QColor(scheme.ink), 1.5)
        ring.setCosmetic(True)
        handle: EdgeHandle
        for handle in self.handles:
            handle.setPen(
                chosen if handle.index in self.chosen_edges else ring
            )
        circle: DimensionHandle
        for circle in self.circles:
            circle.setPen(
                chosen if circle.index in self.chosen_dimensions else ring
            )
        self.viewport().update()

    # Method `OutlineView.corner_tip()`:
    def corner_tip(self, index: int) -> str:
        """Return a corner's tooltip: its formulas, `(W - T, H)`.

        A coordinate not reached by a chain of dimensions from the
        origin is under-constrained, shown as `X-Floating` or
        `Y-Floating`.

        Arguments:
        * `index` (`int`): The corner.

        Returns:
        * (`str`): The tooltip's text.
        """
        x: Formula | None = self.solution.x.get(index)
        y: Formula | None = self.solution.y.get(index)
        x_text: str = "X-Floating" if x is None else str(x)
        y_text: str = "Y-Floating" if y is None else str(y)
        return f"({x_text}, {y_text})"

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
        self.place_handles()

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
        self.place_handles()
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

        # The axes, through the origin, past the window's edges: X
        # light red, Y light green, apart from the grid.
        # A selected axis (#63) in the highlight color, thicker.
        lit: QColor = self.palette().highlight().color()
        axis: int
        color: str
        for axis, color in ((X_AXIS, scheme.x_axis), (Y_AXIS, scheme.y_axis)):
            chosen: bool = axis in self.chosen_edges
            pen.setColor(lit if chosen else QColor(color))
            pen.setWidthF(3.0 if chosen else THIN_PIXELS)
            # Revolved: the Y axis is the center line, dash-dot.
            pen.setStyle(
                Qt.PenStyle.DashDotLine
                if axis == Y_AXIS and self.drawing.revolve
                else Qt.PenStyle.SolidLine
            )
            painter.setPen(pen)
            if axis == X_AXIS:
                painter.drawLine(
                    QPointF(rect.left(), 0.0), QPointF(rect.right(), 0.0)
                )
            else:
                painter.drawLine(
                    QPointF(0.0, rect.top()), QPointF(0.0, rect.bottom())
                )

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


# Class `LiveDelegate`:
class LiveDelegate(QStyledItemDelegate):
    """Edits the letters' cells, keeping each keystroke (#47).

    Attributes:
    * `editor` (`OutlineEditor`): The window whose table it edits.
    """

    # Method `LiveDelegate.__init__()`:
    def __init__(self, editor: "OutlineEditor") -> None:
        """Make the delegate of a window's table.

        Arguments:
        * `editor` (`OutlineEditor`): The window.
        """
        super().__init__(editor.table)
        self.editor: OutlineEditor = editor

    # Method `LiveDelegate.createEditor()`:
    def createEditor(
        self,
        parent: QWidget,
        _option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget:
        """Return an entry that keeps and checks every keystroke."""
        entry: QLineEdit = QLineEdit(parent)
        row: int = index.row()
        column: int = index.column()

        # Function `typed()`:
        def typed(text: str) -> None:
            """Keep the text so far, check it, mark the entry."""
            self.editor.keep(row, column, text)
            cell: QTableWidgetItem | None = self.editor.table.item(row, column)
            problem: str = "" if cell is None else cell.toolTip()
            entry.setToolTip(problem)
            entry.setStyleSheet(
                f"background: {theme.colors().bad}" if problem else ""
            )

        entry.textEdited.connect(typed)
        return entry

    # Method `LiveDelegate.setEditorData()`:
    def setEditorData(
        self,
        editor: QWidget,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        """Fill a fresh entry; never overwrite what is being typed.

        Marking a cell bad changes its data, which would otherwise put
        the cell's old text back into the entry.
        """
        if isinstance(editor, QLineEdit) and editor.isModified():
            return
        super().setEditorData(editor, index)


# Class `OutlineEditor`:
# A window holds its parts and the letters' state.
class OutlineEditor(  # pylint: disable=too-many-instance-attributes
    QWidget
):
    """The editor's window: the mode bar, the drawing, the letters.

    Attributes:
    * `buttons` (`dict[str, QPushButton]`):
      The mode bar's buttons, by their word (`"Grid"`, `"Fit"`, ...).
    * `keys` (`dict[str, QShortcut]`): Each button's key, by its word.
    * `drawing` (`Drawing`): The outline being drawn.
    * `problem` (`str`): The letters' first problem ("" if none).
    * `splitter` (`QSplitter`): The drawing over the table.
    * `status` (`QLabel`): The last refusal, at the bar's end.
    * `table` (`QTableWidget`): The letters, a row each.
    * `view` (`OutlineView`): The drawing area.
    """

    # Method `OutlineEditor.__init__()`:
    def __init__(
        self, drawing: Drawing | None = None, *, path: Path | None = None
    ) -> None:
        """Make the window.

        Arguments:
        * `drawing` (`Drawing | None`):
          The outline to edit (the first triangle when `None`).
        * `path` (`Path | None`): The file it is kept in, rewritten
          after every change (#90); `None` keeps nothing.
        """
        super().__init__()
        self.drawing: Drawing = Drawing() if drawing is None else drawing
        self.path: Path | None = path
        self.saved: str = file_text(path)
        self.setWindowTitle(
            "Outline Editor" if path is None else f"Outline Editor: {path}"
        )
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view: OutlineView = OutlineView(self.drawing)

        # The mode bar: each button shows its key (#20).
        mode_bar: QHBoxLayout = QHBoxLayout()
        layout.addLayout(mode_bar)

        # The drawing over the letters, a bar between them (#27).
        self.splitter: QSplitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.view)
        self.table: QTableWidget = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([title for title, _ in COLUMNS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setItemDelegate(LiveDelegate(self))
        self.splitter.addWidget(self.table)
        self.splitter.setSizes([450, 150])
        layout.addWidget(self.splitter)
        self.problem: str = ""
        self.buttons: dict[str, QPushButton] = {}
        self.keys: dict[str, QShortcut] = {}
        word: str
        key: str
        for word, key in (
            ("Grid", "G"),
            ("Snap", "S"),
            ("Delete", "Del"),
            ("Dimension", "N"),
            ("Dim. Kind", "K"),
            ("Angle", "A"),
            ("Revolve", "R"),
            ("Fit", "F"),
            ("Undo", "Ctrl+Z"),
            ("Redo", "Ctrl+Shift+Z"),
            ("New Letter", "L"),
        ):
            # [Dim. Kind] cycles, so it shows a cycle arrow (U+21BB).
            cycle: str = " \u21bb" if word == "Dim. Kind" else ""
            button: QPushButton = QPushButton(f"{word}{cycle} ({key})")
            # A button's own shortcut never fired; a `QShortcut` does.
            shortcut: QShortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(button.click)
            self.keys[word] = shortcut
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            mode_bar.addWidget(button)
            self.buttons[word] = button
        for word in ("Grid", "Snap"):
            self.buttons[word].setCheckable(True)
            self.buttons[word].setChecked(True)
        self.buttons["Revolve"].setCheckable(True)
        # What each button does.
        does: dict[str, Callable[[], None]] = {
            "Grid": self.view.toggle_grid,
            "Snap": self.toggle_snap,
            "Fit": self.view.fit,
            "Delete": self.view.delete_selected,
            "Dimension": self.view.dimension_selected,
            "Dim. Kind": self.view.cycle_kind,
            "Angle": self.view.angle_selected,
            "Revolve": self.toggle_revolve,
            "Undo": self.view.undo,
            "Redo": self.view.redo,
            "New Letter": self.new_letter,
        }
        action: Callable[[], None]
        for word, action in does.items():
            self.buttons[word].clicked.connect(action)
        self.status: QLabel = QLabel("")
        mode_bar.addWidget(self.status, 1)
        self.view.scene().changed.connect(self.show_message)
        self.view.letters_changed = self.fill_table
        self.view.released = self.save
        self.fill_table()
        self.table.itemChanged.connect(self.letter_edited)
        self.show_message()
        self.resize(800, 600)

    # Method `OutlineEditor.fill_table()`:
    def fill_table(self) -> None:
        """Show every letter, a row each, its problems marked."""
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.drawing.letters))
        row: int
        letter: Letter
        for row, letter in enumerate(self.drawing.letters):
            column: int
            attribute: str
            for column, (_, attribute) in enumerate(COLUMNS):
                self.table.setItem(
                    row, column, QTableWidgetItem(getattr(letter, attribute))
                )
        self.table.blockSignals(False)
        self.check_letters()

    # Method `OutlineEditor.new_letter()`:
    def new_letter(self) -> None:
        """Add a row for the first free letter, ready to be named."""
        self.drawing.letters.append(next_letter(self.drawing.letters))
        self.fill_table()
        row: int = len(self.drawing.letters) - 1
        self.table.setCurrentCell(row, 1)

    # Method `OutlineEditor.letter_edited()`:
    def letter_edited(self, item: QTableWidgetItem) -> None:
        """Keep a finished cell's text in its letter, then check them.

        Arguments:
        * `item` (`QTableWidgetItem`): The cell.
        """
        self.keep(item.row(), item.column(), item.text())

    # Method `OutlineEditor.keep()`:
    def keep(self, row: int, column: int, text: str) -> None:
        """Keep a cell's text in its letter, then check the letters.

        Arguments:
        * `row` (`int`): The letter's row.
        * `column` (`int`): The cell's column (see `COLUMNS`).
        * `text` (`str`): The cell's text so far.
        """
        attribute: str = COLUMNS[column][1]
        setattr(self.drawing.letters[row], attribute, text.strip())
        self.check_letters()
        self.save()

    # Method `OutlineEditor.check_letters()`:
    def check_letters(self) -> None:
        """Mark each bad letter or default, and show the first problem."""
        self.table.blockSignals(True)
        bad: QColor = QColor(theme.colors().bad)
        problems: list[str] = []
        row: int
        letter: Letter
        for row, letter in enumerate(self.drawing.letters):
            kinds: set[str] = {
                "angle" if dimension.kind == ANGLE else "length"
                for dimension in self.drawing.dimensions
                if dimension.letter == letter.letter
            }
            found: str
            column: int
            for found, column in (
                (letter_problem(self.drawing.letters, row), 0),
                (
                    value_problem(letter.default)
                    or use_problem(letter.letter, letter.default, kinds),
                    2,
                ),
            ):
                cell: QTableWidgetItem | None = self.table.item(row, column)
                if cell is not None:
                    cell.setBackground(bad if found else QColor(0, 0, 0, 0))
                    cell.setToolTip(found)
                if found:
                    problems.append(f"{letter.letter}: {found}")
        self.table.blockSignals(False)
        self.problem = problems[0] if problems else ""
        self.show_message()

    # Method `OutlineEditor.toggle_snap()`:
    def toggle_snap(self) -> None:
        """Turn snapping on or off, as [Snap] now shows."""
        self.view.snap_on = self.buttons["Snap"].isChecked()

    # Method `OutlineEditor.toggle_revolve()`:
    def toggle_revolve(self) -> None:
        """[Revolve]: revolve or not, the button showing the result
        (a refusal leaves it as it was)."""
        self.view.toggle_revolve()
        self.buttons["Revolve"].setChecked(self.view.drawing.revolve)

    # Method `OutlineEditor.save()`:
    def save(self) -> None:
        """Rewrite the file if the outline changed (not mid-drag: the
        view saves again when the mouse button comes up)."""
        if self.path is None or QApplication.mouseButtons() != (
            Qt.MouseButton.NoButton
        ):
            return
        text: str = outline_text(
            Outline(
                list(self.drawing.points),
                list(self.drawing.letters),
                list(self.drawing.dimensions),
                self.drawing.revolve,
            )
        )
        if text != self.saved:
            self.path.write_text(text, encoding="utf-8")
            self.saved = text

    # Method `OutlineEditor.show_message()`:
    def show_message(self, *_regions: object) -> None:
        """Show the view's last refusal (or nothing) in the mode bar.

        [Undo] and [Redo] are enabled only when there is something to
        undo or redo.
        """
        history: History = self.view.history
        self.buttons["Undo"].setEnabled(bool(history.done))
        self.buttons["Redo"].setEnabled(bool(history.undone))
        # [Revolve] shows the drawing's state (a refusal, an undo).
        self.buttons["Revolve"].setChecked(self.view.drawing.revolve)
        self.save()
        self.status.setText(self.view.message or self.problem)
        self.status.setStyleSheet(f"color: {theme.colors().problem}")


# Function `file_text()`:
def file_text(path: Path | None) -> str:
    """Return what a file holds ("" for none, or none yet).

    Arguments:
    * `path` (`Path | None`): The file.

    Returns:
    * (`str`): Its text.
    """
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


# Function `drawing_from()`:
def drawing_from(path: Path) -> Drawing:
    """Read a drawing from an outline file.

    Arguments:
    * `path` (`Path`): The file.

    Returns:
    * (`Drawing`): Its drawing.

    Raises:
    * `OutlineError`: When the file cannot be read as an outline.
    * `OSError`: When the file cannot be read at all.
    """
    outline: Outline = outline_from_text(
        path.read_text(encoding="utf-8"), str(path)
    )
    return Drawing(
        outline.points, outline.letters, outline.dimensions, outline.revolve
    )


# Function `main()`:
def main() -> None:
    """Show the editor until its window is closed: on the file named
    on the command line, if any (a new one starts as the triangle),
    refusing one that cannot be read (#93)."""
    path: Path | None = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    drawing: Drawing = Drawing()
    if path is not None and path.exists():
        try:
            drawing = drawing_from(path)
        except (OSError, OutlineError) as error:
            print(error, file=sys.stderr)
            sys.exit(1)
    application: QApplication = make_application(headless=False)
    editor: OutlineEditor = OutlineEditor(drawing, path=path)
    theme.follow(application, editor.view.restyle)
    editor.show()
    editor.view.fit()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
