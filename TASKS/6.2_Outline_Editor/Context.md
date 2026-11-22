# LLM Agent Context Log

Suspended 2026-11-22 while `T.tfo~6.5` works; reopen when it needs
an editor feature (holes, #290, first).  Squeezed 2026-11-22, with
`T.sfoe~6.4` (the SVG) folded in: only
what is in force and where things stand; the history is in `hg` and
`git`.  Issue numbers are shared with `T.tfo~6.5` (next new one in
its notes).

## Files and Tests

`python3 -m scraftcam.gui.outline_editor [FILE]` edits an outline
file, rewriting it and its `NAME.outline.svg` after every change
(never mid-drag); a bad file is refused with every problem named, a
missing one starts as the counterclockwise triangle.

* Qt: `gui/outline_editor.py`.  No Qt: `gui/letters.py`,
  `dimensions.py`, `outline_file.py`, `values.py`, `hides.py`,
  `outline_cuts.py`, `outline_diagram.py`, `outline_polygon.py`;
  `scraftcam/diagram.py`, `hershey.py`, `screws.py`.
* Tests: `test_outline_editor`, `test_letters`, `test_dimensions`,
  `test_outline_file`, `test_values`, `test_hides`,
  `test_outline_cuts`, `test_outline_diagram`, `test_diagram`,
  `test_hershey`, `test_outline_polygon` (live ones skip without
  `solidcraft-cli`); plus `test_shops`, `test_gui_tree`,
  `test_gui_theme` when touched.  Coverage above 95% (`uvx --python
  /usr/bin/python3 coverage run --include=... -m unittest ...`).
* Example: `examples/shop/tools/drill.outline.toml` (on its side,
  `turns = 1`, two hide strips).  `scratch/shot.py IN OUT [ZOOM]`
  grabs the editor (`PYTHONPATH=.`, `QT_QPA_PLATFORM=offscreen`).

## Rules in Force (the user's)

* We place things as well as we can at first; once the user moves
  something, we respect it.  Nothing moves automatically; drawing may
  adjust, saved values never (#317, #323).
* One drawing code for the editor and the SVG (#S4); editing aids
  (circles, selection, lighting, warning rings, crossings, drag
  math) are Qt only, on top.
* Buttons in tabs, the user's way for every GUI (#319).
* Only the user edits letter values (#152); no grid in the working
  view (#183); diameters and whole tip angles wait (#89); no drill
  flutes or cutter teeth (#8).

## The Editor

* `OutlineView(QGraphicsView)`, Y up; grid 1, 2, 5 x 10^k at least
  `GRID_PIXELS` apart, snapped (Shift or [Snap] off frees); wheel
  zooms about the pointer.  Points follow the zoom; lines, handles,
  text and arrowheads keep a fixed pixel size (zoom is `hypot(m11,
  m12)`).  `setItemIndexMethod(NoIndex)` (the index crashed).
* No modes: a drag moves, a press on nothing pans, a click adds to
  the selection.  Circles are `theme.Colors.handle` yellow, filled
  when selected: corners 9 px, edges 7 px (dragged pulls out a
  corner); the origin a filled square.  Not dimensioned: orange ring;
  fillet too big: red ring; crossing edges red and thick.
* Tabs (`BUTTON_KEYS`, `BUTTON_TABS`; each a shared `QAction`, keys
  on any tab, status line under the tabs): [Most Common] (Undo, Redo,
  Delete, Dimension, Fit, Rotate Diagram), [Draw] (Delete, Dimension,
  Dim. Kind, New Letter, Revolve), [Marks] (Horizontal, Vertical,
  Right Angle), [View] (Grid, Snap, Fit, Overview, Hide, Rotate
  Diagram, Font +, Font -).  Keys: Del, N, K, -, |, Shift+L, R, T, H,
  O, G, S, Home, Ctrl+Z, Ctrl+Shift+Z, L, ], [.  Tabs [Drawing] and
  [SVG] above.
* [Dimension] from the selection (`dimension_selected()`): an edge ->
  length; a corner -> its angle; two edges or an axis and an edge ->
  the angle between; an axis and a corner -> across the axis; else
  the last two points.  [Delete]: selected corners and dimensions,
  else the armed or current letter, refused while in use.
* `History` of `Snapshot`s: every change one undo step.
* [Rotate Diagram (T)]: a quarter turn clockwise, letters upright
  (`turns` 0-3).  [Font +]/[Font -]: nothing selected -> the
  diagram's `text_height` x or / 1.25, else the selection's
  `font_step` (+-6).

## Dimensions, Marks and the Solver

* Dimensions: thin lines, extension lines, arrowheads, bold letter;
  a circle moves the letter (`along`) and line (`offset`).  `along`
  outside 0-1 puts the letter past an end, arrows pointing in, a
  `TAIL` past the far arrow.  Angles: positive, under 180 as drawn.
* Marks are letterless dimensions (`is_mark()`): level `—`, upright
  `|`, on an axis, right angle; made only by toggles; red when extra
  or broken (`mark_broken()`).  `—`/`|` boxes can be dragged
  (`moved`); right angles stay in their corners.
* `dimensions.solve()` guesses nothing from the drawing: passes from
  the origin until nothing new (chains, lengths, angles directing
  edges).  `drawn_marks()` gives old files their marks.  Drags obey
  marks (`drag_marked()`); right angles do not hold yet (#244).
* Corners are placed from the values and marks, the same for the
  editor and the SVG (`values.placed_corners()`); nothing moves while
  a used letter is bad, a formula fails or edges cross.

## Letters Table and Fillets

* Under a `QSplitter`: one table under a `QTabBar` ([Dimensions],
  [Fillets]); columns Letter, Name, Value, Fillet, Help; row 0 "No
  fillet" (`NO_FILLET`), letters from `LETTER_ROW` 1.  Letters 1-3
  characters, not `RESERVED`, not differing only in case; values a
  `Length` or `Angle` with a unit; problems in red.
* Fillets: `RADIUS` dimensions, true tangent arcs; note letter `UDF`
  ("All undimensioned fillets are radius UDF").  In [Fillets] a click
  arms a row and a click on a corner paints it.  Hover lights a
  letter's dimensions and corners, and a corner's row.

## Revolve, Hides and Holes

* [Revolve (R)]: half profile at X >= 0, mirror half faint and
  dashed; `outline_polygon.outline_revolved()` makes a
  `solid.SolidRevolved`, tips cut flat.
* Hides (`gui/hides.py`): strips laid in the [Overview (O)] over
  straight stretches; the working view cuts them out with break
  lines; a strip over a letter or glyph is red.
* Holes (`[[holes]]`, `Hole`: plain or counterbored, `at`, `letter`,
  optional `clearance`, `counterbore`, `depth`), sizes from the
  socket head cap screw table (`screws.py`, #4 to 1/2 in); the SVG
  draws them with center marks.  Not yet in the editor or solids.

## The SVG

* Drawn as on paper from the text height h (ASME Y14.2, simple):
  outline 0.2 h, thin lines 0.1 h, arrowheads h by h/3; h starts 1/30
  of the larger side; letters print 3 mm (`LETTER_MM`).  Hershey
  simplex text, `°`, `⌀`, `±` our own.  Black on white always; the
  [SVG] tab uses the theme.  Letters carry hover titles (Firefox's
  square kept until the letters table, #314).

## File Format (`outline_file.py`)

`kind = "outline"`, `version = 4`: `revolve`, `note_radius`,
`text_height`, `turns`, `[letters]` (`name`, `default`, `help`,
`fillet`), `[[points]]`, `[[dimensions]]` (`letter` "" for marks,
`kind`, `from`/`to`, `offset`, `along`, `rays`, `places`,
`font_step`, `moved`), `[[hides]]`, `[[holes]]`; optional fields
written only when set; older versions migrated on read.  Files live
in the shop as `tools/NAME.outline.toml`; the shop reader and tree
skip them until #S7.

## SolidCraft's 2D Solver (if live sketches return)

Fillets per corner and free arcs with given centers work; self
crossings, holes touching the outline, edges too short for their
fillets are taken silently, so we refuse them first.  At most about
500 values a `parameters.change`; always send a unit.  Today solids
are plain numbers (`T.rps~6.6`, #387).

## Open (numbers sticky)

* #290 holes: in the editor (click to place, dimensions to centers),
  as cutting layers in `outline_polygon.py` (a counterbore a child
  layer over its clearance hole), then Shars 202-1664's jaw file
  (#333; L 6, W 1, H 2, D 3-7/8, E 1/2, F 0.937 in, counterbored both
  faces #330, depth a value with no line #331).  Next, when
  `T.tfo~6.5` reaches its first flat tool.
* #373a a Mirror flag beside [Revolve]: mirror about Y, then extrude
  (a vise), by `RoundedPolygon.mirrored()`.
* #S7 [Show in SolidCraft] from the GUI tree (#115).
* #314 a Markdown letters table (names, values, help) for documents.
* #244 drags holding right angles; solver #83, #84.  #238 marks on
  the starting triangle (Claude: no).
* Expected: many corner cases in the marks and solver (the user).
