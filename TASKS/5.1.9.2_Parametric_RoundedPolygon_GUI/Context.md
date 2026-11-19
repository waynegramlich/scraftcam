# LLM Agent Context Log

## 2026-11-17: Created

Created and opened at the user's request at the end of a session of
`T.sdfm~2.5.2.1` (#43: where dimension letters come from has no answer
yet; "at some point we need to have a GUI to create parametric
RoundedPolygons").  `Details.md` is Claude's draft.  Nothing coded.

## 2026-11-17: Design rounds #1-#29 (nothing coded yet)

The user wants every open issue settled before the first prototype
(#14).  A transcript of the session is kept for a friend of the
user's in `~/.scraftcam/transcripts/` (`transcript.py` turns the
session log into Markdown; regenerated each round).  Numbers are
sticky; the top 5 is labelled `#N:` only.

Settled:
* #1 Qt `QGraphicsView`/`QGraphicsScene`, Y up, axes and an origin
  pull square.  #3 the wheel zooms about the pointer; `F` fits.
  #6 dragging the origin or empty space pans the view (the origin
  stays 0, 0).
* #4 counterclockwise is positive, as in `geometry.py`.
* #7, #11 a mode bar, no menus (drop-downs if the user dislikes it):
  [Move] [Add] (click a square: a point after it, splitting the edge
  leaving it at its middle) [Delete] [Grid] [Snap].
* #8 live checks (crossings red).  #9 `scraftcam/gui/outline_editor.py`,
  `python3 -m scraftcam.gui.outline_editor`.
* #12, #15, #16 no numbers in the drawing, letters only: a unitless
  grid, finer as one zooms (#13 snap to it; Shift drags freely).
* #17 TOML: `kind = "outline"`, `[letters]`, `[[points]]` (`at`,
  drawing positions only), `[[dimensions]]` (`letter`, `kind`,
  `from`, `to`).
* #23 the editor makes a parametric `RoundedPolygon` (corners as
  formulas in letters, a radius letter per rounded corner); numbers
  for the letters give a real one, for SolidCraft and the SVG.
* #24 horizontal/vertical dimensions between points (or the origin);
  every X (Y) reachable from the origin by a chain of horizontal
  (vertical) dimensions becomes a formula, signs from the drawing;
  no chain is red, two chains over-dimensioned; one letter on two
  dimensions means equal.  No solver.
* #25 horizontal, vertical, radius first; slanted lengths and angles
  later.  #19 rounding comes last; a radius arrow from the arc's
  center (19a).
* #26 thick outline; thin dimension, extension and leader lines,
  arrowheads, angle arcs, center marks, dash-dot center lines; grid,
  axes, pull squares and winding arrows on screen only.
* #18 undo/redo from the start.  #21 light and dark (`gui/theme.py`).
* #27 below the drawing, past a horizontal bar dragged up and down
  (`QSplitter`), a table: letter (1-2), long name, default value with
  its unit (`Length` text, mixed units), help.  Refuse `in`, `mm`,
  `pi`, ... and letters differing only in case.
* #29 heights (`z_start`, `z_end`) and children left out (to be
  confirmed: the user's "No, z_start/z_end").
* #22 offscreen Qt tests, no SolidCraft.

Open: #28 a to-scale overlay from the defaults (the user unsure;
long skinny parts may need break lines), #20 keyboard keys, #30 how
a dimension is placed, #31 where files go.

## 2026-11-17: Round #28-#32

* #20 keys, each also a labelled button showing it ("Move (M)").
* #22 tests: when done, coverage above 95%.
* #28 the user's (d): the table's default values show what the shape
  really looks like; maybe a break line check box for long
  dimensions (speculative).  Follow up: freehand `at` positions vs
  drawn from the defaults.
* #29 the user recalled `RoundedPolygon` as 2D only; it is not:
  `z_start`, `z_end`, `children`, and `model()` extrudes
  (`geometry.py:838`); `keepout.py` uses `hits()`.
* #30 non-rectilinear designs (drill bits, center drills) need angles
  and slanted lengths early.  #31 files go in the shop's own
  directories (`tools/`, `tooling/`, stock later).

## 2026-11-17: Round #28-#32 answered

* #28 (d), as Claude laid it out: freehand until dimensioned, then
  drawn from the defaults; dragging along a dimensioned direction
  changes that letter's default (snapped).  Break box later.  The
  user will say if it does not work.
* #29 (a): the editor makes corners and radii only.  The user: a
  polygon is planar, so giving it depth was probably a mistake; a
  separate class may do the extruding some day (#33).
* #30 angles and slanted lengths in the first prototype; each point
  from two facts (X chain, Y chain, edge angle, length along an
  edge), formulas with `tan`, `sin`, `sqrt`.  The user recalls the
  revolve breaking at a sharp tip, so tips were flattened slightly:
  `COUNTERSINK_TIP_FLAT` 0.05 (`tooling/cutter_models.py:137`).
* #31 (a): `tools/NAME.outline.toml`, `tooling/...`, and their SVGs,
  all under version control.
* #32 revolved outlines are a must (every mill bit is round): a
  [Revolve] check box (a).

## 2026-11-17: Round #34-#38 answered; design done

* #34 the user recalls the sharp-tip revolve looking wrong in 3D;
  test it again at chunk 6.  #35 revolve rules agreed (Y axis
  dash-dot, X >= 0, tip down, snap to X = 0, diameters, mirrored
  SVG).  #36 reuse `tool_models.py`'s SVG dimensions (`Dimension`,
  `Mark`, `_dimension()`); in the end every tool comes from the
  editor.  #37a old models kept until each is checked; one editor.
* #38 chunk plan agreed: 1 window, axes, origin, zoom, pan, grid,
  snap, triangle with winding arrows; 2 modes, keys, Move/Add/Delete,
  undo; 3 letters table; 4 H/V dimensions, formulas, red marks;
  5 angles, slanted lengths; 6 [Revolve]; 7 TOML; 8 SVG; 9 radii;
  10 opened from the GUI tree.
* New `T.cett2e~5.1.9.2.1` (Pending): convert the existing tools,
  grid plate left off.
* Open, not blocking: #33 a separate extruding class (some day),
  #39 what an outline cannot say (flutes, assemblies).

## 2026-11-17: Where things stand (before `git commit`)

* #33 goes at the end of this task: chunk 11, a separate class that
  extrudes a planar outline (`RoundedPolygon` losing `z_start`,
  `z_end`, `children`; `keepout.py` and `demo.py` follow).
* #34 the sharp tip: retested at chunk 6.  #39 (flutes, assemblies)
  left for `T.cett2e~5.1.9.2.1`; not answered.
* Nothing coded.  Next: chunk 1 of #38 (window, axes, origin, zoom,
  pan, grid and snap, the counterclockwise triangle with winding
  arrows), `scraftcam/gui/outline_editor.py`, its first tests in
  `tests/test_outline_editor.py`.  Numbers are sticky up to #39.
* The session transcript (for the user's friend) is regenerated
  each round into `~/.scraftcam/transcripts/` by its
  `transcript.py`; not under version control.

## 2026-11-17: Chunk 1 done

`scraftcam/gui/outline_editor.py` (`python3 -m
scraftcam.gui.outline_editor`): `OutlineView(QGraphicsView)` Y up,
a scene of unitless drawing steps; `grid_step()` (1, 2, 5 x 10^k, at
least `GRID_PIXELS` 12 apart, every 5th darker) and `snap()`;
`PullSquare`s (fixed size on screen) drag a corner, snapped unless
Shift; `OutlineItem` thick cosmetic edges with an arrowhead at the
end of each; the origin square pans with empty space
(`ScrollHandDrag`); the wheel zooms about the pointer
(`ZOOM_PER_NOTCH` 1.25, `ZOOM_LIMITS`); `F` fits, `G` grid; colors
from `theme.colors()`, `theme.follow()` in `main()`.  `Drawing`
holds the points (`TRIANGLE`, counterclockwise).
`tests/test_outline_editor.py`: 7 tests, 0.05 s, coverage 97%
(`uvx --python /usr/bin/python3 coverage run ...`; only `main()`
missed).  Checkers clean.  Found: something sorts imports (ruff
`I001`), so PySide6 imports in tests go inside the test methods, and
modules call `require("PySide6")` first, as `theme.py` does.
Waiting for the user's run.  Next: chunk 2 (mode bar, keys,
Move/Add/Delete, undo).

## 2026-11-17: Step 2, chunk 1 (the user says "Step" for #38's items)

