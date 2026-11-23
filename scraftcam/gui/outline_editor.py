#!/usr/bin/env python3
"""The 2D outline editor (`T.oe~6.2`).

A window with X and Y axes, an origin square, a grid that gets finer
as one zooms in (#12, #13), and an outline whose corners are pull
squares, dragged and snapped to the grid (Shift drags freely).  Each
edge ends in a small arrowhead showing the winding, counterclockwise
(#4).  The wheel zooms about the pointer (#3); dragging the origin or
empty space pans the view (#6).  There are no modes (#58): dragging
moves (a corner, a dimension's line); each click adds to the
selection (empty space clears it), and the bar's buttons act on it.
[Dimension (N)] dimensions what is selected (#234): one edge's
length, the angle at one corner, the angle between two edges, or the
last two points clicked, before or after it is pressed (#60).
The buttons sit in tabs of related ones (#319), each with its key,
which works whichever tab is showing; no menus (#11).  [Most Common]:
[Undo (Ctrl+Z)], [Redo (Ctrl+Shift+Z)] (#18, a whole drag being one
change), [Delete (Del)], [Dimension (N)], [Fit (Home)], [Rotate
Diagram (T)].  [Draw]: [Delete], [Dimension], [Dim. Kind \u21bb
(K)], [New Letter (L)], [Revolve (R)].  [View]: [Grid (G)], [Snap
(S)], [Fit], [Overview (O)], [Hide (H)], [Rotate Diagram], [Font +
(])], [Font - ([)] (#273), [Show Marks (M)].  Marks (an edge level
or upright, a corner on an axis) are made by dragging, a corner
snapping onto them (`T.tfo~6.5` #451), and drawn only while [Show
Marks] is on.  The refusals and hints show under the
tabs.  Below the drawing, past a bar dragged up and down, the
letters' table (#27): letter, long name, default value with its
unit, help, each kept and checked at every keystroke.

The scene is in unitless drawing steps (letters give the real sizes,
#15), Y up.  Run alone: `python3 -m scraftcam.gui.outline_editor`.
"""

import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from functools import partial
from pathlib import Path

from ..packages import require

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import (  # noqa: E402
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import (  # noqa: E402
    QAction,
    QBrush,
    QColor,
    QFont,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QShortcut,
    QTransform,
    QWheelEvent,
)
from PySide6.QtSvgWidgets import QSvgWidget  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView,
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionGraphicsItem,
    QStyleOptionViewItem,
    QTabBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..diagram import FONT_STEP, TEXT, Stroke, svg  # noqa: E402
from ..geometry import ArcSegment, LineSegment, XYSegment  # noqa: E402
from . import theme  # noqa: E402
from .dimensions import (  # noqa: E402
    ANGLE,
    AXES,
    DIAMETER,
    HORIZONTAL,
    LENGTH,
    ON_AXIS,
    ORIGIN,
    RADIUS,
    VERTICAL,
    X_AXIS,
    Y_AXIS,
    Dimension,
    Formula,
    Solution,
    is_mark,
    mark_broken,
    mark_edge,
    next_kind,
    placement_problem,
    snapped,
    solve,
    tip_on_origin,
    without_marks,
)
from .hides import (  # noqa: E402
    HIDE_X,
    HIDE_Y,
    Hide,
    across,
    inside_spans,
    lay,
    minus,
    strip,
)
from .letters import (  # noqa: E402
    Letter,
    fillet_kind_problem,
    letter_problem,
    next_letter,
    use_problem,
    value_problem,
)
from .outline_diagram import (  # noqa: E402
    Fillet,
    dimension_strokes,
    fillet_arcs,
    outline_sheet,
    outline_strokes,
    upright_text,
)
from .outline_diagram import edge_arc as shared_arc  # noqa: E402
from .outline_file import (  # noqa: E402
    Hole,
    Outline,
    OutlineError,
    outline_from_text,
    outline_text,
)
from .values import (  # noqa: E402
    crossings,
    fillet_problems,
    formula_problem,
    placed_corners,
    refresh_formulas,
)
from .window import make_application  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order

# Screen sizes, in pixels: a corner circle's width, an arrowhead's length,
# the outline's and the thin lines' widths (#26), and the least gap
# between minor grid lines.
SQUARE_PIXELS: float = 9.0

# How near a dragged corner snaps level, upright or onto an axis, on
# screen (`T.tfo~6.5` #451).
SNAP_PIXELS: float = 6.0

# A lit corner's square (#199) is this much bigger.
LIT_SCALE: float = 1.8
ARROW_PIXELS: float = 9.0


# How many straight pieces draw an angle's arc.
ARC_STEPS: int = 48

THICK_PIXELS: float = 2.0
THIN_PIXELS: float = 1.0
CHOSEN_PIXELS: float = 2.5
GRID_PIXELS: float = 12.0

# Every `MAJOR_EVERY`th grid line is drawn darker.
MAJOR_EVERY: int = 5

# How far one wheel notch (120 eighths of a degree) zooms, and the
# zoom's limits (pixels per drawing step).
ZOOM_PER_NOTCH: float = 1.25
ZOOM_LIMITS: tuple[float, float] = (1e-3, 1e5)

# The note's letter (#120): "All undimensioned fillets are radius UDF",
# and its choice, standing for it before it is made.
NOTE_LETTER: str = "UDF"
NOTE_CHOICE: str = "*note*"

# The tabs over the letters' table: every letter, or only the fillet
# radii (#213).
DIMENSIONS_TAB: int = 0
FILLETS_TAB: int = 1

# The table's first row, shown only in [Fillets]: "No fillet", a
# fixed entry never edited, deleted or saved (#219, #222); the letters
# follow it, letter `i` in row `i + LETTER_ROW`.
LETTER_ROW: int = 1
NO_FILLET: tuple[str, ...] = ("", "No fillet", "0", "", "(No Edit Allowed)")

# The letters' table: its columns, each with its `Letter` field.
COLUMNS: tuple[tuple[str, str], ...] = (
    ("Letter", "letter"),
    ("Name", "name"),
    # Its value (#147); `default` in files, or `= PA / 2`: a formula
    # (`T.tfo~6.5` #430).
    ("Value", "default"),
    ("Fillet", "fillet"),  # A check box: a fillet radius (#213).
    ("Help", "help"),
)

# A dimension's extension lines run this far past its line, and its
# letter sits this far from it (pixels); the letters' size (points).
LETTER_GAP_PIXELS: float = 4.0
LETTER_POINTS: int = 11

# The text height of dimensions and marks drawn through `diagram.py`
# (#S4): their letters, arrowheads that long and marks' boxes, at any
# zoom (#311).
TEXT_PIXELS: float = 14.0

# Each button's word and key (#20); the key works on any tab.
BUTTON_KEYS: tuple[tuple[str, str], ...] = (
    ("Grid", "G"),
    ("Snap", "S"),
    ("Delete", "Del"),
    ("Dimension", "N"),
    ("Dim. Kind", "K"),
    ("Revolve", "R"),
    ("Rotate Diagram", "T"),
    ("Font +", "]"),
    ("Font -", "["),
    ("Hide", "H"),
    ("Overview", "O"),
    ("Fit", "Home"),
    ("Undo", "Ctrl+Z"),
    ("Redo", "Ctrl+Shift+Z"),
    ("New Letter", "L"),
    ("Show Marks", "M"),
)

# The buttons in tabs of related ones (#319), the most used first; a
# button may sit on more than one tab.
BUTTON_TABS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Most Common",
        ("Undo", "Redo", "Delete", "Dimension", "Fit", "Rotate Diagram"),
    ),
    ("Draw", ("Delete", "Dimension", "Dim. Kind", "New Letter", "Revolve")),
    (
        "View",
        (
            "Grid",
            "Snap",
            "Fit",
            "Overview",
            "Hide",
            "Rotate Diagram",
            "Font +",
            "Font -",
            "Show Marks",
        ),
    ),
)

# [Font +] and [Font -] stop this many steps from a letter's start
# (#273): 1.25**6 is about 3.8 times.
FONT_STEPS: int = 6

# Letters' lines are this wide (pixels), a little bolder than the thin
# lines (#316; to be tuned by eye).
TEXT_PEN_PIXELS: float = 1.5

# An edge handle's size, smaller than a corner's circle (#235), and
# the least length on screen of an edge that shows one (pixels).
HANDLE_PIXELS: float = 7.0
GRIP_PIXELS: float = 11.0

# The working view (#170, #172): the gap at a cut, and a long break
# line's zigzag, half its length and its height (pixels).
GAP_PIXELS: float = 20.0
ZIG_HALF_PIXELS: float = 10.0
ZIG_HIGH_PIXELS: float = 6.0

# Half the length of the small S ending a dimension line at a cut.
ESS_PIXELS: float = 9.0

# How far the working view's pieces reach (past any drawing).
FAR: float = 1e6
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
# A snapshot holds every part of the drawing that undo restores, so
# it has as many attributes as the drawing has parts.
@dataclass(frozen=True, slots=True)
class Snapshot:  # pylint: disable=too-many-instance-attributes
    """A drawing's corners and dimensions at one time, for undo.

    Attributes:
    * `points` (`tuple[tuple[float, float], ...]`): The corners.
    * `dimensions` (`tuple[Dimension, ...]`): Copies of the dimensions.
    * `letters` (`tuple[Letter, ...]`): Copies of the letters.
    * `revolve` (`bool`): Whether it is revolved (#32).
    * `note_radius` (`str`): The fillets' note letter (#116).
    * `hides` (`tuple[Hide, ...]`): Copies of the hide strips.
    * `turns` (`int`): Quarter turns clockwise it is shown (#300).
    * `text_height` (`float`): The diagram's letter height (#273).

    Constructor:
    * `Snapshot(points, dimensions, letters, revolve, note_radius,
      hides, turns, text_height)`
    """

    # Constructor arguments:
    points: tuple[tuple[float, float], ...] = field(init=True)
    dimensions: tuple[Dimension, ...] = field(init=True)
    letters: tuple[Letter, ...] = field(init=True)
    revolve: bool = field(init=True, default=False)
    note_radius: str = field(init=True, default="")
    hides: tuple[Hide, ...] = field(init=True, default=())
    turns: int = field(init=True, default=0)
    text_height: float = field(init=True, default=0.0)


