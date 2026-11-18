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