Mode bar in `OutlineEditor`: [Move (M)] [Add (A)] [Delete (D)] (a
`QButtonGroup`, one down) [Grid (G)] [Snap (S)] [Fit (F)], keys by
`setShortcut`, buttons never take focus; a red status label for
refusals.  `OutlineView.mode`, `snap_on`, `make_squares()`,
`add_after()` (the exact middle of the edge leaving the corner, not
snapped), `delete()` (refused below `LEAST_CORNERS` 3).  A
`PullSquare` is placed before it sends moves, so making squares never
snaps a corner (a bug found by the tests).  The view's own key
handling is gone (the buttons have the keys).  10 tests pass.  Next:
chunk 2, undo and redo.

## 2026-11-17: Step 2, chunk 2: undo and redo; Step 2 done

The user: #40 OK for now (more features before suggestions); #41
arrowheads as they are; #42 1, 2, 5, 10 (people do not think in
binary); #44 the unsnapped middle corner assumed OK.
`History` (`done`, `undone`: the corners before each change;
`remember()`, `undo()`, `redo()`); `OutlineView.undo()`, `redo()`,
`show_points()`; a drag is remembered on release only if it moved
the corner (`PullSquare.before`); add and delete remember first.
[Undo (Ctrl+Z)] and [Redo (Ctrl+Shift+Z)] enabled only when there
is something to do (`OutlineEditor.show_message()`, on the scene's
`changed`).  12 tests, coverage 98% (only `main()`), checkers clean.
Next: Step 3, the letters table below a horizontal bar.

## 2026-11-17: Step 3 done: the letters table

`git`: `1cb3bf5` (steps 1 and 2), pushed.  New
`scraftcam/gui/letters.py` (no Qt): `Letter(letter, name, default,
help)`; `letter_problem()` (one or two letters or digits, a letter
first; not in `RESERVED`, units and constants, `e` a guess; not used
twice; not differing only in case); `value_problem()` (a `Length`,
or an `Angle` ending `deg`/`rad`; a bare number refused);
`next_letter()` (first free `A`-`Z`, then `A1`...; default `1` in
the last length's unit).  `outline_editor.py`: `Drawing.letters`; a
vertical `QSplitter` with the view over a `QTableWidget` (Letter,
Name, Default, Help); [New Letter (L)]; `fill_table()`,
`letter_edited()`, `check_letters()` (bad cells in
`theme.colors().bad`, the problem as tooltip, the first one in the
mode bar).  `tests/test_letters.py` (3), `test_outline_editor` (14);
coverage 98% (only `main()`); checkers clean.  Not yet: table edits
in undo/redo; deleting a letter.  Next: Step 4 (dimensions).

## 2026-11-17: #47-#50 answered

* #47 letters may be 1-3 characters (`OAL`); `RESERVED` adds
  SolidCraft's short function names (`sin`, `cos`, `tan`, `abs`,
  `min`, `max`, `log`, `exp`, `ln`).  Each keystroke is kept and
  checked (`LiveDelegate`: its entry's `textEdited` calls
  `OutlineEditor.keep()`; `setEditorData()` never overwrites a
  modified entry, since marking a cell bad resets the entry
  otherwise, found by the test).
* #49 the user could not find Undo/Redo: they are at x 516-731 of an
  843 px bar, greyed until there is a change; to ask.
* #50 `pi` and `e` are the only constants.
* #45 the user: commit, then Step 4 (dimension lines).

## 2026-11-17: Step 4, chunks 1-2

