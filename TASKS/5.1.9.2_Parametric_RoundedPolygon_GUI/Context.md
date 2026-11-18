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
