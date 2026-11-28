"""The 2D outline editor (`T.oe~6.2`).

A window with X and Y axes, an origin square, a grid that gets finer
as one zooms in (#12, #13), and an outline whose corners are pull
squares, dragged and snapped to the grid (Shift drags freely).  Each
edge ends in a small arrowhead showing the winding, counterclockwise
(#4).  The wheel zooms about the pointer (#3); dragging the origin or
empty space pans the view (#6).  There are no modes (#58): dragging
moves (a corner, a dimension's line); each click adds to the
selection (empty space clears it), and the bar's buttons act on it.
[Dimension] dimensions what is selected (#234): one edge's
length, the angle at one corner, the angle between two edges, or the
last two points clicked, before or after it is pressed (#60).
The buttons sit in tabs of related ones (#319); no menus (#11), and
no shortcut keys (#589: in the GUI a key can reach the wrong panel).
[Most Common]: [Undo], [Redo] (#18, a whole drag being one change),
[Delete], [Dimension], [Fit], [Rotate Diagram].  [Draw]: [Delete],
[Dimension], [Dim. Kind \u21bb], [New Letter], [Revolve].  [View]:
[Grid], [Snap], [Fit], [Overview], [Hide], [Rotate Diagram], [Font
+], [Font -] (#273), [Show Marks].  Marks (an edge level
or upright, a corner on an axis) are made by dragging, a corner
snapping onto them (`T.tfo~6.5` #451), and drawn only while [Show
Marks] is on.  The refusals and hints show under the
tabs.  Below the drawing, past a bar dragged up and down, the
letters' table (#27): letter, long name, default value with its
unit, help, each kept and checked at every keystroke.

The scene is in unitless drawing steps (letters give the real sizes,
#15), Y up.  It runs in a panel of `scraftcam.run` (`T.og~6.9` #S5):
`--outline FILE`, `--tutorial FILE`, `--record [FILE]`.
"""

import copy
import math
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from functools import partial
from pathlib import Path
from typing import assert_never

from ..packages import require

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import (  # noqa: E402
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
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QTransform,
    QWheelEvent,
)
from PySide6.QtSvgWidgets import QSvgWidget  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
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
    QStackedWidget,
    QStyleOptionGraphicsItem,
    QTabBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..appearance import Color, Hatch, material_look  # noqa: E402
from ..diagram import FONT_STEP, TEXT, Stroke, Weight, svg  # noqa: E402
from ..geometry import ArcSegment, LineSegment, XYSegment  # noqa: E402
from ..model import MM_PER  # noqa: E402
from ..model_cache import Cacheable  # noqa: E402
from ..shops import OUTLINE_SUFFIX, material_looks, shop_of  # noqa: E402
from . import theme  # noqa: E402
from .assembly_file import move_outline  # noqa: E402
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
    Edge,
    Formula,
    Solution,
    angle_edges,
    is_across,
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
    next_letter,
)
from .outline_cuts import cut_pieces  # noqa: E402
from .outline_diagram import (  # noqa: E402
    Fillet,
    circle_radius,
    dimension_arc,
    dimension_strokes,
    fillet_arcs,
    hatch_strokes,
    outline_sheet,
    outline_strokes,
    upright_text,
)
from .outline_diagram import edge_arc as shared_arc  # noqa: E402
from .outline_file import (  # noqa: E402
    ENDS,
    VERTEX_NAME,
    Circle,
    Cut,
    Hole,
    Outline,
    Polygon,
    Role,
    letter_scope_problems,
    outline_from_text,
    outline_text,
)
from .outline_polygon import outline_cacheable, outline_unit  # noqa: E402
from .outline_values import (  # noqa: E402
    DEFAULT_TOOL_MATERIAL,
    ToolValues,
    ValuesTable,
)
from .solid_viewer import VIEWER, ViewerError  # noqa: E402
from .values import (  # noqa: E402
    circle_in_loop,
    crossings,
    overlaps,
    placed_corners,
    poking_out,
    set_letters,
    values_cross,
)

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

# A dimension's extension lines run this far past its line, and its
# letter sits this far from it (pixels); the letters' size (points).
LETTER_GAP_PIXELS: float = 4.0
LETTER_POINTS: int = 11

# The text height of dimensions and marks drawn through `diagram.py`
# (#S4): their letters, arrowheads that long and marks' boxes, at any
# zoom (#311).
TEXT_PIXELS: float = 14.0

# Each button's word (#20); no keys (#589: a key can reach the wrong
# panel).
BUTTON_WORDS: tuple[str, ...] = (
    "Grid",
    "Snap",
    "Delete",
    "Dimension",
    "Dim. Kind",
    "Revolve",
    "Rotate Diagram",
    "Font +",
    "Font -",
    "Hide",
    "Fit",
    "Undo",
    "Redo",
    "New Letter",
    "New Polygon",
    "New Circle",
    "Cut Line",
    "Show Marks",
    "Show Names",
)

# The buttons that change the outline, greyed while it is read only
# (#590b, #590c); the rest only change the view.
CHANGE_WORDS: tuple[str, ...] = (
    "Delete",
    "Dimension",
    "Dim. Kind",
    "New Letter",
    "New Polygon",
    "New Circle",
    "Cut Line",
    "Revolve",
    "Hide",
    "Rotate Diagram",
    "Undo",
    "Redo",
)


# What a refused change says, by why the outline may not be changed
# (#590b, `T.toasl~6.8` #755-#757).
READ_ONLY_MESSAGE: str = "Choose the [Edit] tab to change the outline."
LOCKED_MESSAGE: str = (
    "This outline is read only: [Copy Shop] makes a shop of your own."
)
TOOL_MESSAGE: str = (
    "Only this tool's values change here; its kind's outline is "
    "changed in its own [Edit] tab."
)


# Class `ViewTab`:
class ViewTab(StrEnum):
    """The drawing's tabs (`T.toasl~6.8` #755), in their order.

    Attributes:
    * `DRAWING`: The working view, hide strips cut out; look only.
    * `SVG`: The diagram the outline makes.
    * `EDIT`: The whole drawing, strips shaded; where it is changed.
    """

    DRAWING = "Drawing"
    SVG = "SVG"
    EDIT = "Edit"


