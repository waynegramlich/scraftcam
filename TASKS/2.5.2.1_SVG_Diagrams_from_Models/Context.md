# LLM Agent Context Log

## 2026-11-16: Created

Created and opened from `T.cmt~5.3` (#72, #73) at the user's request;
`Details.md` is Claude's draft.  The user reviews both in the morning.
Nothing coded.

## 2026-11-17: Experiment: a parametric `RoundedPolygon` in SolidCraft

Scratchpad `fillet_test.py` (headless; gone after the session): a
closed `sketch.line` through `[0,0] [W,0] [W,H] [0,H]` (expressions),
then one `sketch.fillet(points=[...], radius="R")` on all four
corners, extruded by `T`.
* Works: dof 0; the sharp corners stay as virtual points
  `corner1..4` (dimensions can measure to them); one radius dimension
  `R` for all corners (`points` rounds alike; separate radii need one
  call per corner, not tried).
* Live changes of `W`, `H`, `R` rebuild in 2-6 ms; volume within
  ~2e-5 relative, box exact.
* `R` = half of `H` (edges used up, which `RoundedPolygon` allows):
  taken, but the extrude fails ("no closed profiles") and the body is
  gone; going back to `R = 3` restores it.  `R` past half: refused
  ("would flip the sketch over"), nothing changed.  `R = 0`: refused
  (constraints conflict), so sharp <-> rounded is a shape change
  (rebuild).  Our `update()` must check radii first.
* `sketch.export_dxf(sketch=)` returns DXF text: LINE and ARC
  entities, millimeters, no dimensions.  Enough for an SVG outline;
  letters and dimension lines come from our model.

## 2026-11-17: Experiment: polygons of lines only (#10)

Scratchpad `polygon_test.py` (headless): triangle, L, trapezoid and
a dented pentagon, corners as expressions (way (a)); then the L held
by a fixed origin, horizontal/vertical constraints and four length
dimensions `W`, `A`, `B`, `H` (way (b)).
* Every change 1-5 ms, no errors reported, areas exact for every
  simple polygon, including a zero-length edge (`X = 0`), three
  corners in a line (`Y = 0`), a 0.001 mm sliver, and the L's notch
  moved past the top (`A > H`).
* Way (b) gave exactly way (a)'s results at every step: no flips,
  even when an edge reversed direction.  dof 10 before the
  dimensions, 0 after.
* Self-crossing outlines are taken silently (no error, extrude
  fine): SolidCraft fills every region of the loop.  Trapezoid bow
  tie 650 (signed area 600); L with `B > W` 2450 (2350); dent past
  the top 660.71 (625).  So our model must refuse crossings itself
  (`RoundedPolygon._check_crossings()` does today).

## 2026-11-17: Experiment: arcs (#11)

Scratchpad `arc_test.py`, `arc_a25.py` (headless).
* A: the L with its own `sketch.fillet(point=, radius="Rn")` per
  corner, one inward, one left sharp: dof 0; live radius and size
  changes 3-12 ms, right.
* A, the trap: when an edge is too short for its two radii (`A` 2.5
  or exactly 3 = 1 + 2), the change reports no error and the
  parameter takes the value, but the solid silently goes back to the
  sketch as first built (A = 6 there, A = 10 in the first run), not
  to the last good state.  A later good value (`A = 7`) recovers.
  Our `update()` must refuse these; SolidCraft never tells.
* `parameters.list` shows `used_by: []` for a parameter used only in
  point expressions, though it drives the sketch: the graph cannot be
  trusted to tell what is used.
* B: a box with a free (not tangent) arc top by
  `arc_center_point(center=["W / 2", "C"], start=, end=)`, center
  given (the user's #16 rule): joins the lines, dof 0, all changes
  right (C below, near, and the top's height changed).
* C: a lens of two arcs meeting at sharp corners (arc to arc): right,
  from nearly half circles (`D = 0.001`) to a 0.25 mm sliver.
* Boxes exact to 1e-4 mm; volumes from `component.properties` are
  approximate (1e-5 relative usually, 4e-3 on the sliver), so tests
  compare boxes or loose volumes.

## 2026-11-17: Experiment: limits (staircases, waves, sizes)

Scratchpad `limits_test.py`, `loose_ends.py` (headless).  Python
(`RoundedPolygon`) computes every point and arc center, each
coordinate its own SolidCraft parameter (`p3x`, `c3y`); a change sends
only the values that moved, as plain numbers; a change of structure
(segment kinds) rebuilds.
* Right (area within 1e-5, box exact) and 4-8 ms per change: a
  5-step staircase with inside arcs only; with inside and outside
  arcs; a wavy staircase of arcs only, centers flipping side to side
  (treads and risers used up); a saw tooth of 60/120 degree corners,
  all filleted; 0.01 mm steps; 1 m steps; a 270 degree arc and chord.
* Wavy <-> lines between arcs is a structure change: rebuilt, 25-40
  ms.  50 steps (204 segments): built in 1.3 s, a change 36 ms.
* Limit: one `parameters.change` takes at most about 500 values
  (500 ok, 510 refused: "too many parameter changes", nothing
  changed).  The 50-step `w, h` change (600 values) was refused.
* `arc_center_point` takes its radius from center and start; `end`
  only gives the angle (an end 0.1 mm off along the radius made the
  same half disk, no error).  An end off sideways is not tried.
* Expressions know `sqrt`, `sin(30 deg)`, `pi`, `atan`, `abs`, `^`,
  `min`, `1e-3` (an earlier probe that said otherwise was our bug:
  `parameters.list()` returns a dict with `parameters`).
* `RoundedPolygon.box` is a little big around arcs, as documented
  (`_box_around()`), so compare SolidCraft's box with the true one.
* Volumes from `component.properties` are tessellated: 0.12% low on
  0.01 mm steps.

## 2026-11-17: Experiment: holes, long runs, degenerate shapes, units

Scratchpad `deep_test.py`, `inch_probe.py` (headless; every point and
center its own parameter, as before).
* #28 holes in one sketch: right inside, either winding.  Two holes
  overlapping cut their union; one on top of the other cuts once;
  an island in a hole is solid again.  A hole touching the outline,
  crossing it, through its rounded corner, or wholly outside is
  dropped silently (the outer alone, no error); moved back inside it
  cuts again.  So our model checks children (`_check_children()`).
* #29 100 random staircase edits (seed 17): all 90 good ones right,
  6.9 ms mean.  Each bad one (a corner thrown far off, edges
  crossing) reported "outline has no closed profiles" and an empty
  solid, and the next good edit recovered.
* #30 an arc of radius 1e3 over a 10 mm chord: right (sagitta
  0.0125).  Radius 1e6 (sagitta 1.25e-5 mm): drawn flat, top 5.0.
  Radius 1e9: refused "degenerate arc".  A 1e-7 mm line: taken;
  1e-10 refused "zero-length line".  So SolidCraft's tolerance is
  near 1e-6 to 1e-5 mm.  A full circle: `circle_center`, an arc with
  `start == end` (a full circle), or two half arcs: all right.
* #26b an arc end off sideways: up to 1e-6 mm snapped closed; 1e-3
  refused at the extrude ("no closed profiles").  Not silent.
* #31 inch design (`document.units(units="in")`): a parameter added
  as a bare number is in mm (`unit` mm), and points given as bare
  numbers are mm, but a bare extrude distance is inches.  So always
  send a unit (`"5 mm"`, `"(3 + 7/8) in"`, as `Length.solidcraft()`
  does).
* #32 two outlines in one sketch: two bodies' worth, right.  A
  staircase pocket cut 3 deep in a plate (`extrude(distance="-3",
  operation="cut", targets=["plate"])`): right; live changes 40 ms.
* #33 a visible window (`--control 8087`, raised by a KWin script,
  closed after): building is about 10x slower than headless (5 steps
  1.7 s, 204 segments 13.6 s: each command redraws), live changes
  stay fast (10-55 ms).  A rebuild over the 500 value limit took
  13.7 s.  Not tried: `engine.batch` for the build, which may cut the
  redraws.

## 2026-11-17: The user's answers; `scraftcam/outline.py` chunk 1 (#21)

* #34: our model catches the silent failures itself.  #35: builds in
  a window do not matter much; a `.step` is probably built anyway.
  #36: changes over 500 values go in chunks.  #37: not needed.
  #16: arc centers are always given (constrained), as a rule.
  #17: `T.sdfm~2.5.2.1`'s `Details.md` is OK; `T.oacv~5.1.9.1`'s
  "does not say much of anything" (not yet acted on).
* `scraftcam/outline.py`: `Profile(name, outer, holes)` of
  `geometry.Loop`s in mm, checked in `__post_init__()`: closed (gap
  <= `TOUCH`), no segment under `MIN_LENGTH` 1e-6 mm, arc ends on
  their circle, no crossings, holes inside and not touching the outer
  loop, holes apart and not nested (islands not yet).  `structure()`
  (`l`/`a` per loop), `values(prefix)` (`PREFIX__l0__p3x` points,
  `__c3x` centers, `"5.0 mm"`, rounded to 12 decimals so float noise
  is not resent), `sketch(solidcraft, prefix)`; `add_parameters()`,
  `send_changes(old, new, limit=500)` (only moved values, in chunks).
* `geometry.check_crossings(name, segments)`: the crossing check moved
  out of `RoundedPolygon._check_crossings()` to be shared.
* `tests/test_outline.py` (8 tests, 0.4 s, one headless SolidCraft);
  `test_geometry` (94) still passes; checkers clean.
* Not yet: `SolidCraftLink` using `Profile`; a `SolidModel` whose
  `build()` draws a `Profile`; islands in holes; the SVG from a
  `Profile`.

## 2026-11-17: #39 a `SolidModel` drawn from a `Profile`; #41 units

* The user: #39 before #38 (SVG), in ~3 minute chunks.  #40 islands
  wait (moving a tool between an island's gaps is the hard part).
  #17 `T.oacv~5.1.9.1` left as it is.  #41 mixed units are a must;
  1 in is exactly 25.4 mm; users must see their own units in errors.
* `SolidModel.solidcraft_values(name)` (`model.py`): every SolidCraft
  parameter `build()` makes, as expressions; by default each `Length`
  parameter and result (`NAME__PATH`).  `SolidCraftLink` now keeps
  `LinkedModel.values` (was `lengths`) and `send()` rebuilds when a
  `shape` field changes or the names change (a `Profile` with more
  segments), else sends the moved values by
  `outline.send_changes()` (chunks of 500).
* `Profile.unit` (default `mm`): messages give lengths in it
  (`_shown()`); `geometry.check_crossings(..., per_unit=,
  shown_unit=)` likewise.
* `scraftcam/tooling/parallel.py` `Parallel(SolidModel)`: inches, the
  1 in parallel of `tools.PARALLELS` by default (6 x 1 x 1/8 in, two
  1/2 in holes 3 in apart); fields `hole_count` (any number, 0 for
  none), `hole_spacing`, `hole_diameter`; result `side`, a `Profile`
  on YZ (rectangle, each hole one full-circle arc), its points as
  `NAME__side__l1__c0x`; `build()` sketches on YZ at
  `-NAME__half_thickness` and extrudes `NAME__thickness`.  Checks
  read in the user's units ("3 holes 3 in apart need 6-1/2 in of a
  6 in parallel").  `python3 -m scraftcam.tooling.parallel headless`.
* `tests/test_parallel.py` (3: side, refusals, a link run headless:
  longer -> `changed`, a third hole -> `rebuilt`); with
  `test_outline`, `test_solidcraft_link`, `test_jaw_plate`,
  `test_model`, `test_geometry`: 129 pass; checkers clean.
* Next: #38, SVG from a `Profile`.

## 2026-11-17: Where things stand (before `git commit` and `/clear`)

Answers: #38 SVG from a `Profile`: agreed, next, in ~3 minute chunks.
#42: both light and dark.  #43 (where dimension letters come from):
no answer yet; a GUI for making parametric RoundedPolygons is needed
some day, now `T.prg~5.1.9.2` (Open).  #44: no window demo of the
parallel needed.  #45: the old `tools.Parallel` (mounts, shop files)
is not moved to the new one until the GUI is debugged.

Next: #38, `Profile` to SVG (lines and arcs as path commands, holes
cut by the fill rule, light and dark), tried on `Parallel().side`.
The scratchpad scripts are gone with the session; every finding is
above.  Item numbers are sticky up to #45.
