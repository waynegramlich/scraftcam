# LLM Agent Context Log

Squeezed 2026-11-19: only what is in force and where things stand;
the full history (scratchpad experiments) is in `hg` and `git`.

## SolidCraft's 2D Solver (experiments, 2026-11-17)

* Good: closed polylines, per-corner fillets, free arcs with given
  centers (#16: arc centers are always given), arc to arc, holes, two
  outlines in one sketch, pockets cut into a plate; 204 segments
  built in 1.3 s, changes 1-55 ms; areas exact, boxes to 1e-4 mm.
  Driving each point and arc center as its own parameter (Python
  computes them) matches dimensioned sketches exactly.
* Taken silently, so our model must refuse them first (#34):
  self-crossing outlines (every region filled); holes touching,
  crossing or outside the outline (dropped); an edge too short for
  its two fillets (the solid goes back to the first build); a fillet
  radius using up an edge, then the extrude fails ("no closed
  profiles").  `R = 0` and over-half radii are refused, so sharp <->
  rounded is a rebuild.
* Limits: one `parameters.change` takes at most about 500 values
  (changes go in chunks, #36); tolerance near 1e-6 mm (1e-10 lines
  and 1e9 radii refused); `arc_center_point` takes its radius from
  center and start.
* Inches: bare parameter and point numbers are mm, a bare extrude
  distance is inches, so always send a unit (#31).
* Volumes from `component.properties` are tessellated (compare boxes
  or loose volumes); `parameters.list()` shows `used_by: []` for
  parameters used only in point expressions.
* `sketch.export_dxf(sketch=)` gives LINE and ARC entities, mm, no
  dimensions; no SVG export.  A visible window builds ~10x slower
  (#35: does not matter much).

## Code Today

* `scraftcam/outline.py` `Profile(name, outer, holes, unit)` of
  `geometry.Loop`s, checked in `__post_init__()` (closed, no segment
  under `MIN_LENGTH` 1e-6 mm, arcs on their circles, no crossings,
  holes inside, apart, not nested; islands wait, #40); messages in
  the user's units (#41).  `structure()`, `values(prefix)`
  (`PREFIX__l0__p3x`, rounded to 12 decimals), `sketch()`,
  `add_parameters()`, `send_changes(old, new, limit=500)`.
* `geometry.check_crossings(name, segments, per_unit=, shown_unit=)`
  shared with `RoundedPolygon`.
* `SolidModel.solidcraft_values()`; `SolidCraftLink` rebuilds when a
  `shape` field changes or the names change (`T.cmt~5.3`).
* `scraftcam/tooling/parallel.py` `Parallel` (side a `Profile` on
  YZ); `python3 -m scraftcam.tooling.parallel headless`.
* Tests: `test_outline` (8), `test_parallel` (3).

## Decisions and Next

* #42 diagrams light and dark.  #43 where dimension letters come
  from: being answered by the outline editor (`T.oe~6.2`).
* #45 the old `tools.Parallel` is not replaced until the GUI is
  debugged.
* Next: #38, `Profile` to SVG (lines and arcs as path commands, holes
  by the fill rule, light and dark), tried on `Parallel().side`.
  Numbers sticky up to #45.
