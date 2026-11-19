# LLM Agent Context Log

Squeezed 2026-11-19: only what is in force and where things stand;
designs tried and dropped are listed once at the end so they are not
brought back.  The full history is in `hg` and `git` (last before
the squeeze: `12f77bc`).

## The Editor Today

`python3 -m scraftcam.gui.outline_editor [FILE]` edits an outline
file, rewriting it after every change (never mid-drag); a bad file is
refused with every problem named, a missing one starts as the
counterclockwise triangle.  The editor makes a parametric
`RoundedPolygon`: corners as formulas in letters, fillet radii by
letter.  Light and dark (`gui/theme.py`); offscreen Qt tests, no
SolidCraft except `test_outline_solid`.

Files: `scraftcam/gui/outline_editor.py` (Qt), `letters.py`,
`dimensions.py`, `outline_file.py`, `values.py`, `hides.py`,
`outline_solid.py` (no Qt), `fillet_panel.py` (Qt); tests
`test_outline_editor`, `test_letters`, `test_dimensions`,
`test_outline_file`, `test_values`, `test_hides`,
`test_outline_solid`, plus `test_shops`, `test_gui_tree`,
`test_gui_theme` when touched.  Coverage target above 95%
(`uvx --python /usr/bin/python3 coverage run --include=... -m
unittest ...`).  Example: `examples/shop/tools/drill.outline.toml`.

### View and Interaction

* `OutlineView(QGraphicsView)`, Y up, unitless drawing steps; grid
  1, 2, 5 x 10^k at least `GRID_PIXELS` 12 apart, finer when zoomed,
  snap to it (Shift or [Snap] off drags freely); wheel zooms about
  the pointer; `Home` fits; X axis light red, Y axis light green.
  `setItemIndexMethod(NoIndex)` (the scene's index crashed on
  deleting a dragged dimension).
* No modes: a drag moves (corners, circles), a press nothing takes
  pans (arrow pointer, closed hand only while panning); a click adds
  to the selection (clicked again: becomes the latest), empty space
  clears it.  An edge's mid circle dragged pulls out a new corner,
  clicked selects the edge (only for [Angle]); a click near an axis
  selects it.