# The buttons in tabs of related ones (#319), the most used first; a
# button may sit on more than one tab.
BUTTON_TABS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Most Common",
        ("Undo", "Redo", "Delete", "Dimension", "Fit", "Rotate Diagram"),
    ),
    (
        "Draw",
        (
            "Delete",
            "Dimension",
            "Dim. Kind",
            "New Letter",
            "New Polygon",
            "New Circle",
            "Cut Line",
            "Revolve",
        ),
    ),
    (
        "View",
        (
            "Grid",
            "Snap",
            "Fit",
            "Hide",
            "Rotate Diagram",
            "Font +",
            "Font -",
            "Show Marks",
            "Show Names",
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

# A selected mirrored corner (#478) is `MIRRORED - index` in
# `OutlineView.chosen_points`, below `ORIGIN` and the axes.
MIRRORED: int = -10


# Function `mirror_code()`:
def mirror_code(corner: int) -> int:
    """Return the selection code of a corner's mirror image (#478).

    Arguments:
    * `corner` (`int`): The corner's index.

    Returns:
    * (`int`): Its code in `OutlineView.chosen_points`.
    """
    return MIRRORED - corner


# Function `real_point()`:
def real_point(code: int) -> int:
    """Return the point a selection code stands for: a mirrored
    corner's own corner, else the code itself (#478).

    Arguments:
    * `code` (`int`): A code in `OutlineView.chosen_points`.

    Returns:
    * (`int`): `ORIGIN` or a corner's index.
    """
    return MIRRORED - code if code <= MIRRORED else code


# The parts of a dimension's line its circles sit on (#469, #470).
# Closed set: a `StrEnum` with `match`/`assert_never()` would let
# mypy catch a missed value (#762).
LINE_MIDDLE: str = "middle"
LINE_START: str = "start"
LINE_END: str = "end"

# A dimension's end dropped this close to a corner (pixels) moves
# there (#470).
DROP_PIXELS: float = 12.0
GRIP_PIXELS: float = 11.0

# The working view (#170, #172): the gap at a cut, and a long break
# line's zigzag, half its length and its height (pixels).
GAP_PIXELS: float = 20.0
ZIG_HALF_PIXELS: float = 10.0
ZIG_HIGH_PIXELS: float = 6.0

# Half the length of the small S ending a dimension line at a cut.
ESS_PIXELS: float = 9.0

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
    * `holes` (`tuple[Hole, ...]`): Copies of the holes (#447).
    * `names` (`tuple[str, ...]`): The corners' names (#787).
    * `polygons` (`tuple[Polygon, ...]`): Copies of the polygons
      (#765).
    * `circles` (`tuple[Circle, ...]`): Copies of the circles
      (`T.sa~6.11` #789).
    * `cuts` (`tuple[Cut, ...]`): Copies of the cut lines (#861).

    Constructor:
    * `Snapshot(points, dimensions, letters, revolve, note_radius,
      hides, turns, text_height, holes, names, polygons, circles,
      cuts)`
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
    holes: tuple[Hole, ...] = field(init=True, default=())
    names: tuple[str, ...] = field(init=True, default=())
    polygons: tuple[Polygon, ...] = field(init=True, default=())
    circles: tuple[Circle, ...] = field(init=True, default=())
    cuts: tuple[Cut, ...] = field(init=True, default=())


# Function `_reached()`:
def _reached(edge: Edge, count: int) -> int:
    """Return the corner an angle's edge reaches, as a `Dimension`
    keeps it: -1 for an axis or the corner after it in `points`
    (#797).

    Arguments:
    * `edge` (`Edge`): The corners it leaves and reaches.
    * `count` (`int`): How many corners there are.

    Returns:
    * (`int`): `Dimension.start_to` or `end_to`.
    """
    if edge[0] in AXES or edge[1] == (edge[0] + 1) % count:
        return -1
    return edge[1]


# Function `_copied()`:
def _copied(polygon: Polygon) -> Polygon:
    """Return a copy of a polygon, its vertex list its own.

    Arguments:
    * `polygon` (`Polygon`): The polygon.

    Returns:
    * (`Polygon`): The copy.
    """
    return replace(polygon, vertices=list(polygon.vertices))


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
    * `names` (`list[str]`): Each corner's name (#787).
    * `polygons` (`list[Polygon]`): The polygons (#765).

    Constructor:
    * `Drawing(points, letters, dimensions, revolve, note_radius,
      hides, text_height, turns, holes, names, polygons, circles,
      cuts)`
    """

    # Remaining attributes (alphabetized):
    scale: float = field(init=False, default=0.0)

    # Method `Drawing.__post_init__()`:
    def __post_init__(self) -> None:
        """Start from the first triangle when no corners are given."""
        if not self.points:
            self.points[:] = triangle()
        self.fill_names()
        self.fill_polygons()

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
            tuple(replace(hole) for hole in self.holes),
            tuple(self.names),
            tuple(_copied(polygon) for polygon in self.polygons),
            tuple(replace(circle) for circle in self.circles),
            tuple(
                replace(cut, vertices=list(cut.vertices)) for cut in self.cuts
            ),
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
        self.holes[:] = [replace(hole) for hole in snapshot.holes]
        self.names[:] = snapshot.names
        self.fill_names()
        self.polygons[:] = [_copied(polygon) for polygon in snapshot.polygons]
        self.circles[:] = [replace(circle) for circle in snapshot.circles]
        self.cuts[:] = [
            replace(cut, vertices=list(cut.vertices)) for cut in snapshot.cuts
        ]

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
                self.points,
                dimension.start,
                dimension.end,
                (dimension.start_to, dimension.end_to),
            )
            if rays is None:
                continue
            dimension.rays = rays
            arc: tuple[QPointF, float, float] | None = angle_arc(
                self.points, dimension
            )
            if arc is not None and arc[2] > 180.0:
                dimension.start, dimension.end = dimension.end, dimension.start
                dimension.start_to, dimension.end_to = (
                    dimension.end_to,
                    dimension.start_to,
                )
                dimension.rays = (rays[1], rays[0])

    # Method `Drawing.insert()`:
    def insert(self, point: tuple[float, float], edge: Edge) -> int:
        """Add a corner splitting an edge: it goes last in `points`,
        in the order made (`T.sa~6.11` #799), so no other corner is
        renumbered; it joins each polygon with the edge, a mark on
        the edge goes (#233), and an angle on it reaches the new
        corner (#797).

        Arguments:
        * `point` (`tuple[float, float]`): The new corner.
        * `edge` (`Edge`): The edge it splits.

        Returns:
        * (`int`): The new corner's index.
        """
        # A mark on the split edge goes (#233).
        self.explicit_angles()
        loops: list[list[int]] = self.loops()
        self.dimensions[:] = [
            dimension
            for dimension in self.dimensions
            if (found := mark_edge(dimension, len(self.points), loops)) is None
            or frozenset(found) != frozenset(edge)
        ]
        before: str = self.names[edge[0]]
        after: str = self.names[edge[1]]
        index: int = len(self.points)
        self.points.append(point)
        name: str = self.new_name()
        self.names.append(name)

        # Into each polygon with the split edge, between its ends.
        polygon: Polygon
        for polygon in self.polygons:
            corners: list[str] = polygon.vertices
            spot: int
            corner: str
            for spot, corner in enumerate(corners):
                if {corner, corners[spot - 1]} == {before, after}:
                    corners.insert(spot, name)
                    break

        # An angle along the split edge now reaches the new corner.
        dimension: Dimension
        for dimension in self.dimensions:
            if dimension.kind != ANGLE:
                continue
            if {dimension.start, dimension.start_to} == set(edge):
                dimension.start_to = index
            if {dimension.end, dimension.end_to} == set(edge):
                dimension.end_to = index
        return index

    # Method `Drawing.new_triangle()`:
    def new_triangle(self, first: int, second: int) -> str:
        """Add a polygon (`T.sa~6.11` #772): an equilateral triangle on
        the edge between two corners, outside the one polygon that has
        the edge, sharing the two; its third corner made last.

        Arguments:
        * `first` (`int`): One corner of the edge.
        * `second` (`int`): The other.

        Returns:
        * (`str`): The new polygon's name; "" when the two are not an
          edge of exactly one polygon (nothing is changed).
        """
        # The one polygon with the edge, and the edge as it walks it.
        found: list[tuple[list[int], Edge]] = [
            (loop, (corner, loop[(spot + 1) % len(loop)]))
            for loop in self.loops()
            for spot, corner in enumerate(loop)
            if {corner, loop[(spot + 1) % len(loop)]} == {first, second}
        ]
        if len(found) != 1:
            return ""
        loop: list[int]
        edge: Edge
        loop, edge = found[0]

        # Outside: right of the edge as a counterclockwise polygon walks
        # it (left for a clockwise one), at the equilateral height.
        ring: list[tuple[float, float]] = [self.points[at] for at in loop]
        area: float = sum(
            here[0] * there[1] - there[0] * here[1]
            for here, there in zip(ring, ring[1:] + ring[:1], strict=True)
        )
        start: tuple[float, float] = self.points[edge[0]]
        end: tuple[float, float] = self.points[edge[1]]
        side: float = (1.0 if area > 0.0 else -1.0) * math.sqrt(3.0) / 2.0
        apex: tuple[float, float] = (
            (start[0] + end[0]) / 2.0 + side * (end[1] - start[1]),
            (start[1] + end[1]) / 2.0 - side * (end[0] - start[0]),
        )
        self.points.append(apex)
        name: str = self.new_name()
        self.names.append(name)
        polygon: str = self.new_polygon_name()
        self.polygons.append(
            Polygon(
                polygon,
                Role.OTHER,
                [self.names[edge[1]], self.names[edge[0]], name],
            )
        )
        return polygon

    # Method `Drawing.new_circle()`:
    def new_circle(self, corner: int) -> str:
        """Add a circle (`T.sa~6.11` #789) standing on the first
        polygon through a corner: its center a new vertex at the
        polygon's middle, its diameter a sixth of the polygon's
        smaller side as drawn, at the drawing's scale when known.

        Arguments:
        * `corner` (`int`): A corner of the polygon.

        Returns:
        * (`str`): The new circle's name; "" when the outline is
          revolved or no polygon has the corner (nothing changed).
        """
        if self.revolve:
            return ""
        loops: list[list[int]] = self.loops()
        found: list[int] = [
            index for index, loop in enumerate(loops) if corner in loop
        ]
        if not found:
            return ""
        ring: list[tuple[float, float]] = [
            self.points[at] for at in loops[found[0]]
        ]
        xs: list[float] = [x for x, _ in ring]
        ys: list[float] = [y for _, y in ring]
        self.points.append((sum(xs) / len(xs), sum(ys) / len(ys)))
        center: str = self.new_name()
        self.names.append(center)
        span: float = min(max(xs) - min(xs), max(ys) - min(ys)) / 6.0
        unit: str = outline_unit(self)
        size: float = span / self.scale if self.scale > 0.0 else span
        per: float = float(MM_PER[unit])
        name: str = self.new_circle_name()
        self.circles.append(
            Circle(
                name,
                Role.OTHER,
                center,
                f"{size / per:.4g} {unit}",
                self.polygons[found[0]].name,
            )
        )
        return name

    # Method `Drawing.new_cut()`:
    def new_cut(self, corner: int) -> str:
        """Add a cut line (`T.sa~6.11` #776, #861) across the middle
        of the first polygon through a corner, left to right and a
        little beyond, looking toward -Y; its three vertices are made
        last, with no dimensions.

        Arguments:
        * `corner` (`int`): A corner of the polygon.

        Returns:
        * (`str`): The cut's name; "" when the outline is revolved or
          no polygon has the corner (nothing changed).
        """
        if self.revolve:
            return ""
        loops: list[list[int]] = self.loops()
        found: list[int] = [
            index for index, loop in enumerate(loops) if corner in loop
        ]
        if not found:
            return ""
        xs: list[float] = [self.points[at][0] for at in loops[found[0]]]
        ys: list[float] = [self.points[at][1] for at in loops[found[0]]]
        middle: float = (min(ys) + max(ys)) / 2.0
        beyond: float = (max(xs) - min(xs)) / 8.0
        places: list[tuple[float, float]] = [
            (min(xs) - beyond, middle),
            (max(xs) + beyond, middle),
            ((min(xs) + max(xs)) / 2.0, middle - beyond),
        ]
        names: list[str] = []
        place: tuple[float, float]
        for place in places:
            self.points.append(place)
            names.append(self.new_name())
            self.names.append(names[-1])
        name: str = self.new_cut_name()
        self.cuts.append(Cut(name, names))
        return name

    # Method `Drawing.forget_vertex()`:
    def forget_vertex(self, gone: str) -> None:
        """Take away the circles about a deleted vertex, what stood on
        them standing on their parents, and the cut lines through it
        (`T.sa~6.11` #861).

        Arguments:
        * `gone` (`str`): The vertex's name.
        """
        circle: Circle
        for circle in [each for each in self.circles if each.center == gone]:
            self.circles.remove(circle)
            shapes: list[Polygon | Circle] = [*self.polygons, *self.circles]
            shape: Polygon | Circle
            for shape in shapes:
                if shape.parent == circle.name:
                    shape.parent = circle.parent
        self.cuts[:] = [cut for cut in self.cuts if gone not in cut.vertices]

    # Method `Drawing.explicit_angles()`:
    def explicit_angles(self) -> None:
        """Give every angle's edges both their corners, so that none
        relies on the next corner in `points` while corners come and
        go (#799)."""
        count: int = len(self.points)
        dimension: Dimension
        for dimension in self.dimensions:
            if dimension.kind != ANGLE:
                continue
            first: Edge
            second: Edge
            first, second = angle_edges(dimension, count)
            dimension.start_to = first[1]
            dimension.end_to = second[1]

    # Method `Drawing.remove()`:
    def remove(self, index: int) -> None:
        """Remove a corner, with the dimensions that measure it and
        the hide strips placed from it (#446).

        Arguments:
        * `index` (`int`): The corner.
        """
        # An angle's edge reaching the corner reaches on, to the
        # corner after it in its polygon (#45, #797).
        self.explicit_angles()
        ahead: int = self.neighbours(index)[1]
        dimension: Dimension
        for dimension in self.dimensions:
            if dimension.kind == ANGLE:
                if dimension.start_to == index:
                    dimension.start_to = ahead
                if dimension.end_to == index:
                    dimension.end_to = ahead
        # An edge shrunk to a corner goes, as one measuring the corner.
        self.dimensions[:] = [
            dimension
            for dimension in self.dimensions
            if dimension.kind != ANGLE
            or (
                dimension.start != dimension.start_to
                and dimension.end != dimension.end_to
            )
        ]
        del self.points[index]
        gone: str = self.names.pop(index)
        polygon: Polygon
        for polygon in self.polygons:
            if gone in polygon.vertices:
                polygon.vertices.remove(gone)
        self.forget_vertex(gone)
        self.dimensions[:] = [
            dimension
            for dimension in self.dimensions
            if index
            not in (
                dimension.start,
                dimension.end,
                dimension.start_to,
                dimension.end_to,
            )
        ]
        for dimension in self.dimensions:
            if dimension.start > index:
                dimension.start -= 1
            if dimension.end > index:
                dimension.end -= 1
            if dimension.start_to > index:
                dimension.start_to -= 1
            if dimension.end_to > index:
                dimension.end_to -= 1
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
    letter is armed fillets its corner (#214).  A revolved outline's
    mirrored half has circles too (#474): one moves its corner as the
    mirror image of the drag, and acts on that corner (#476).

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its corner's index in the drawing.
    * `mirrored` (`bool`): Whether it sits on the corner's mirror
      image across the Y axis.
    * `before` (`Snapshot | None`):
      The drawing when a drag began (`None` between drags).
    """

    # Method `CornerCircle.__init__()`:
    def __init__(
        self, editor: "OutlineView", index: int, mirrored: bool = False
    ) -> None:
        """Make the square of one corner.

        Arguments:
        * `editor` (`OutlineView`): The view it is drawn in.
        * `index` (`int`): Its corner's index in the drawing.
        * `mirrored` (`bool`): Whether it sits on the corner's mirror
          image (#474).
        """
        half: float = SQUARE_PIXELS / 2.0
        super().__init__(-half, -half, SQUARE_PIXELS, SQUARE_PIXELS)
        self.editor: OutlineView = editor
        self.index: int = index
        self.mirrored: bool = mirrored
        self.before: Snapshot | None = None

        # Placed before it sends its moves, so placing it never snaps
        # its corner.
        x: float
        y: float
        x, y = editor.drawing.points[index]
        self.setPos(-x if mirrored else x, y)
        flags: type[QGraphicsItem.GraphicsItemFlag] = (
            QGraphicsItem.GraphicsItemFlag
        )
        self.setFlag(flags.ItemIgnoresTransformations)
        self.setFlag(flags.ItemIsMovable)
        self.setFlag(flags.ItemSendsGeometryChanges)
        self.setZValue(2.0)
        self.setAcceptHoverEvents(True)

    # Method `CornerCircle.code()`:
    def code(self) -> int:
        """Return what selecting it puts in the selection: its corner,
        or a mirrored one's `mirror_code()` (#478).

        Returns:
        * (`int`): The code.
        """
        return mirror_code(self.index) if self.mirrored else self.index

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
        """Select its corner (a mirrored one only its mirror image,
        #478), then start a drag."""
        self.editor.select_point(self.code())
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
        """Snap a move, and move the corner with it (#451); a mirrored
        circle moves it as the mirror image (#474)."""
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and isinstance(value, QPointF)
            and not self.editor.placing
        ):
            free: bool = not self.editor.snap_on or bool(
                QApplication.keyboardModifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )
            moved: QPointF = value if free else snap(value, self.editor.step())
            if self.mirrored:
                moved.setX(-moved.x())
            if self.editor.drawing.revolve and moved.x() < 0.0:
                moved.setX(0.0)  # A revolved outline keeps to X >= 0.
            # Nothing pins it (#457); it snaps level, upright or onto
            # an axis (#451).
            self.editor.drag_corner(self.index, moved)
            self.editor.outline.refresh()
            self.editor.moving = self
            self.editor.follow()
            self.editor.moving = None
            if self.mirrored:
                moved.setX(-moved.x())
            return moved
        return super().itemChange(change, value)

    # Method `CornerCircle.place()`:
    def place(self) -> None:
        """Sit on its corner (or its mirror image), without moving the
        corner; a mirrored one shows only on a revolved outline, and
        not where it would cover its corner's own circle (#477)."""
        if self.editor.moving is self:
            return  # Qt puts it where its own move goes.
        x: float
        y: float
        x, y = self.editor.drawing.points[self.index]
        if self.mirrored:
            self.setVisible(
                self.editor.drawing.revolve
                and 2.0 * abs(x) * self.editor.zoom() >= SQUARE_PIXELS
            )
            x = -x
        if self.pos() != QPointF(x, y):
            self.editor.placing = True
            self.setPos(x, y)
            self.editor.placing = False


# The hatch angles Qt draws, and their brushes (#810), by the set of
# angles, each turned to 0, 45, 90 or 135 degrees.
HATCH_STYLES: dict[frozenset[int], Qt.BrushStyle] = {
    frozenset({0}): Qt.BrushStyle.HorPattern,
    frozenset({90}): Qt.BrushStyle.VerPattern,
    frozenset({45}): Qt.BrushStyle.BDiagPattern,
    frozenset({135}): Qt.BrushStyle.FDiagPattern,
    frozenset({0, 90}): Qt.BrushStyle.CrossPattern,
    frozenset({45, 135}): Qt.BrushStyle.DiagCrossPattern,
}


# Function `hatch_style()`:
def hatch_style(hatch: Hatch) -> Qt.BrushStyle:
    """Return the Qt brush nearest a hatch, for the screen (#810).

    Arguments:
    * `hatch` (`Hatch`): The hatch.

    Returns:
    * (`Qt.BrushStyle`): Its lines' angles, each to the nearest 45
      degrees; a pair Qt has no brush for takes its first set's.
    """
    angles: list[int] = [
        round(lines.angle / 45.0) * 45 % 180 for lines in hatch.lines
    ]
    return HATCH_STYLES.get(
        frozenset(angles), HATCH_STYLES[frozenset(angles[:1])]
    )


# Class `OutlineItem`:
class OutlineItem(QGraphicsItem):
    """The outline: thick edges, each ending in a small arrowhead,
    each polygon hatched by its material (`T.sa~6.11` #808, #812).

    Attributes:
    * `drawing` (`Drawing`): What it draws.
    * `hatch` (`Hatch | None`): The hatch of the material it is
      drawn for (a tool's, `appearance.material_look()`), over every
      polygon; `None` (a bare outline) hatches nothing (#840).
    """

    # Method `OutlineItem.__init__()`:
    def __init__(self, drawing: Drawing) -> None:
        """Make the outline of a drawing.

        Arguments:
        * `drawing` (`Drawing`): What it draws.
        """
        super().__init__()
        self.drawing: Drawing = drawing
        self.hatch: Hatch | None = None
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
        crossed: set[Edge] = {
            edge
            for pair in crossings(self.drawing.points, self.drawing.loops())
            for edge in pair
        }
        bad: QPen = QPen(QColor(theme.colors().problem), 2 * THICK_PIXELS)
        bad.setCosmetic(True)
        painter.setPen(bad)
        start: int
        end: int
        for start, end in sorted(crossed):
            painter.drawLine(corners[start], corners[end])

    # Method `OutlineItem.paint_hatch()`:
    def paint_hatch(
        self, painter: QPainter, fillets: dict[int, Fillet]
    ) -> None:
        """Hatch every polygon by the material it is drawn for, in ink,
        under the outline: drawings are monochrome (#812, #840).  The
        hatch is Qt's, its spacing fixed on screen at any zoom (#810).

        Arguments:
        * `painter` (`QPainter`): What draws, in drawing steps.
        * `fillets` (`dict[int, Fillet]`): From `fillet_arcs()`.
        """
        if self.hatch is None:
            return
        # The hatch's pattern is kept in screen pixels.
        brush: QBrush = QBrush(
            QColor(theme.colors().ink), hatch_style(self.hatch)
        )
        brush.setTransform(painter.worldTransform().inverted()[0])
        area: Stroke
        for area in hatch_strokes(self.drawing, fillets, self.hatch):
            path: QPainterPath = stroke_path(area)
            path.closeSubpath()
            painter.fillPath(path, brush)

    # Method `OutlineItem.paint_thin()`:
    def paint_thin(self, painter: QPainter, strokes: list[Stroke]) -> None:
        """Draw the thin strokes: a shared edge in ink (#845); revolved,
        the mirror half, faint and dashed.

        Arguments:
        * `painter` (`QPainter`): What draws, in drawing steps.
        * `strokes` (`list[Stroke]`): The outline's strokes.
        """
        thin: QPen = QPen(QColor(theme.colors().ink), THIN_PIXELS)
        thin.setCosmetic(True)
        ghost: QPen = QPen(QColor(theme.colors().quiet), THIN_PIXELS)
        ghost.setCosmetic(True)
        ghost.setStyle(Qt.PenStyle.DashLine)
        stroke: Stroke
        for stroke in strokes:
            if stroke.weight != Weight.THICK:
                painter.setPen(ghost if stroke.dashed else thin)
                painter.drawPath(stroke_path(stroke))

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
        # In [Edit] an edge two polygons share is thick, for editing;
        # in [Drawing] it is thin, as on the diagram (#851).
        scene: QGraphicsScene | None = self.scene()
        editing: bool = scene is not None and any(
            isinstance(view, OutlineView) and view.overview
            for view in scene.views()
        )
        strokes: list[Stroke] = outline_strokes(
            self.drawing, fillets, thin_shared=not editing
        )
        thick: list[Stroke] = [
            stroke for stroke in strokes if stroke.weight == Weight.THICK
        ]
        self.paint_hatch(painter, fillets)
        painter.setPen(pen)
        stroke: Stroke
        for stroke in thick:
            painter.drawPath(stroke_path(stroke))

        self.paint_thin(painter, strokes)

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
        for segment in (
            segment for stroke in thick for segment in stroke.segments
        ):
            if isinstance(segment, LineSegment):
                painter.drawPath(
                    arrowhead(
                        QPointF(*segment.start), QPointF(*segment.end), length
                    )
                )


# Function `tool_drawing()`:
def tool_drawing(drawing: Drawing, values: dict[str, str]) -> Drawing:
    """Return an outline drawn for one tool, in its true proportions.

    The tool's values go into the letters, and the corners go where
    they put them, at the outline's own scale, so a tool and its
    kind's diagram are drawn alike (`T.toasl~6.8` #737a, #737b).  A
    tool bigger than its kind's outline is shrunk into the same box
    (#737c); a smaller one keeps its size.

    Arguments:
    * `drawing` (`Drawing`): The kind's outline (not changed).
    * `values` (`dict[str, str]`): The tool's values, by letter.

    Returns:
    * (`Drawing`): A new drawing; the outline's corners when the
      values can not be drawn.
    """
    # The outline's own scale, from its defaults.
    scale: float = placed_corners(
        drawing.points,
        drawing.letters,
        drawing.dimensions,
        drawing.scale,
        drawing.loops(),
    )[1]
    tool: Drawing = copy.deepcopy(drawing)
    set_letters(tool.letters, values)
    points: list[tuple[float, float]] = placed_corners(
        tool.points, tool.letters, tool.dimensions, scale, tool.loops()
    )[0]

    # Into the outline's box, never bigger.
    factor: float = 1.0
    axis: int
    for axis in (0, 1):
        old: float = _extent(drawing.points, axis)
        new: float = _extent(points, axis)
        if new > old > 0.0:
            factor = min(factor, old / new)
    tool.points = [(x * factor, y * factor) for x, y in points]
    tool.scale = scale * factor
    return tool


# Function `_extent()`:
def _extent(points: list[tuple[float, float]], axis: int) -> float:
    """Return how far the corners spread along one axis.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `axis` (`int`): 0 for X, 1 for Y.

    Returns:
    * (`float`): The spread; 0 for no corners.
    """
    coordinates: list[float] = [point[axis] for point in points]
    return max(coordinates) - min(coordinates) if coordinates else 0.0


# Function `tool_svg()`:
def tool_svg(outline: Path, values: dict[str, str], material: str = "") -> str:
    """Return a tool's diagram: its kind's outline, drawn for it and
    hatched by its material (`T.sa~6.11` #840).

    Arguments:
    * `outline` (`Path`): The kind's `.outline.toml`.
    * `values` (`dict[str, str]`): The tool's values, by letter.
    * `material` (`str`): The tool's material ("": HSS, #821).

    Returns:
    * (`str`): The `.svg`, as the outline's own is written.
    """
    return svg(
        outline_sheet(
            tool_drawing(drawing_from(outline), values),
            hatch=tool_hatch(outline, material),
        )
    )


# Function `tool_hatch()`:
def tool_hatch(outline: Path | None, material: str) -> Hatch | None:
    """Return the hatch of a tool's material, from the outline's own
    shop (the example shop's for one in none, #809).

    Arguments:
    * `outline` (`Path | None`): The kind's outline file, if any.
    * `material` (`str`): The tool's material ("": HSS, #821).

    Returns:
    * (`Hatch | None`): Its hatch.
    """
    return material_look(
        material or DEFAULT_TOOL_MATERIAL,
        material_looks(shop_of(outline)),
    ).hatch


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


# Function `has_end_circles()`:
def has_end_circles(dimension: Dimension) -> bool:
    """Return whether a dimension has circles at its line's ends
    (#470): a length of any kind, not a mark.

    Arguments:
    * `dimension` (`Dimension`): The dimension.

    Returns:
    * (`bool`): `True` when it has end circles.
    """
    return not is_mark(dimension) and dimension.kind in (
        HORIZONTAL,
        VERTICAL,
        LENGTH,
        DIAMETER,
    )


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
    points: list[tuple[float, float]],
    first: int,
    second: int,
    reach: tuple[int, int] = (-1, -1),
) -> QPointF | None:
    """Return where two edges' lines cross.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `first` (`int`): The corner the first edge leaves.
    * `second` (`int`): The corner the second edge leaves.
    * `reach` (`tuple[int, int]`): The corner each edge reaches
      (`T.sa~6.11` #797); -1 for the corner after the one it leaves.

    Returns:
    * (`QPointF | None`): The crossing; `None` for parallel edges.
    """
    arc: tuple[tuple[float, float], float, float] | None = shared_arc(
        points, first, second, (1, 1), reach
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
def edge_way(
    points: list[tuple[float, float]], edge: int, to: int = -1
) -> QPointF:
    """Return an edge's direction, from the corner it leaves (+X or
    +Y, for an axis).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `edge` (`int`): The corner the edge leaves, or an axis.
    * `to` (`int`): The corner it reaches (#797); -1 for the next.

    Returns:
    * (`QPointF`): The corner it reaches less this one.
    """
    if edge == X_AXIS:
        return QPointF(1.0, 0.0)
    if edge == Y_AXIS:
        return QPointF(0.0, 1.0)
    there: int = to if to >= 0 else (edge + 1) % len(points)
    return QPointF(*points[there]) - QPointF(*points[edge])


# Function `middle_rays()`:
def middle_rays(
    points: list[tuple[float, float]],
    first: int,
    second: int,
    reach: tuple[int, int] = (-1, -1),
) -> tuple[int, int] | None:
    """Return the rays from two edges' crossing toward their middles,
    each `1` along its edge's direction or `-1` against it (#53).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.
    * `first` (`int`): The corner the first edge leaves.
    * `second` (`int`): The corner the second edge leaves.
    * `reach` (`tuple[int, int]`): The corner each edge reaches
      (`T.sa~6.11` #797); -1 for the corner after the one it leaves.

    Returns:
    * (`tuple[int, int] | None`): The two rays; `None` for parallel
      edges.
    """
    center: QPointF | None = crossing(points, first, second, reach)
    if center is None:
        return None
    signs: list[int] = []
    edge: int
    other: int
    to: int
    other_to: int
    for edge, other, to, other_to in (
        (first, second, reach[0], reach[1]),
        (second, first, reach[1], reach[0]),
    ):
        # An axis's ray points toward the other edge's side (#65).
        middle: QPointF = (
            edge_start(points, other) + edge_way(points, other, other_to) / 2
            if edge in AXES
            else edge_start(points, edge) + edge_way(points, edge, to) / 2
        )
        toward: float = QPointF.dotProduct(
            middle - center, edge_way(points, edge, to)
        )
        signs.append(1 if toward >= 0.0 else -1)
    return signs[0], signs[1]


# Function `edge_arc()`:
def edge_arc(
    points: list[tuple[float, float]],
    first: int,
    second: int,
    rays: tuple[int, int],
    reach: tuple[int, int] = (-1, -1),
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
    * `reach` (`tuple[int, int]`): The corner each edge reaches
      (`T.sa~6.11` #797); -1 for the corner after the one it leaves.

    Returns:
    * (`tuple[QPointF, float, float] | None`): The crossing, the first
      ray's direction and the turn to the second ray (degrees, 0 to
      360, counterclockwise); `None` for parallel edges.
    """
    arc: tuple[tuple[float, float], float, float] | None = shared_arc(
        points, first, second, rays, reach
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
    arc: tuple[tuple[float, float], float, float] | None = dimension_arc(
        points, dimension
    )
    return None if arc is None else (QPointF(*arc[0]), arc[1], arc[2])


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
    the edge (for [Dimension], #231, #234).  A revolved outline's
    mirrored edges have them too (#475): the corner is pulled out of
    the real edge as the mirror image of the drag.

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): The corner its edge leaves.
    * `end` (`int`): The corner its edge reaches, in its polygon
      (`T.sa~6.11` #797).
    * `mirrored` (`bool`): Whether it sits on the edge's mirror image
      across the Y axis.
    * `before` (`Snapshot | None`): The drawing when a drag began.
    * `added` (`int`): The new corner's index during a drag (`-1`
      before the pointer moves).
    """

    # Method `EdgeHandle.__init__()`:
    def __init__(
        self,
        editor: "OutlineView",
        edge: Edge,
        mirrored: bool = False,
    ) -> None:
        """Make the handle of one edge.

        Arguments:
        * `editor` (`OutlineView`): The view it is drawn in.
        * `edge` (`Edge`): The corners it leaves and reaches (#797).
        * `mirrored` (`bool`): Whether it sits on the edge's mirror
          image (#475).
        """
        half: float = HANDLE_PIXELS / 2.0
        super().__init__(-half, -half, HANDLE_PIXELS, HANDLE_PIXELS)
        self.editor: OutlineView = editor
        self.index: int = edge[0]
        self.end: int = edge[1]
        self.mirrored: bool = mirrored
        self.before: Snapshot | None = None
        self.added: int = -1
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setZValue(1.5)

    # Method `EdgeHandle.place()`:
    def place(self) -> None:
        """Sit in the middle of its edge (or its mirror image); hidden
        if the edge is short, and a mirrored one unless the outline is
        revolved and the edge is off the axis (#477)."""
        points: list[tuple[float, float]] = self.editor.drawing.points
        x0: float
        y0: float
        x1: float
        y1: float
        x0, y0 = points[self.index]
        x1, y1 = points[self.end]
        middle: float = (x0 + x1) / 2.0
        self.setPos(-middle if self.mirrored else middle, (y0 + y1) / 2.0)
        length: float = (
            (x1 - x0) ** 2 + (y1 - y0) ** 2
        ) ** 0.5 * self.editor.zoom()
        shown: bool = length >= HANDLE_EDGE_PIXELS
        if self.mirrored:
            shown = (
                shown
                and self.editor.drawing.revolve
                and 2.0 * abs(middle) * self.editor.zoom() >= SQUARE_PIXELS
            )
        self.setVisible(shown)

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
        if self.mirrored:
            where.setX(-where.x())  # The real half's corner (#475).
        if self.editor.drawing.revolve and where.x() < 0.0:
            where.setX(0.0)  # A revolved outline keeps to X >= 0.
        if self.added < 0:
            self.added = self.editor.drawing.insert(
                (where.x(), where.y()), (self.index, self.end)
            )
        # It snaps as a dragged corner does (#451).
        self.editor.dragged = self.added
        self.editor.drag_corner(self.added, where)
        self.setPos(-where.x() if self.mirrored else where.x(), where.y())
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
            self.editor.select_edge((self.index, self.end))
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
        # Closed set: a `StrEnum` with `match`/`assert_never()`
        # would let mypy catch a missed value (#762).
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
# A circle keeps its own drag state beside which part of which
# dimension it moves, so it has more attributes than most.
class DimensionHandle(  # pylint: disable=too-many-instance-attributes
    QGraphicsEllipseItem
):
    """One of a dimension's small hollow circles, which sit on its
    line as corners' and edges' circles sit on the outline (#63,
    #469, #470): one in the middle (clear of its letter), and one on
    each end.

    Dragged, the middle one moves the line across (an angle's arc in
    and out); an end dropped on a corner, or the origin, moves that
    end of the dimension there; a `—` or `|` mark's one circle moves
    its box anywhere (#317).  Snapped as corners are, the whole drag
    one change.  The letter moves by dragging the letter itself
    (`DimensionItem`, #471).

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its dimension's index in the drawing.
    * `part` (`str`): Where on the line it sits: `LINE_MIDDLE`,
      `LINE_START` or `LINE_END`.
    * `before` (`Snapshot | None`): The drawing when a drag began.
    * `grab` (`QPointF`): Where the pointer was from the circle's
      middle when a drag began, so the circle does not jump.
    * `pressed` (`QPointF`): Where a mark's drag began (scene).
    * `was` (`tuple[float, float]`): The mark's `moved` then.
    * `target` (`int`): The corner (or `ORIGIN`) an end was dropped
      on, until the drop is applied.
    """

    # Method `DimensionHandle.__init__()`:
    def __init__(
        self, editor: "OutlineView", index: int, part: str = LINE_MIDDLE
    ) -> None:
        """Make one circle of one dimension.

        Arguments:
        * `editor` (`OutlineView`): The view it is drawn in.
        * `index` (`int`): Its dimension's index in the drawing.
        * `part` (`str`): Where on the line it sits (`LINE_MIDDLE`,
          `LINE_START` or `LINE_END`).
        """
        half: float = HANDLE_PIXELS / 2.0
        super().__init__(-half, -half, HANDLE_PIXELS, HANDLE_PIXELS)
        self.editor: OutlineView = editor
        self.index: int = index
        self.part: str = part
        self.before: Snapshot | None = None
        self.grab: QPointF = QPointF()
        self.pressed: QPointF = QPointF()
        self.was: tuple[float, float] = (0.0, 0.0)
        self.target: int = ORIGIN
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)

        # An end circle sits just under its dimension, so the
        # arrowhead's tip is drawn over it (#483); the dimension's
        # band leaves a hole there, so a press still reaches it.
        self.setZValue(1.5 if part == LINE_MIDDLE else 0.4)

    # Method `DimensionHandle.place()`:
    def place(self) -> None:
        """Sit on its part of the line (the middle one clear of the
        letter, a `—` or `|` mark's off its box, #315, #317); hidden
        for a fillet and a right angle, for now.  An angle has no end
        circles (#470)."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        lined: bool = (
            dimension.kind != ANGLE
            if is_mark(dimension)
            else dimension.kind != RADIUS
        )
        # Marks show only under [Show Marks] (#451).
        lined = lined and (not is_mark(dimension) or self.editor.marks_shown)
        if self.part != LINE_MIDDLE:
            lined = lined and has_end_circles(dimension)
        self.setVisible(lined)
        if not lined:
            return
        measure: DimensionItem = self.editor.measures[self.index]
        if self.part == LINE_MIDDLE:
            self.setPos(measure.handle_spot())
            return
        ends: tuple[QPointF, QPointF, QPointF, QPointF] = measure.ends()
        self.setPos(ends[2] if self.part == LINE_START else ends[3])

    # Method `DimensionHandle.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Select the dimension; get ready to move it."""
        self.editor.select_dimension(self.index)
        self.before = self.editor.drawing.snapshot()
        self.grab = event.scenePos() - self.pos()
        self.pressed = event.scenePos()
        self.was = self.editor.drawing.dimensions[self.index].moved
        event.accept()

    # Method `DimensionHandle.mouseMoveEvent()`:
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Move the line across (an angle's arc in and out), or an end
        circle with the pointer."""
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        where: QPointF = event.scenePos() - self.grab
        free: bool = not self.editor.snap_on or bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        if not free:
            where = snap(where, self.editor.step())

        # An end goes where it is dragged, until it is dropped.
        if self.part != LINE_MIDDLE:
            self.setPos(where)
            return

        # A mark's box goes where it is dragged (#317).
        measure: DimensionItem = self.editor.measures[self.index]
        measure.prepareGeometryChange()
        if is_mark(dimension):
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

        # Otherwise only the line moves, across; its letter keeps its
        # share of the line (#471).  A diameter runs across, as a
        # horizontal one (`T.tfo~6.5` #456).
        if dimension.kind == ANGLE:
            placed: tuple[float, float] | None = angle_place(
                self.editor.drawing.points, dimension, where
            )
            if placed is not None:
                dimension.offset = placed[0]
        elif dimension.kind in (HORIZONTAL, DIAMETER):
            dimension.offset = where.y()
        elif dimension.kind == LENGTH:
            first: QPointF = self.editor.point(dimension.start)
            way: QPointF = self.editor.point(dimension.end) - first
            dimension.offset = QPointF.dotProduct(where - first, left_of(way))
        else:
            dimension.offset = where.x()
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
        placed: tuple[float, float] | None = angle_place(
            self.editor.drawing.points, dimension, where
        )
        if placed is not None:
            dimension.offset, dimension.along = placed

    # Method `DimensionHandle.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, _event: QGraphicsSceneMouseEvent) -> None:
        """End a drag: remember it, if it moved the dimension.  An end
        dropped on another corner moves there (#470), after this event,
        as that remakes the circles; dropped elsewhere it goes back.  A
        mirrored corner (#479) takes a diameter (either end moves it to
        that corner), a vertical dimension, or one from the origin:
        those measure the same from its own corner."""
        if self.part != LINE_MIDDLE:
            dimension: Dimension = self.editor.drawing.dimensions[self.index]
            code: int | None = self.editor.corner_near(self.pos())
            target: int = ORIGIN if code is None else real_point(code)
            fixed: tuple[int, int] = (dimension.start, dimension.end)
            if is_across(dimension):
                # Across the axis (#479): the start on a mirror image,
                # the end on a corner.
                mirror: bool = code is not None and code <= MIRRORED
                if (
                    code is not None
                    and target not in fixed
                    and (mirror == (self.part == LINE_START))
                ):
                    self.target = target
                    QTimer.singleShot(0, self.reattach)
                    return
                self.before = None
                self.place()
                return
            same: bool = (
                (code is not None and code > MIRRORED)
                or dimension.kind in (DIAMETER, VERTICAL)
                or ORIGIN in fixed
            )
            if (
                code is None
                or not same
                or target in fixed
                or (dimension.kind == DIAMETER and target == ORIGIN)
            ):
                self.before = None
                self.place()
                return
            self.target = target
            QTimer.singleShot(0, self.reattach)
            return
        if self.before is not None and self.before.dimensions != tuple(
            self.editor.drawing.dimensions
        ):
            self.editor.history.remember(self.before)
        self.before = None

    # Method `DimensionHandle.reattach()`:
    def reattach(self) -> None:
        """Move the dropped end of the dimension to `target` (#470),
        as one change, and draw everything again."""
        editor: OutlineView = self.editor
        if self.before is None or self.index >= len(editor.drawing.dimensions):
            return
        editor.history.remember(self.before)
        self.before = None
        dimension: Dimension = editor.drawing.dimensions[self.index]
        if self.part == LINE_START and (
            dimension.kind != DIAMETER or is_across(dimension)
        ):
            dimension.start = self.target
        else:
            dimension.end = self.target
        editor.make_squares()
        editor.select_dimension(self.index)
        editor.letters_changed()
        editor.follow()


# Function `angle_place()`:
def angle_place(
    points: list[tuple[float, float]], dimension: Dimension, where: QPointF
) -> tuple[float, float] | None:
    """Return an angle's arc radius and its letter's share of the arc
    for the pointer at `where`.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `dimension` (`Dimension`): The angle.
    * `where` (`QPointF`): The pointer, in the scene.

    Returns:
    * (`tuple[float, float] | None`): The radius and the share, or
      `None` when no arc can be drawn there.
    """
    arc: tuple[QPointF, float, float] | None = angle_arc(points, dimension)
    if arc is None:
        return None
    center: QPointF
    start: float
    turn: float
    center, start, turn = arc
    out: QPointF = where - center
    radius: float = math.hypot(out.x(), out.y())
    if radius == 0.0 or turn == 0.0:
        return None
    past: float = math.degrees(math.atan2(out.y(), out.x())) - start
    past = (past - turn / 2.0 + 180.0) % 360.0 - 180.0 + turn / 2.0
    # The letter may go past either ray (#321; it was held between
    # the arrowheads, #76); `past` already keeps it off the far side
    # of the circle.
    return radius, past / turn


# Class `DimensionItem`:
class DimensionItem(QGraphicsItem):
    """A dimension: thin extension lines, a line with an arrowhead at
    each end, and its letter (#26).

    Attributes:
    * `editor` (`OutlineView`): The view it is drawn in.
    * `index` (`int`): Its dimension's index in the drawing.
    * `before` (`Snapshot | None`): The drawing when a drag of its
      letter began (`None` when its letter is not being dragged).
    * `grab` (`QPointF`): Where the pointer was from the letter's
      point (`at()`) when that drag began.

    A click on it selects it; dragging its letter moves the letter
    along its line (#471); its `DimensionHandle`s move the rest.
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
        self.before: Snapshot | None = None
        self.grab: QPointF = QPointF()
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
            # across at `offset`, as `outline_diagram` draws it (#456);
            # or from `start`'s mirror image, across to `end` (#479).
            first = (
                QPointF(-second.x(), second.y())
                if dimension.start == ORIGIN
                else QPointF(-first.x(), first.y())
            )
        if dimension.kind in (HORIZONTAL, DIAMETER):
            return (
                first,
                second,
                QPointF(first.x(), dimension.offset),
                QPointF(second.x(), dimension.offset),
            )
        if self.editor.drawing.revolve and dimension.offset < 0.0:
            # On the mirrored side, from the points' mirror images, as
            # `outline_diagram` draws it (#481).
            first = QPointF(-first.x(), first.y())
            second = QPointF(-second.x(), second.y())
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

        # Holes where the end circles sit, under the arrowheads, so a
        # press there reaches them (#483).
        if has_end_circles(self.editor.drawing.dimensions[self.index]):
            ends: tuple[QPointF, QPointF, QPointF, QPointF] = self.ends()
            half: float = HANDLE_PIXELS / 2.0 / max(self.editor.zoom(), 1e-12)
            holes: QPainterPath = QPainterPath()
            end: QPointF
            for end in ends[2:]:
                holes.addEllipse(end, half, half)
            band = band.subtracted(holes)
        return band

    # Method `DimensionItem.mousePressEvent()`:
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Select the dimension; a press on its letter starts moving
        the letter (#471; its circles move the rest, #64)."""
        self.editor.select_dimension(self.index)
        self.before = None
        box: QRectF | None = self.letter_box()
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        if (
            box is not None
            and not is_mark(dimension)
            and box.contains(event.scenePos())
        ):
            self.before = self.editor.drawing.snapshot()
            self.grab = event.scenePos() - self.at()
        event.accept()

    # Method `DimensionItem.mouseMoveEvent()`:
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Move a grabbed letter along its line (an angle's arc)."""
        if self.before is None:
            return
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        where: QPointF = event.scenePos() - self.grab
        self.prepareGeometryChange()
        if dimension.kind == ANGLE:
            placed: tuple[float, float] | None = angle_place(
                self.editor.drawing.points, dimension, where
            )
            if placed is not None:
                dimension.along = placed[1]
        else:
            start: QPointF
            end: QPointF
            _, _, start, end = self.ends()
            way: QPointF = end - start
            square: float = QPointF.dotProduct(way, way)
            if square != 0.0:
                dimension.along = (
                    QPointF.dotProduct(where - start, way) / square
                )
        self.update()
        if self.index < len(self.editor.circles):
            self.editor.circles[self.index].place()

    # Method `DimensionItem.mouseReleaseEvent()`:
    def mouseReleaseEvent(self, _event: QGraphicsSceneMouseEvent) -> None:
        """End a letter's drag: remember it, if it moved the letter."""
        if self.before is not None and self.before.dimensions != tuple(
            self.editor.drawing.dimensions
        ):
            self.editor.history.remember(self.before)
        self.before = None

    # Method `DimensionItem.line_point()`:
    def line_point(self, share: float) -> QPointF:
        """Return a point of its line (an angle's arc).

        Arguments:
        * `share` (`float`): How far along, 0 at its start, 1 at its
          end.

        Returns:
        * (`QPointF`): The point.
        """
        dimension: Dimension = self.editor.drawing.dimensions[self.index]
        if dimension.kind == ANGLE:
            return self.arc_point(share)
        start: QPointF
        end: QPointF
        _, _, start, end = self.ends()
        return start + (end - start) * share

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
        """Return where its middle circle sits (#469): on its line (an
        angle's arc), in the middle unless its letter is there, else
        the first of a few spots along it clear of the letter.  A `—`
        or `|` mark's sits just off its box's upper right corner (Y is
        up, #315).

        Returns:
        * (`QPointF`): The circle's middle, in drawing steps.
        """
        found: QRectF | None = self.letter_box()
        letter: QRectF = QRectF() if found is None else found
        off: float = HANDLE_PIXELS / max(self.editor.zoom(), 1e-12)
        if not is_mark(self.editor.drawing.dimensions[self.index]):
            clear: QRectF = letter.adjusted(-off, -off, off, off)
            share: float
            for share in (0.5, 0.25, 0.75, 0.125, 0.875):
                spot: QPointF = self.line_point(share)
                if letter.isNull() or not clear.contains(spot):
                    return spot
            return self.line_point(0.5)
        if letter.isNull():
            return self.at()

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
    * `read_only` (`bool`): True while nothing may be dragged
      (#590b); presses still choose, and the view still pans.
    * `read_only_message` (`str`): What a refused change says, read
      only (`READ_ONLY_MESSAGE`, `LOCKED_MESSAGE`, `TOOL_MESSAGE`).
    * `chosen_points` (`list[int]`):
      The selected points (`ORIGIN` or corners), in the order clicked.
    * `chosen_dimensions` (`list[int]`): The selected dimensions.
    * `chosen_edges` (`list[Edge]`): The selected edges, each by the
      corners it leaves and reaches (an axis as `(X_AXIS, -1)`,
      `T.sa~6.11` #797), in the order clicked.
    * `wanted` (`bool`): Whether [Dimension] waits for points.
    * `pan_from` (`QPoint | None`):
      Where the pointer was, while empty space is dragged.
    * `letters_changed` (`Callable[[], None]`):
      Called after a new dimension adds a letter (the window sets it).
    * `armed` (`str | None`): The fillet letter a corner clicked takes
      ("" makes it sharp), armed in [Fillets] (#214); `None`: none.
    * `names_shown` (`bool`): Whether [Edit] writes the corners'
      names beside them, [Show Names] (#796).
    * `released` (`Callable[[], None]`):
      Called after a mouse button comes up (the window saves).
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
    * `mirror_squares` (`list[CornerCircle]`): The corners' circles on
      a revolved outline's mirrored half (#474).
    * `mirror_handles` (`list[EdgeHandle]`): The mirrored edges'
      handles (#475).
    * `placing` (`bool`): Whether a circle is being put on its corner
      (its move is not a drag).
    * `moving` (`CornerCircle | None`): The circle whose own drag is
      being followed, which Qt places itself.
    * `circles` (`list[DimensionHandle]`): The dimensions' middle
      circles, one per dimension, in order.
    * `tips` (`list[DimensionHandle]`): The dimensions' end circles
      (#470).
    * `grips` (`list[StripHandle]`): The hide strips' circles.
    * `solution` (`Solution`): The corners' formulas, and what is
      amiss.
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
        self.names_shown: bool = False
        # The corner being dragged, whose own marks are left out until
        # it is dropped (#451), or -1.
        self.dragged: int = -1
        self.history: History = History()
        self.message: str = ""
        self.read_only: bool = False
        self.read_only_message: str = READ_ONLY_MESSAGE
        self.chosen_points: list[int] = []
        self.chosen_dimensions: list[int] = []
        self.chosen_edges: list[Edge] = []
        self.wanted: bool = False
        self.letters_changed: Callable[[], None] = self.update
        self.released: Callable[[], None] = self.update
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
        self.mirror_squares: list[CornerCircle] = []
        self.mirror_handles: list[EdgeHandle] = []
        self.placing: bool = False
        self.moving: CornerCircle | None = None
        self.circles: list[DimensionHandle] = []
        self.tips: list[DimensionHandle] = []
        self.grips: list[StripHandle] = []
        self.measures: list[DimensionItem] = []
        self.solution: Solution = solve(
            drawing.points, drawing.dimensions, drawing.loops()
        )
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
        for square in self.squares + self.mirror_squares:
            self.scene().removeItem(square)
        corners: range = range(len(self.drawing.points))
        self.squares = [CornerCircle(self, index) for index in corners]
        self.mirror_squares = [
            CornerCircle(self, index, mirrored=True) for index in corners
        ]
        for square in self.squares + self.mirror_squares:
            self.scene().addItem(square)
            square.place()
        handle: EdgeHandle
        for handle in self.handles + self.mirror_handles:
            self.scene().removeItem(handle)
        edges: list[Edge] = self.drawing.edges()
        self.handles = [EdgeHandle(self, edge) for edge in edges]
        self.mirror_handles = [
            EdgeHandle(self, edge, mirrored=True) for edge in edges
        ]
        for handle in self.handles + self.mirror_handles:
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
        for circle in self.circles + self.tips:
            self.scene().removeItem(circle)
        self.circles = [
            DimensionHandle(self, index)
            for index in range(len(self.drawing.dimensions))
        ]
        self.tips = [
            DimensionHandle(self, index, part)
            for index in range(len(self.drawing.dimensions))
            for part in (LINE_START, LINE_END)
        ]
        for circle in self.circles + self.tips:
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

    # Method `OutlineView.corner_near()`:
    def corner_near(self, where: QPointF) -> int | None:
        """Return the corner (or `ORIGIN`, or on a revolved outline a
        corner's mirror image, as its `mirror_code()`) nearest `where`,
        within `DROP_PIXELS` on screen: where a dimension's end circle
        dropped there lands (#470, #479).

        Arguments:
        * `where` (`QPointF`): The drop, in the scene.

        Returns:
        * (`int | None`): The point's code, or `None` when none is
          that close.
        """
        reach: float = DROP_PIXELS / max(self.zoom(), 1e-12)
        best: int | None = None
        corners: list[int] = list(range(len(self.drawing.points)))
        mirrors: list[int] = (
            [mirror_code(corner) for corner in corners]
            if self.drawing.revolve
            else []
        )
        which: int
        for which in [ORIGIN, *corners, *mirrors]:
            spot: QPointF = self.point(real_point(which))
            if which <= MIRRORED:
                spot.setX(-spot.x())
            gap: QPointF = spot - where
            far: float = math.hypot(gap.x(), gap.y())
            if far <= reach:
                reach = far
                best = which
        return best

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
    def select_edge(self, edge: Edge) -> None:
        """Add an edge to the selection (as the latest, if it was in).

        Arguments:
        * `edge` (`Edge`): The corners it leaves and reaches, or an
          axis and -1.
        """
        if edge in self.chosen_edges:
            self.chosen_edges.remove(edge)
        self.chosen_edges.append(edge)
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

        # Read only, a press on the drawing says why (#754a).
        if (
            self.read_only
            and event.button() == Qt.MouseButton.LeftButton
            and self.itemAt(event.position().toPoint()) is not None
        ):
            self.message = self.read_only_message
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.scene().mouseGrabberItem() is None
        ):
            axis: int = self.axis_at(event.position().toPoint())
            if self.origin in self.items(event.position().toPoint()):
                self.select_point(ORIGIN)
            elif axis in AXES:
                self.select_edge((axis, -1))
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
            # Read only, a drag of a corner, strip or dimension goes
            # nowhere (#590b): every drag changes things only here.
            if self.read_only and self.scene().mouseGrabberItem() is not None:
                self.message = self.read_only_message
                return
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
        """Take the scale from the values, solve again, then draw the
        dimensions and squares to match.  The corners stay as drawn:
        an outline file is a template (#457)."""
        self.apply_values()
        self.outline.refresh()
        self.solution = solve(
            self.drawing.points, self.working(), self.drawing.loops()
        )
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
            self.drawing.dimensions,
            self.dragged,
            len(self.drawing.points),
            self.drawing.loops(),
        )

    # Method `OutlineView.apply_values()`:
    def apply_values(self) -> None:
        """Take the drawing's scale (drawing steps per mm) from the
        letters' values (`values.placed_corners()`, #148), leaving the
        corners where they are drawn (#457)."""
        self.drawing.scale = placed_corners(
            self.drawing.points,
            self.drawing.letters,
            self.working(),
            self.drawing.scale,
            self.drawing.loops(),
        )[1]

    # Method `OutlineView.place_handles()`:
    def place_handles(self) -> None:
        """Put each edge's handle in its middle (shown if long enough),
        and each corner's circles on it and its mirror image (#474)."""
        handle: EdgeHandle
        for handle in self.handles + self.mirror_handles:
            handle.place()
        square: CornerCircle
        for square in self.squares + self.mirror_squares:
            square.place()
        circle: DimensionHandle
        for circle in self.circles + self.tips:
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
        end: int = self.drawing.neighbours(index)[1]
        x0, y0 = points[index]
        x1, y1 = points[end]
        self.history.remember(self.drawing.snapshot())
        self.drawing.insert(((x0 + x1) / 2.0, (y0 + y1) / 2.0), (index, end))
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
        problem: str = self.removal_problem([index])
        if problem:
            self.message = problem
            return
        self.history.remember(self.drawing.snapshot())
        self.drawing.remove(index)
        self.message = ""
        self.make_squares()

    # Method `OutlineView.removal_problem()`:
    def removal_problem(self, corners: list[int]) -> str:
        """Say why corners may not be deleted: one is shared by
        polygons (`T.sa~6.11` #777), or a polygon would be left with
        fewer than `LEAST_CORNERS`.

        Arguments:
        * `corners` (`list[int]`): The corners.

        Returns:
        * (`str`): The reason, or "" when they may go.
        """
        names: list[str] = self.drawing.names
        corner: int
        for corner in corners:
            sharing: list[str] = self.drawing.sharing(corner)
            if len(sharing) > 1:
                return (
                    f"{names[corner]} is a corner of {' and '.join(sharing)}"
                    ": a shared corner can not be deleted."
                )
        going: set[str] = {names[corner] for corner in corners}
        polygon: Polygon
        for polygon in self.drawing.polygons:
            left: int = len(set(polygon.vertices) - going)
            if left < LEAST_CORNERS:
                return (
                    f"{polygon.name} needs at least {LEAST_CORNERS} corners."
                )
        return ""

    # Method `OutlineView.delete_selected()`:
    def delete_selected(self) -> None:
        """Delete the selected corners and dimensions, as one change.

        A letter goes with its dimension, unless another one still
        uses it.  An outline keeps at least `LEAST_CORNERS` corners.
        """
        corners: list[int] = sorted(
            {
                real_point(point)
                for point in self.chosen_points
                if point != ORIGIN
            },
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
        problem: str = self.removal_problem(corners)
        if problem:
            self.message = problem
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
        edges: list[Edge] = self.chosen_edges
        points: list[int] = self.chosen_points
        if len(edges) >= 2:
            self.angle_selected()
            return
        if len(edges) == 1 and edges[0][0] not in AXES and not points:
            self.dimension_between(edges[0][0], edges[0][1], LENGTH)
            return
        if not edges and len(points) == 1 and points[0] != ORIGIN:
            # The corner's two edges in its polygon (#797).
            corner: int = real_point(points[0])
            back: int
            ahead: int
            back, ahead = self.drawing.neighbours(corner)
            self.chosen_edges = [(back, corner), (corner, ahead)]
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
        axes: list[int] = [
            edge[0] for edge in self.chosen_edges if edge[0] in AXES
        ]
        corners: list[int] = [
            real_point(point)
            for point in self.chosen_points
            if point != ORIGIN
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
        self.dimension_codes(first, second)

    # Method `OutlineView.dimension_codes()`:
    def dimension_codes(self, first: int, second: int) -> None:
        """Dimension two selected points, either of which may be a
        mirrored corner (#478), as the kinds the solver knows: a
        corner and its own mirror image give its diameter; two mirror
        images, or one and the origin, what their corners give; one
        and another corner a vertical, or a horizontal across the axis
        when wider than tall (#479).

        Arguments:
        * `first` (`int`): The first point's code.
        * `second` (`int`): The second point's code.
        """
        mirrored: tuple[bool, bool] = (first <= MIRRORED, second <= MIRRORED)
        start: int = real_point(first)
        end: int = real_point(second)
        kind: str = ""
        if mirrored[0] != mirrored[1] and ORIGIN not in (start, end):
            if start == end:
                self.dimension_between(ORIGIN, start, DIAMETER)
                return

            # Across the axis (#479): horizontal from the mirrored
            # one's image (stored as `start`) when wider than tall.
            if mirrored[1]:
                start, end = end, start
            wide: float = abs(self.point(start).x() + self.point(end).x())
            up: float = abs(self.point(start).y() - self.point(end).y())
            if wide >= up:
                self.dimension_between(start, end, DIAMETER)
                return
            kind = VERTICAL
        if self.point(start) == self.point(end):
            self.message = "Those two points are in the same place."
            self.scene().update()
            return
        self.dimension_between(start, end, kind)

    # Method `OutlineView.angle_selected()`:
    def angle_selected(self) -> None:
        """[Angle]: an angle between the last two edges clicked, its
        letter's default the angle as drawn, to a whole degree."""
        if len(self.chosen_edges) < 2:
            self.message = "Select two edges' circles for an angle."
            self.scene().update()
            return
        first: Edge
        second: Edge
        first, second = self.chosen_edges[-2:]
        if first[0] in AXES and second[0] in AXES:
            self.message = "The axes are 90 deg apart: pick an edge."
            self.scene().update()
            return
        points: list[tuple[float, float]] = self.drawing.points
        rays: tuple[int, int] | None = middle_rays(
            points, first[0], second[0], (first[1], second[1])
        )
        if rays is None:
            self.message = "Those edges are parallel: no angle."
            self.scene().update()
            return

        # The rays toward the edges' middles fix the sector (#53);
        # measured counterclockwise from the edge that makes it under
        # 180 degrees, so the value is positive (#57).
        arc: tuple[QPointF, float, float] | None = edge_arc(
            points, first[0], second[0], rays, (first[1], second[1])
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
                edge_start(points, edge[0])
                + edge_way(points, edge[0], edge[1]) / 2.0
                - arc[0]
                for edge in (first, second)
                if edge[0] not in AXES
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
                first[0],
                second[0],
                max(reach / 2.0, 2.0 * self.step()),
                rays=rays,
                start_to=_reached(first, len(points)),
                end_to=_reached(second, len(points)),
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
          radius UDF", #116, #120); "" for sharp.  Refused, saying why,
          for a corner of more than one polygon (#798).
        """
        # A shared corner stays sharp, or its polygons would part
        # (`T.sa~6.11` #798).
        shared: list[str] = [
            self.drawing.names[corner]
            for corner in corners
            if choice and len(self.drawing.sharing(corner)) > 1
        ]
        if shared:
            self.message = (
                f"{', '.join(shared)}: a corner of more than one polygon"
                " can not be filleted."
            )
            self.scene().update()
            return
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
        X or Y, or onto an axis, within `SNAP_PIXELS`.  Nothing holds
        it (#457): the values never place a template's corners.

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
            self.drawing.loops(),
        )
        moved.setX(here[0])
        moved.setY(here[1])
        points[corner] = here

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
            self.drawing.points,
            self.drawing.dimensions,
            corner,
            0.0,
            self.drawing.loops(),
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

    # Method `OutlineView.rename_corner()`:
    def rename_corner(self, corner: int, name: str) -> bool:
        """Rename a corner, as one change (#795); refused, saying why,
        when read only or when the name is bad or used (#787).

        Arguments:
        * `corner` (`int`): The corner's index.
        * `name` (`str`): Its new name.

        Returns:
        * (`bool`): Whether it was renamed.
        """
        problem: str = ""
        if self.read_only:
            problem = self.read_only_message
        elif not VERTEX_NAME.fullmatch(name):
            problem = (
                f"{name!r} is not a vertex name: a letter, then letters,"
                " digits or _."
            )
        elif name in ENDS.values():
            problem = f"{name!r} names an end; choose another name."
        elif name in self.drawing.names and (
            self.drawing.names.index(name) != corner
        ):
            problem = f"{name} is already a vertex's name."
        self.message = problem
        if not problem and self.drawing.names[corner] != name:
            self.history.remember(self.drawing.snapshot())
            old: str = self.drawing.names[corner]
            self.drawing.names[corner] = name
            polygon: Polygon
            for polygon in self.drawing.polygons:
                polygon.vertices[:] = [
                    name if each == old else each for each in polygon.vertices
                ]
        self.scene().update()
        return not problem

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

    # Method `OutlineView.loose_corners()`:
    def loose_corners(self) -> set[int]:
        """Return the corners a solid needs that are not dimensioned
        yet; a cut line's need none (`T.sa~6.11` #861).

        Returns:
        * (`set[int]`): Their indices.
        """
        needed: set[int] = self.drawing.solid_corners()
        return {
            corner
            for corner, _ in self.solution.missing(len(self.drawing.points))
            if corner in needed
        }

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
        missing: set[int] = self.loose_corners()
        square: CornerCircle
        for square in self.squares + self.mirror_squares:
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
                chosen if square.code() in self.chosen_points else hollow
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
        for handle in self.handles + self.mirror_handles:
            handle.setPen(ring)
            handle.setBrush(
                chosen
                if (handle.index, handle.end) in self.chosen_edges
                else hollow
            )
        # A strip's circles have a paper inside, so the hatching does
        # not run through them (#177); they look hollow all the same.
        grip: StripHandle
        for grip in self.grips:
            grip.setPen(ring)
            grip.setBrush(QBrush(QColor(scheme.paper)))
        circle: DimensionHandle
        for circle in self.circles + self.tips:
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
        """Fit the outline, the origin and the dimensions shown, with
        their letters, in the window (#572)."""
        # Twice: a letter's room is in pixels, so it is known only
        # once the zoom is near its last.
        for _ in range(2):
            box: QRectF = self.outline.boundingRect().united(
                QRectF(-1.0, -1.0, 2.0, 2.0)
            )
            measure: DimensionItem
            for measure in self.measures:
                if measure.isVisible():
                    box = box.united(measure.boundingRect())
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
        for circle in self.circles + self.tips:
            circle.place()
        self.viewport().update()

    # Method `OutlineView.new_polygon()`:
    def new_polygon(self) -> None:
        """[New Polygon] (`T.sa~6.11` #772): on the edge between the
        last two corners chosen, an equilateral triangle outside its
        polygon, sharing the two; one change."""
        corners: list[int] = [
            real_point(code)
            for code in self.chosen_points
            if real_point(code) >= 0
        ]
        problem: str = ""
        if self.read_only:
            problem = self.read_only_message
        elif len(corners) < 2:
            problem = "Choose the two corners of an edge for [New Polygon]."
        if not problem:
            before: Snapshot = self.drawing.snapshot()
            if self.drawing.new_triangle(corners[-2], corners[-1]):
                self.history.remember(before)
            else:
                problem = (
                    "Those two corners are not an edge of one polygon,"
                    " outside every other: choose the ends of an edge."
                )
        self.message = problem
        if not problem:
            self.make_squares()
            self.restyle()
        self.scene().update()

    # Method `OutlineView.new_circle()`:
    def new_circle(self) -> None:
        """[New Circle] (`T.sa~6.11` #789): a circle in the middle of
        the polygon through the last corner chosen, standing on it;
        one change.  Its `z` and diameter are set in [Polygons]."""
        corners: list[int] = [
            real_point(code)
            for code in self.chosen_points
            if real_point(code) >= 0
        ]
        problem: str = ""
        if self.read_only:
            problem = self.read_only_message
        elif self.drawing.revolve:
            problem = "A revolved outline has no circles."
        elif not corners:
            problem = "Choose a corner of the polygon for [New Circle]."
        if not problem:
            before: Snapshot = self.drawing.snapshot()
            if self.drawing.new_circle(corners[-1]):
                self.history.remember(before)
            else:
                problem = "That corner is in no polygon."
        self.message = problem
        if not problem:
            self.make_squares()
            self.restyle()
        self.scene().update()

    # Method `OutlineView.new_cut()`:
    def new_cut(self) -> None:
        """[Cut Line] (`T.sa~6.11` #776, #861): a cut line across the
        polygon through the last corner chosen; one change.  Its ends
        and side point are dragged like corners."""
        corners: list[int] = [
            real_point(code)
            for code in self.chosen_points
            if real_point(code) >= 0
        ]
        problem: str = ""
        if self.read_only:
            problem = self.read_only_message
        elif self.drawing.revolve:
            problem = "A revolved outline is its own section."
        elif not corners:
            problem = "Choose a corner of the polygon for [Cut Line]."
        if not problem:
            before: Snapshot = self.drawing.snapshot()
            if self.drawing.new_cut(corners[-1]):
                self.history.remember(before)
            else:
                problem = "That corner is in no polygon."
        self.message = problem
        if not problem:
            self.make_squares()
            self.restyle()
        self.scene().update()

    # Method `OutlineView.toggle_names()`:
    def toggle_names(self) -> None:
        """[Show Names] (#796): write each corner's name beside it in
        [Edit], or not."""
        self.names_shown = not self.names_shown
        self.viewport().update()

    # Method `OutlineView.draw_names()`:
    def draw_names(self, painter: QPainter) -> None:
        """Write each corner's name up and right of its circle (#796),
        in screen pixels so it stays one size at every zoom.

        Arguments:
        * `painter` (`QPainter`): What draws, in scene coordinates.
        """
        painter.save()
        painter.resetTransform()
        painter.setPen(QColor(theme.colors().ink))
        painter.setFont(QFont("sans-serif", LETTER_POINTS))
        name: str
        x: float
        y: float
        for name, (x, y) in zip(
            self.drawing.names, self.drawing.points, strict=True
        ):
            spot: QPoint = self.mapFromScene(QPointF(x, y))
            painter.drawText(
                QPointF(spot.x() + SQUARE_PIXELS, spot.y() - SQUARE_PIXELS),
                name,
            )
        painter.restore()

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
        in the working view (#170); in the overview, the corners' names
        under [Show Names] (#796); write the fillets' note in the
        lower left, when any fillet has no radius of its own (#118)."""
        if self.overview:
            self.shade_hides(painter, QRectF(exposed))
            if self.names_shown:
                self.draw_names(painter)
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
        return cut_pieces(self.drawing.points, self.drawing.hides, axis, gap)

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

        # The end pieces reach `FAR`: trimmed to what is drawn, or
        # zoomed in they overflow Qt's clipping and draw nothing
        # (`T.toasl~6.8` #743, an upright drill with strips across).
        box: QRectF = self.scene().itemsBoundingRect().adjusted(-1, -1, 1, 1)
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
                ).intersected(box)
                if source.isEmpty():
                    continue
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
                        self.drawing.loops(),
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
        the working view would leave it out.  A strip cuts its stretch
        out of the whole drawing, so a letter anywhere along that
        stretch is covered, beside the outline too (`T.toasl~6.8`
        #742).  The user moves the strip or the letter.  Marks are not
        in the diagram (#451), so a strip may cover them.

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
            # Any part of a letter in the stretch counts (#322, #742):
            # its box overlaps the strip along it, wherever across.
            letter: QRectF
            for letter in boxes:
                ends: tuple[float, float] = (
                    (letter.top(), letter.bottom())
                    if hide.axis == HIDE_Y
                    else (letter.left(), letter.right())
                )
                if ends[0] < high and ends[1] > low:
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
            chosen: bool = (axis, -1) in self.chosen_edges
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
    * `drawing` (`Drawing`): The outline being drawn.
    * `read_only` (`bool`): True while the outline may not be changed
      (locked, a tool's values, or not [Edit], #590, #755): the view
      still zooms, pans and chooses.
    * `locked` (`bool`): True when its owner forbids changes (a read
      only shop, #756), so [Edit] is greyed.
    * `tool_values` (`bool`): True while it shows one tool's values
      (`show_tool()`), so the outline is never saved.
    * `edit_outline` (`Callable[[], None] | None`): Opens a tool's
      kind's outline, from the link beside the tabs (#757).
    * `views` (`QWidget`): The drawing's tabs over what they show.
    * `tab_bar` (`QTabBar`): [Drawing], [SVG], [Edit] (`ViewTab`).
    * `stack` (`QStackedWidget`): The view or the diagram.
    * `outline_link` (`QLabel`): "Edit the Drill outline", for a tool.
    * `users_link` (`QLabel`): "Used by:" the assemblies using the
      outline, each a link (`T.sa~6.11` #783h).
    * `open_user` (`Callable[[str], None] | None`): Opens one of them,
      by its path.
    * `file_field` (`QLineEdit`): The outline's place in its shop,
      typed over to move or rename it, in [Edit] (`T.sa~6.11` #783h).
    * `moved` (`Callable[[Path], None] | None`): Shows the outline at
      its new place.
    * `picture` (`QSvgWidget`): The diagram, in [SVG].
    * `splitter` (`QSplitter`): The drawing over the table.
    * `status` (`QLabel`): The last refusal, under the button tabs.
    * `letters` (`ValuesTable`): The letters' table, its tabs and
      problems (`outline_values.py`).
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
        self.read_only: bool = False
        self.locked: bool = False
        self.tool_values: bool = False
        self.tool_material: str = ""
        self.tool_name: str = ""
        self.edit_outline: Callable[[], None] | None = None
        self.open_user: Callable[[str], None] | None = None
        self.moved: Callable[[Path], None] | None = None
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
        self.views: QWidget = self.drawing_tabs()
        self.splitter.addWidget(self.views)
        self.values: ValuesTable = ValuesTable(
            self.drawing,
            self.view,
            save=self.save,
            show_message=self.show_message,
            arm=self.arm,
        )
        self.splitter.addWidget(self.values)
        self.splitter.setSizes([450, 150])
        layout.addWidget(self.splitter)
        self.vertex_name: QLineEdit = QLineEdit()
        self.make_buttons()
        self.hook_view()
        self.values.fill_table()
        self.show_tab(ViewTab.EDIT)
        self.resize(800, 600)

    # Method `OutlineEditor.make_buttons()`:
    def make_buttons(self) -> None:
        """Make the buttons (#319): each word one `QAction`, shown as
        a button on every tab listing it, so that its checked and
        enabled state is the same on all of them."""
        self.button_actions: dict[str, QAction] = {}
        self.buttons: dict[str, QToolButton] = {}
        word: str
        for word in BUTTON_WORDS:
            # [Dim. Kind] cycles, so it shows a cycle arrow (U+21BB).
            cycle: str = " \u21bb" if word == "Dim. Kind" else ""
            self.button_actions[word] = QAction(f"{word}{cycle}", self)
        for word in ("Grid", "Snap", "Revolve", "Show Marks", "Show Names"):
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
            if title == "Draw":
                self.add_vertex_name(row)
            row.addStretch(1)
            self.button_tabs.addTab(page, title)

        # What each button does.
        does: dict[str, Callable[[], None]] = {
            "Grid": self.view.toggle_grid,
            "Snap": self.toggle_snap,
            "Fit": self.view.fit,
            "Delete": self.values.delete,
            "Dimension": self.view.dimension_selected,
            "Dim. Kind": self.view.cycle_kind,
            "Show Marks": self.view.toggle_marks,
            "Show Names": self.view.toggle_names,
            "Revolve": self.toggle_revolve,
            "Rotate Diagram": self.view.rotate_diagram,
            "Font +": partial(self.view.step_font, 1),
            "Font -": partial(self.view.step_font, -1),
            "Hide": self.view.start_hide,
            "Undo": self.view.undo,
            "Redo": self.view.redo,
            "New Letter": self.values.new_letter,
            "New Polygon": self.view.new_polygon,
            "New Circle": self.view.new_circle,
            "Cut Line": self.view.new_cut,
        }
        does_it: Callable[[], None]
        for word, does_it in does.items():
            self.button_actions[word].triggered.connect(does_it)

    # Method `OutlineEditor.add_vertex_name()`:
    def add_vertex_name(self, row: QHBoxLayout) -> None:
        """Add the chosen corner's name to a row of buttons (#795):
        shown when one corner is chosen, renamed by typing a new one
        and pressing Enter.

        Arguments:
        * `row` (`QHBoxLayout`): The [Draw] tab's row.
        """
        row.addWidget(QLabel("Vertex:"))
        self.vertex_name.setMaximumWidth(90)
        self.vertex_name.setToolTip(
            "The chosen corner's name: type a new one and press Enter."
        )
        self.vertex_name.returnPressed.connect(self.rename_vertex)
        row.addWidget(self.vertex_name)

    # Method `OutlineEditor.chosen_corner()`:
    def chosen_corner(self) -> int:
        """Return the one corner chosen (its mirror counts), else -1.

        Returns:
        * (`int`): Its index, or -1 unless one corner is chosen.
        """
        corners: set[int] = {
            real_point(code)
            for code in self.view.chosen_points
            if real_point(code) >= 0
        }
        return corners.pop() if len(corners) == 1 else -1

    # Method `OutlineEditor.show_vertex_name()`:
    def show_vertex_name(self) -> None:
        """Show the chosen corner's name, unless it is being typed
        (#795); with no corner (or several) chosen, nothing."""
        corner: int = self.chosen_corner()
        self.vertex_name.setEnabled(corner >= 0 and not self.read_only)
        if not self.vertex_name.hasFocus() or corner < 0:
            self.vertex_name.setText(
                self.drawing.names[corner] if corner >= 0 else ""
            )

    # Method `OutlineEditor.rename_vertex()`:
    def rename_vertex(self) -> None:
        """[Enter] in the vertex name: rename the chosen corner (#795);
        a refusal is said in the status line and the name kept to be
        fixed."""
        corner: int = self.chosen_corner()
        if corner >= 0 and self.view.rename_corner(
            corner, self.vertex_name.text().strip()
        ):
            self.view.setFocus()
        self.show_message()

    # Method `OutlineEditor.drawing_tabs()`:
    def drawing_tabs(self) -> QWidget:
        """Return the drawing's tabs (`ViewTab`, #755): [Drawing] and
        [Edit] share the one view, cut out or whole; [SVG] the
        diagram it makes, kept to its shape.  Beside them, for a
        tool, the link to its kind's outline (#757).

        Returns:
        * (`QWidget`): The tabs over what they show.
        """
        self.tab_bar: QTabBar = QTabBar()
        tab: ViewTab
        for tab in ViewTab:
            self.tab_bar.addTab(tab.value)
        self.outline_link: QLabel = QLabel("")
        self.outline_link.setVisible(False)
        self.outline_link.linkActivated.connect(self.follow_outline_link)
        self.users_link: QLabel = QLabel("")
        self.users_link.setVisible(False)
        self.users_link.linkActivated.connect(self.follow_user_link)
        self.file_field: QLineEdit = QLineEdit()
        self.file_field.setToolTip(
            "This outline's place in the shop: type a new one and press"
            " Enter to move or rename it; the assemblies using it follow"
        )
        self.file_field.setVisible(False)
        self.file_field.returnPressed.connect(self.move_file)
        # [Solid] shows a round tool in SolidCraft (`T.sa~6.11` #819).
        self.solid_button: QPushButton = QPushButton("Solid")
        self.solid_button.setToolTip("Show this as a solid in SolidCraft")
        self.solid_button.clicked.connect(self.show_solid)
        row: QHBoxLayout = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.tab_bar)
        row.addWidget(self.solid_button)
        row.addWidget(self.outline_link)
        row.addWidget(self.users_link)
        row.addStretch(1)
        row.addWidget(self.file_field)
        self.stack: QStackedWidget = QStackedWidget()
        self.stack.addWidget(self.view)
        self.stack.addWidget(self.picture)
        views: QWidget = QWidget()
        column: QVBoxLayout = QVBoxLayout(views)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addLayout(row)
        column.addWidget(self.stack)
        self.tab_bar.currentChanged.connect(self.tab_changed)
        return views

    # Method `OutlineEditor.tab()`:
    def tab(self) -> ViewTab:
        """Return the drawing's tab shown.

        Returns:
        * (`ViewTab`): It.
        """
        return list(ViewTab)[max(self.tab_bar.currentIndex(), 0)]

    # Method `OutlineEditor.show_tab()`:
    def show_tab(self, tab: ViewTab) -> None:
        """Show one of the drawing's tabs; [Edit] only when it may be
        chosen (else [Drawing]).

        Arguments:
        * `tab` (`ViewTab`): The tab.
        """
        index: int = list(ViewTab).index(tab)
        if tab is ViewTab.EDIT and not self.tab_bar.isTabEnabled(index):
            index = list(ViewTab).index(ViewTab.DRAWING)
        if index == self.tab_bar.currentIndex():
            self.tab_changed(index)
        else:
            self.tab_bar.setCurrentIndex(index)

    # Method `OutlineEditor.tab_changed()`:
    def tab_changed(self, _index: int) -> None:
        """Show what the tab now chosen shows: the view, cut out or
        whole, or the diagram; changes only in [Edit] (#755, #759)."""
        tab: ViewTab = self.tab()
        match tab:
            case ViewTab.SVG:
                self.stack.setCurrentWidget(self.picture)
                self.show_svg()
            case ViewTab.DRAWING | ViewTab.EDIT:
                self.stack.setCurrentWidget(self.view)
                if self.view.overview != (tab is ViewTab.EDIT):
                    self.view.toggle_overview()
            case _:
                assert_never(tab)
        self.apply_read_only()

    # Method `OutlineEditor.offer_outline()`:
    def offer_outline(self, kind: str, edit: Callable[[], None]) -> None:
        """For a tool: a link to its kind's outline, in place of the
        [Edit] tab (#757).

        Arguments:
        * `kind` (`str`): The kind's name, as "Drill".
        * `edit` (`Callable[[], None]`): Opens the kind's outline.
        """
        self.edit_outline = edit
        self.outline_link.setText(
            f'<a href="edit">Edit the {kind} outline</a>'
        )
        self.outline_link.setToolTip(
            f"This tool's values change here; the {kind.lower()} "
            "outline every one of them shares is changed in its own "
            "[Edit] tab."
        )
        self.outline_link.setVisible(True)

    # Method `OutlineEditor.offer_users()`:
    def offer_users(
        self, users: list[tuple[str, str]], open_user: Callable[[str], None]
    ) -> None:
        """Say which assemblies use this outline, each a link that opens
        it (`T.sa~6.11` #783h); nothing when none do.

        Arguments:
        * `users` (`list[tuple[str, str]]`): Each one's name, as "Z
          setter assembly", and its path.
        * `open_user` (`Callable[[str], None]`): Opens one, by path.
        """
        self.open_user = open_user
        self.users_link.setText(
            "Used by: "
            + ", ".join(f'<a href="{path}">{name}</a>' for name, path in users)
        )
        self.users_link.setToolTip(
            "Changing this outline changes these assemblies too."
        )
        self.users_link.setVisible(bool(users))

    # Method `OutlineEditor.follow_user_link()`:
    def follow_user_link(self, link: str) -> None:
        """Open an assembly using this outline (its link's path)."""
        if self.open_user is not None:
            self.open_user(link)

    # Method `OutlineEditor.follow_outline_link()`:
    def follow_outline_link(self, _link: str) -> None:
        """Open the kind's outline (the link beside the tabs)."""
        if self.edit_outline is not None:
            self.edit_outline()

    # Method `OutlineEditor.show_svg()`:
    def show_svg(self) -> None:
        """Draw the [SVG] tab again when it is chosen: the outline's
        diagram (`outline_sheet()`), in the theme's ink and paper."""
        colors: theme.Colors = theme.colors()
        self.picture.load(
            svg(
                outline_sheet(self.drawing, hatch=self.view.outline.hatch),
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
        self.view.letters_changed = self.values.fill_table
        self.view.released = self.save
        self.view.cleared = self.cleared
        self.view.lighted = self.values.frame_row

    # Method `OutlineEditor.cleared()`:
    def cleared(self) -> None:
        """The drawing's selection is cleared: the table's too, and
        any armed letter (#214)."""
        self.values.table.clearSelection()
        self.arm(None)

    # Method `OutlineEditor.arm()`:
    def arm(self, letter: str | None) -> None:
        """Arm a fillet letter ("" for "No fillet"), or disarm (`None`);
        arming also fillets the corners already selected (#218).

        Arguments:
        * `letter` (`str | None`): The letter.
        """
        # Read only, arming would fillet the chosen corners (#590b).
        if self.read_only and letter is not None:
            self.view.message = self.view.read_only_message
            letter = None
        self.view.armed = letter
        if letter is not None:
            corners: list[int] = list(
                dict.fromkeys(
                    real_point(point)
                    for point in self.view.chosen_points
                    if point != ORIGIN
                )
            )
            if corners:
                self.view.set_fillets(corners, letter)
        self.values.light_armed()
        self.show_message()

    # Method `OutlineEditor.toggle_snap()`:
    def toggle_snap(self) -> None:
        """Turn snapping on or off, as [Snap] now shows."""
        self.view.snap_on = self.button_actions["Snap"].isChecked()

    # Method `OutlineEditor.toggle_revolve()`:
    def toggle_revolve(self) -> None:
        """[Revolve]: revolve or not, the button showing the result
        (a refusal leaves it as it was)."""
        self.view.toggle_revolve()
        self.button_actions["Revolve"].setChecked(self.view.drawing.revolve)

    # Method `OutlineEditor.show_tool()`:
    def show_tool(self, tool: ToolValues) -> None:
        """Show one tool of the outline's kind: its values drawn and in
        the table beside the defaults (`T.toasl~6.8` #735, #736).

        The outline itself is never changed or saved from here; only
        the tool's values may be typed in, into the tool's file.

        Arguments:
        * `tool` (`ToolValues`): The tool's values, and how to write
          them.
        """
        self.tool_values = True
        self.tool_material = tool.material
        self.tool_name = tool.name
        self.view.outline.hatch = tool_hatch(self.path, tool.material)
        template: Drawing = copy.deepcopy(self.drawing)

        # Function `redraw()`:
        def redraw() -> None:
            """Draw the outline for the tool's values as they are now."""
            drawn: Drawing = tool_drawing(template, tool.values)
            self.drawing.letters[:] = drawn.letters
            self.drawing.points[:] = drawn.points
            self.drawing.scale = drawn.scale
            self.view.follow()

        tool.redraw = redraw
        redraw()
        self.prepare_solid()
        self.tab_bar.setTabVisible(list(ViewTab).index(ViewTab.EDIT), False)
        self.set_read_only(True)
        self.values.show_tool(tool)

    # Method `OutlineEditor.solid_model()`:
    def solid_model(self) -> Cacheable:
        """Return the solid this drawing makes, for the cache: a tool's
        named after it, in its material's colour; a bare outline's
        after its file, in HSS (`T.sa~6.11` #827, #846).

        Returns:
        * (`Cacheable`): The solid.

        Raises:
        * `ValueError`: If the drawing makes no solid.
        """
        kind: str = (
            self.path.name.removesuffix(OUTLINE_SUFFIX)
            if self.path is not None
            else "outline"
        )
        name: str = re.sub(r"\W", "_", self.tool_name or kind)
        if not name[:1].isalpha():
            name = f"{kind}_{name}"
        color: Color | None = material_look(
            self.tool_material or DEFAULT_TOOL_MATERIAL,
            material_looks(shop_of(self.path)),
        ).color
        return outline_cacheable(self.drawing, name, color=color)

    # Method `OutlineEditor.prepare_solid()`:
    def prepare_solid(self) -> None:
        """Make the solid's `.step` in the background, so that [Solid]
        finds it made (`T.sa~6.11` #843); a failure is left for [Solid]
        to say."""
        try:
            model: Cacheable = self.solid_model()
        except ValueError:
            return
        path: Path = VIEWER.cache.path(model)
        if path.exists():
            return

        # Function `make()`:
        def make() -> None:
            """Make the file headless (whole or not at all)."""
            try:
                VIEWER.cache.sweep()
                VIEWER.cache.create_headless(model, path)
            except OSError:
                pass

        threading.Thread(target=make, daemon=True).start()

    # Method `OutlineEditor.show_solid()`:
    def show_solid(self) -> None:
        """[Solid]: show the drawing's solid in SolidCraft, started if
        need be, saying so in the message line (#819, #843)."""
        self.view.message = "Building the solid..."
        self.show_message()
        QApplication.processEvents()
        try:
            VIEWER.show(self.solid_model())
        except (ValueError, ViewerError) as error:
            self.view.message = f"No solid: {error}"
        else:
            self.view.message = ""
        self.show_message()

    # Method `OutlineEditor.set_read_only()`:
    def set_read_only(self, read_only: bool) -> None:
        """Lock the outline, or let it be changed in [Edit] (#590,
        #756).

        Locked, [Edit] is greyed, its tooltip saying why, and the
        drawing goes back to [Drawing].

        Arguments:
        * `read_only` (`bool`): True to lock it.
        """
        self.locked = read_only
        edit: int = list(ViewTab).index(ViewTab.EDIT)
        may: bool = not read_only and not self.tool_values
        # Off [Edit] first: Qt would move a greyed current tab to [SVG].
        if not may and self.tab() is ViewTab.EDIT:
            self.tab_bar.setCurrentIndex(list(ViewTab).index(ViewTab.DRAWING))
        self.tab_bar.setTabEnabled(edit, may)
        self.tab_bar.setTabToolTip(
            edit,
            "Change the outline here: the whole drawing, hide strips shaded"
            if may
            else TOOL_MESSAGE
            if self.tool_values
            else LOCKED_MESSAGE,
        )
        self.apply_read_only()

    # Method `OutlineEditor.apply_read_only()`:
    def apply_read_only(self) -> None:
        """Refuse every change unless [Edit] is shown and allowed.

        Read only, the buttons that change the outline are greyed,
        the letters table cannot be typed in, and drags go nowhere;
        zooming, panning, choosing and the view's buttons still work.
        A refusal says why (`read_only_message`).
        """
        read_only: bool = (
            self.locked or self.tool_values or self.tab() is not ViewTab.EDIT
        )
        self.read_only = read_only
        self.view.read_only = read_only
        self.view.read_only_message = (
            TOOL_MESSAGE
            if self.tool_values
            else LOCKED_MESSAGE
            if self.locked
            else READ_ONLY_MESSAGE
        )
        word: str
        for word in CHANGE_WORDS:
            self.button_actions[word].setEnabled(not read_only)
        self.values.new_fillet.setEnabled(not read_only)
        if read_only:
            self.values.table.setCurrentCell(-1, -1)
            self.arm(None)
        self.values.show_rows()
        self.show_file_field()
        self.show_message()

    # Method `OutlineEditor.show_file_field()`:
    def show_file_field(self) -> None:
        """Show the outline's place in its shop, to move it, only in
        an [Edit] that may change it (`T.sa~6.11` #783h)."""
        place: str = self.shop_place()
        shown: bool = bool(place) and not self.read_only
        self.file_field.setVisible(shown)
        if shown:
            self.file_field.setText(place)

    # Method `OutlineEditor.shop_place()`:
    def shop_place(self) -> str:
        """Return the outline's place from its shop's top, without
        `.outline.toml`; "" when it has no file or is in no shop.

        Returns:
        * (`str`): The place, as `tooling/z_setters/z_setter_block`.
        """
        if self.path is None:
            return ""
        try:
            return (
                self.path.resolve()
                .relative_to(shop_of(self.path))
                .as_posix()
                .removesuffix(OUTLINE_SUFFIX)
            )
        except ValueError:
            return ""

    # Method `OutlineEditor.move_file()`:
    def move_file(self) -> None:
        """Move or rename the outline to the place typed (from the
        shop's top, without `.outline.toml`), its `.svg` and the
        assemblies using it following; a bad place is refused."""
        if self.path is None or self.read_only or not self.shop_place():
            return
        shop: Path = shop_of(self.path)
        text: str = self.file_field.text().strip().strip("/")
        new: Path = shop / f"{text}{OUTLINE_SUFFIX}"
        if new.resolve() == self.path.resolve():
            return
        problem: str = ""
        if not re.fullmatch(r"[A-Za-z0-9_]+(/[A-Za-z0-9_]+)*", text):
            problem = (
                f"{text!r} is not a place for an outline: names of"
                " letters, digits and _, joined by /."
            )
        else:
            try:
                move_outline(self.path, new, shop)
            except OSError as error:
                problem = f"Not moved: {error}"
        if problem:
            self.view.message = problem
            self.show_file_field()
            self.show_message()
            return
        self.path = new
        self.saved = new.read_text(encoding="utf-8")
        self.view.message = ""
        self.show_message()
        if self.moved is not None:
            self.moved(new)

    # Method `OutlineEditor.save()`:
    def save(self) -> None:
        """Rewrite the file if the outline changed (not mid-drag: the
        view saves again when the mouse button comes up), and its
        diagram beside it (`svg_path()`, #248), written too when
        missing."""
        if (
            self.path is None
            or self.tool_values
            or QApplication.mouseButtons() != Qt.MouseButton.NoButton
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

    # Method `OutlineEditor.overlap_problem()`:
    def overlap_problem(self) -> str:
        """Say which polygons overlap (`T.sa~6.11` #790), or "".

        Returns:
        * (`str`): The problem, naming the first pair.
        """
        drawing: Drawing = self.view.drawing
        names: list[str] = [polygon.name for polygon in drawing.polygons]
        found: list[tuple[int, int]] = [
            (one, other)
            for one, other in overlaps(drawing.points, drawing.loops())
            if not drawing.nested(names[one], names[other])
        ]
        if not found:
            return self.parent_problem()
        first: str = names[found[0][0]]
        second: str = names[found[0][1]]
        return (
            f"Polygons {first} and {second} overlap: move a corner so"
            " they only touch."
        )

    # Method `OutlineEditor.parent_problem()`:
    def parent_problem(self) -> str:
        """Say which polygon or circle is not wholly inside its parent
        (`T.sa~6.11` #790, #868), as drawn, or "".

        Returns:
        * (`str`): The problem, naming the first.
        """
        drawing: Drawing = self.view.drawing
        loops: dict[str, list[int]] = dict(
            zip(
                [polygon.name for polygon in drawing.polygons],
                drawing.loops(),
                strict=True,
            )
        )
        circles: dict[str, tuple[tuple[float, float], float]] = {
            circle.name: (
                drawing.points[drawing.names.index(circle.center)],
                circle_radius(drawing, circle, drawing.scale),
            )
            for circle in drawing.circles
        }
        child: str
        parent: str
        for child, parent in drawing.parents().items():
            if parent and not self.inside(child, parent, loops, circles):
                return (
                    f"{child} is not wholly inside its parent {parent}:"
                    " move it in, or choose another parent."
                )
        return ""

    # Method `OutlineEditor.inside()`:
    def inside(
        self,
        child: str,
        parent: str,
        loops: dict[str, list[int]],
        circles: dict[str, tuple[tuple[float, float], float]],
    ) -> bool:
        """Return whether a polygon or circle lies wholly inside
        another, as drawn, touching allowed (#868).

        Arguments:
        * `child` (`str`): Its name.
        * `parent` (`str`): The other's name.
        * `loops` (`dict[str, list[int]]`): Each polygon's corners.
        * `circles` (`dict[str, tuple[tuple[float, float], float]]`):
          Each circle's center and radius, as drawn.

        Returns:
        * (`bool`): Whether it is inside (True when either is unknown).
        """
        points: list[tuple[float, float]] = self.view.drawing.points
        slack: float = 1e-9
        if child in loops and parent in loops:
            return not poking_out(points, loops[child], loops[parent])
        if child in circles and parent in loops:
            return circle_in_loop(*circles[child], points, loops[parent])
        if child in circles and parent in circles:
            (center, radius), (outer, room) = circles[child], circles[parent]
            return math.dist(center, outer) + radius <= room + slack
        if child in loops and parent in circles:
            outer, room = circles[parent]
            return all(
                math.dist(points[corner], outer) <= room + slack
                for corner in loops[child]
            )
        return True

    # Method `OutlineEditor.show_message()`:
    def show_message(self, *_regions: object) -> None:
        """Show the view's last refusal (or nothing) in the mode bar.

        [Undo] and [Redo] are enabled only when there is something to
        undo or redo.
        """
        history: History = self.view.history
        changes: bool = not self.read_only
        self.button_actions["Undo"].setEnabled(changes and bool(history.done))
        self.button_actions["Redo"].setEnabled(
            changes and bool(history.undone)
        )
        # [Revolve] shows the drawing's state (a refusal, an undo).
        self.button_actions["Revolve"].setChecked(self.view.drawing.revolve)
        self.show_vertex_name()
        self.save()
        # A refusal in red; else the armed letter's hint (#214).
        hint: str = ""
        if self.view.armed == "":
            hint = "Click corners to make them sharp"
        elif self.view.armed is not None:
            hint = f"Click corners to fillet them by {self.view.armed}"
        # Crossing edges (#242) and overlapping polygons (#790) are
        # problems too, until undone.
        covered: str = (
            "A hide strip hides a letter (red in the Overview): "
            "move the strip or the letter."
            if self.view.covering()
            else ""
        )
        problem: str = (
            self.view.message
            or (
                "Edges cross (drawn red): move a corner to uncross them."
                if crossings(
                    self.view.drawing.points, self.view.drawing.loops()
                )
                else ""
            )
            or self.overlap_problem()
            or covered
        )
        self.status.setText(problem or hint)
        self.status.setStyleSheet(
            f"color: {theme.colors().problem}" if problem else ""
        )
        self.show_problems()

    # Method `OutlineEditor.show_problems()`:
    def show_problems(self) -> None:
        """Show the letters' problems under the table, then what keeps
        the outline from its real sizes (#445, #448), then any edges
        that the default values make cross (#457)."""
        drawing: Drawing = self.view.drawing
        lines: list[str] = list(self.values.letter_lines)
        placed: str = placement_problem(
            drawing.points, drawing.dimensions, drawing.revolve
        )
        if placed:
            lines.append(placed)
        crossed: list[tuple[Edge, Edge]] = values_cross(
            drawing.points,
            drawing.letters,
            drawing.dimensions,
            drawing.loops(),
        )
        if crossed:
            lines.append(crossing_problem(crossed, drawing.names))
        lines += letter_scope_problems(drawing)
        self.values.problems.setText("\n".join(lines))


# Function `crossing_problem()`:
def crossing_problem(
    crossed: list[tuple[Edge, Edge]], names: list[str]
) -> str:
    """Return the problem shown when the default values make edges
    cross (#457), each edge named by its corners, `V1-V2` (#797).

    Arguments:
    * `crossed` (`list[tuple[Edge, Edge]]`): Each pair of edges that
      cross.
    * `names` (`list[str]`): The corners' names.

    Returns:
    * (`str`): The problem.
    """
    pairs: str = "; ".join(
        f"{names[one[0]]}-{names[one[1]]} and"
        f" {names[other[0]]}-{names[other[1]]}"
        for one, other in crossed
    )
    return (
        f"The default values make edges cross (the edges {pairs}): "
        "change a default, or drag a corner so the template looks "
        "like them."
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
    return drawing_from_text(path.read_text(encoding="utf-8"), str(path))


# Function `drawing_from_text()`:
def drawing_from_text(text: str, source: str = "") -> Drawing:
    """Read a drawing from an outline file's text.

    Arguments:
    * `text` (`str`): The file's text.
    * `source` (`str`): Where it came from, for the messages.

    Returns:
    * (`Drawing`): Its drawing.

    Raises:
    * `OutlineError`: When the text cannot be read as an outline.
    """
    outline: Outline = outline_from_text(text, source)
    return Drawing(
        outline.points,
        outline.letters,
        outline.dimensions,
        outline.revolve,
        outline.note_radius,
        outline.hides,
        outline.text_height,
        outline.turns,
        outline.holes,
        outline.names,
        outline.polygons,
        outline.circles,
        outline.cuts,
    )