`git`: `e8b985e` (Step 3), pushed.  `scraftcam/gui/dimensions.py`
(no Qt): `Dimension(letter, kind, start, end, offset)` (`ORIGIN` -1
or a corner index; `offset` the line's Y or X), `Formula` (`W - T`),
`Solution` (`x`, `y`, `extra`, `missing()`), `solve()` (breadth
first from the origin per kind; signs from the drawing; a dimension
reaching a known point is extra).  `tests/test_dimensions.py` (3).
`outline_editor.py`: `Snapshot` (points, dimension copies) for
`History`; `Drawing.dimensions`, `snapshot()`, `restore()`,
`insert()`, `remove()` (dimensions keep to their corners; removing
a corner drops its dimensions); `DimensionItem` (thin extension
lines past the line, arrowheads at both ends, bold upright letter;
red when extra); `OutlineView.point()`, `add_dimension()`,
`follow()` (solve, redraw; squares red while not dimensioned, once
any dimension exists).  The user stopped a 6 minute run: one chunk
per turn, then stop.  Next: the [Dimension (N)] mode (#52).

## 2026-11-17: Step 4, chunk 3-4: the [Dimension (N)] mode

`MEASURE` mode: click a point (a corner square or the origin), then a
second (`OutlineView.pick()`); horizontal if further apart in X than
Y, else vertical; the line two grid steps past the points; the next
free letter added to the table (`letters_changed`, set to
`fill_table`).  Bugs found by the test: two quick clicks are a double
click, so `mouseDoubleClickEvent()` picks the origin too;
`DimensionItem`s take no mouse buttons; Qt asks a removed item's
`boundingRect()` during an undo (guarded).  21 tests pass, checkers
clean.  The user uses Ctrl+/ and Ctrl+? for undo and redo (#54, not
yet acted on).  Next: the user tries it.

## 2026-11-17: Step 4, chunk 5: dragging dimension lines

The user's run: horizontal/vertical dimensions "work great".  #54
stay with Qt's keys (Ctrl+Z, Ctrl+Shift+Z).  `DimensionItem` in
[Move]: `shape()` a band `SQUARE_PIXELS` wide along the line (only
it grabs), drag moves `offset` (Y for horizontal, X for vertical),
snapped unless Shift or [Snap] off, remembered on release as one
change; other modes let the click pass.  22 tests pass.

## 2026-11-17: Step 4, chunk 6: an arrow pointer

The user (#55): the hand pointer must be an arrow to aim; #56b
delete and place again is fine, but no way to delete a dimension yet;
the user has not managed to drag a dimension (maybe still in
[Dimension]; not yet known).  `ScrollHandDrag` dropped: the view pans
by hand (`pan_from`; a press nothing takes starts it, closed hand
only while panning).  23 tests pass.  Next chunks: delete a dimension
in [Delete] (with its letter) and a hint after placing one; then the
formula tooltips (#57).

## 2026-11-17: No modes (#58, #59)

The user: modes need training; drag and drop is natural; the [Del]
button deletes.  Done in 3 chunks: no mode buttons; dragging moves
corners and dimension lines; a click selects (Shift adds or drops;
empty space clears; the origin too), highlighted in the palette's
highlight color (`chosen_points` in click order, `chosen_dimensions`,
cleared by `make_squares()`).  [Delete (Del)] (`delete_selected()`:
corners and dimensions as one change, their letters too unless still
used; at least 3 corners) and [Dimension (N)]
(`dimension_selected()`: the two selected points; refused for same
place).  `Snapshot` holds letters, so undo restores table rows.
`EdgeHandle` (#59): a 7 px hollow circle mid-edge in the quiet color,
hidden when the edge is under 27 px on screen; dragging pulls out a
snapped corner (made at the first move), one change; a click does
nothing.  27 tests pass, checkers clean.  Next: #57 formula
tooltips, then Step 4 is done.

## 2026-11-17: #60 the keys never fired

The user could not make dimensions; the edge circles work great
(zoom when crowded), but should be more visible; the edge showing
through the circle is natural.  Found by an offscreen probe: a
`QPushButton.setShortcut()` key never fired (button clicks did), so
`N`, `G`, `Del`, ... did nothing from the keyboard; a `QShortcut`
on the window does (`OutlineEditor.keys`, each `activated` ->
`button.click`).  A test now presses `G` for real.  Handles: 9 px,
hollow, 1.5 px ink ring.  27 tests pass, checkers clean.

## 2026-11-17: #60 dimensioning in any order, no Shift

The user: circles "look great and are really natural"; Shift+click
does not feel natural; C1-C2-D, C1-D-C2 and D-C1-C2 must all make a
dimension; no commit until dimensioning feels easier.  Now every
click adds to the selection (a point clicked again becomes the
latest), empty space clears it (and the waiting); [Dimension] uses
the last two points clicked, or waits (`wanted`) with "Click two
points to dimension." / "Click a second point."  27 tests pass.

## 2026-11-17: #63 the dimension circle (#64: the line only selects)

`Dimension.along` (the letter's place along the line, a share from
the `start` end; below 0 or above 1 is past the arrowheads, the line
drawn on out to it, `DimensionItem.draw_reach()`).
`DimensionHandle`: the edge handles' hollow circle at
`DimensionItem.at()`; dragged along the line it moves `along`, across
it `offset`, snapped, one change.  A click on the line only selects
(no line drag).  `OutlineView.circles`.  27 tests pass, checkers
clean.  Awaiting the user's run; commit after.

## 2026-11-17: Where things stand (before `git commit` and `/clear`)

* Letters sit on the side of their line away from the middle of the
  outline's box (`DimensionItem.draw_letter()`), as the user asked.
* The user: "We are really close"; the circles on edges and
  dimensions feel natural.  Not yet confirmed by a run: dimensioning
  in any order (#60), the dimension circle (#63), the letter side.
* Done: Steps 1-3; Step 4 all but #57 (each corner's formula as a
  tooltip on its square, e.g. "(W - T, H)" or "x not dimensioned
  yet").  No modes: drag moves, clicks add to the selection, empty
  space clears; [Delete (Del)], [Dimension (N)] (last two points, in
  any order, waiting if needed); edge circles pull out corners;
  dimension circles move letter (`along`) and line (`offset`); keys
  are `QShortcut`s (button shortcuts never fired).
* Files: `scraftcam/gui/outline_editor.py`, `letters.py`,
  `dimensions.py`; `tests/test_outline_editor.py`, `test_letters.py`,
  `test_dimensions.py` (27 tests, coverage last measured 98%; run
  `uvx --python /usr/bin/python3 coverage run --include=... -m
  unittest ...`).  Checkers clean.
* Open items, numbers sticky up to #64: #57 tooltips (next); #62 a
  big selection is cleared by an empty-space click (asked, no
  answer); #56a/#33/#39 later.  Next Steps: 5 angles and slanted
  lengths, 6 [Revolve], 7 TOML, 8 SVG, 9 radii, 10 the GUI tree,
  11 a separate extruding class (#33).
* Work rule: ~3 minute chunks with a progress note at each mark;
  the transcript for the user's friend is regenerated each round
  (`~/.scraftcam/transcripts/transcript.py`).

## 2026-11-18: Renumbered for this session

The user asked for fresh numbers (sticky this session): steps #S1
finish Step 4 (#57 tooltips), #S2 Step 5 angles and slanted lengths,
#S3 Step 6 [Revolve], #S4 Step 7 TOML, #S5 Step 8 SVG, #S6 Step 9
radii, #S7 Step 10 GUI tree, #S8 Step 11 extruding class.  Issues:
#1 = old #57, #2 = #60, #3 = #63, #4 the letter side, #5 = #62,
#6 = #56a, #7 = #34, #8 = #39, #9 = #28, #10 = #49.  This session's
transcript: `~/.scraftcam/transcripts/2026-11-18_T.prg_5.1.9.2.md`.

## 2026-11-18: The user's answers; a segmentation fault fixed

* #2 all three dimensioning orders work; #3 the circles (new corner,
  moving dimensions) are natural; deleting corners works; #4 the
  letter side is right; #5 an empty-space click clears the
  selection: kept.  #1 tooltips: build them and see; the user doubts
  end users care about formulas, and suggests showing them from the
  letters table instead.  The user wants `#N:` only, never `1. #1:`.
* Segmentation fault deleting a dimension after dragging its circle
  (reproduced offscreen every time; not without the drag): the
  scene's spatial index had the item under its old box, and a
  deletion changes the box before removal, so the index kept a
  dangling pointer.  Fixed by `setItemIndexMethod(NoIndex)` in
  `OutlineView.__init__()`; `test_delete_after_drag` added.  21 tests
  in `test_outline_editor` pass, checkers clean.

## 2026-11-18: #1 tooltips, #13 lit circles

* The user: #11 tooltips only for now (formulas may be dropped
  entirely: "option c"); #12 deleting dimensions no longer crashes;
  #6 dropped; #10 Undo/Redo work great.
* #1: `OutlineView.corner_tip()`: each square's tooltip is its
  formulas, `(W - T, H)`, `?` with "x not dimensioned yet" for a
  coordinate no chain reaches; the origin says "(0, 0)"; set in
  `restyle()`.  #13 (the user): a clicked dimension circle is lit in
  the highlight color, as a clicked square is.  `test_corner_tips`;
  22 editor tests pass, checkers clean.  Not acted on:
  `QMouseEvent.pos()` is deprecated (PySide6 warns in the tests).
* Next: the user tries #1 and #13; then #S1 is done and #S2 (angles
  and slanted lengths) starts.

## 2026-11-18: #15-#19 answered; #19 done

* #15 tooltips are all `?` until dimensions exist.  #16 angles: two
  edges, then [Angle (A)], default like `118 deg`.  #17 the user:
  a dimension between two points is ambiguous (horizontal, vertical
  or the slanted length); no right-click menus ever; a dimension has
  (at least) three states and a button cycles them.  #18 the #S2
  chunk order agreed (slanted length, edge angle, formulas with
  `sin`/`tan`/`sqrt`, red marks).  #19 `event.pos()` ->
  `event.position().toPoint()`, no more warnings.
* Work in ~3 minute increments (the user tracks tokens).

## 2026-11-18: #15, #17, #20 done; #22, #23 open

* #15 tooltips: `(W, Y-Floating)`, `X-Floating` for a coordinate no
  chain reaches (the user: "Under-constrained" is exact, "Floating"
  gets it across).
* #17 [Dim. Kind ↻ (K)] (U+21BB, the user's name) right of
  [Dimension]: `OutlineView.cycle_kind()` turns the selected
  dimensions horizontal <-> vertical, one change, line moved to
  `offset_for()` (shared with `dimension_between()`); the slanted
  length (third state) comes with #S2.
* #20 a corner not yet dimensioned is yellow (`theme.Colors.warning`
  `#f2c200` light, `#d9b300` dark), not red; extra dimensions stay
  red.  Button actions are one table (pylint's statement limit).
* #22 the user: overload [Dim. Kind] for angles too.  #23 (the
  user's): a point on the X or Y axis removes one degree of freedom.
* `test_cycle_kind`; 23 editor tests, `test_gui_theme` pass; checkers
  clean.

## 2026-11-18: #23 corners on an axis; #28 axis colors

* #27 (the user): corners on an axis showed as floating.  #23 done:
  `dimensions._chain()` seeds every corner drawn within `ON_AXIS`
  (1e-9) of the axis across the kind as `0` (on the Y axis: X = 0;
  at the origin both); a dimension to such a corner is extra (red).
  `test_on_axis`.
* #28 (the user): X axis light red (`theme.Colors.x_axis` `#e87070`,
  dark `#d46a6a`), Y axis light green (`y_axis` `#5cb85c`, dark
  `#6abf6a`), in `OutlineView.drawBackground()`.
* #24/#29 the user: not ready to move on; [Dim. Kind] must cycle all
  three kinds (horizontal, length, vertical) first.  Next chunk.
* 30 tests (`test_outline_editor`, `test_dimensions`,
  `test_gui_theme`) pass; checkers clean.

## 2026-11-18: #29 length (slanted) dimensions

* `dimensions.LENGTH`, `NEXT_KIND` (horizontal -> length -> vertical
  -> horizontal); `solve()` ignores lengths (not in `AXIS`), so a
  corner with only a length stays yellow until angles (#S2).
* `outline_editor.left_of()` (unit vector a quarter turn left);
  `DimensionItem.ends()` for a length: parallel to its points,
  `offset` aside (left of start -> end positive);
  `DimensionHandle` drags a length's `along` and `offset` by
  projection; `OutlineView.offset_for(LENGTH)` puts it away from the
  outline's middle; `DimensionItem.letter_side()` (split out of
  `draw_letter()`; it had read the painter's transform after
  `resetTransform()`).  `cycle_kind()` uses `NEXT_KIND`.
* An offscreen picture of the triangle with three lengths looked
  right.  `test_length`, `test_cycle_kind` (all three kinds); 28
  tests (`test_outline_editor`, `test_dimensions`) pass; checkers
  clean.  New dimensions still start horizontal or vertical.

## 2026-11-18: #29 each kind keeps its place; #30 new dimension selected

* #29 (the user): no surprise moves; each of the three kinds keeps
  its own line and letter place.  `Dimension.places` (kind, offset,
  along; a tuple so `replace()` snapshots stay apart),
  `place_of()`, `become()`; `cycle_kind()` uses `become()`.  Places
  are kept when corners move (to confirm, #36).
* #30 the user could not get a slanted dimension from +X axis to +Y
  axis corners; likely cause: a new dimension was not selected, so
  [Dim. Kind] said "Select dimensions".  Now `dimension_between()`
  selects it.  Not confirmed by the user.
* #31, #33 OK.  #35: the user expects lengths to bring grief (two
  solutions); Claude's answer below in the conversation.
* 28 tests pass; checkers clean.

## 2026-11-18: Where things stand (before `git commit`)

* Answered: #30 the slanted dimension from +X to +Y axis corners
  works (a new dimension starts selected); #34 each kind's place is
  "sticky", works; #36 no: horizontal and vertical places stay fixed
  when corners move (keep it simple); #37 lengths (and later angles)
  with two solutions: the drawing picks the side, as it picks signs
  now, and defaults with no solution (L shorter than dx) show red
  with the reason; #26 angles wait until after this commit.
* Done today: #S1 (Step 4) is finished: corner tooltips
  (`(W, Y-Floating)`), yellow for corners not yet dimensioned,
  corners on an axis count as 0 there, colored axes, a segmentation
  fault fixed (`NoIndex`), [Dim. Kind ↻ (K)] cycling horizontal,
  length (slanted), vertical, each kind keeping its place, selected
  circles lit.  The first chunk of #S2 (slanted lengths drawn) is in.
* Open, numbers sticky this session: #7 sharp-tip revolve (#S3), #8
  flutes and assemblies (`T.cett2e~5.1.9.2.1`), #9 break-line box
  (later).  Steps left: #S2 (angles [Angle (A)] with [Dim. Kind]
  cycling the four arcs; formulas with `sin`/`tan`/`sqrt`; red
  marks and two-solution handling per #37), #S3 [Revolve], #S4
  TOML, #S5 SVG, #S6 radii, #S7 GUI tree, #S8 extruding class.
* Transcript: `~/.scraftcam/transcripts/2026-11-18_T.prg_5.1.9.2.md`.

## 2026-11-18: #S2 chunk 1: edges selected

`git`: `5cf2a11` (committed by Claude at the user's request with the
suggested message), pushed.  The user: finish #S2 before #S3, in ~3
minute chunks.  A click (no drag) on an edge's circle selects the
edge (`OutlineView.chosen_edges`, `select_edge()`), its circle lit;
cleared with the rest.  `test_select_edge`; 25 editor tests pass.
Next: [Angle (A)] between the two last selected edges, drawn as an
arc with its letter (default `deg`).

## 2026-11-18: #S2 chunk 2: [Angle (A)]

* The user: #38 edge selection works; #39 [Angle] after [Dim.
  Kind]; few angles expected, mostly drill tips; #40 any two edges,
  crossing of their lines as the center, parallel refused; #41 the
  default comes from the drawing (the closed outline is the start);
  #42 a selected edge is only for [Angle].
* `dimensions.ANGLE` (`start`, `end` the edges' corners; `offset`
  the arc's radius; `along` the letter on the arc).
  `outline_editor.edge_arc()` (crossing, first ray's direction, turn
  to the second, rays toward each edge's middle; `None` if parallel
  within `PARALLEL` 1e-6), `direction()`; `DimensionItem.arc_point()`,
  `arc_path()` (`ARC_STEPS` 48), `reach_path()` (extension lines
  past an edge's end), `paint_angle()`; `letter_side()` radial;
  `DimensionHandle.drag_angle()` (around: `along`; in/out: radius).
  `OutlineView.angle_selected()`: letter default the drawn angle to
  a whole degree (`118 deg` on a drill tip, picture checked);
  `cycle_kind()` skips angles (four arcs not yet).
* `test_angle`; 30 tests pass; checkers clean.  Not yet: angles in
  `solve()` (formulas), the four arcs by [Dim. Kind], deleting a
  corner leaves angles on its other edge pointing at shifted edges
  (to check).

## 2026-11-18: #45 checked; #48 angles past 180 degrees

* #43 [Angle] works; #44 a parallel angle just vanishing is OK.
* #45: `Drawing.insert()`/`remove()` keep an angle on its edges (by
  the corner each leaves): a split before shifts it; deleting an
  edge's far corner lets the edge reach on (merged); deleting the
  corner an edge leaves deletes the angle.  `test_angle_edges_change`
  pins it; no code change.
* #48 (the user): angles may pass 180 degrees; an angle needs a
  start edge and a direction (CW or CCW), so there is one answer.
  Proposal in the conversation; not coded.

## 2026-11-18: #48-#51 answered; design review before coding

* #48 (the user): no CW/CCW flag: angles are always CCW from the
  start edge, a negative value for CW.  #49 the other two arcs are
  dropped.  #50 default under 180 degrees, but the user is torn (it
  may come out negative).  #51 a direction arrowhead: yes.
* The user asked for the problems the proposals bring (and avoid)
  before coding; Claude's list is #53-#62 in the conversation
  (stored ray directions, `K` on angles, value redundancy 118 vs
  -242, near-180 values, angles to the axes for revolved tips,
  shared letters with signs, arrowhead only on screen, letter unit
  checks).  `Angle`/`parse_number()` take `-118` already.

## 2026-11-18: #53, #57, #59, #61 answered

* The user: angles are always measured CCW (negative for CW); an
  experiment, to be changed when something nasty shows up.
* #59 yes: angles between an edge and the X or Y axis; a revolved
  outline's tip angle doubled.  #57 yes: a new angle's start edge is
  the one that makes it positive and under 180 degrees.  #53 yes:
  each ray's direction (with or against its edge) stored at
  creation, never recomputed.  #61 the direction arrowhead on screen
  and in the SVG: the two must mean the same (someone re-entering
  the SVG with the same values gets the same outline).
* Open: #56 `K` on angles, #58 near-parallel values, #60 mirrored
  angles sharing a letter, #62 letter unit checks, #63 selecting an
  axis.

## 2026-11-18: #56 angles as people draw them

* The user rethought #48: an angle is what the person drawing it
  would write, e.g. a drill point is always positive, under 180
  degrees, its arc across the body.  #58 agreed (refuse near 0 and
  180); #62 yes (letters checked against their use); #60 decide
  when met.
* Claude's proposal (#64): the value is a plain positive magnitude,
  under 180 degrees; which of the four sectors is meant is set once,
  at creation, by the rays toward the edges' middles (#53, stored);
  no signs, no direction arrowhead (an arc in its sector is complete,
  as in drafting, so screen and SVG mean the same, #61).  Mirrored
  tips can share a letter (#60).  Lost: angles over 180 degrees.

## 2026-11-18: Angle design agreed

The user agreed: #48, #49, #53, #56, #57, #58, #59, #60, #62, #64
(positive values under 180 degrees, sector fixed at creation by the
stored rays, no direction arrowhead), #65 (an axis ray toward the
edge's side), #66 (no angles over 180 degrees).  #62 (letter unit
against its use) explained again; then coding starts (#67: stored
rays, then the letter checks; axis angles the chunk after).

## 2026-11-18: Angle chunk 1: rays stored (#53, #57)

* #62 the user: the table must require units (it does: a bare
  number is refused); the diagram shows letters only.
* `Dimension.rays` (each ray along `1` or against `-1` its edge's
  direction); `outline_editor.crossing()`, `edge_way()`,
  `middle_rays()` (toward the edges' middles, at creation only),
  `edge_arc(points, first, second, rays)` (turn counterclockwise,
  0-360), `angle_arc(points, dimension)` for the items.
  `angle_selected()` swaps the edges when the turn is over 180, so a
  new angle is positive and under 180 whichever edge is clicked
  first.  `test_angle_sector_fixed` (118 deg both orders; a tip
  pushed past its shoulders turns the long way, no sector jump).
  32 tests pass; checkers clean.  Next: chunk 2, the letter checks
  (#58, #62).

## 2026-11-18: #68 angles follow the drawing

* #68 (the user): swinging the triangle's top corner around an angle
  at the lower right corner gave arcs over 180 degrees: unexpected.
  The rays fixed at creation (#53) were the cause.  Now
  `Drawing.follow_angles()` (called from `OutlineView.follow()` on
  every change) sets the rays toward the edges' middles and swaps the
  edges so the turn is under 180.  A full 360 degree swing: largest
  arc 179.5.  `test_angle_sector_fixed` reworked.  32 tests pass.
* So #53 now holds only between changes: when formulas drive the
  drawing (later), the last rays are what keep the sector (#70).
* #69: deal with issues as they come.  #62: the user still does not
  see the issue; explained again with a different example.

## 2026-11-18: Angle chunk 2: letter checks (#58, #62)

* #71 the user's triangle swing works; #72 no angles of 270 degrees
  (always the side under 180).
* `letters.use_problem(letter, text, kinds)` (`kinds`: `length`,
  `angle`, from the dimensions using the letter): both kinds
  refused; a length letter holding an angle and the reverse
  refused; an angle outside `ANGLE_LIMITS` (0.1, 179.9) degrees
  refused (also negatives).  `OutlineEditor.check_letters()` shows
  it in the Default cell, as `value_problem()`'s.  `test_use_problem`,
  `test_letter_uses`; 37 tests (`test_outline_editor`,
  `test_dimensions`, `test_letters`) pass; checkers clean.
* Next: chunk 3, selecting an axis and angles to an axis (#59, #63,
  #65).

## 2026-11-18: Angle chunk 3: angles to an axis (#59, #63, #65, #76)

* #58: the user found no way to set table values: a double click on
  a cell edits it (the window's button keys take plain keystrokes).
* #76 (the user): an angle's circle dragged past its arc left the
  arc behind; now `drag_angle()` keeps `along` in 0..1 (on the arc).
* `dimensions.X_AXIS` -2, `Y_AXIS` -3, `AXES`: an angle's `start` or
  `end` may be an axis.  `edge_start()`, `edge_way()` know the axes
  (origin, +X/+Y); `middle_rays()` points an axis's ray toward the
  other edge's middle (#65); `reach_path()` skips axes.
  `OutlineView.axis_at()`: a click within half a square of an axis
  (not the origin) selects it (`select_edge()`), drawn thick in the
  highlight color.  Two axes refused.  A new arc's radius is half the
  distance to the nearer edge's middle.  Half a drill point (edge
  and Y axis): `59 deg`, picture checked.  Doubling for [Revolve]
  waits for #S3 (#74).
* `test_axis_angle`; 38 tests pass; checkers clean.  Next: #S2's
  last chunk, the formulas (#75).

## 2026-11-18: #S2 formulas, chunk A: `solve()` by passes; lengths

* #77, #73, #78 tried, fine.  #79 commit once #S2 is done.
* `dimensions.solve()` now passes over the dimensions until none
  tells anything new (`_apply()`, `_along_axis()`,
  `_along_length()`, `_drawn()`); seeds: the origin and corners on
  an axis.  A length from a point known in full to a corner known in
  one coordinate gives the other: `Y0 +/- sqrt(L^2 - (dx)^2)`, the
  sign from the drawing (#37).  `Formula.text` holds such a start.
  `test_length`; 35 tests pass; checkers clean.
* Next, chunk B: angles give edge directions (from an axis or an
  edge already directed); a directed edge from a known corner gives
  the other corner from one coordinate or a length.

## 2026-11-18: #S2 formulas, chunk B: angles; #80; #S2 done

* #80 (the user): no way to dimension from an axis to a corner.  Now
  an axis plus one corner, then [Dimension], gives a dimension from
  the origin across the axis (vertical from the X axis, horizontal
  from the Y axis): `dimension_between(..., kind)`.
  `test_dimension_from_axis`.  #81 tooltips seen; tidying formulas
  later.  #83 two lengths at a corner: left out.
* `dimensions.solve()`: `ways` (each directed edge's direction, an
  expression in degrees; axes `0 deg`, `90 deg`); `_angle_way()`
  (an angle from a directed edge directs the other, `+ 180 deg`
  for a ray against its edge); `_along_edge()` (a directed edge
  known in full at one end gives the other end from one coordinate:
  `y0 + (x - x0) * tan(way)` or `x0 + (y - y0) / tan(way)`).  Half
  a drill point (angle to the Y axis plus a horizontal from the
  origin) checked numerically, both sides: 1.202 against 1.2 drawn.
  `test_angle`; 42 tests (`test_dimensions`, `test_outline_editor`,
  `test_letters`) pass; checkers clean.
* Not done (#84): a length along a directed edge (cos/sin); two
  lengths at a corner (#83); an angle one too many is not red (#33).

## 2026-11-18: Where things stand (before `git commit`)

* #S1 and #S2 are done.  Next: #S3 [Revolve] (doubled diameters and
  tip angles, #74; sharp-tip retest, #7), then #S4 TOML, #S5 SVG
  (semantically the same as the screen, #61), #S6 radii, #S7 GUI
  tree, #S8 extruding class.
* Open: #7, #8, #9, #81 (formula tidying), #83, #84.  Numbers sticky
  this session (up to #84).
* Transcript: `~/.scraftcam/transcripts/2026-11-18_T.prg_5.1.9.2.md`.

`git`: `fea4900` (#S2), pushed.

## 2026-11-18: #S3 chunk 1: [Revolve (R)]

`Drawing.revolve`, `Snapshot.revolve` (undoable); [Revolve (R)]
checkable, after [Angle] (`OutlineEditor.toggle_revolve()` sets the
button from the drawing; `OutlineView.toggle_revolve()` refuses while
a corner is left of the Y axis).  Revolved: the mirror half faint and
dashed (`OutlineItem.paint()`, `boundingRect()` both halves), the Y
axis dash-dot, corner and edge-circle drags kept at X >= 0 (snapped
to 0).  `test_revolve`; 32 editor tests pass; checkers clean;
picture checked.  Next: chunk 2, diameters (horizontal dimensions
from the Y axis shown and solved as diameters), then doubled tip
angles (#74), then #7.

## 2026-11-18: #S3 done (by the user); #S4 design questions

* #85 [Revolve] works.  #86 diameters: "I think so, but not sure
  where this is going"; #87 the user makes the half angle with a
  letter of their own; #88 the mirror shows the outline only; #7
  moved after #S4.  The user: #S3 done.  #86/#87 kept as deferred
  items (#89) for catalog numbers (diameters, whole tip angles).
* #S4 questions #90-#94 in the conversation.  Found:
  `gui/fields.py` `write_item()`/`item_text()` writes shop TOML (not
  yet checked for arrays of tables).

## 2026-11-18: #S4 chunk 1: outlines as TOML text

* #90 (save after every change) and #91 (the layout) taken as
  agreed; #92 fixed field order; #93 refuse bad files, never rewrite
  one; #94 four chunks.
* New `scraftcam/gui/outline_file.py` (no Qt): `Outline(points,
  letters, dimensions, revolve)`, `outline_text()` (fixed order;
  `from`/`to` as an index or `"origin"`, `"x_axis"`, `"y_axis"`;
  `rays` for angles only, `places` only when set; floats by `repr`,
  strings by `json.dumps`), `outline_from_text(text, source)`
  raising `OutlineError` (unchecked beyond `tomllib` and `kind`;
  `type: ignore` casts to go in chunk 2).
  `tests/test_outline_file.py` (3: round trip, one moved corner one
  changed line, bad text).  Checkers clean.  Next: chunk 2, checks.

## 2026-11-18: #S4 chunk 2: checks on reading

* #95-#99 agreed: every problem named by file and entry; editor rules
  (letter names, units, values) left to the table (#96); `FILE` on
  the command line, rewritten after every change (#97);
  `examples/shop/tools/` for the drill (#98); the outline file holds
  the drawing only, the shop item tied in at #S7 (#99).
* `outline_file._Reader` (`note()`, `outline()`, `points()`,
  `letters()`, `dimension()`, `end()`, `places()`), `KINDS`,
  `_is_number()`: kind, revolve, 3+ corners `at = [x, y]`, revolved
  corners at X >= 0, letters with text name/default/help, dimension
  kind and letter known, ends in range ("origin" for lengths, axes
  for angles), numbers for offset/along, rays of +/-1, places.
  `test_checks`; 4 tests pass; checkers clean.  Next: chunk 3, the
  editor on a file.

## 2026-11-18: #S4 chunk 3: the editor on a file

`python3 -m scraftcam.gui.outline_editor FILE`: `main()` reads it by
`drawing_from()` (`outline_from_text()`), printing every problem and
exiting 1 for a bad file (tried); a missing file starts as the
triangle and is written at once.  `OutlineEditor(drawing, path=)`,
`path`, `saved` (`file_text()`), `save()` (rewrites when the text
changed, never mid-drag); called from `show_message()` (scene
changes), `keep()` (table typing) and `OutlineView.released` (after a
mouse button comes up).  Title shows the file.  `test_file`; 37 tests
(`test_outline_editor`, `test_outline_file`) pass; checkers clean.
Next: chunk 4, a half drill in `examples/shop/tools/`.

## 2026-11-18: #S4 chunk 4: `examples/shop/tools/drill.outline.toml`; #S4 done

Made through the editor's own calls (offscreen): half a 1/4 in drill,
revolved; `A` half point angle `59 deg` (edge 0 to the Y axis), `R`
radius `1/8 in` (horizontal from the origin to corners 1 and 2), `L`
overall length `4 in` (vertical from the origin to corners 2 and 3).
Every corner dimensioned (no yellow, no red); the tip shoulder's Y is
`(R) * tan(90 deg - A)`.  Picture checked.  Found: a level top edge
still needs its own dimension (no "horizontal edge" rule, #100).

## 2026-11-18: #101 duplicates gone: level and upright edges (#100)

* #101 (the user): `L` and `R` were each drawn twice; keep the right
  ones.  #102: no commit until they are gone.
* #100 done the #23 way: an edge drawn exactly level (upright) gives
  its corners the same Y (X): `dimensions._level_edges()` adds them
  as letterless dimensions, tried first (each pass starts over after
  a new fact), so a dimension repeating one is the extra (red);
  `_seed()` split out.  `test_level_edges`; the L bracket needs fewer
  dimensions now.  The drill keeps `A`, `R` (to corner 1) and `L` (to
  corner 2): every corner known, no extras; picture checked.
* #103 found real: the shop reader took `drill.outline.toml` for an
  item (`ShopError`, the example shop would not load).
  `shops.OUTLINE_SUFFIX`; `_Reader.directories()` and
  `gui/tree.shop_children()` skip outline files (the tree until #S7).
* Tests: `test_dimensions`, `test_outline_editor`, `test_outline_file`
  (44), `test_shops`, `test_gui_tree` (60) pass; checkers clean.

## 2026-11-18: #7 the sharp drill tip revolved in SolidCraft

* #104 the drill looks right (staged, not committed yet).  #105
  explained; drop unless needed.
* Scratchpad `show_outline.py FILE (PORT | headless)` (gone after
  the session; enough to redo): reads the outline file, `solve()`s
  it, adds each letter as a SolidCraft parameter (`Length.solidcraft()`
  for lengths, angles as written), sketches the corners as the
  formulas themselves on the XZ plane (`sketch.line(points=,
  closed=True)`, a bare `0` sent as `0 mm`), revolves about Z
  (`solid.revolve`).
* Headless and in a window (`--control 8085`, raised by KWin
  script): the sharp tip (corner on the axis) revolved with no error
  or warning (70-75 ms); live changes `A` 45 deg, back to 59 deg,
  `R` 1/4 in: 14-26 ms each.  The camera looked from above, tip
  hidden; `view.navigate` and `view.save` need a `camera` object of
  unknown shape (`"current"`, `{}`, eye/target/up and
  position/target/up all "invalid camera"): asked the user to orbit.

## 2026-11-18: #106 the sharp tip looks broken: cut flat at build

* #106 (the user): the sharp tip is "ill defined" and "broken"
  looking in SolidCraft, as before; cut off the very tip so a small
  circle is at the bottom (the old fix).
* The scratch `show_outline.py` now has `flatten_tips()` (build time
  only; the outline file stays the true sharp drill): a corner at X =
  0 between an edge on the axis and a slanted (not level) edge
  becomes two, `TIP_FLAT` 0.05 along the slanted edge and on the axis
  at that height, as `COUNTERSINK_TIP_FLAT` did.  Built headless and
  in a window (restarted, the user had closed it): 49 ms, live `A`
  changes 8-33 ms.  Awaiting the user's look.

## 2026-11-18: #110 the cut tip works; #S3/#S4 committed

#110 the flat tip looks right; #111 5% of the radius kept.  #102
commit and push.  #109: the user asked what #S6 (radii) is.

## 2026-11-18: #108 the tip cutting built in: `gui/outline_solid.py`

* The user: #112 #S6 before #S5; #113 key for [Fillet] open (`F` Fit
  and `S` Snap are taken; the letter is only the shortcut, the button
  shows the word); #114 a ball end (radius using up an edge) allowed;
  #108 build the tip cutting in now; #81 parked until Claude asks.
* New `scraftcam/gui/outline_solid.py` (no Qt): `TIP_FLAT` 0.05,
  `ZERO`, `corner_expressions()` (refuses a floating corner),
  `flatten_tips()`, `letter_value()`, `build(solidcraft, outline,
  name)` (revolved only so far; XZ plane, about Z), `main()`:
  `python3 -m scraftcam.gui.outline_solid FILE (PORT | headless)`.
  `tests/test_outline_solid.py` (5, one headless SolidCraft build
  with a live change); checkers clean.
* Next: #S6, once #113's key is chosen.

## 2026-11-18: #S6 chunk 1: [Fillet (F)]

* The user: #113 (c): [Fillet (F)], Fit moved to `Home`; #115 [Show
  in SolidCraft] with #S7; #116 the chunk order agreed, plus the
  drafting note "All undimensioned fillets are radius RF" (maybe a
  second for exterior fillets).
* `dimensions.RADIUS` (`start` = `end` = the corner, `offset` the
  radius as drawn); `Drawing.note_radius`, `Snapshot.note_radius`,
  `Outline.note_radius` (`note_radius = "A"` in the file, read and
  checked).  `OutlineView.fillet_selected()` (selected corners not yet
  rounded get a radius dimension by the note letter, made the first
  time: "Fillet radius", `1/16 in`), `drawn_radius()` (a fifth of the
  shorter edge).  `fillet_radii()`, `fillet_ends()`
  (`_tangent_reach()`, capped at the edges), `rounded_path()`,
  `_arc_to()`: the outline drawn with true tangent arcs; arrowheads
  end where the fillets begin.  Radius dimensions draw nothing yet,
  their circles hidden; `K` skips them.  `test_fillet`; 50 tests
  (`test_outline_editor`, `test_outline_file`, `test_outline_solid`,
  `test_dimensions`) pass; checkers clean; picture checked (two
  outside, one inside fillet).
* Next: chunk 2, the note on screen, and a fillet's own radius
  dimension (leader from the center).

## 2026-11-18: #117-#121 answered

#117 [Fillet] works (the user clicks buttons, not keys); the user
asks about dashed lines showing the sharp polygon, to anchor the
dimension lines.  #118 the note in the lower left: OK.  #119 own
radius by [Dimension] on one corner, [Delete] back to the note: OK.
#120 a fixed note letter: the user suggests `DFR` (Default Fillet
Radius).  #121 not understood; explained again in the conversation.

## 2026-11-18: #S6 chunk 2a: `UDF`, dashed corners, the note

* The user: #117/#122 dashed lines at filleted corners only; #120
  the note letter is `UDF` ("Undimensioned Fillet Radius", matching
  the note); #123 no fillets expected on revolved tools (vises etc.
  will have them); #121 taken as recommended.
* `NOTE_LETTER` "UDF" (the next free letter only if `UDF` is taken),
  name "Undimensioned fillet radius"; `FILLET_SHARE` 0.2 and
  `drawn_radius(points, corner)`: a fillet's drawn size follows its
  corners (the radius dimension's `offset` no longer used for it).
  `OutlineItem.paint()` draws thin dashed lines from each arc's ends
  to the sharp corner; `OutlineView.drawForeground()` writes "All
  undimensioned fillets are radius UDF" lower left while any fillet
  uses the note.  34 editor tests pass; checkers clean; picture
  checked.  Next: chunk 2b, a fillet's own radius (#119).

## 2026-11-18: #124/#129 marks: hollow, filled when selected

* The user: corner squares were filled (paper or yellow) while edge
  circles were hollow; make both hollow, filled only when selected;
  never tell things by color alone (color blindness).  A circle is
  only a corner not yet made.  #125 fillet sizes bound from the
  letters table (corners, a row, [Fillet]; again to remove) liked;
  #126 a radius label is the letter alone; #128 not reproducible;
  #130 #119 dropped (never built; #125 replaces it).
* `OutlineView.restyle()`: squares, edge circles and dimension circles
  hollow with an ink ring, filled with ink when selected; a corner
  not dimensioned yet has a dashed ring in the warning color; the
  origin a filled square, its ring thick when selected.  Tests check
  fills and dashes, not colors.  34 editor tests pass; checkers clean;
  picture checked.  Not changed yet: a selected dimension line or arc
  is still told by the highlight color only (#131).
* Next: chunk B, #125 binding fillets to letters.

## 2026-11-18: Polishing: #133 solid warning ring; #131 thick selected lines

* #133 (the user): the dashed yellow squares showed two gaps; now a
  solid 3 px ring in the warning color (thickness the color-free
  cue), mitered.  Squares and circles are both 9 px (`SQUARE_PIXELS`,
  `HANDLE_PIXELS`); a square only looks bigger.
* #131: a selected dimension line or arc is colored and drawn
  `CHOSEN_PIXELS` 2.5 thick (`DimensionItem.pen()`, split out of
  `paint()`).  #132, #127 agreed.  #125 (binding) waits for more
  polishing.  34 editor tests pass; checkers clean; picture checked.

## 2026-11-18: #S6 chunk B: fillets bound to letters (#125, #126, #132)

* The user: #134 marks look great; #135 squares stay 9 px (a little
  more prominent is good); #136 selections stay until empty space is
  clicked.
* `OutlineView.fillet_selected(letter)`: the selected corners get the
  letter (the table's selected row, via `OutlineEditor.fillet_selected()`),
  else the note letter (`note_letter()`, `UDF` made the first time);
  corners already filleted change letter; if every selected corner
  already has that letter, they are made sharp again (#125).  An
  angle letter (`is_angle()`: on an angle, or a deg/rad default) is
  refused (#132).  `OutlineView.cleared` hook: an empty-space click
  clears the table's row too.
* #126: a fillet on its own letter shows the letter past its sharp
  corner, on the line from its center through its arc's middle
  (`fillet_middle()`, `_fillet_center()` shared with `_arc_to()`,
  `DimensionItem.paint_radius()`, `boundingRect()` around it); note
  fillets show nothing.  Picture checked.
* `test_fillet` reworked, `test_fillet_letters`; 35 editor tests pass;
  checkers clean.  Next: chunk C, fillets too big for their edges
  (#127).

## 2026-11-18: #S6 chunk C: fillets too big (#127, #139); #141 problems under the table

* The user: #141 table problems right under their entry, not in the
  bar (the window grew); #137/#138 binding works; #139 red both on
  the drawing and in the table (the user must see how to fix it).
* New `scraftcam/gui/values.py` (no Qt): `letter_values()` (mm,
  radians), `evaluate()` (an `ast` reader: numbers, letters, `deg`,
  `mm`, `pi`, `+ - * / ^`, `sin cos tan atan sqrt abs`; anything
  else refused), `real_corners()`, `fillet_problems()` (each edge's
  two fillets' reach `r / tan(half angle)` against its length,
  `FIT_SLACK` 1e-9 mm so using an edge up is allowed, #114; message
  in the first fillet letter's unit by `Length.from_mm()`).
  `tests/test_values.py` (3).
* Editor: `letters_area()` (the table, then `problems`, a red
  wrapped `QLabel` with every problem, a line each); `self.problem`
  gone; the bar's `status` has an `Ignored` width (never widens the
  window).  `fillet_trouble()` sets `OutlineView.trouble` (by
  corner): a red 3 px ring on the square, a red own-letter label; the
  letter's Default cell red with the reason.  `test_fillet_too_big`;
  tests moved from `status` to `problems`.  56 tests
  (`test_outline_editor`, `test_values`, `test_outline_file`,
  `test_outline_solid`, `test_dimensions`, `test_letters`) pass;
  checkers clean; picture checked.  Small: the line reads "UDF: UDF
  need ..." (#143).
* Next: chunk D, fillets built in SolidCraft (#140).

## 2026-11-18: #143 done; #142, #145 explained

#143: a table problem already starting with its letter is not
prefixed again ("UDF need 3/4 in ...").  #141, #144 agreed (commit
after chunk D).  #142: the user thought typing a size needs a
dimension entry; sizes are the letters' Default cells (double-click).
#145: the user has seen no problems under the table yet.  #140 (flat
outlines in SolidCraft: a thickness letter now, or wait for #S8)
asked again.

## 2026-11-18: #147 "Value"; #148 after #S6; #140 waits for #S8

* #147: the table's third column is "Value" (the `Letter.default`
  attribute and the file's `default` key unchanged).
* #148 (drawn from the values, to scale, #28) after #S6; until then a
  changed value does not change the drawing (the user's #142).
* #140 (b): fillets in SolidCraft wait for #S8 (extruding class);
  leftovers may go to a new #S9 later.  So #S6 is chunks A-C; done
  once the user has checked chunk C (#142).
* #81 explained again (formula tidying).

## 2026-11-18: Typing into the table; work reordered

* #150 (the user, standing rule, also in memory): reorder Steps and
  chunks freely; deal now with what blocks use and testing, defer the
  rest to later Steps.
* #142 the user could not make a typed value stick.  Found offscreen:
  a key typed on a selected but not edited cell half-started an edit
  (letter `3`, cell still `1 in`) and letters in the text fired button
  keys (`n` of `in` is [Dimension]).  Now one click on a cell edits it
  (`setEditTriggers(CurrentChanged | SelectedClicked | DoubleClicked |
  EditKeyPressed)`); `test_click_and_type`.  37 editor tests pass.
* Correction to the entry above: the checkpoint went in with
  `test_live_typing` failing.  Fixed: `fill_table()` leaves no cell
  current (a current cell would now be edited at once, taking the
  buttons' keys) and gives the drawing the keyboard; [New Letter]
  still edits the new Name cell on purpose.  `test_live_typing`
  moves to the Value cell by `setCurrentCell()`.  58 tests (editor,
  values, file, solid, dimensions, letters) pass; checkers clean.

## 2026-11-18: The order from here (#150)

Now: (1) #148 drawn from the values (the user cannot test chunk C,
or see any value, until the drawing follows the table); (2) #81
formula tidying (the same formulas, now on screen everywhere);
(3) the user checks chunk C (#142), then commit #S6.  Deferred:
SolidCraft fillets and flat outlines to #S8 (#140); #S5 SVG, #S7
GUI tree after; leftovers to a new #S9.
* The order as the user wants it written (issue numbers only, no
  1-2-3): #81, then #148, then #142 (the user's check), then #156 git
  commit.

## 2026-11-18: #81 tidy formulas

`dimensions.grouped()` (brackets unless a token or one call,
`_one_call()` matching brackets), `total()`, `difference()`,
`product()`; `_along_length()` and `_along_edge()` build with them.
The drill's shoulder reads `R * tan(90 deg - A)` (was `0 + ((R) -
(0)) * tan(90 deg - A)`); a length `sqrt(S^2 - (P - W)^2)`, below
`-sqrt(...)`.  `test_tidy`; 61 tests (dimensions, solid, values,
editor, file, letters) pass, the headless SolidCraft build too;
checkers clean.  Next: #148.

## 2026-11-18: #148 chunk 1: the drawing follows the values

* #152, #153, #154 agreed.
* `values.real_coordinates()` (each fixed coordinate in mm, partly
  fixed corners too), `crosses()`/`_segments_cross()`.
  `Drawing.scale` (steps per mm, chosen once by `first_scale()`: the
  middle drawn/real ratio).  `OutlineView.apply_values()` (in
  `follow()`): fixed coordinates to `real * scale`, the others as
  drawn; nothing changes while a used letter is bad (`letters_bad()`),
  a formula fails or edges cross (#154); squares moved with
  `placing` set so their moves are not drags.  `PullSquare.itemChange()`
  holds fixed coordinates (dragging them to change the value is
  #152, next).  Table edits call `view.follow()`.
* `letters._range_problem()`: a length used by a dimension must be
  more than 0 (#154; `-2 in` had mirrored the rectangle).
* `test_follows_values`; tests pass (editor, values, dimensions,
  letters, file, solid); checkers clean.
* Found (#157): drawn to scale, the drill (1/4 in by 4 in) is a thin
  stick, its tip a few pixels: long thin parts need break lines (#9)
  or "not to scale" dimensions.  Asked the user.

## 2026-11-18: Hide strips (#157), chunk 1 part 1

* The user's view (#157, #167, #168): mark boring stretches with
  rectangles, as the grid plate's sketch did (`tool_models._Broken`,
  `_zigzag()`); two views of one drawing: an overview (whole, to
  scale, strips shaded) and a working view (strips cut out, long
  break lines); strips are part of the drawing and its file.
  [Hide (H)] lays one by dragging (#164); [Overview (O)] toggles
  (#168); a strip covers straight stretches only: no corner, no
  fillet arc; a radius change pushing an arc into a strip is declined
  (#165); a strip hides more when values grow, the view unchanged
  (#160 (a)); no break marks on dimension lines (#166).  Chunks are
  Claude's to reshape (#169).
* New `scraftcam/gui/hides.py` (no Qt): `Hide(axis, below, above,
  low, high)` tied to the corners outside it, `strip()`, `lay()`
  (refuses corners, fillet arcs, outside the outline).
  `tests/test_hides.py` (2).  Checkers clean.

## 2026-11-18: Hide strips, chunk 1 done

* `Drawing` is now a subclass of `outline_file.Outline` (pylint found
  the two duplicated; `Outline.points` defaults to `[]`,
  `Drawing.__post_init__()` gives the triangle), so `save()` writes
  the drawing itself.  `hides` in `Outline`, `Drawing`, `Snapshot`
  (undo) and the file (`[[hides]]`: `axis` "x"/"y", `below`,
  `above`, `low`, `high`; `_Reader.hides()` checks them).
* Editor: [Hide (H)] (`OutlineView.start_hide()`: to the overview,
  wait for a drag; press/move/release draw `band`; `lay_hide()`: wide
  -> `HIDE_Y`, tall -> `HIDE_X`, fillet arcs passed to `lay()`; a
  refusal in the bar) and [Overview (O)] (checkable,
  `toggle_overview()`); `shade_hides()` hatches each strip right
  across the view in the overview (from `drawForeground()`).
* `test_hide` (the drag by mouse), file round trip and checks with
  hides; tests pass (editor, file, hides, solid); checkers clean;
  picture checked.  The working view does not cut strips out yet.
* Next: chunk 2, the working view: strips cut out, long break lines.

## 2026-11-18: #173 strips finite, resized and moved by circles

* The user: #170 long break lines must mesh (peak in valley); #171
  keep it simple, the wheel zooms to details: taken as dragging in
  the overview only, the working view for looking and selecting
  (not confirmed in words); #172 a gap of ~20 px; #173 endless strips
  cannot be reached: make them finite; #174 the grid plate is Python
  and hand SVG, not tried in the editor.
* `StripHandle` (`low`, `high`, `whole`): circles on a strip's sides
  and middle, overview only; a drag re-lays the strip by `lay()`
  (refused over a corner or a fillet, the message in the bar);
  `_snapped()` snaps where it lands (a move snaps its low side, width
  kept); one change on release.  `OutlineView.grips`,
  `fillet_arcs()`.  `shade_hides()` draws each strip across the
  outline's box plus two grid steps.  `test_strip_circles`; tests
  pass (editor, hides, file); checkers clean; picture checked.
* Next: #170, the working view: strips cut out, meshing long break
  lines, dimensions across a cut shortened.

## 2026-11-18: #176 corners could not cross an axis

The user could not drag a corner across the X or Y axis.  Cause:
since #148 a known coordinate is held during a drag, and a corner on
an axis is known by #23 (and one beside a level edge by #100), so a
corner reaching an axis stuck.  Now `solve(..., drawn=False)` leaves
out what the drawing says (axis seeds, level edges), and
`OutlineView.pinned` (that solution) is what `PullSquare.itemChange()`
holds: only dimensions pin a drag.  `test_drag_across_axes`; tests
pass (editor, dimensions, values, solid); checkers clean.

## 2026-11-18: #177 strip circles could not be found

The user: corners drag freely now; a hide strip was made, but no
circles to resize or move it.  Offscreen the circles existed and were
shown, but on the triangle they sat at X = 0: the middle one under
the origin's square, the others on the Y axis inside the hatching,
small and hollow.  Now `GRIP_PIXELS` 11, placed in the strip's
margin one grid step past the outline (right of it, or above for a
top-to-bottom strip), with a paper inside so the hatching does not
run through them.  Tests pass; checkers clean; picture checked.

## 2026-11-18: #178 a strip resized on all four sides, moved from the middle

The user: resize left/right/up/down, and a middle circle to move.
`Hide.under`, `Hide.over` (how far past the outline it reaches across
its axis, never below 0: it must cut right through the part, #180),
`hides.across()`; in the file (`under`, `over`, default 1).
`StripHandle` parts `low`, `high`, `under`, `over`, `whole` at the
middles of the rectangle's sides and its middle; `whole` moves both
ways; a side into the outline is refused ("A hide must reach right
across the part.").  `lay_hide()` keeps the dragged rectangle's
reach.  `shade_hides()` draws the rectangle as it is.  The local
`across` in `dimension_between()` renamed `wide`.  Tests pass
(editor, hides, file); checkers clean.

## 2026-11-18: #180 hide regions reach past the part and its dimensions

#181 all five circles work.  #180 (the user): a hide region must
reach past the outline's box and its dimensions, up/down or
left/right.  `OutlineView.reach(axis)` (outline box united with each
dimension's line ends and angle arcs); `lay_hide()` makes a new
region reach at least a grid step past it; `StripHandle` refuses a
side inside it ("A hide must reach past the part and its
dimensions."); `proposed()` split out of `mouseMoveEvent()`.  Tests
pass; checkers clean.  Next: #170, the working view.

## 2026-11-18: #170 the working view

* `OutlineView.cut_offsets(axis)` (pieces between cuts, each shifted
  by the stretches hidden below it less `GAP_PIXELS` 20 per cut),
  `draw_cut()` (from `drawForeground()` out of the overview: paper
  over the normal drawing, then the scene rendered piece by piece,
  each clipped to itself, X pieces times Y pieces so crossing strips
  leave four corners), `draw_breaks()` and `zigzag()` (a long break
  line on each side of a cut, the zigzag the same way on both so
  they mesh, `ZIG_HALF_PIXELS` 10, `ZIG_HIGH_PIXELS` 6), `shift_at()`.
  The working view with strips is look and pan only
  (`setInteractive()` in `restyle()`; [Overview] and [Hide]
  restyle).
* Found and fixed: a tall drag over a long upright shank was taken
  as hiding width and refused; `lay_hide()` now decides by what the
  rectangle reaches across (the part's width: hide height; its
  height: hide width; else wide hides height).  Without clipping,
  items reaching into a hidden stretch were drawn across the gap.
* `test_working_view`; 68 tests (editor, hides, file, values,
  dimensions, letters, solid) pass; checkers clean; picture of a real
  1/4 x 4 in drill checked.  Open: a dimension's letter inside a
  hidden stretch is not drawn (#182); no grid or axes in the working
  view (#183).

## 2026-11-18: #185 break lines edge to edge; S ends on dimension lines

The user (drafting practice, the grid plate's SVG): long break lines
end at the outline's edges (and at another hide's gap); a dimension
line a cut chops ends in a small S on each side, hump facing valley.
`hides.inside_spans()` (where a line across is inside the outline,
even-odd, a revolved outline's mirror counted, joined), `minus()`
(less other hides' stretches); `draw_breaks()` draws each side of a
cut where it really is (spans at that side), shifted with its piece,
one zigzag per span.  `draw_esses()`/`ess()`: an S (cubic,
`ESS_PIXELS` 9) wholly on its own side of the gap, the same shape on
both (first try straddled the gap and the two S's met, hiding it).
`test_spans`; `test_working_view` adds a dimension across the cut.
Tests pass (editor, hides, file, values, dimensions, letters, solid);
checkers clean; pictures checked.

## 2026-11-18: #187 the S's lie across the dimension line

The user: the long break lines match perfectly; the S's were turned
90 degrees the wrong way; "one fix away from basically being done
with hide zones".  `ess()` now lies across the line (like a small
break line), its middle on the line, wholly on its own side of the
gap, the same shape on both.  Test checks it is wider than tall.
Tests pass; checkers clean; picture checked.

## 2026-11-18: #188 the S's middle at the line's end

The user: the S's middle must be exactly at the end of the dimension
line (it went over a little).  `ess(axis, at, across_at)` (no `way`):
centered on the cut's side.  Test checks the center.  Tests pass;
checkers clean; picture checked.

## 2026-11-18: Where things stand (before `git commit`)

* Done since `fea4900` (#S2): #S3 [Revolve] and #S4 outline files
  (committed as `ee27af0`), then: `gui/outline_solid.py` (revolved
  outlines built in SolidCraft, tips cut flat, #108); #S6 fillets
  ([Fillet (F)], the `UDF` note, letters bound from the table,
  fillets too big red, #116-#143); marks hollow, filled when selected
  (#124-#136); table problems under the table, one click edits a cell
  (#141, #142); "Value" column (#147); #81 tidy formulas; #148 the
  drawing follows the values to a fixed scale (lengths > 0, bad values
  keep the last shape); #176 only dimensions pin a drag; hide regions
  (#157-#188: `gui/hides.py`, [Hide (H)], [Overview (O)], five
  circles, reach past part and dimensions, the working view cut with
  meshing long break lines edge to edge and S's on dimension lines).
* Open, numbers sticky this session: #142 (the user's fillet check),
  #152 (dragging a fixed corner changes its letter's value), #182 (a
  long dimension's letter inside a hidden stretch is not drawn), #183
  (no grid or axes in the working view), #7, #8, #9, #83, #84, #89.
  Deferred: SolidCraft fillets and flat outlines to #S8 (#140); #S5
  SVG; #S7 GUI tree; a new #S9 for leftovers when needed.
* Tests: `test_outline_editor`, `test_hides`, `test_outline_file`,
  `test_values`, `test_dimensions`, `test_letters`,
  `test_outline_solid`, plus `test_shops`, `test_gui_tree`,
  `test_gui_theme` for the files touched; all pass.  Checkers clean.
* Transcript: `~/.scraftcam/transcripts/2026-11-18_T.prg_5.1.9.2.md`.
