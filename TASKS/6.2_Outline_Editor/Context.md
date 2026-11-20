# LLM Agent Context Log

Squeezed 2026-11-19 (second time): only what is in force and where
things stand; designs dropped and the full history are in `hg` and
`git` (last before this squeeze: `f51b4d0` and the commit after it).

## The Editor Today

`python3 -m scraftcam.gui.outline_editor [FILE]` edits an outline
file, rewriting it after every change (never mid-drag); a bad file is
refused with every problem named, a missing one starts as the
counterclockwise triangle (no marks, #238 open).  It makes a
parametric `RoundedPolygon`: corners as formulas in letters, fillet
radii by letter.  Light and dark (`gui/theme.py`); offscreen Qt
tests, no SolidCraft except `test_outline_solid`.

Files: `scraftcam/gui/outline_editor.py` (Qt), `letters.py`,
`dimensions.py`, `outline_file.py`, `values.py`, `hides.py`,
`outline_solid.py` (no Qt); tests `test_outline_editor`,
`test_letters`, `test_dimensions`, `test_outline_file`,
`test_values`, `test_hides`, `test_outline_solid`, plus
`test_shops`, `test_gui_tree`, `test_gui_theme` when touched.
Coverage target above 95% (`uvx --python /usr/bin/python3 coverage
run --include=... -m unittest ...`).  Example:
`examples/shop/tools/drill.outline.toml` (version 1, migrated on
read).

### View and Selection

* `OutlineView(QGraphicsView)`, Y up, unitless drawing steps; grid
  1, 2, 5 x 10^k at least `GRID_PIXELS` 12 apart, snap to it (Shift
  or [Snap] off drags freely); wheel zooms about the pointer; `Home`
  fits; X axis light red, Y axis light green.
  `setItemIndexMethod(NoIndex)` (the index crashed on deleting a
  dragged dimension).
* No modes: a drag moves, a press nothing takes pans, a click adds to
  the selection (empty space clears it).  Every circle is
  `theme.Colors.handle` yellow, hollow, filled when selected (#237):
  corners `CornerCircle` 9 px, edges `EdgeHandle` 7 px (dragged pulls
  out a corner, clicked selects the edge), dimension and strip
  circles; the origin a filled ink square; a click near an axis
  selects it.  Not dimensioned: orange `warning` 3 px ring; fillet
  too big: red ring.  Tooltips give the formulas.
* Buttons with keys (`QShortcut`s on the window): [Delete (Del)],
  [Dimension (N)], [Dim. Kind ↻ (K)], [Horizontal (-)], [Vertical
  (|)], [Right Angle (Shift+L)], [Revolve (R)], [Hide (H)],
  [Overview (O)], [Grid (G)], [Snap (S)], [Fit (Home)], [Undo
  (Ctrl+Z)], [Redo (Ctrl+Shift+Z)], [New Letter (L)].
* [Dimension] works from the selection (`dimension_selected()`,
  #234): one edge -> its length; one corner -> the angle there (under
  180 as drawn); two edges, or an axis and an edge -> the angle
  between; an axis and a corner -> across the axis; else the last
  two points (`dimension_points()`, waits for them).
* [Delete] (`OutlineEditor.delete()`): selected corners and
  dimensions; with none, the letter armed in [Fillets] or the
  table's current row, refused while in use (named and lit, #215,
  #245).
* `History` of `Snapshot`s: every change one undo step.
* Crossing edges drawn red and thick, with a bar message
  (`values.crossings()`, #242).

### Dimensions, Marks and the Solver

* Dimensions: thin lines, extension lines, arrowheads, bold letter
  away from the outline's middle; a circle moves the letter (`along`)
  and the line (`offset`).  Angles: between two edges or an edge and
  an axis, a positive value under 180 as drawn
  (`Drawing.follow_angles()`), default the drawn angle.
* Marks (#233, #236) are letterless dimensions (`is_mark()`): a
  VERTICAL one across an edge = level `—`, HORIZONTAL = upright `|`
  (`mark_edge()`), from `ORIGIN` = a corner on the X/Y axis (#239),
  a letterless ANGLE between a corner's edges = right angle (the
  solver reads "90 deg").  Made and removed only by the toggle
  buttons (`toggle_mark()`, `toggle_right()`), drawn so at once.
  Glyphs: a `MARK_PIXELS` box out from the edge's middle or corner
  (`mark_spot()`, `paint_mark()`), the right angle's square in its
  sector (`right_box()`); clicked selects; red when extra or broken
  by the drawing (`mark_broken()`, #241).  Pulling a corner out of a
  marked edge drops the mark.
* `dimensions.solve(points, dimensions)` guesses nothing from the
  drawing: from the origin, passes until nothing new; horizontal and
  vertical chains, lengths (`sqrt`, side as drawn), angles direct
  edges (`ways`; marked edges directed from the start,
  `_drawn_way()`), a directed edge gives its far corner by `tan`.
  Extras: an axis dimension between known points, an angle between
  directed edges (#230).  `drawn_marks()` gives old files the marks
  their drawing showed.  Formulas tidy (`grouped()`, `total()`, ...).
* Drags obey marks (#243, `drag_marked()`, `mark_chain()`): marked
  corners move together; a chain reaching the origin or a corner the
  dimensions pin holds.  Right angles do not hold yet (#244, last).
* The drawing follows the values (#148): `Drawing.scale` puts each
  known coordinate at `real * scale`; nothing moves while a used
  letter is bad, a formula fails or edges cross.

### Letters Table and Fillets

* Below the drawing past a `QSplitter`: one table under a `QTabBar`
  ([Dimensions] every letter; [Fillets] the fixed "No fillet" row and
  the letters checked "Fillet", plus [New Fillet Dimension]).
  Columns Letter, Name, Value, Fillet (check box), Help.  Table row
  0 is "No fillet" (`NO_FILLET`, never edited or saved); letters
  start at `LETTER_ROW` 1.
* Letters: 1-3 characters, a letter first, not `RESERVED`, not
  differing only in case; Value a `Length` or `Angle` with a unit;
  problems in red under the table and in the cell
  (`letters.use_problem()`, `fillet_kind_problem()`).  One click
  edits in [Dimensions]; each keystroke kept (`LiveDelegate`).
* Fillets: `RADIUS` dimensions on corners, true tangent arcs at the
  letter's value, dashed lines to the sharp corner; the note letter
  `UDF` ("All undimensioned fillets are radius UDF", no letter
  shown); own letters shown past the arc's middle.  In [Fillets] a
  click arms a row (`arm()`, `view.armed`; "" = sharp; selected
  corners take it at once, #218), a plain click on a corner paints
  it (one undo step), a drag still moves; disarm by the row again,
  empty space or [Dimensions].  "Fillet" cannot be unchecked while
  it rounds a corner (#225).
* Hover (#224): a row lights its letter's dimensions and corners
  (`lit_letter`, `corner_lit()`); a corner makes its letter's row
  bold (`frame_row()`).

### Revolve and Hides

* [Revolve (R)]: half profile at X >= 0, the mirror half faint and
  dashed; corners kept at X >= 0.  `gui/outline_solid.py FILE (PORT |
  headless)` builds a revolved outline in SolidCraft, sharp tips cut
  flat (`TIP_FLAT`).
* Hides (`gui/hides.py`): [Hide (H)] lays a strip in the [Overview
  (O)] over straight stretches only; five circles resize and move
  it; the working view cuts strips out with meshing break lines and
  S-ended dimension lines.  A strip covering a letter or a mark's
  glyph is red in the Overview, with a bar message (`covering()`,
  `letter_spot()`, #182); letters are never moved for it.

### File Format (`outline_file.py`)

`kind = "outline"`, `version = 2`, `revolve`, `note_radius`,
`[letters]` (`name`, `default`, `help`, `fillet = true` when set),
`[[points]]`, `[[dimensions]]` (`letter` "" for marks, `kind`,
`from`/`to`, `offset`, `along`, `rays`, `places`), `[[hides]]`;
fixed field order.  A file without `version` gets `drawn_marks()`
ahead of its dimensions.  Outline files live in the shop's
directories (`tools/NAME.outline.toml`); the shop reader and tree
skip them until #S7.

## Steps Left and Open Items

Numbers sticky; the next new one is #247.
* #S5 SVG: now its own sub-task, `T.sfoe~6.2.2` (an SVG that
  resembles the GUI; the user leans to an [SVG] tab, #189).
* #S7 opened from the GUI tree with [Show in SolidCraft] (#115,
  after #S5).  #S8 a separate class extruding a planar outline
  (`RoundedPolygon` losing `z_start`, `z_end`, `children`;
  `keepout.py`, `demo.py` follow; SolidCraft fillets, #140; #217
  SolidCraft drops zero-length segments, so a value through 0
  rebuilds).  #S9 leftovers: solver #83 (two slanted lengths at a
  corner), #84 (a length along a directed edge); #244 drags holding
  right angles.
* Open: #238 marks on the starting triangle (Claude: no).  Expected:
  many corner cases to debug in the marks and solver (the user,
  2026-11-19).  Four right angles on a quadrilateral: the fourth is
  extra (red) by design.
* Settled: no grid in the working view (#183); diameters and whole
  tip angles wait for the catalog work (#89); drill flutes and cutter
  teeth not planned (#8); only the user edits letter values (#152).
* Work rules: ~3 minute chunks (longer when the user says), a top 5
  each round with tokens left; `#N:` issues, never `1. 2. 3.`.
  Transcripts per the session rules (`R.ccsr~6`): one per session in
  `~/.claude_transcriptions/`, `YYYY-MM-DD_HH-MM_scraftcam.md` (the
  start time, `-` for `:`), made by `transcript.py` there, not
  versioned; regenerate before each commit and `/clear`.  Older ones
  stay in `~/.scraftcam/transcripts/`.