# Class `Drawing`:
@dataclass(slots=True)
class Drawing(Outline):
    """The outline being drawn: an `Outline` (what its file holds,
    corners in drawing steps) with the editor's own state.

    Attributes:
    * `points` (`list[tuple[float, float]]`): The corners, in order,
      counterclockwise (the first triangle when none are given).
    * `letters` (`list[Letter]`): The letters naming its sizes.
    * `dimensions` (`list[Dimension]`): The dimensions, by letter.
    * `revolve` (`bool`): Whether it is revolved about the Y axis
      (#32): a round tool, drawn at X >= 0 only.
    * `note_radius` (`str`): The letter of every fillet without a
      radius of its own (#116), "" before the first fillet.
    * `hides` (`list[Hide]`): The hide strips (#157).
    * `text_height` (`float`): The diagram's letter height; 0 picks
      one (#280).
    * `turns` (`int`): Quarter turns clockwise it is shown (#300).
    * `scale` (`float`): Drawing steps per millimeter, once the
      drawing follows the values (#148); 0 before.

    Constructor:
    * `Drawing(points, letters, dimensions, revolve, note_radius,
      hides, text_height, turns)`
    """

    # Remaining attributes (alphabetized):
    scale: float = field(init=False, default=0.0)

    # Method `Drawing.__post_init__()`:
    def __post_init__(self) -> None:
        """Start from the first triangle when no corners are given."""
        if not self.points:
            self.points[:] = triangle()

    # Method `Drawing.snapshot()`:
    def snapshot(self) -> Snapshot:
        """Return the corners and dimensions as they are now."""
        return Snapshot(
            tuple(self.points),
            tuple(replace(dimension) for dimension in self.dimensions),
            tuple(replace(letter) for letter in self.letters),
            self.revolve,
            self.note_radius,
            tuple(replace(hide) for hide in self.hides),
            self.turns,
            self.text_height,
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
        self.note_radius = snapshot.note_radius
        self.hides[:] = [replace(hide) for hide in snapshot.hides]
        self.turns = snapshot.turns
        self.text_height = snapshot.text_height

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
        """Insert a corner; the dimensions and hide strips keep to
        their corners (#446), and a mark on the edge it splits goes
        (#233).

        Arguments:
        * `index` (`int`): Where the new corner goes.
        * `point` (`tuple[float, float]`): The new corner.
        """
        split: int = (index - 1) % len(self.points)
        self.dimensions[:] = [
            dimension
            for dimension in self.dimensions
            if mark_edge(dimension, len(self.points)) != split
        ]
        self.points.insert(index, point)
        dimension: Dimension
        for dimension in self.dimensions:
            if dimension.start >= index:
                dimension.start += 1
            if dimension.end >= index:
                dimension.end += 1
        self.hides[:] = [
            replace(
                hide,
                below=hide.below + (hide.below >= index),
                above=hide.above + (hide.above >= index),
            )
            for hide in self.hides
        ]

    # Method `Drawing.remove()`:
    def remove(self, index: int) -> None:
        """Remove a corner, with the dimensions that measure it and
        the hide strips placed from it (#446).

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
        self.hides[:] = [
            replace(
                hide,
                below=hide.below - (hide.below > index),
                above=hide.above - (hide.above > index),
            )
            for hide in self.hides
            if index not in (hide.below, hide.above)
        ]


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


# Class `CornerCircle`:
class CornerCircle(QGraphicsEllipseItem):
    """A corner's circle (a square until #235), the same size on
    screen at any zoom; where it sits (on a corner, mid-edge) tells
    it from an edge's smaller circle.

    Dragged, it moves its corner, snapped to the grid when [Snap] is
    on and Shift is not held; a click selects it, or while a fillet
    letter is armed fillets its corner (#214).

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its corner's index in the drawing.
    * `before` (`Snapshot | None`):
      The drawing when a drag began (`None` between drags).
    """

    # Method `CornerCircle.__init__()`:
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
        self.setAcceptHoverEvents(True)

    # Method `CornerCircle.hoverEnterEvent()`:
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """Light its corner (and its [Fillets] row, #199)."""
        self.editor.light(self.index)
        super().hoverEnterEvent(event)

    # Method `CornerCircle.hoverLeaveEvent()`:
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """Put its corner out."""
        self.editor.light(-1)
        super().hoverLeaveEvent(event)

    # Method `CornerCircle.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Select its corner, then start a drag."""
        self.editor.select_point(self.index)
        self.before = self.editor.drawing.snapshot()
        self.editor.dragged = self.index
        super().mousePressEvent(event)

    # Method `CornerCircle.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """End a drag: remember it, if it moved the corner; a plain
        click while a letter is armed fillets the corner by it (#214,
        #227), after this event, as it remakes the squares."""
        super().mouseReleaseEvent(event)
        moved: bool = self.before is not None and self.before.points != (
            tuple(self.editor.drawing.points)
        )
        if moved and self.before is not None:
            self.editor.history.remember(self.before)
            QTimer.singleShot(0, self.remark)
        else:
            self.editor.dragged = -1
        self.before = None
        if not moved and self.editor.armed is not None:
            QTimer.singleShot(0, self.paint_fillet)

    # Method `CornerCircle.remark()`:
    def remark(self) -> None:
        """Remake its corner's marks where it was dropped (#451),
        after the release, as it remakes the squares."""
        self.editor.remark(self.index)

    # Method `CornerCircle.paint_fillet()`:
    def paint_fillet(self) -> None:
        """Fillet its corner by the armed letter: one undo step."""
        if self.editor.armed is not None:
            self.editor.set_fillets([self.index], self.editor.armed)

    # Method `CornerCircle.itemChange()`:
    def itemChange(
        self, change: QGraphicsItem.GraphicsItemChange, value: object
    ) -> object:
        """Snap a move, and move the corner with it; a coordinate the
        dimensions fix does not move (#148)."""
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and isinstance(value, QPointF)
            and self.editor.placing
        ):
            return value
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
            # Only dimensions pin a coordinate (#176); it snaps level,
            # upright or onto an axis (#451).
            self.editor.drag_corner(self.index, moved)
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

    # Method `OutlineItem.paint_crossings()`:
    def paint_crossings(
        self, painter: QPainter, corners: list[QPointF]
    ) -> None:
        """Draw the edges that cross (#242) red and thick, over the
        outline.

        Arguments:
        * `painter` (`QPainter`): What draws, in drawing steps.
        * `corners` (`list[QPointF]`): The corners.
        """
        crossed: set[int] = {
            edge for pair in crossings(self.drawing.points) for edge in pair
        }
        bad: QPen = QPen(QColor(theme.colors().problem), 2 * THICK_PIXELS)
        bad.setCosmetic(True)
        painter.setPen(bad)
        edge: int
        for edge in sorted(crossed):
            painter.drawLine(corners[edge], corners[(edge + 1) % len(corners)])

    # Method `OutlineItem.paint()`:
    def paint(
        self,
        painter: QPainter,
        _option: QStyleOptionGraphicsItem,
        _widget: QWidget | None = None,
    ) -> None:
        """Draw the outline's strokes (`outline_strokes()`, the SVG's
        own, #S4) with pens of fixed pixel widths (#302), then the
        editing aids: crossings and an arrowhead along each edge (a
        fillet's dashes to its sharp corner are its own, #117)."""
        # Pens are cosmetic: their widths are pixels at any zoom.
        ink: QColor = QColor(theme.colors().ink)
        pen: QPen = QPen(ink, THICK_PIXELS)
        pen.setCosmetic(True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        fillets: dict[int, Fillet] = fillet_arcs(
            self.drawing, self.drawing.scale
        )
        strokes: list[Stroke] = outline_strokes(self.drawing, fillets)
        painter.setPen(pen)
        painter.drawPath(stroke_path(strokes[0]))

        # Revolved: the mirror half, faint and dashed.
        ghost: QPen = QPen(QColor(theme.colors().quiet), THIN_PIXELS)
        ghost.setCosmetic(True)
        ghost.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(ghost)
        stroke: Stroke
        for stroke in strokes[1:]:
            painter.drawPath(stroke_path(stroke))

        corners: list[QPointF] = [
            QPointF(x, y) for x, y in self.drawing.points
        ]
        self.paint_crossings(painter, corners)

        # Each arrowhead is `ARROW_PIXELS` long on screen, pointing
        # along its edge to where it ends.
        painter.setPen(pen)
        world: QTransform = painter.worldTransform()
        # A quarter turn moves the scale off the diagonal (#300).
        scale: float = math.hypot(world.m11(), world.m12())
        length: float = ARROW_PIXELS / max(scale, 1e-12)
        painter.setBrush(ink)
        segment: XYSegment
        for segment in strokes[0].segments:
            if isinstance(segment, LineSegment):
                painter.drawPath(
                    arrowhead(
                        QPointF(*segment.start), QPointF(*segment.end), length
                    )
                )


# Function `svg_path()`:
def svg_path(path: Path) -> Path:
    """Return where an outline file's diagram is written (#248):
    beside it, `NAME.outline.svg` for `NAME.outline.toml`.

    Arguments:
    * `path` (`Path`): The outline file.

    Returns:
    * (`Path`): Its `.svg`, which follows the viewer's theme.
    """
    # The same name, its last suffix `.svg`.
    return path.with_suffix(".svg")


# Function `stroke_box()`:
def stroke_box(strokes: list[Stroke], margin: float) -> QRectF:
    """Return a box around some strokes' paths, grown by a margin.

    Arguments:
    * `strokes` (`list[Stroke]`): The strokes.
    * `margin` (`float`): How far past them (drawing steps).

    Returns:
    * (`QRectF`): The box; empty for no strokes.
    """
    # Each stroke's path box, joined.
    box: QRectF = QRectF()
    stroke: Stroke
    for stroke in strokes:
        box = box.united(stroke_path(stroke).boundingRect())
    if box.isNull():
        return box
    return box.adjusted(-margin, -margin, margin, margin)


# Function `stroke_path()`:
def stroke_path(stroke: Stroke) -> QPainterPath:
    """Return a stroke's segments as a Qt path, each arc in
    `ARC_STEPS` straight pieces.

    Arguments:
    * `stroke` (`Stroke`): Lines and arcs, in drawing steps.

    Returns:
    * (`QPainterPath`): The path, closed when the stroke is.
    """
    # Each segment from where the last one ended (or a jump to it).
    path: QPainterPath = QPainterPath()
    segment: XYSegment
    for segment in stroke.segments:
        if path.isEmpty() or path.currentPosition() != QPointF(*segment.start):
            path.moveTo(*segment.start)
        if isinstance(segment, ArcSegment):
            first: float = math.atan2(
                segment.start[1] - segment.center[1],
                segment.start[0] - segment.center[0],
            )
            step: int
            for step in range(1, ARC_STEPS + 1):
                angle: float = first + segment.sweep * step / ARC_STEPS
                path.lineTo(
                    segment.center[0] + segment.radius * math.cos(angle),
                    segment.center[1] + segment.radius * math.sin(angle),
                )
        else:
            path.lineTo(*segment.end)
    return path


# Function `shift_at()`:
def shift_at(pieces: list[tuple[float, float, float]], at: float) -> float:
    """Return how far the working view shifts a place: by its piece.

    Arguments:
    * `pieces` (`list[tuple[float, float, float]]`): From
      `OutlineView.cut_offsets()`.
    * `at` (`float`): The place.

    Returns:
    * (`float`): The shift (0 inside a cut, or past every piece).
    """
    low: float
    high: float
    shift: float
    for low, high, shift in pieces:
        if low <= at <= high:
            return shift
    return 0.0


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
    arc: tuple[tuple[float, float], float, float] | None = shared_arc(
        points, first, second, (1, 1)
    )
    return None if arc is None else QPointF(*arc[0])


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
    turn counterclockwise from the first ray to the second
    (`outline_diagram.edge_arc()`, as the SVG draws it, #295).

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
    arc: tuple[tuple[float, float], float, float] | None = shared_arc(
        points, first, second, rays
    )
    return None if arc is None else (QPointF(*arc[0]), arc[1], arc[2])


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


# Class `EdgeHandle`:
class EdgeHandle(QGraphicsEllipseItem):
    """A small hollow circle in the middle of an edge (#59).

    Dragged, it pulls out a new corner there, snapped as corners are,
    the whole drag one change; a click that does not move selects
    the edge (for [Dimension], #231, #234).

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
        # It snaps as a dragged corner does (#451).
        self.editor.dragged = self.added
        self.editor.drag_corner(self.added, where)
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
            self.editor.remark(self.added)  # Its marks, and its square.
        elif self.before is not None:
            self.editor.select_edge(self.index)
        self.before = None


# Class `StripHandle`:
class StripHandle(QGraphicsEllipseItem):
    """A hide strip's circle, in the overview (#173, #178): one on each
    of its four sides resizes it, the middle one moves it; snapped; a
    strip that would cover a corner or a fillet, or not reach right
    across the part, stays put (#165, #180).

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its strip's index in the drawing.
    * `part` (`str`): `"low"`, `"high"` (its sides along the axis),
      `"under"`, `"over"` (across it) or `"whole"`.
    * `before` (`Snapshot | None`): The drawing when a drag began.
    * `grabbed` (`tuple[float, float]`): Where the drag began, along
      the axis and across it.
    """

    # Method `StripHandle.__init__()`:
    def __init__(self, editor: "OutlineView", index: int, part: str) -> None:
        """Make one circle of a strip.

        Arguments:
        * `editor` (`OutlineView`): The view it is drawn in.
        * `index` (`int`): Its strip's index in the drawing.
        * `part` (`str`): `"low"`, `"high"` or `"whole"`.
        """
        half: float = GRIP_PIXELS / 2.0
        super().__init__(-half, -half, GRIP_PIXELS, GRIP_PIXELS)
        self.editor: OutlineView = editor
        self.index: int = index
        self.part: str = part
        self.before: Snapshot | None = None
        self.grabbed: tuple[float, float] = (0.0, 0.0)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setZValue(2.5)

    # Method `StripHandle.place()`:
    def place(self) -> None:
        """Sit in the middle of its side of the strip's rectangle, or
        in its middle (#178); shown in the overview only."""
        hide: Hide = self.editor.drawing.hides[self.index]
        points: list[tuple[float, float]] = self.editor.drawing.points
        low: float
        high: float
        low, high = strip(points, hide)
        near: float
        far: float
        near, far = across(points, hide)
        along: float = {"low": low, "high": high}.get(
            self.part, (low + high) / 2.0
        )
        side: float = {"under": near, "over": far}.get(
            self.part, (near + far) / 2.0
        )
        self.setPos(
            QPointF(side, along)
            if hide.axis == HIDE_Y
            else QPointF(along, side)
        )
        self.setVisible(self.editor.overview)

    # Method `StripHandle.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Get ready to resize or move the strip."""
        self.before = self.editor.drawing.snapshot()
        hide: Hide = self.editor.drawing.hides[self.index]
        at: QPointF = event.scenePos()
        self.grabbed = (
            (at.y(), at.x()) if hide.axis == HIDE_Y else (at.x(), at.y())
        )
        event.accept()

    # Method `StripHandle.mouseMoveEvent()`:
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Resize the strip from a side, or move it, if it may go
        there: never over a corner or a fillet (#165), and past the
        part and its dimensions (#180)."""
        assert self.before is not None
        axis: int = self.before.hides[self.index].axis
        low: float
        high: float
        under: float
        over: float
        low, high, under, over = self.proposed(event.scenePos())
        laid: Hide | str = lay(
            self.editor.drawing.points,
            axis,
            low,
            high,
            self.editor.fillet_arcs(axis),
        )
        other: list[float] = [
            point[1 - axis] for point in self.editor.drawing.points
        ]
        least: tuple[float, float] = self.editor.reach(axis)
        if isinstance(laid, Hide) and (
            min(other) - under > least[0] or max(other) + over < least[1]
        ):
            laid = "A hide must reach past the part and its dimensions."
        if isinstance(laid, str):
            self.editor.message = laid
        else:
            laid.under, laid.over = under, over
            self.editor.drawing.hides[self.index] = laid
            self.editor.message = ""
        self.editor.place_handles()
        self.editor.viewport().update()
        self.editor.scene().update()

    # Method `StripHandle.proposed()`:
    def proposed(self, at: QPointF) -> tuple[float, float, float, float]:
        """Return where the strip would go with this circle dragged to
        a point: its two sides along the axis, and how far it reaches
        past the outline on each side across it.

        Arguments:
        * `at` (`QPointF`): The pointer, in the scene.

        Returns:
        * (`tuple[float, float, float, float]`): Low, high, under,
          over.
        """
        assert self.before is not None
        old: Hide = self.before.hides[self.index]
        low: float
        high: float
        low, high = strip(list(self.before.points), old)
        under: float = old.under
        over: float = old.over
        along: float = at.y() if old.axis == HIDE_Y else at.x()
        side: float = at.x() if old.axis == HIDE_Y else at.y()
        other: list[float] = [
            point[1 - old.axis] for point in self.editor.drawing.points
        ]
        if self.part == "whole":
            # Moved: its low side snapped, its size kept.
            width: float = high - low
            low = self._snapped(low + along - self.grabbed[0])
            high = low + width
            shift: float = self._snapped(side - self.grabbed[1])
            under, over = under - shift, over + shift
        elif self.part == "low":
            low = self._snapped(along)
        elif self.part == "high":
            high = self._snapped(along)
        elif self.part == "under":
            under = min(other) - self._snapped(side)
        else:
            over = self._snapped(side) - max(other)
        return low, high, under, over

    # Method `StripHandle.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, _event: QGraphicsSceneMouseEvent) -> None:
        """End the drag: remember it, if it changed the strip."""
        if self.before is not None and self.before.hides != tuple(
            self.editor.drawing.hides
        ):
            self.editor.history.remember(self.before)
        self.before = None

    # Method `StripHandle._snapped()`:
    def _snapped(self, along: float) -> float:
        """Return a place along the axis, snapped when [Snap] is on.

        Arguments:
        * `along` (`float`): The place.

        Returns:
        * (`float`): It, on the grid if snapping.
        """
        if not self.editor.snap_on:
            return along
        return snap(QPointF(along, along), self.editor.step()).x()


# Class `DimensionHandle`:
class DimensionHandle(QGraphicsEllipseItem):
    """A dimension's small hollow circle, beside its letter (#63).

    Dragged along the line it moves the letter (past the arrowheads
    too); across the line it moves the line; a `—` or `|` mark's moves
    its box anywhere (#317); snapped as corners are, the whole drag
    one change.

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its dimension's index in the drawing.
    * `before` (`Snapshot | None`): The drawing when a drag began.
    * `grab` (`QPointF`): Where it sits from its letter's point (the
      line's `at()`) when a drag began, so the letter does not jump.
    * `pressed` (`QPointF`): Where a mark's drag began (scene).
    * `was` (`tuple[float, float]`): The mark's `moved` then.
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
        self.grab: QPointF = QPointF()
        self.pressed: QPointF = QPointF()
        self.was: tuple[float, float] = (0.0, 0.0)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setZValue(1.5)

    # Method `DimensionHandle.place()`:
    def place(self) -> None:
        """Sit just off its letter's (or a `—` or `|` mark's box's)
        upper right corner (#315, #317; hidden for a fillet and a right
        angle, for now)."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        lined: bool = (
            dimension.kind != ANGLE
            if is_mark(dimension)
            else dimension.kind != RADIUS
        )
        # Marks show only under [Show Marks] (#451).
        lined = lined and (not is_mark(dimension) or self.editor.marks_shown)
        self.setVisible(lined)
        if lined:
            self.setPos(self.editor.measures[self.index].handle_spot())

    # Method `DimensionHandle.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Select the dimension; get ready to move it."""
        self.editor.select_dimension(self.index)
        self.before = self.editor.drawing.snapshot()
        self.grab = self.pos() - self.editor.measures[self.index].at()
        self.pressed = event.scenePos()
        self.was = self.editor.drawing.dimensions[self.index].moved
        event.accept()

    # Method `DimensionHandle.mouseMoveEvent()`:
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Move the letter along the line, and the line across."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        where: QPointF = event.scenePos() - self.grab
        free: bool = not self.editor.snap_on or bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        if not free:
            where = snap(where, self.editor.step())
        measure: DimensionItem = self.editor.measures[self.index]
        start: QPointF
        end: QPointF
        measure.prepareGeometryChange()
        if is_mark(dimension):
            # A mark's box goes where it is dragged (#317).
            shift: QPointF = event.scenePos() - self.pressed
            if not free:
                shift = snap(shift, self.editor.step())
            dimension.moved = (
                self.was[0] + shift.x(),
                self.was[1] + shift.y(),
            )
            measure.update()
            self.place()
            return
        if dimension.kind == ANGLE:
            self.drag_angle(dimension, where)
            measure.update()
            self.place()
            return
        _, _, start, end = measure.ends()
        # A diameter runs across, as a horizontal one (`T.tfo~6.5`
        # #456: it was moved as a vertical one).
        if dimension.kind in (HORIZONTAL, DIAMETER):
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
        # The letter may go past either ray (#321; it was held between
        # the arrowheads, #76); `past` already keeps it off the far
        # side of the circle.
        dimension.along = past / turn

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
        if dimension.kind == DIAMETER:
            # From the corner's mirror image across the axis (#437),
            # across at `offset`, as `outline_diagram` draws it (#456).
            first = QPointF(-second.x(), second.y())
        if dimension.kind in (HORIZONTAL, DIAMETER):
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
        if self.editor.drawing.dimensions[self.index].kind == RADIUS:
            return path  # Drawn as its outline's arc (#116).
        if is_mark(self.editor.drawing.dimensions[self.index]):
            path.addRect(stroke_box(self.strokes(), 0.0))  # (#233)
            return path
        # A band along each line drawn, and its letter's box (#305).
        strokes: list[Stroke] = self.strokes()
        stroke: Stroke
        for stroke in strokes:
            if not stroke.filled and stroke.role != TEXT:
                path.addPath(stroke_path(stroke))
        stroker: QPainterPathStroker = QPainterPathStroker()
        stroker.setWidth(SQUARE_PIXELS / max(self.editor.zoom(), 1e-12))
        band: QPainterPath = stroker.createStroke(path)
        letter: QRectF = stroke_box(
            [stroke for stroke in strokes if stroke.role == TEXT], 0.0
        )
        if not letter.isNull():
            band.addRect(letter)
        return band

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
        return stroke_box(self.strokes(), margin)

    # Method `DimensionItem.pen()`:
    def pen(self) -> QPen:
        """Return the pen it is drawn with: thin, red when one too
        many or a fillet too big for its edges; selected, colored and
        thicker, not told by color alone (#131).

        Returns:
        * (`QPen`): A cosmetic pen.
        """
        # One too many, or a mark the drawing breaks (#241).
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        extra: bool = (
            self.index in self.editor.solution.extra
            or mark_broken(self.editor.drawing.points, dimension)
            or (
                dimension.kind == RADIUS
                and dimension.start in self.editor.trouble
            )
        )
        ink: QColor = QColor(
            theme.colors().problem if extra else theme.colors().ink
        )
        # Selected, or its letter's row pointed at (#224).
        lit: str = self.editor.lit_letter
        chosen: bool = self.index in self.editor.chosen_dimensions or bool(
            lit and self.editor.drawing.dimensions[self.index].letter == lit
        )
        if chosen:
            ink = self.editor.palette().highlight().color()
        pen: QPen = QPen(ink, CHOSEN_PIXELS if chosen else THIN_PIXELS)
        pen.setCosmetic(True)
        return pen

    # Method `DimensionItem.paint()`:
    def paint(
        self,
        painter: QPainter,
        _option: QStyleOptionGraphicsItem,
        _widget: QWidget | None = None,
    ) -> None:
        """Draw its shared strokes (#S4): dimensions, marks and
        fillets alike."""
        pen: QPen = self.pen()
        painter.setPen(pen)
        painter.setBrush(pen.color())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint_strokes(painter)

    # Method `DimensionItem.handle_spot()`:
    def handle_spot(self) -> QPointF:
        """Return where its circle sits (#315): just off its letter's
        upper right corner (Y is up), clear of the letter.

        Returns:
        * (`QPointF`): The circle's middle, in drawing steps.
        """
        found: QRectF | None = self.letter_box()
        letter: QRectF = QRectF() if found is None else found
        if letter.isNull():
            return self.at()
        off: float = HANDLE_PIXELS / max(self.editor.zoom(), 1e-12)

        # The screen's upper right, in drawing steps: (1, 1) turned a
        # quarter turn counterclockwise per turn of the view (#300).
        way: tuple[float, float] = (1.0, 1.0)
        _turn: int
        for _turn in range(self.editor.drawing.turns % 4):
            way = (-way[1], way[0])
        middle: QPointF = letter.center()
        return QPointF(
            middle.x() + way[0] * (letter.width() / 2.0 + off),
            middle.y() + way[1] * (letter.height() / 2.0 + off),
        )

    # Method `DimensionItem.strokes()`:
    def strokes(self) -> list[Stroke]:
        """Return its strokes (`dimension_strokes()`), its text and
        arrowheads `TEXT_PIXELS` high at the view's zoom (#311).

        Returns:
        * (`list[Stroke]`): In drawing steps.
        """
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        return upright_text(
            dimension_strokes(
                self.editor.drawing,
                dimension,
                (
                    fillet_arcs(self.editor.drawing, self.editor.drawing.scale)
                    if dimension.kind == RADIUS
                    else {}
                ),
                TEXT_PIXELS
                * FONT_STEP**dimension.font_step
                / max(self.editor.zoom(), 1e-12),
            ),
            self.editor.drawing.turns,
        )

    # Method `DimensionItem.paint_strokes()`:
    def paint_strokes(self, painter: QPainter) -> None:
        """Draw its strokes: lines with the pen, arrowheads filled.

        Arguments:
        * `painter` (`QPainter`): What draws, pen and brush set.
        """
        pen: QPen = painter.pen()
        letter: QPen = QPen(pen)
        letter.setWidthF(max(pen.widthF(), TEXT_PEN_PIXELS))
        stroke: Stroke
        for stroke in self.strokes():
            path: QPainterPath = stroke_path(stroke)
            if stroke.filled:
                path.closeSubpath()
                painter.drawPath(path)
            else:
                painter.strokePath(
                    path, letter if stroke.role == TEXT else pen
                )

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

    # Method `DimensionItem.letter_box()`:
    def letter_box(self) -> QRectF | None:
        """Return the box its letter (or a mark's glyph) is drawn in,
        for the hide strips' check (#182, the whole box, #322); `None`
        for a fillet's (on its arc, at a corner no strip covers).

        Returns:
        * (`QRectF | None`): The box, in drawing steps.
        """
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        if is_mark(dimension):
            return stroke_box(self.strokes(), 0.0)
        if dimension.kind == RADIUS:
            return None
        # Its letter as drawn (#305), else its point.
        letter: QRectF = stroke_box(
            [stroke for stroke in self.strokes() if stroke.role == TEXT], 0.0
        )
        if letter.isNull():
            return QRectF(self.at(), self.at())
        return letter


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
    * `armed` (`str | None`): The fillet letter a corner clicked takes
      ("" makes it sharp), armed in [Fillets] (#214); `None`: none.
    * `released` (`Callable[[], None]`):
      Called after a mouse button comes up (the window saves).
    * `placing` (`bool`): Whether the squares are being put where the
      values say (their moves are not drags).
    * `overview` (`bool`): Whether the whole drawing is shown, its
      hide strips shaded (#168), not cut out.
    * `hiding` (`bool`): Whether [Hide] waits for a drag (#164).
    * `hide_from` (`QPointF | None`): Where that drag began.
    * `band` (`QGraphicsRectItem`): The rectangle being dragged.
    * `cleared` (`Callable[[], None]`): Called when the selection is
      cleared (the window clears the table's, #125).
    * `restyled` (`Callable[[], None]`): Called after `restyle()`, so
      the window can follow the selection ([Fillets], #142.2).
    * `lit` (`int`): The corner pointed at, on the drawing or by its
      [Fillets] row (-1 for none, #199): drawn bigger and thicker.
    * `lighted` (`Callable[[int], None]`): Called with `lit` when it
      changes (the window frames the row).
    * `lit_letter` (`str`): The letter whose row is pointed at, or
      whose uses a refusal shows ("" for none, #224, #245): its
      dimensions and the corners it rounds are lit.
    * `trouble` (`dict[int, str]`): Fillets too big for their edges,
      by corner (#127; the window finds them).
    * `origin` (`QGraphicsRectItem`): The origin's square.
    * `outline` (`OutlineItem`): The outline.
    * `snap_on` (`bool`): Whether drags snap to the grid.
    * `squares` (`list[CornerCircle]`): The corners' squares.
    * `measures` (`list[DimensionItem]`): The dimensions' items.
    * `handles` (`list[EdgeHandle]`): The edges' handles.
    * `circles` (`list[DimensionHandle]`): The dimensions' circles.
    * `grips` (`list[StripHandle]`): The hide strips' circles.
    * `solution` (`Solution`): The corners' formulas, and what is
      amiss.
    * `pinned` (`Solution`): The coordinates the dimensions alone fix,
      which a drag does not move (#176).
    """

    # Method `OutlineView.__init__()`:
    # Every attribute of the view is set up here, in one place.
    # pylint: disable-next=too-many-statements
    def __init__(self, drawing: Drawing) -> None:
        """Make the view of a drawing, fitted to it.

        Arguments:
        * `drawing` (`Drawing`): The outline being drawn.
        """
        super().__init__()
        self.drawing: Drawing = drawing
        self.grid_shown: bool = True
        self.marks_shown: bool = False
        # The corner being dragged, whose own marks are left out until
        # it is dropped (#451), or -1.
        self.dragged: int = -1
        self.history: History = History()
        self.message: str = ""
        self.chosen_points: list[int] = []
        self.chosen_dimensions: list[int] = []
        self.chosen_edges: list[int] = []
        self.wanted: bool = False
        self.letters_changed: Callable[[], None] = self.update
        self.released: Callable[[], None] = self.update
        self.placing: bool = False
        self.overview: bool = False
        self.hiding: bool = False
        self.hide_from: QPointF | None = None
        self.band: QGraphicsRectItem = QGraphicsRectItem()
        self.band.setVisible(False)
        self.band.setZValue(3.0)
        self.cleared: Callable[[], None] = self.update
        self.restyled: Callable[[], None] = self.update
        self.lit: int = -1
        self.armed: str | None = None
        self.lighted: Callable[[int], None] = self.lit_nothing
        self.lit_letter: str = ""
        self.trouble: dict[int, str] = {}
        self.snap_on: bool = True
        scene: QGraphicsScene = QGraphicsScene(self)
        scene.setSceneRect(QRectF(-1e6, -1e6, 2e6, 2e6))
        # No spatial index: a deletion changes the boxes of the items
        # it removes, so an index loses them and keeps a dangling
        # pointer (a segmentation fault after a dimension's drag).  A
        # drawing has only a few dozen items.
        scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        self.setScene(scene)

        # Panned by hand (`pan_from`), so the pointer stays an arrow
        # for aiming; a closed hand only while panning (#55).
        self.pan_from: QPoint | None = None
        self.set_up_view()

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
        scene.addItem(self.band)
        self.squares: list[CornerCircle] = []
        self.handles: list[EdgeHandle] = []
        self.circles: list[DimensionHandle] = []
        self.grips: list[StripHandle] = []
        self.measures: list[DimensionItem] = []
        self.solution: Solution = solve(drawing.points, drawing.dimensions)
        # Only dimensions and marks pin a dragged corner (#176, #233).
        self.pinned: Solution = self.solution
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
        square: CornerCircle
        for square in self.squares:
            self.scene().removeItem(square)
        self.squares = []
        index: int
        for index in range(len(self.drawing.points)):
            square = CornerCircle(self, index)
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
            measure.setVisible(
                self.marks_shown
                or not is_mark(self.drawing.dimensions[measure.index])
            )
        circle: DimensionHandle
        for circle in self.circles:
            self.scene().removeItem(circle)
        self.circles = [
            DimensionHandle(self, index)
            for index in range(len(self.drawing.dimensions))
        ]
        for circle in self.circles:
            self.scene().addItem(circle)
        grip: StripHandle
        for grip in self.grips:
            self.scene().removeItem(grip)
        self.grips = [
            StripHandle(self, index, part)
            for index in range(len(self.drawing.hides))
            for part in ("low", "high", "under", "over", "whole")
        ]
        for grip in self.grips:
            self.scene().addItem(grip)
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
            self.dimension_points()
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
        self.cleared()
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
        wide: float = abs(end.x() - start.x())
        up: float = abs(end.y() - start.y())
        if not kind:
            kind = HORIZONTAL if wide >= up else VERTICAL
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
        if kind in (HORIZONTAL, DIAMETER):
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
        (horizontal, length, vertical, then horizontal again; on a
        revolved outline, from the origin, a diameter after horizontal,
        #437), as one change.  Each kind keeps its own place: the line
        and letter go back to where they were last time it was that
        kind, or the first time to where a new one would go (#29)."""
        if not self.chosen_dimensions:
            self.message = "Select dimensions to change their kind."
            self.scene().update()
            return
        self.history.remember(self.drawing.snapshot())
        index: int
        for index in self.chosen_dimensions:
            dimension: Dimension = self.drawing.dimensions[index]
            if dimension.kind in (ANGLE, RADIUS) or is_mark(dimension):
                continue  # Not cycled.
            self.measures[index].prepareGeometryChange()
            kind: str = next_kind(dimension, self.drawing.revolve)
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
        no corner or dimension takes the press; after [Hide], start
        the rectangle instead."""
        if self.hiding and event.button() == Qt.MouseButton.LeftButton:
            self.hide_from = self.mapToScene(event.position().toPoint())
            self.band.setRect(QRectF(self.hide_from, self.hide_from))
            self.band.setVisible(True)
            return
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
        """While panning, move the view with the pointer; while
        hiding, stretch the rectangle."""
        if self.hide_from is not None:
            self.band.setRect(
                QRectF(
                    self.hide_from,
                    self.mapToScene(event.position().toPoint()),
                ).normalized()
            )
            return
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
        if self.hide_from is not None:
            self.lay_hide(self.band.rect())
            self.hide_from = None
            self.hiding = False
            self.band.setVisible(False)
            self.released()
            return
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
        """Draw the dimensioned corners from the values, solve again,
        then draw the dimensions and squares to match."""
        self.apply_values()
        self.outline.refresh()
        self.solution = solve(self.drawing.points, self.working())
        self.pinned = self.solution
        measure: DimensionItem
        for measure in self.measures:
            measure.prepareGeometryChange()
        self.drawing.follow_angles()
        for measure in self.measures:
            measure.update()
        self.place_handles()
        self.restyle()

    # Method `OutlineView.working()`:
    def working(self) -> list[Dimension]:
        """Return the dimensions to place corners by: all of them, but
        a dragged corner's own marks, which it may be dragged off
        (#451).

        Returns:
        * (`list[Dimension]`): The dimensions.
        """
        if self.dragged < 0:
            return self.drawing.dimensions
        return without_marks(
            self.drawing.dimensions, self.dragged, len(self.drawing.points)
        )

    # Method `OutlineView.apply_values()`:
    def apply_values(self) -> None:
        """Put each coordinate the dimensions fix where the letters'
        values put it, to scale (`values.placed_corners()`, #148)."""
        placed: list[tuple[float, float]]
        placed, self.drawing.scale = placed_corners(
            self.drawing.points,
            self.drawing.letters,
            self.working(),
            self.drawing.scale,
        )
        if placed == self.drawing.points:
            return
        self.drawing.points[:] = placed
        self.placing = True
        square: CornerCircle
        for square in self.squares:
            square.setPos(*placed[square.index])
        self.placing = False
        self.outline.refresh()

    # Method `OutlineView.place_handles()`:
    def place_handles(self) -> None:
        """Put each edge's handle in its middle (shown if long enough)."""
        handle: EdgeHandle
        for handle in self.handles:
            handle.place()
        circle: DimensionHandle
        for circle in self.circles:
            circle.place()
        grip: StripHandle
        for grip in self.grips:
            grip.place()

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
        """[Dimension]: dimension what is selected (#234): two edges
        (or an axis and an edge) give the angle between them; one edge
        alone its length (#231); one corner alone the angle there,
        between its two edges (#232); else points (`dimension_points()`).
        """
        edges: list[int] = self.chosen_edges
        points: list[int] = self.chosen_points
        if len(edges) >= 2:
            self.angle_selected()
            return
        if len(edges) == 1 and edges[0] not in AXES and not points:
            edge: int = edges[0]
            self.dimension_between(
                edge, (edge + 1) % len(self.drawing.points), LENGTH
            )
            return
        if not edges and len(points) == 1 and points[0] != ORIGIN:
            corner: int = points[0]
            self.chosen_edges = [
                (corner - 1) % len(self.drawing.points),
                corner,
            ]
            self.angle_selected()
            return
        self.dimension_points()

    # Method `OutlineView.dimension_points()`:
    def dimension_points(self) -> None:
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
                else "Select an edge, a corner, two edges or two points."
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
            self.message = "Select two edges' circles for an angle."
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

    # Method `OutlineView.light()`:
    def light(self, corner: int) -> None:
        """Light a corner (none for -1), here and in [Fillets] (#199).

        Arguments:
        * `corner` (`int`): The corner, or -1.
        """
        if corner == self.lit:
            return
        self.lit = corner
        self.restyle()
        self.lighted(corner)

    # Method `OutlineView.corner_lit()`:
    def corner_lit(self, corner: int) -> bool:
        """Return whether a corner is lit: pointed at (#199), or
        rounded by the lit letter (#224).

        Arguments:
        * `corner` (`int`): The corner.

        Returns:
        * (`bool`): Whether it is lit.
        """
        return corner == self.lit or bool(
            self.lit_letter and self.fillets().get(corner) == self.lit_letter
        )

    # Method `OutlineView.light_letter()`:
    def light_letter(self, letter: str) -> None:
        """Light a letter's uses: its dimensions and the corners it
        rounds (#224, #245); "" for none.

        Arguments:
        * `letter` (`str`): The letter.
        """
        if letter == self.lit_letter:
            return
        self.lit_letter = letter
        self.restyle()
        measure: DimensionItem
        for measure in self.measures:
            measure.update()

    # Method `OutlineView.lit_nothing()`:
    def lit_nothing(self, _corner: int) -> None:
        """Do nothing: `lighted` until the window sets it."""

    # Method `OutlineView.fillets()`:
    def fillets(self) -> dict[int, str]:
        """Return each rounded corner's letter.

        Returns:
        * (`dict[int, str]`): Letter by corner.
        """
        return {
            dimension.start: dimension.letter
            for dimension in self.drawing.dimensions
            if dimension.kind == RADIUS
        }

    # Method `OutlineView.fillet_letters()`:
    def fillet_letters(self) -> list[str]:
        """Return the letters fillets use, in table order.

        Returns:
        * (`list[str]`): The letters.
        """
        used: set[str] = set(self.fillets().values())
        return [
            letter.letter
            for letter in self.drawing.letters
            if letter.letter in used
        ]

    # Method `OutlineView.set_fillets()`:
    def set_fillets(self, corners: list[int], choice: str) -> None:
        """Give corners a fillet by a letter, or make them sharp; one
        change (none if nothing would change).

        Arguments:
        * `corners` (`list[int]`): The corners.
        * `choice` (`str`): The letter; `NOTE_CHOICE` for the note
          letter (made the first time: "All undimensioned fillets are
          radius UDF", #116, #120); "" for sharp.
        """
        now: dict[int, str] = self.fillets()
        target: str = (
            self.drawing.note_radius or NOTE_CHOICE
            if choice == NOTE_CHOICE
            else choice
        )
        if all(now.get(corner, "") == target for corner in corners):
            return
        self.history.remember(self.drawing.snapshot())
        if choice == NOTE_CHOICE:
            target = self.note_letter()
        self.drawing.dimensions[:] = [
            dimension
            for dimension in self.drawing.dimensions
            if not (dimension.kind == RADIUS and dimension.start in corners)
        ]
        if target:
            corner: int
            for corner in corners:
                self.drawing.dimensions.append(
                    Dimension(target, RADIUS, corner, corner)
                )
        chosen: list[int] = list(self.chosen_points)
        self.message = ""
        self.make_squares()
        self.chosen_points = chosen
        self.letters_changed()
        self.restyle()

    # Method `OutlineView.drag_corner()`:
    def drag_corner(self, corner: int, moved: QPointF) -> None:
        """Move a dragged corner (#451): it snaps to its neighbors'
        X or Y, or onto an axis, within `SNAP_PIXELS`; a coordinate
        the other dimensions fix (its own marks aside) holds.

        Arguments:
        * `corner` (`int`): The corner dragged.
        * `moved` (`QPointF`): Where the drag puts it; changed to where
          it may go.
        """
        points: list[tuple[float, float]] = self.drawing.points
        trial: list[tuple[float, float]] = list(points)
        trial[corner] = (moved.x(), moved.y())
        here: tuple[float, float]
        here, _ = snapped(
            trial,
            self.drawing.dimensions,
            corner,
            SNAP_PIXELS / max(self.zoom(), 1e-9),
        )
        held: Solution = solve(
            points, without_marks(self.drawing.dimensions, corner, len(points))
        )
        place: list[float] = list(here)
        if corner in held.x:
            place[0] = points[corner][0]
        if corner in held.y:
            place[1] = points[corner][1]
        moved.setX(place[0])
        moved.setY(place[1])
        points[corner] = (place[0], place[1])

    # Method `OutlineView.remark()`:
    def remark(self, corner: int) -> None:
        """Remake a dropped corner's marks from where it is drawn
        (#451): its edges level or upright, it on an axis.

        Arguments:
        * `corner` (`int`): The corner.
        """
        self.dragged = -1
        if not 0 <= corner < len(self.drawing.points):
            return
        self.drawing.dimensions[:] = snapped(
            self.drawing.points, self.drawing.dimensions, corner, 0.0
        )[1]
        points: list[int] = list(self.chosen_points)
        self.make_squares()
        self.chosen_points = points
        self.letters_changed()
        self.restyle()

    # Method `OutlineView.note_letter()`:
    def note_letter(self) -> str:
        """Return the note letter, making it the first time (`UDF`, or
        the next free letter if `UDF` is taken).

        Returns:
        * (`str`): The letter.
        """
        if self.drawing.note_radius:
            return self.drawing.note_radius
        letter: Letter = replace(
            next_letter(self.drawing.letters),
            name="Undimensioned fillet radius",
            default="1/16 in",
            help="Every fillet without a radius of its own.",
            fillet=True,
        )
        if not any(
            each.letter == NOTE_LETTER for each in self.drawing.letters
        ):
            letter = replace(letter, letter=NOTE_LETTER)
        self.drawing.letters.append(letter)
        self.drawing.note_radius = letter.letter
        return letter.letter

    # Method `OutlineView.is_angle()`:
    def is_angle(self, letter: str) -> bool:
        """Return whether a letter is an angle: used by an angle, or
        its default in degrees or radians.

        Arguments:
        * `letter` (`str`): The letter.

        Returns:
        * (`bool`): Whether it is.
        """
        if any(
            dimension.kind == ANGLE and dimension.letter == letter
            for dimension in self.drawing.dimensions
        ):
            return True
        return any(
            each.letter == letter
            and each.default.split()[-1:] in (["deg"], ["rad"])
            for each in self.drawing.letters
        )

    # Method `OutlineView.start_hide()`:
    def start_hide(self) -> None:
        """[Hide]: wait for a rectangle dragged over a boring stretch,
        in the overview (#164, #168)."""
        self.overview = True
        self.hiding = True
        self.place_handles()
        self.restyle()
        self.message = "Drag a rectangle over the stretch to hide."
        self.viewport().update()
        self.scene().update()

    # Method `OutlineView.lay_hide()`:
    def lay_hide(self, rectangle: QRectF) -> None:
        """Lay a strip from a dragged rectangle: one reaching across the
        part's width hides a stretch of height, one reaching top to
        bottom a stretch of width (else a wide one hides height); not
        over a corner or a fillet (#165).  One change.

        Arguments:
        * `rectangle` (`QRectF`): The rectangle, in the scene.
        """
        # Hiding height if it reaches across the part's width, width if
        # top to bottom; when both or neither, a wide one hides height.
        xs: list[float] = [x for x, _ in self.drawing.points]
        ys: list[float] = [y for _, y in self.drawing.points]
        wide: bool = rectangle.left() <= min(xs) and rectangle.right() >= max(
            xs
        )
        tall: bool = rectangle.top() <= min(ys) and rectangle.bottom() >= max(
            ys
        )
        axis: int = (
            (HIDE_Y if wide else HIDE_X)
            if wide != tall
            else (
                HIDE_Y if rectangle.width() >= rectangle.height() else HIDE_X
            )
        )
        low: float = rectangle.top() if axis == HIDE_Y else rectangle.left()
        high: float = (
            rectangle.bottom() if axis == HIDE_Y else rectangle.right()
        )
        laid: Hide | str = lay(
            self.drawing.points, axis, low, high, self.fillet_arcs(axis)
        )
        if isinstance(laid, str):
            self.message = laid
            self.scene().update()
            return
        # It reaches across as far as dragged, and at least a step
        # past the outline and its dimensions (#180).
        other: list[float] = [point[1 - axis] for point in self.drawing.points]
        near: float = rectangle.left() if axis == HIDE_Y else rectangle.top()
        far: float = (
            rectangle.right() if axis == HIDE_Y else rectangle.bottom()
        )
        least: tuple[float, float] = self.reach(axis)
        laid.under = min(other) - min(near, least[0] - self.step())
        laid.over = max(far, least[1] + self.step()) - max(other)
        self.history.remember(self.drawing.snapshot())
        self.drawing.hides.append(laid)
        self.message = ""
        self.make_squares()
        self.viewport().update()
        self.scene().update()

    # Method `OutlineView.reach()`:
    def reach(self, axis: int) -> tuple[float, float]:
        """Return how far the outline and its dimensions reach across a
        strip's axis: a strip must reach past both (#180).

        Arguments:
        * `axis` (`int`): The strip's axis, `HIDE_X` or `HIDE_Y`.

        Returns:
        * (`tuple[float, float]`): The low and high ends, across.
        """
        box: QRectF = self.outline.boundingRect()
        measure: DimensionItem
        for measure in self.measures:
            if self.drawing.dimensions[
                measure.index
            ].kind == RADIUS or is_mark(
                self.drawing.dimensions[measure.index]
            ):
                continue
            if self.drawing.dimensions[measure.index].kind == ANGLE:
                box = box.united(measure.arc_path().boundingRect())
            else:
                corner: QPointF
                for corner in measure.ends():
                    box = box.united(QRectF(corner, corner))
        return (
            (box.left(), box.right())
            if axis == HIDE_Y
            else (box.top(), box.bottom())
        )

    # Method `OutlineView.fillet_arcs()`:
    def fillet_arcs(self, axis: int) -> list[tuple[float, float]]:
        """Return where along an axis each fillet's arc runs, as drawn.

        Arguments:
        * `axis` (`int`): `HIDE_X` or `HIDE_Y`.

        Returns:
        * (`list[tuple[float, float]]`): Each arc's two ends.
        """
        return [
            (
                (fillet.arc.start[1], fillet.arc.end[1])
                if axis == HIDE_Y
                else (fillet.arc.start[0], fillet.arc.end[0])
            )
            for fillet in fillet_arcs(
                self.drawing, self.drawing.scale
            ).values()
        ]

    # Method `OutlineView.toggle_overview()`:
    def toggle_overview(self) -> None:
        """[Overview]: the whole drawing, strips shaded, or the working
        view, strips cut out (#168)."""
        self.overview = not self.overview
        self.hiding = False
        self.place_handles()
        self.restyle()
        self.viewport().update()
        self.scene().update()

    # Method `OutlineView.toggle_revolve()`:
    def toggle_revolve(self) -> None:
        """[Revolve]: turn revolving about the Y axis on or off, as one
        change; refused while a corner is left of the axis.  Turned on,
        a corner drawn on the origin is marked onto both axes: the
        tool's tip (`T.tfo~6.5` #448)."""
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
        tip: int = next(
            (
                corner
                for corner, (x, y) in enumerate(self.drawing.points)
                if abs(x) <= ON_AXIS and abs(y) <= ON_AXIS
            ),
            -1,
        )
        if (
            self.drawing.revolve
            and tip >= 0
            and not tip_on_origin(self.drawing.dimensions)
        ):
            kind: str
            for kind in (HORIZONTAL, VERTICAL):
                self.drawing.dimensions.append(
                    Dimension("", kind, ORIGIN, tip)
                )
            self.make_squares()
        self.message = ""
        self.outline.refresh()
        self.resetCachedContent()
        self.follow()

    # Method `OutlineView.turn_view()`:
    def turn_view(self) -> None:
        """Show the drawing turned its `turns` quarter turns clockwise
        (#300), Y up, at the zoom it has now."""
        zoom: float = self.zoom()
        turned: QTransform = QTransform()
        turned.scale(zoom, -zoom)
        # With Y flipped, a negative angle turns clockwise on screen.
        turned.rotate(-90.0 * (self.drawing.turns % 4))
        self.setTransform(turned)

    # Method `OutlineView.rotate_diagram()`:
    def rotate_diagram(self) -> None:
        """[Rotate Diagram]: turn the drawing a quarter turn clockwise
        (#300), as one change; four turns come back to the start.  The
        letters stay upright, and the file keeps the tool axis along
        Y (only `turns` is saved)."""
        self.history.remember(self.drawing.snapshot())
        self.drawing.turns = (self.drawing.turns + 1) % 4
        self.turn_view()
        self.fit()
        self.follow()

    # Method `OutlineView.step_font()`:
    def step_font(self, way: int) -> None:
        """[Font +] (`way` 1) or [Font -] (`way` -1) (#273): the
        selected dimensions' letters a `FONT_STEP` bigger or smaller
        (at most `FONT_STEPS` steps either way), or with none
        selected, the whole diagram's; one change each press.

        Arguments:
        * `way` (`int`): 1 bigger, -1 smaller.
        """
        self.history.remember(self.drawing.snapshot())
        if self.chosen_dimensions:
            index: int
            for index in self.chosen_dimensions:
                dimension: Dimension = self.drawing.dimensions[index]
                dimension.font_step = max(
                    -FONT_STEPS, min(FONT_STEPS, dimension.font_step + way)
                )
        else:
            # The height the diagram has now, picked when never set.
            height: float = (
                self.drawing.text_height
                or outline_sheet(self.drawing).text_height
            )
            self.drawing.text_height = height * FONT_STEP**way
        self.message = ""
        self.follow()
        self.scene().update()

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
            self.turn_view()
            self.make_squares()
            self.letters_changed()

    # Method `OutlineView.restyle()`:
    def restyle(self) -> None:
        """Color everything for the scheme in use (light or dark)."""
        scheme: theme.Colors = theme.colors()
        self.setBackgroundBrush(QColor(scheme.paper))
        pen: QPen = QPen(QColor(scheme.ink), THIN_PIXELS)
        pen.setCosmetic(True)
        # Every circle alike, in the handle color (yellow, #237): hollow,
        # so the edges show through; filled when selected, not told by
        # color alone (#124, #129).  A corner not dimensioned yet has a
        # thick ring in the warning color (orange; dashes left gaps on
        # so small a circle, #133).
        ring: QPen = QPen(QColor(scheme.handle), 2.0)
        ring.setCosmetic(True)
        warned: QPen = QPen(QColor(scheme.warning), 3.0)
        bad: QPen = QPen(QColor(scheme.problem), 3.0)
        bad.setCosmetic(True)
        warned.setCosmetic(True)
        warned.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        chosen: QBrush = QBrush(QColor(scheme.handle))
        hollow: QBrush = QBrush(Qt.BrushStyle.NoBrush)

        # The origin is a filled square, a fixed point; selected, its
        # ring is thick.
        thick: QPen = QPen(QColor(scheme.ink), 3.0)
        thick.setCosmetic(True)
        self.origin.setPen(thick if ORIGIN in self.chosen_points else pen)
        self.origin.setBrush(QBrush(QColor(scheme.ink)))
        missing: set[int] = {
            corner
            for corner, _ in self.solution.missing(len(self.drawing.points))
        }
        square: CornerCircle
        for square in self.squares:
            loose: bool = bool(self.drawing.dimensions) and (
                square.index in missing
            )
            square.setPen(
                bad
                if square.index in self.trouble
                else warned
                if loose
                else ring
            )
            square.setBrush(
                chosen if square.index in self.chosen_points else hollow
            )
            # Lit (#199, #224): bigger, its ring thick; not by color
            # alone.
            if self.corner_lit(square.index):
                square.setPen(thick)
            square.setScale(
                LIT_SCALE if self.corner_lit(square.index) else 1.0
            )
            square.setToolTip(self.corner_tip(square.index))
        self.origin.setToolTip("The origin: (0, 0)")
        handle: EdgeHandle
        for handle in self.handles:
            handle.setPen(ring)
            handle.setBrush(
                chosen if handle.index in self.chosen_edges else hollow
            )
        # A strip's circles have a paper inside, so the hatching does
        # not run through them (#177); they look hollow all the same.
        grip: StripHandle
        for grip in self.grips:
            grip.setPen(ring)
            grip.setBrush(QBrush(QColor(scheme.paper)))
        circle: DimensionHandle
        for circle in self.circles:
            circle.setPen(ring)
            circle.setBrush(
                chosen if circle.index in self.chosen_dimensions else hollow
            )
        # The working view with cuts: look and pan only (#171), since
        # its items are not where they are drawn.
        self.setInteractive(self.overview or not self.drawing.hides)
        self.viewport().update()
        self.restyled()

    # Method `OutlineView.set_up_view()`:
    def set_up_view(self) -> None:
        """Make Y point up and hide the scroll bars (empty space is
        dragged to pan).  Zooming keeps the point under the pointer
        itself (`wheelEvent()`): Qt's `AnchorUnderMouse` asks where the
        cursor is on the screen, which Wayland does not tell."""
        self.turn_view()
        anchor: QGraphicsView.ViewportAnchor = (
            QGraphicsView.ViewportAnchor.NoAnchor
        )
        self.setTransformationAnchor(anchor)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

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
        # A quarter turn moves the scale off the diagonal (#300).
        return math.hypot(self.transform().m11(), self.transform().m12())

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
        """Zoom about the pointer, within `ZOOM_LIMITS`: the point
        under it stays under it.

        Arguments:
        * `event` (`QWheelEvent`): The wheel turned, where it was.
        """
        notches: float = event.angleDelta().y() / 120.0
        factor: float = ZOOM_PER_NOTCH**notches
        low: float
        high: float
        low, high = ZOOM_LIMITS
        wanted: float = min(max(self.zoom() * factor, low), high)
        factor = wanted / self.zoom()
        pointer: QPointF = event.position()
        held: QPointF = self.mapToScene(pointer.toPoint())
        self.scale(factor, factor)

        # Scroll so that the point held is back under the pointer.
        moved: QPointF = QPointF(self.mapFromScene(held)) - pointer
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() + round(moved.x())
        )
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() + round(moved.y())
        )
        self.place_handles()
        event.accept()

    # Method `OutlineView.toggle_marks()`:
    def toggle_marks(self) -> None:
        """[Show Marks] (#451): draw the marks, or hide them."""
        self.marks_shown = not self.marks_shown
        index: int
        measure: DimensionItem
        for index, measure in enumerate(self.measures):
            measure.setVisible(
                self.marks_shown or not is_mark(self.drawing.dimensions[index])
            )
        circle: DimensionHandle
        for circle in self.circles:
            circle.place()
        self.viewport().update()

    # Method `OutlineView.toggle_grid()`:
    def toggle_grid(self) -> None:
        """Show the grid, or hide it."""
        self.grid_shown = not self.grid_shown
        self.viewport().update()

    # Method `OutlineView.drawForeground()`:
    def drawForeground(
        self, painter: QPainter, exposed: QRectF | QRect
    ) -> None:
        """Shade the hide strips in the overview (#168), or cut them out
        in the working view (#170); write the fillets' note in the
        lower left, when any fillet has no radius of its own (#118)."""
        if self.overview:
            self.shade_hides(painter, QRectF(exposed))
        elif self.drawing.hides:
            self.draw_cut(painter, QRectF(exposed))
        note: str = self.drawing.note_radius
        if not any(
            dimension.kind == RADIUS and dimension.letter == note
            for dimension in self.drawing.dimensions
        ):
            return
        painter.save()
        painter.resetTransform()
        painter.setPen(QColor(theme.colors().ink))
        painter.setFont(QFont("sans-serif", LETTER_POINTS))
        painter.drawText(
            QRectF(
                LETTER_GAP_PIXELS * 2,
                0.0,
                self.viewport().width(),
                self.viewport().height() - LETTER_GAP_PIXELS * 2,
            ),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
            f"All undimensioned fillets are radius {note}",
        )
        painter.restore()

    # Method `OutlineView.cut_offsets()`:
    def cut_offsets(self, axis: int) -> list[tuple[float, float, float]]:
        """Return the working view's pieces along an axis: each from
        one cut to the next, and how far it is drawn shifted (#170).

        Arguments:
        * `axis` (`int`): `HIDE_X` or `HIDE_Y` (cuts across X, or Y).

        Returns:
        * (`list[tuple[float, float, float]]`): Each piece's low and
          high ends, and its shift (drawing steps).
        """
        gap: float = GAP_PIXELS / max(self.zoom(), 1e-12)
        cuts: list[tuple[float, float]] = sorted(
            strip(self.drawing.points, hide)
            for hide in self.drawing.hides
            if hide.axis == axis
        )
        pieces: list[tuple[float, float, float]] = []
        start: float = -FAR
        shift: float = 0.0
        low: float
        high: float
        for low, high in cuts:
            pieces.append((start, low, shift))
            shift -= high - low - gap
            start = high
        pieces.append((start, FAR, shift))
        return pieces

    # Method `OutlineView.draw_cut()`:
    def draw_cut(self, painter: QPainter, exposed: QRectF) -> None:
        """Draw the working view: the drawing again, piece by piece, each
        shifted to close up the hidden stretches, a gap at each cut with
        a long break line on each side (#170).

        Arguments:
        * `painter` (`QPainter`): What draws, in scene coordinates.
        * `exposed` (`QRectF`): What is shown (cleared first).
        """
        painter.fillRect(exposed, QColor(theme.colors().paper))

        # The grid stays under the pieces (#443): clearing hid it.
        if self.grid_shown:
            pen: QPen = QPen(QColor(theme.colors().quiet), THIN_PIXELS)
            pen.setCosmetic(True)
            self.draw_grid(painter, exposed, pen)
        across_x: list[tuple[float, float, float]] = self.cut_offsets(HIDE_X)
        across_y: list[tuple[float, float, float]] = self.cut_offsets(HIDE_Y)
        left: float
        right: float
        dx: float
        for left, right, dx in across_x:
            bottom: float
            top: float
            dy: float
            for bottom, top, dy in across_y:
                source: QRectF = QRectF(
                    left, bottom, right - left, top - bottom
                )
                # Clipped to its piece: items reaching into a hidden
                # stretch are cut there, not drawn on across the gap.
                painter.save()
                painter.setClipRect(source.translated(dx, dy))
                self.scene().render(
                    painter,
                    source.translated(dx, dy),
                    source,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                )
                painter.restore()
        self.draw_breaks(painter, across_x, across_y)

    # Method `OutlineView.draw_breaks()`:
    def draw_breaks(
        self,
        painter: QPainter,
        across_x: list[tuple[float, float, float]],
        across_y: list[tuple[float, float, float]],
    ) -> None:
        """Draw a long break line on each side of every cut: straight,
        with a zigzag in its middle, the two meshing (#170); only where
        the cut crosses the part, edge to edge, stopping at another
        cut's gap (#185).

        Arguments:
        * `painter` (`QPainter`): What draws, in scene coordinates.
        * `across_x` (`list[tuple[float, float, float]]`): The pieces
          along X, from `cut_offsets()`.
        * `across_y` (`list[tuple[float, float, float]]`): Along Y.
        """
        pen: QPen = QPen(QColor(theme.colors().ink), THIN_PIXELS)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        hide: Hide
        for hide in self.drawing.hides:
            pieces: list[tuple[float, float, float]] = (
                across_y if hide.axis == HIDE_Y else across_x
            )
            others: list[tuple[float, float, float]] = (
                across_x if hide.axis == HIDE_Y else across_y
            )
            holes: list[tuple[float, float]] = [
                strip(self.drawing.points, other)
                for other in self.drawing.hides
                if other.axis != hide.axis
            ]
            # Each side of the cut where it really is, then shifted
            # with its piece.
            side: float
            for side in strip(self.drawing.points, hide):
                at: float = side + shift_at(pieces, side)
                start: float
                end: float
                for start, end in minus(
                    inside_spans(
                        self.drawing.points,
                        hide.axis,
                        side,
                        self.drawing.revolve,
                    ),
                    holes,
                ):
                    shift: float = shift_at(others, (start + end) / 2.0)
                    painter.drawPath(
                        self.zigzag(hide.axis, at, start + shift, end + shift)
                    )
            self.draw_esses(painter, hide, pieces, others)

    # Method `OutlineView.draw_esses()`:
    def draw_esses(
        self,
        painter: QPainter,
        hide: Hide,
        pieces: list[tuple[float, float, float]],
        others: list[tuple[float, float, float]],
    ) -> None:
        """End each dimension line a cut chops with a small S on each
        side of the gap, the same way round, so the hump of one matches
        the valley of the other (#185).

        Arguments:
        * `painter` (`QPainter`): What draws, pen set.
        * `hide` (`Hide`): The cut.
        * `pieces` (`list[tuple[float, float, float]]`): The pieces
          along the cut's axis.
        * `others` (`list[tuple[float, float, float]]`): Across it.
        """
        measure: DimensionItem
        for measure in self.measures:
            dimension: Dimension = self.drawing.dimensions[measure.index]
            if dimension.kind in (ANGLE, RADIUS) or is_mark(dimension):
                continue
            start: QPointF
            end: QPointF
            _, _, start, end = measure.ends()
            first: float = start.y() if hide.axis == HIDE_Y else start.x()
            last: float = end.y() if hide.axis == HIDE_Y else end.x()
            side: float
            for side in strip(self.drawing.points, hide):
                if (first - side) * (last - side) >= 0.0:
                    continue  # The line does not cross this side.
                meets: QPointF = start + (end - start) * (
                    (side - first) / (last - first)
                )
                across_at: float = (
                    meets.x() if hide.axis == HIDE_Y else meets.y()
                )
                painter.drawPath(
                    self.ess(
                        hide.axis,
                        side + shift_at(pieces, side),
                        across_at + shift_at(others, across_at),
                    )
                )

    # Method `OutlineView.ess()`:
    def ess(self, axis: int, at: float, across_at: float) -> QPainterPath:
        """Return a small S ending a dimension line at a cut's side: it
        lies across the line (#187), its middle exactly at the line's
        end (#188); the same shape on both sides, so the hump of one
        faces the valley of the other.

        Arguments:
        * `axis` (`int`): The cut's axis (`HIDE_Y`: the dimension line
          runs along Y, the S lies along X).
        * `at` (`float`): The cut's side, along the axis.
        * `across_at` (`float`): The dimension line, across it.

        Returns:
        * (`QPainterPath`): The S.
        """
        long: float = ESS_PIXELS / max(self.zoom(), 1e-12)
        wide: float = long / 2.0

        # Function `point()`:
        def point(along: float, off: float) -> QPointF:
            """Return a point along the line and off to its side."""
            return (
                QPointF(across_at + off, at + along)
                if axis == HIDE_Y
                else QPointF(at + along, across_at + off)
            )

        # Across the line, like a small break line (#187), its middle
        # exactly at the line's end (#188): the same way round on either
        # side.
        path: QPainterPath = QPainterPath(point(0.0, -long))
        path.cubicTo(
            point(wide, -long / 3.0),
            point(-wide, long / 3.0),
            point(0.0, long),
        )
        return path

    # Method `OutlineView.zigzag()`:
    def zigzag(
        self, axis: int, at: float, near: float, far: float
    ) -> QPainterPath:
        """Return a long break line: straight across, with a zigzag in
        its middle that goes the same way on both sides of a cut, so
        the two mesh (#170), as the grid plate's sketch does.

        Arguments:
        * `axis` (`int`): The cut's axis (`HIDE_Y`: a line along X).
        * `at` (`float`): Where the line is, along the axis.
        * `near` (`float`): Where it starts, across.
        * `far` (`float`): Where it ends.

        Returns:
        * (`QPainterPath`): The line.
        """
        half: float = ZIG_HALF_PIXELS / max(self.zoom(), 1e-12)
        high: float = ZIG_HIGH_PIXELS / max(self.zoom(), 1e-12)
        middle: float = (near + far) / 2.0
        steps: list[tuple[float, float]] = [
            (near, 0.0),
            (middle - half, 0.0),
            (middle - half / 3.0, high),
            (middle + half / 3.0, -high),
            (middle + half, 0.0),
            (far, 0.0),
        ]
        path: QPainterPath = QPainterPath()
        index: int
        along: float
        off: float
        for index, (along, off) in enumerate(steps):
            point: QPointF = (
                QPointF(along, at + off)
                if axis == HIDE_Y
                else QPointF(at + off, along)
            )
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        return path

    # Method `OutlineView.covering()`:
    def covering(self) -> set[int]:
        """Return the hide strips that cover a dimension's letter (#182):
        the working view would leave it out.  The user moves the strip;
        letters are never moved for it.  Marks are not in the diagram
        (#451), so a strip may cover them.

        Returns:
        * (`set[int]`): The strips, by index.
        """
        boxes: list[QRectF] = [
            box
            for measure in self.measures
            if measure.index < len(self.drawing.dimensions)
            and not is_mark(self.drawing.dimensions[measure.index])
            and (box := measure.letter_box()) is not None
        ]
        found: set[int] = set()
        index: int
        hide: Hide
        for index, hide in enumerate(self.drawing.hides):
            low: float
            high: float
            low, high = strip(self.drawing.points, hide)
            near: float
            far: float
            near, far = across(self.drawing.points, hide)
            # Any part of a letter under the strip counts (#322): its
            # box overlaps the strip both along and across.
            letter: QRectF
            for letter in boxes:
                ends: tuple[float, float, float, float] = (
                    (
                        letter.top(),
                        letter.bottom(),
                        letter.left(),
                        letter.right(),
                    )
                    if hide.axis == HIDE_Y
                    else (
                        letter.left(),
                        letter.right(),
                        letter.top(),
                        letter.bottom(),
                    )
                )
                if (
                    ends[0] < high
                    and ends[1] > low
                    and ends[2] <= far
                    and ends[3] >= near
                ):
                    found.add(index)
        return found

    # Method `OutlineView.shade_hides()`:
    def shade_hides(self, painter: QPainter, _rect: QRectF) -> None:
        """Shade each hide strip across the outline, with a margin, so
        its sides can be reached (#173): hatched, so it is told by more
        than its color.

        Arguments:
        * `painter` (`QPainter`): What draws, in scene coordinates.
        * `_rect` (`QRectF`): What is shown.
        """
        quiet: QColor = QColor(theme.colors().quiet)
        pen: QPen = QPen(quiet, THIN_PIXELS)
        pen.setCosmetic(True)
        painter.save()
        painter.setPen(pen)
        painter.setBrush(QBrush(quiet, Qt.BrushStyle.BDiagPattern))
        # A strip covering a letter or glyph is red (#182).
        red: QPen = QPen(QColor(theme.colors().problem), THICK_PIXELS)
        red.setCosmetic(True)
        covering: set[int] = self.covering()
        index: int
        hide: Hide
        for index, hide in enumerate(self.drawing.hides):
            painter.setPen(red if index in covering else pen)
            painter.setBrush(
                QBrush(
                    QColor(theme.colors().problem)
                    if index in covering
                    else quiet,
                    Qt.BrushStyle.BDiagPattern,
                )
            )
            low: float
            high: float
            low, high = strip(self.drawing.points, hide)
            near: float
            far: float
            near, far = across(self.drawing.points, hide)
            painter.drawRect(
                QRectF(near, low, far - near, high - low)
                if hide.axis == HIDE_Y
                else QRectF(low, near, high - low, far - near)
            )
        painter.restore()

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
# A window holds its parts and the letters' state, and answers each of
# its buttons and the table's signals with a method of its own.
# pylint: disable-next=too-many-instance-attributes,too-many-public-methods
class OutlineEditor(QWidget):
    """The editor's window: the mode bar, the drawing, the letters.

    Attributes:
    * `button_actions` (`dict[str, QAction]`): What each button does,
      by its word (`"Grid"`, ...); its state is the buttons'.
    * `button_tabs` (`QTabWidget`): The buttons in tabs (#319).
    * `buttons` (`dict[str, QToolButton]`): Each word's first button.
    * `keys` (`dict[str, QShortcut]`): Each button's key, by its word.
    * `drawing` (`Drawing`): The outline being drawn.
    * `new_fillet` (`QPushButton`): [New Fillet Dimension], shown
      in [Fillets] only (#214).
    * `tabs` (`QTabBar`): [Dimensions] (every letter) and [Fillets]
      (only those checked "Fillet", #213), over the one table.
    * `problems` (`QLabel`): The letters' problems, a line each, red,
      right under the table (#141).
    * `letter_lines` (`list[str]`): The letters' problems, a line
      each, shown above the outline's own (`show_problems()`).
    * `renaming` (`dict[int, str]`): By table row, a letter's last good
      name while its name is being typed and is not good yet: the
      name its uses still carry (`T.tfo~6.5` #441).
    * `splitter` (`QSplitter`): The drawing over the table.
    * `status` (`QLabel`): The last refusal, under the button tabs.
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

        # The buttons in tabs (#319) over the status line.
        self.button_tabs: QTabWidget = QTabWidget()
        self.button_tabs.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        layout.addWidget(self.button_tabs)
        self.status: QLabel = QLabel("")
        self.status.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.status)

        # The drawing over the letters, a bar between them (#27); the
        # drawing in two tabs: the working view, and the diagram it
        # makes as SVG, redrawn each time it is shown (`T.sfoe~6.4`
        # #248, #189).
        self.splitter: QSplitter = QSplitter(Qt.Orientation.Vertical)
        self.picture: QSvgWidget = QSvgWidget()
        self.views: QTabWidget = self.drawing_tabs()
        self.splitter.addWidget(self.views)
        self.table: QTableWidget = QTableWidget(0, len(COLUMNS))
        self.problems: QLabel = QLabel("")
        self.renaming: dict[int, str] = {}
        self.letter_lines: list[str] = []
        self.tabs: QTabBar = QTabBar()
        self.new_fillet: QPushButton = QPushButton("New Fillet Dimension")
        self.splitter.addWidget(self.letters_area())
        self.splitter.setSizes([450, 150])
        layout.addWidget(self.splitter)
        self.make_buttons()
        self.hook_view()
        self.fill_table()
        self.table.itemChanged.connect(self.letter_edited)
        self.show_message()
        self.resize(800, 600)

    # Method `OutlineEditor.make_buttons()`:
    def make_buttons(self) -> None:
        """Make the buttons (#319): each word one `QAction` with its
        key, shown as a button on every tab listing it, so that its
        checked and enabled state is the same on all of them."""
        self.button_actions: dict[str, QAction] = {}
        self.buttons: dict[str, QToolButton] = {}
        self.keys: dict[str, QShortcut] = {}
        word: str
        key: str
        for word, key in BUTTON_KEYS:
            # [Dim. Kind] cycles, so it shows a cycle arrow (U+21BB).
            cycle: str = " \u21bb" if word == "Dim. Kind" else ""
            action: QAction = QAction(f"{word}{cycle} ({key})", self)
            # A button's own shortcut never fired; a `QShortcut` does.
            shortcut: QShortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(action.trigger)
            self.keys[word] = shortcut
            self.button_actions[word] = action
        for word in ("Grid", "Snap", "Revolve", "Overview", "Show Marks"):
            self.button_actions[word].setCheckable(True)
        for word in ("Grid", "Snap"):
            self.button_actions[word].setChecked(True)

        # Each tab a row of buttons; `buttons` keeps a word's first.
        title: str
        words: tuple[str, ...]
        for title, words in BUTTON_TABS:
            page: QWidget = QWidget()
            row: QHBoxLayout = QHBoxLayout(page)
            row.setContentsMargins(2, 2, 2, 2)
            for word in words:
                button: QToolButton = QToolButton()
                button.setDefaultAction(self.button_actions[word])
                button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                row.addWidget(button)
                self.buttons.setdefault(word, button)
            row.addStretch(1)
            self.button_tabs.addTab(page, title)

        # What each button does.
        does: dict[str, Callable[[], None]] = {
            "Grid": self.view.toggle_grid,
            "Snap": self.toggle_snap,
            "Fit": self.view.fit,
            "Delete": self.delete,
            "Dimension": self.view.dimension_selected,
            "Dim. Kind": self.view.cycle_kind,
            "Show Marks": self.view.toggle_marks,
            "Revolve": self.toggle_revolve,
            "Rotate Diagram": self.view.rotate_diagram,
            "Font +": partial(self.view.step_font, 1),
            "Font -": partial(self.view.step_font, -1),
            "Hide": self.view.start_hide,
            "Overview": self.toggle_overview,
            "Undo": self.view.undo,
            "Redo": self.view.redo,
            "New Letter": self.new_letter,
        }
        does_it: Callable[[], None]
        for word, does_it in does.items():
            self.button_actions[word].triggered.connect(does_it)

    # Method `OutlineEditor.drawing_tabs()`:
    def drawing_tabs(self) -> QTabWidget:
        """Return the drawing's tabs: [Drawing], the working view, and
        [SVG], the diagram it makes, kept to its shape.

        Returns:
        * (`QTabWidget`): The tabs.
        """
        views: QTabWidget = QTabWidget()
        views.addTab(self.view, "Drawing")
        views.addTab(self.picture, "SVG")
        views.currentChanged.connect(self.show_svg)
        return views

    # Method `OutlineEditor.show_svg()`:
    def show_svg(self, tab: int) -> None:
        """Draw the [SVG] tab again when it is chosen: the outline's
        diagram (`outline_sheet()`), in the theme's ink and paper.

        Arguments:
        * `tab` (`int`): The tab now shown.
        """
        if self.views.widget(tab) is not self.picture:
            return
        colors: theme.Colors = theme.colors()
        self.picture.load(
            svg(
                outline_sheet(self.drawing),
                colors.ink,
                colors.paper,
            ).encode("utf-8")
        )
        # Kept to its shape: each load resets this.
        self.picture.renderer().setAspectRatioMode(
            Qt.AspectRatioMode.KeepAspectRatio
        )

    # Method `OutlineEditor.hook_view()`:
    def hook_view(self) -> None:
        """Have the view tell the window what changed."""
        self.view.scene().changed.connect(self.show_message)
        self.view.letters_changed = self.fill_table
        self.view.released = self.save
        self.view.cleared = self.cleared
        self.view.lighted = self.frame_row
        self.table.cellClicked.connect(self.row_clicked)
        # Pointing at a row lights its letter's uses (#224); leaving
        # the table puts them out.
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self.hover_row)
        self.table.viewport().installEventFilter(self)

    # Method `OutlineEditor.eventFilter()`:
    def eventFilter(  # pylint: disable=invalid-name
        self, watched: QObject, event: QEvent
    ) -> bool:
        """Put the lit letter out when the pointer leaves the table.

        Arguments:
        * `watched` (`QObject`): The table's viewport.
        * `event` (`QEvent`): What happened to it.

        Returns:
        * (`bool`): Never taken: `False`.
        """
        if (
            watched is self.table.viewport()
            and event.type() == QEvent.Type.Leave
        ):
            self.view.light_letter("")
        return False

    # Method `OutlineEditor.hover_row()`:
    def hover_row(self, row: int, _column: int) -> None:
        """Light the uses of the letter pointed at (#224).

        Arguments:
        * `row` (`int`): The table row.
        """
        self.view.light_letter(
            ""
            if row < LETTER_ROW
            else self.drawing.letters[row - LETTER_ROW].letter
        )

    # Method `OutlineEditor.frame_row()`:
    def frame_row(self, corner: int) -> None:
        """Make the row of the letter rounding a corner pointed at bold
        (#224); every other row plain.

        Arguments:
        * `corner` (`int`): The corner, or -1.
        """
        letter: str = self.view.fillets().get(corner, "")
        self.table.blockSignals(True)
        index: int
        each: Letter
        for index, each in enumerate(self.drawing.letters):
            column: int
            for column in range(len(COLUMNS)):
                item: QTableWidgetItem | None = self.table.item(
                    LETTER_ROW + index, column
                )
                if item is not None:
                    font: QFont = item.font()
                    font.setBold(bool(letter) and each.letter == letter)
                    item.setFont(font)
        self.table.blockSignals(False)

    # Method `OutlineEditor.cleared()`:
    def cleared(self) -> None:
        """The drawing's selection is cleared: the table's too, and
        any armed letter (#214)."""
        self.table.clearSelection()
        self.arm(None)

    # Method `OutlineEditor.row_clicked()`:
    def row_clicked(self, row: int, _column: int) -> None:
        """A click on a [Fillets] row arms it, or disarms it if armed
        (#214).

        Arguments:
        * `row` (`int`): The table row.
        """
        if self.tabs.currentIndex() != FILLETS_TAB:
            return
        letter: str = (
            ""
            if row < LETTER_ROW
            else self.drawing.letters[row - LETTER_ROW].letter
        )
        self.arm(None if letter == self.view.armed else letter)

    # Method `OutlineEditor.arm()`:
    def arm(self, letter: str | None) -> None:
        """Arm a fillet letter ("" for "No fillet"), or disarm (`None`);
        arming also fillets the corners already selected (#218).

        Arguments:
        * `letter` (`str | None`): The letter.
        """
        self.view.armed = letter
        if letter is not None:
            corners: list[int] = [
                point for point in self.view.chosen_points if point != ORIGIN
            ]
            if corners:
                self.view.set_fillets(corners, letter)
        self.light_armed()
        self.show_message()

    # Method `OutlineEditor.light_armed()`:
    def light_armed(self) -> None:
        """Select the armed letter's row, and only it."""
        self.table.clearSelection()
        armed: str | None = self.view.armed
        if armed is None:
            return
        rows: list[int] = [0] + [
            LETTER_ROW + index
            for index, letter in enumerate(self.drawing.letters)
            if letter.letter == armed
        ]
        self.table.selectRow(rows[-1] if armed else 0)

    # Method `OutlineEditor.show_rows()`:
    def show_rows(self) -> None:
        """Show every letter in [Dimensions], only the fillet radii in
        [Fillets], with [New Fillet Dimension] there (#213, #214)."""
        fillets: bool = self.tabs.currentIndex() == FILLETS_TAB
        self.table.setRowHidden(0, not fillets)
        index: int
        letter: Letter
        for index, letter in enumerate(self.drawing.letters):
            self.table.setRowHidden(
                LETTER_ROW + index, fillets and not letter.fillet
            )
        self.new_fillet.setVisible(fillets)
        # In [Fillets] a click arms a row (#214), so a cell is edited
        # only by a double click there.
        triggers: type[QAbstractItemView.EditTrigger] = (
            QAbstractItemView.EditTrigger
        )
        self.table.setEditTriggers(
            triggers.DoubleClicked | triggers.EditKeyPressed
            if fillets
            else triggers.CurrentChanged
            | triggers.SelectedClicked
            | triggers.DoubleClicked
            | triggers.EditKeyPressed
        )
        if not fillets:
            self.arm(None)

    # Method `OutlineEditor.add_fillet()`:
    def add_fillet(self) -> None:
        """[New Fillet Dimension]: a new letter, checked "Fillet",
        ready to be named (#214)."""
        self.drawing.letters.append(
            replace(
                next_letter(self.drawing.letters),
                name="Fillet radius",
                fillet=True,
            )
        )
        self.fill_table()
        self.table.setCurrentCell(len(self.drawing.letters), 1)

    # Method `OutlineEditor.letters_area()`:
    def letters_area(self) -> QWidget:
        """Return the tab bar, [Dimensions] and [Fillets], over the
        letters' table (#213), with the problems right under them, in
        red, wrapped so the window never widens (#141).

        Returns:
        * (`QWidget`): The tabs and the problem line.
        """
        self.table.setHorizontalHeaderLabels([title for title, _ in COLUMNS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setItemDelegate(LiveDelegate(self))
        # One click on a cell edits it, so typing goes into the cell:
        # a key typed onto a cell not being edited half-started an edit
        # and could fire a button's key (`n` of `in`: [Dimension]).
        triggers: type[QAbstractItemView.EditTrigger] = (
            QAbstractItemView.EditTrigger
        )
        self.table.setEditTriggers(
            triggers.CurrentChanged
            | triggers.SelectedClicked
            | triggers.DoubleClicked
            | triggers.EditKeyPressed
        )
        self.problems.setWordWrap(True)
        self.problems.setStyleSheet(f"color: {theme.colors().problem}")
        area: QWidget = QWidget()
        stack: QVBoxLayout = QVBoxLayout(area)
        stack.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab("Dimensions")
        self.tabs.addTab("Fillets")
        self.tabs.currentChanged.connect(self.show_rows)
        self.new_fillet.clicked.connect(self.add_fillet)
        self.new_fillet.setVisible(False)
        stack.addWidget(self.tabs)
        stack.addWidget(self.table)
        stack.addWidget(self.new_fillet, 0, Qt.AlignmentFlag.AlignLeft)
        stack.addWidget(self.problems)
        return area

    # Method `OutlineEditor.fill_table()`:
    def fill_table(self) -> None:
        """Show every letter, a row each, its problems marked.

        No cell is left current: one would be edited at once (a click
        edits), taking the keys the buttons answer to.
        """
        self.table.blockSignals(True)
        self.renaming.clear()
        self.table.setRowCount(LETTER_ROW + len(self.drawing.letters))
        column: int
        text: str
        for column, text in enumerate(NO_FILLET):
            fixed: QTableWidgetItem = QTableWidgetItem(text)
            fixed.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(0, column, fixed)
        index: int
        letter: Letter
        for index, letter in enumerate(self.drawing.letters):
            attribute: str
            for column, (_, attribute) in enumerate(COLUMNS):
                self.table.setItem(
                    LETTER_ROW + index, column, self.cell(letter, attribute)
                )
        self.table.setCurrentCell(-1, -1)
        self.table.blockSignals(False)
        self.show_rows()
        self.light_armed()
        self.view.setFocus()
        self.check_letters()

    # Method `OutlineEditor.cell()`:
    @staticmethod
    def cell(letter: Letter, attribute: str) -> QTableWidgetItem:
        """Return a letter's cell: its text, or for "Fillet" a check
        box that a click flips, never edited as text (#213).  A formula
        letter's value cell shows `= ` and its formula (#430).

        Arguments:
        * `letter` (`Letter`): The letter.
        * `attribute` (`str`): Its field shown (see `COLUMNS`).

        Returns:
        * (`QTableWidgetItem`): The cell.
        """
        if attribute == "default" and letter.formula:
            return QTableWidgetItem(f"= {letter.formula}")
        if attribute != "fillet":
            return QTableWidgetItem(getattr(letter, attribute))
        item: QTableWidgetItem = QTableWidgetItem()
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
        )
        item.setCheckState(
            Qt.CheckState.Checked if letter.fillet else Qt.CheckState.Unchecked
        )
        return item

    # Method `OutlineEditor.new_letter()`:
    def new_letter(self) -> None:
        """Add a row for the first free letter, ready to be named; in
        [Fillets], a fillet radius (#214)."""
        if self.tabs.currentIndex() == FILLETS_TAB:
            self.add_fillet()
            return
        self.drawing.letters.append(next_letter(self.drawing.letters))
        self.fill_table()
        self.table.setCurrentCell(len(self.drawing.letters), 1)

    # Method `OutlineEditor.letter_edited()`:
    def letter_edited(self, item: QTableWidgetItem) -> None:
        """Keep a finished cell's text in its letter, then check them.

        Arguments:
        * `item` (`QTableWidgetItem`): The cell.
        """
        if item.row() < LETTER_ROW:
            return
        if COLUMNS[item.column()][1] == "fillet":
            letter: Letter = self.drawing.letters[item.row() - LETTER_ROW]
            checked: bool = item.checkState() == Qt.CheckState.Checked
            if not checked and self._uses(letter.letter, fillets=True):
                # Still a fillet radius somewhere (#225): stays checked.
                self.view.message = (
                    f"{letter.letter} rounds "
                    f"{self._uses(letter.letter, fillets=True)}: "
                    "it stays a fillet radius."
                )
                self.table.blockSignals(True)
                item.setCheckState(Qt.CheckState.Checked)
                self.table.blockSignals(False)
                self.view.light_letter(letter.letter)  # Its uses (#245).
                self.show_message()
                return
            letter.fillet = checked
            self.check_letters()
            self.save()
        else:
            self.keep(item.row(), item.column(), item.text())

    # Method `OutlineEditor.delete()`:
    def delete(self) -> None:
        """[Delete]: the selected corners and dimensions; with none,
        the letter armed in [Fillets] or the table's current row,
        refused while it is in use, its uses named (#215)."""
        view: OutlineView = self.view
        if view.chosen_points or view.chosen_dimensions:
            view.delete_selected()
            return
        letter: str = ""
        row: int = self.table.currentRow()
        if self.tabs.currentIndex() == FILLETS_TAB and view.armed:
            letter = view.armed
        elif row >= LETTER_ROW:
            letter = self.drawing.letters[row - LETTER_ROW].letter
        if not letter:
            view.delete_selected()  # Says what to select.
            return
        used: str = self._uses(letter)
        if used:
            view.light_letter(letter)  # Its uses shown (#245).
            view.message = f"{letter} is used by {used}: not deleted."
            view.scene().update()
            self.show_message()
            return
        view.history.remember(self.drawing.snapshot())
        self.drawing.letters[:] = [
            each for each in self.drawing.letters if each.letter != letter
        ]
        if self.drawing.note_radius == letter:
            self.drawing.note_radius = ""
        view.armed = None
        view.message = ""
        self.fill_table()
        self.save()

    # Method `OutlineEditor._uses()`:
    def _uses(self, letter: str, fillets: bool = False) -> str:
        """Return what uses a letter, in words ("" for nothing).

        Arguments:
        * `letter` (`str`): The letter.
        * `fillets` (`bool`): Only its fillets.

        Returns:
        * (`str`): E.g. "2 fillets and 1 dimension".
        """
        rounds: int = sum(
            1
            for dimension in self.drawing.dimensions
            if dimension.letter == letter and dimension.kind == RADIUS
        )
        sizes: int = (
            0
            if fillets
            else sum(
                1
                for dimension in self.drawing.dimensions
                if dimension.letter == letter and dimension.kind != RADIUS
            )
        )
        words: list[str] = [
            f"{count} {name}{'' if count == 1 else 's'}"
            for count, name in ((rounds, "fillet"), (sizes, "dimension"))
            if count
        ]
        return " and ".join(words)

    # Method `OutlineEditor.keep()`:
    def keep(self, row: int, column: int, text: str) -> None:
        """Keep a cell's text in its letter, then check the letters.

        A value starting `=` makes a formula letter (#430); any other
        makes it a letter given a value.  Formula letters' values are
        worked out again after every change.

        Arguments:
        * `row` (`int`): The letter's table row (see `LETTER_ROW`).
        * `column` (`int`): The cell's column (see `COLUMNS`).
        * `text` (`str`): The cell's text so far.
        """
        attribute: str = COLUMNS[column][1]
        letter: Letter = self.drawing.letters[row - LETTER_ROW]
        kept: str = text.strip()
        if attribute == "letter":
            self.rename(row, kept)
            refresh_formulas(self.drawing.letters)
            self.check_letters()
            self.save()
            return
        if attribute == "default":
            letter.formula = kept[1:].strip() if kept.startswith("=") else ""
            if letter.formula:
                kept = ""
        setattr(letter, attribute, kept)
        refresh_formulas(self.drawing.letters)
        self.check_letters()
        self.save()

    # Method `OutlineEditor.rename()`:
    def rename(self, row: int, name: str) -> None:
        """Rename a letter, and everything that uses it with it (#441):
        its dimensions, holes, the fillets' note letter and the
        formulas that name it.  Its uses follow only a good name, one
        not taken (`letter_problem()`), so that typing `OAL` through
        `O` and `OA`, or a name half typed, never leaves them blank.

        Arguments:
        * `row` (`int`): The letter's table row (see `LETTER_ROW`).
        * `name` (`str`): Its new name, as typed so far.
        """
        index: int = row - LETTER_ROW
        letter: Letter = self.drawing.letters[index]
        carried: str = self.renaming.get(row, letter.letter)
        letter.letter = name
        taken: bool = any(
            other.letter.lower() == name.lower()
            for place, other in enumerate(self.drawing.letters)
            if place != index
        )
        if taken or letter_problem(self.drawing.letters, index):
            self.renaming[row] = carried
            return
        self.renaming.pop(row, None)
        if carried == name:
            return
        dimension: Dimension
        for dimension in self.drawing.dimensions:
            if dimension.letter == carried:
                dimension.letter = name
        hole: Hole
        for hole in self.drawing.holes:
            if hole.letter == carried:
                hole.letter = name
        if self.drawing.note_radius == carried:
            self.drawing.note_radius = name
        pattern: re.Pattern[str] = re.compile(rf"\b{re.escape(carried)}\b")
        other: Letter
        for other in self.drawing.letters:
            if other.formula:
                other.formula = pattern.sub(name, other.formula)

    # Method `OutlineEditor.check_letters()`:
    def check_letters(self) -> None:
        """Mark each bad letter or default, and show the first problem."""
        self.table.blockSignals(True)
        bad: QColor = QColor(theme.colors().bad)
        problems: list[str] = []
        row: int
        letter: Letter
        trouble: dict[str, str] = self.fillet_trouble()
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
                    formula_problem(self.drawing.letters, row)
                    or value_problem(letter.default)
                    or use_problem(letter.letter, letter.default, kinds)
                    or trouble.get(letter.letter, ""),
                    2,
                ),
                (fillet_kind_problem(letter, kinds), 3),
            ):
                cell: QTableWidgetItem | None = self.table.item(
                    LETTER_ROW + row, column
                )
                if cell is not None:
                    cell.setBackground(bad if found else QColor(0, 0, 0, 0))
                    # A good formula letter's tip is its value (#430).
                    cell.setToolTip(
                        found
                        or (
                            f"= {letter.default}"
                            if column == 2 and letter.formula
                            else ""
                        )
                    )
                if found:
                    # A message naming its letter first is not given it
                    # twice (#143).
                    problems.append(
                        found
                        if found.startswith(f"{letter.letter} ")
                        else f"{letter.letter}: {found}"
                    )
        self.table.blockSignals(False)
        self.letter_lines = problems
        self.show_message()

    # Method `OutlineEditor.fillet_trouble()`:
    def fillet_trouble(self) -> dict[str, str]:
        """Find the fillets too big for their edges (#127), mark them
        in the drawing, and return each one's problem by letter.

        Returns:
        * (`dict[str, str]`): The first problem of each fillet letter.
        """
        self.view.trouble = fillet_problems(
            self.drawing.points, self.drawing.letters, self.drawing.dimensions
        )
        self.view.follow()  # The drawing follows the values (#148).
        letters: dict[int, str] = {
            dimension.start: dimension.letter
            for dimension in self.drawing.dimensions
            if dimension.kind == RADIUS
        }
        trouble: dict[str, str] = {}
        corner: int
        message: str
        for corner, message in self.view.trouble.items():
            trouble.setdefault(letters[corner], message)
        return trouble

    # Method `OutlineEditor.toggle_snap()`:
    def toggle_snap(self) -> None:
        """Turn snapping on or off, as [Snap] now shows."""
        self.view.snap_on = self.button_actions["Snap"].isChecked()

    # Method `OutlineEditor.toggle_overview()`:
    def toggle_overview(self) -> None:
        """[Overview]: switch views, the button showing which."""
        self.view.toggle_overview()
        self.button_actions["Overview"].setChecked(self.view.overview)

    # Method `OutlineEditor.toggle_revolve()`:
    def toggle_revolve(self) -> None:
        """[Revolve]: revolve or not, the button showing the result
        (a refusal leaves it as it was)."""
        self.view.toggle_revolve()
        self.button_actions["Revolve"].setChecked(self.view.drawing.revolve)

    # Method `OutlineEditor.save()`:
    def save(self) -> None:
        """Rewrite the file if the outline changed (not mid-drag: the
        view saves again when the mouse button comes up), and its
        diagram beside it (`svg_path()`, #248), written too when
        missing."""
        if self.path is None or QApplication.mouseButtons() != (
            Qt.MouseButton.NoButton
        ):
            return
        text: str = outline_text(self.drawing)
        picture: Path = svg_path(self.path)
        if text != self.saved or (self.path.exists() and not picture.exists()):
            self.path.write_text(text, encoding="utf-8")
            self.saved = text
            picture.write_text(
                svg(outline_sheet(self.drawing)), encoding="utf-8"
            )

    # Method `OutlineEditor.show_message()`:
    def show_message(self, *_regions: object) -> None:
        """Show the view's last refusal (or nothing) in the mode bar.

        [Undo] and [Redo] are enabled only when there is something to
        undo or redo.
        """
        history: History = self.view.history
        self.button_actions["Undo"].setEnabled(bool(history.done))
        self.button_actions["Redo"].setEnabled(bool(history.undone))
        # [Revolve] shows the drawing's state (a refusal, an undo).
        self.button_actions["Revolve"].setChecked(self.view.drawing.revolve)
        self.button_actions["Overview"].setChecked(self.view.overview)
        self.save()
        # A refusal in red; else the armed letter's hint (#214).
        hint: str = ""
        if self.view.armed == "":
            hint = "Click corners to make them sharp"
        elif self.view.armed is not None:
            hint = f"Click corners to fillet them by {self.view.armed}"
        # Crossing edges (#242) are a problem too, until undone.
        problem: str = self.view.message or (
            "Edges cross (drawn red): move a corner to uncross them."
            if crossings(self.view.drawing.points)
            else "A hide strip covers a letter or mark (red in the "
            "Overview): move the strip."
            if self.view.covering()
            else ""
        )
        self.status.setText(problem or hint)
        self.status.setStyleSheet(
            f"color: {theme.colors().problem}" if problem else ""
        )
        self.show_problems()

    # Method `OutlineEditor.show_problems()`:
    def show_problems(self) -> None:
        """Show the letters' problems under the table, then what keeps
        the outline from its real sizes (#445, #448)."""
        placed: str = placement_problem(
            self.view.drawing.points,
            self.view.drawing.dimensions,
            self.view.drawing.revolve,
        )
        self.problems.setText(
            "\n".join(self.letter_lines + ([placed] if placed else []))
        )


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
        outline.points,
        outline.letters,
        outline.dimensions,
        outline.revolve,
        outline.note_radius,
        outline.hides,
        outline.text_height,
        outline.turns,
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