* Buttons, each showing its key (`QShortcut`s on the window; a
  button's own `setShortcut()` never fired): [Delete (Del)]
  (corners, dimensions, their unused letters; at least 3 corners),
  [Dimension (N)] (last two points in any order, or waits; an axis
  plus a corner gives a dimension across the axis from the origin),
  [Dim. Kind ↻ (K)] (horizontal -> length -> vertical, each kind
  keeping its own place), [Angle (A)], [Revolve (R)], [Hide (H)],
  [Overview (O)], [Grid (G)], [Snap (S)], [New Letter (L)], [Undo
  (Ctrl+Z)], [Redo (Ctrl+Shift+Z)] (greyed until possible).
* `History` of `Snapshot`s (points, dimensions, letters, revolve,
  note radius, hides): every change one undo step.
* Marks never told by color alone: squares and circles 9 px, hollow
  with an ink ring, filled when selected; origin a filled square; a
  corner not yet dimensioned a solid 3 px warning (yellow) ring; a
  fillet too big a red 3 px ring; a selected dimension drawn 2.5 px
  and colored; extra dimensions red.  Tooltips on squares give the
  formulas, `(W, Y-Floating)`.
* Dimensions: thin lines, extension lines, arrowheads, bold upright
  letter on the side away from the outline's middle; a circle on
  each moves its letter (`along`, past the arrowheads extends the
  line) and its line (`offset`); a click on the line only selects.

### Letters Table

* Below the drawing past a `QSplitter` bar, in a [Dimensions] tab:
  Letter (1-3 characters, a letter first; not `RESERVED`: units,
  `pi`, `e`, SolidCraft's short functions; not differing only in
  case), Name, Value (a `Length`, mixed units, or an `Angle` in
  `deg`/`rad`; a bare number refused; the file key stays
  `default`), Help.
* One click edits a cell (`CurrentChanged | SelectedClicked | ...`);
  `fill_table()` leaves no cell current and gives the drawing the
  keyboard (letters typed must not fire button keys).  Each
  keystroke is kept and checked (`LiveDelegate`).
* Problems in red right under the table, one a line, and the bad
  cell red with the reason (`letters.use_problem()`: a length
  letter holds a length > 0, an angle letter an angle in 0.1..179.9
  deg, not both kinds).

### Dimensions and Formulas

* `dimensions.solve()` passes over the dimensions until nothing new:
  seeds the origin, corners on an axis (`ON_AXIS`), and edges drawn
  exactly level or upright (letterless, tried first, so a dimension
  repeating one is extra).  Horizontal/vertical chains give X/Y
  with signs from the drawing; a length from a known point gives
  `sqrt(...)` on the side drawn; an angle directs an edge
  (`ways`), and a directed edge gives its far corner by `tan`.
  `solve(..., drawn=False)` leaves out what only the drawing says;
  only dimensions pin a dragged corner (`OutlineView.pinned`).
* Formulas tidy: `grouped()`, `total()`, `difference()`,
  `product()`: `R * tan(90 deg - A)`.
* Angles: between two edges or an edge and an axis; a plain positive
  value under 180 degrees, always the side under 180 as drawn
  (`Drawing.follow_angles()` resets the rays toward the edges'
  middles and swaps edges on every change); no direction arrowhead;
  default the drawn angle to a whole degree; parallel refused.
  `K` skips angles.  Kept on their edges when corners are added or
  deleted.
* `values.py`: `letter_values()` (mm, radians), `evaluate()` (an
  `ast` reader), `real_corners()`, `real_coordinates()`,
  `crosses()`, `fillet_problems()` (an edge's two fillet reaches
  against its length, `FIT_SLACK`; using an edge up is allowed).
* The drawing follows the values (#148): `Drawing.scale` (steps per
  mm, chosen once) puts each fixed coordinate at `real * scale`;
  nothing moves while a used letter is bad, a formula fails or edges
  cross.

### Revolve, Fillets, Hides

* [Revolve (R)]: half profile at X >= 0, tip down, Y axis dash-dot,
  the mirror half faint and dashed (outline only); corners kept off
  the left side (snapped to 0).  Users make their own half angle
  letters (#87); diameters and whole tip angles deferred (#89).
* Fillets: `dimensions.RADIUS` on a corner; true tangent arcs drawn
  at their letter's value to scale (capped by the edges), thin dashed
  lines to the sharp corner.  The note letter `UDF` ("Undimensioned
  fillet radius"), with "All undimensioned fillets are radius UDF"
  lower left; `UDF` fillets show no letter, own-letter fillets show
  it past the arc's middle.  Too big: red ring and red table cell.
  Today a [Fillets] tab (`fillet_panel.FilletPanel`) lists the
  selected corners ("All:" row, a line, rows `1:`..`N:` in selection
  order, one-down buttons [No fillet], [UDF], each fillet letter),
  with two-way hover lighting (`OutlineView.light()`, `lit`,
  `lighted`); this is to be replaced (below).
* Hides (`gui/hides.py`, `Hide(axis, below, above, low, high, under,
  over)`, `[[hides]]` in the file): [Hide (H)] lays a strip by a
  drag in the [Overview (O)] (straight stretches only: no corner, no
  fillet arc), five circles resize its four sides and move it; it
  must reach past the part and its dimensions (`OutlineView.reach()`).
  The working view cuts strips out (`GAP_PIXELS` 20), long break
  lines meshing edge to edge (`inside_spans()`), dimension lines
  ending in S's centered on the cut; look and pan only there.
* `gui/outline_solid.py`: `python3 -m scraftcam.gui.outline_solid
  FILE (PORT | headless)` builds a revolved outline in SolidCraft
  (XZ plane, about Z, letters as parameters), sharp tips cut flat
  at build only (`TIP_FLAT` 0.05 of the radius); live changes 8-33
  ms.  Flat outlines and fillets in SolidCraft wait for #S8 (#140).

### File Format (`outline_file.py`)

`kind = "outline"`, `revolve`, `note_radius`, `[letters]`,
`[[points]]` (`at = [x, y]`, drawing positions), `[[dimensions]]`
(`letter`, `kind`, `from`/`to` an index or `"origin"`, `"x_axis"`,
`"y_axis"`, `offset`, `along`, `rays` for angles, `places` when
set), `[[hides]]`; fixed field order so a moved corner changes one
line.  `Drawing` subclasses `Outline`.  Outline files live in the
shop's own directories (`tools/NAME.outline.toml`) under version
control; the shop reader and tree skip them (`shops.OUTLINE_SUFFIX`)
until #S7.

## Next: the Fillet Design Agreed (2026-11-19, not coded)

Numbers sticky; the next new one is #230.
* #213 One letters table.  A tab bar over it: [Dimensions] shows
  every row; [Fillets] shows only rows checked "Fillet" (a new check
  box column, `fillet = true` on the letter in the file; only length
  letters; `UDF` checked when made) plus fillet controls.
* #216 an entry is a number and a type (length, angle, later a plain
  number); one letter may be a fillet radius and a dimension.
* #214 letter first: clicking a [Fillets] row arms it (lit; the bar
  says "Click corners to fillet them by UDF"); each corner clicked
  takes the armed letter (#228: a different letter is replaced;
  #220 the same letter again does nothing).  Disarm: click the armed
  row again, empty space, or switch to [Dimensions]; no `Esc`
  (#229).  #218 arming also applies to corners already selected (to
  try).  #227 drags still work while armed; only plain clicks paint.
  #223 each painted corner one undo step.  No entries yet: the tab
  shows [New Fillet Dimension] (next free letter, checked, "Fillet
  radius").
* #219/#222 a fixed first row "No fillet", value 0, never editable or
  deletable, not in [Dimensions] nor the file, Letter cell blank;
  attaching it removes the fillet.  Maybe an "uneditable" marker.
* #215 an entry in use cannot be deleted: [Delete] refuses, naming
  and lighting its uses; unchecking "Fillet" in use likewise (#225).
* #224 hovering any row lights everything using it; hovering a
  corner frames its letter's row.  To try.
* #226 own-letter fillets show their letter; `UDF` ones do not.
* #217 for #S8: SolidCraft drops zero-length lines and arcs (~1e-6
  mm), so a 0 fillet is sharp and a used-up edge vanishes; a value
  through 0 changes the segment count, so `SolidCraftLink` rebuilds.
* Chunk plan (#221): (1) one table, tab bar, "Fillet" column, file;
  per-corner rows out; (2) "No fillet" row, arming and painting;
  (3) hover lighting and refused deletes.  Then #182 (a letter in a
  hidden stretch moves to the nearest visible part of its line).

## Steps Left and Open Items

* Steps: #S5 SVG (the same meaning as the screen, #61; working view
  or not, #189), #S7 opened from the GUI tree (with [Show in
  SolidCraft], #115), #S8 a separate class extruding a planar outline
  (`RoundedPolygon` losing `z_start`, `z_end`, `children`;
  `keepout.py`, `demo.py` follow; SolidCraft fillets, #140), #S9
  leftovers.  Steps and chunks may be reordered freely (#150).
* Open: #152 dragging a fixed corner changes its letter's value;
  #182 above; #183 no grid or axes in the working view; #8 flutes and
  assemblies (`T.cett2e~5.1.9.2.1`); #83 two lengths at a corner;
  #84 a length along a directed edge; an angle one too many is not
  red; #89 diameters and whole tip angles for catalog numbers.
* Work rules: one ~3 minute chunk per turn; summaries in sentences or
  `#N:` issues, never `1. 2. 3.`; a top 5 each round with tokens left
  as a percentage.  Transcript for the user's friend:
  `~/.scraftcam/transcripts/2026-11-19_T.prg_5.1.9.2.md` (made by
  `~/.scraftcam/transcripts/transcript.py`, not versioned).

## Tried and Dropped (do not bring back)

* Modes ([Move]/[Add]/[Delete] mode bar, [Dimension] mode): need
  training; drag and click instead.  Shift+click to select.
  `ScrollHandDrag` (hand pointer, cannot aim).  Dragging a dimension
  line itself (its circle does it).
* Angles: rays fixed at creation (gave arcs over 180 when corners
  swung), CW/CCW flags, signed values, direction arrowheads, angles
  over 180, four arcs by [Dim. Kind].
* Fillets: a [Fillet] button picking the table's row (press again
  for sharp); a fillet pop-up window (covers things); per-corner
  rows in [Fillets] (current code, to be replaced by #213); a fixed
  drawn size of a fifth of the shorter edge; fillet formula labels
  on rows.
* Break-line check box (#9): [Hide] replaces it.  Endless hide
  strips (cannot be reached); dragging in the working view.
* Dashed yellow warning rings (gaps); filled colored squares;
  corner tooltips as anything but formulas.
* Sharp tips revolved as drawn (look broken in SolidCraft).
* Heights and children in the editor (corners and radii only).
