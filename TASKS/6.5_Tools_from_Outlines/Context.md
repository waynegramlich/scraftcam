# LLM Agent Context Log

Squeezed 2026-11-22, after taking in `T.cmt~5.3` (closed) and
`T.tm~2.5` with its children (closed).  Issue numbers are shared with
`T.oe~6.2`; the next new one is #406.

## Ready

* `gui/outline_polygon.py`: `outline_polygon()`,
  `outline_revolved(outline, name)` -> `solid.SolidRevolved` (half
  profile about Z, tip at the origin, shank up +Z, tips cut flat,
  fillets as arcs); the example drill builds live (volume within
  2e-3 of Pappus).  Holes are refused until `T.oe~6.2` #290.
* `scraftcam/solid.py` (`T.rps~6.6`): `RoundedPolygon` (immutable,
  `flip()`, `rotate()`, `mirrored()`, `circle()`),
  `SolidRoundedPolygon` of `Layer`s (adding or cutting),
  `SolidRevolved`, `SolidStep`, `SolidAssembly` of `Placed(solid,
  placement, appearance)`; `Rotation(x, y, z, w)`; one color per
  solid.  `tooling/kurt_vise.py` `kurt_dx6(gap)`,
  `tooling/vise_setup.py`, `tooling/parallel.py` already use it.

## The Old Models (to be replaced one at a time)

* `tooling/tools.py` (Tormach tables, `SCMachineVise`, `SCJawPlate`,
  `SCParallel`, `SCGridPlate`, `SCDoubleEndCountersink`),
  `tooling/cutter_models.model_tool()` (every `TOOL_KINDS` kind in
  `examples/shop/tools.toml`, flute lines, banded holders, STEP
  cache `model_cache.py`), `tooling/tool_models.py` writing
  `Tool_Models.md` and `docs/tool_models/` (letters one meaning on
  every model: A angle, C cut, D diameter, K shank length, L length,
  M neck length, N neck diameter, P point angle, R radius, S shank,
  T tip, W width).
* From `T.cmt~5.3`: `model.py` (`Length`, `Angle`, `Placement`,
  `SolidModel`, `meta()`), `solidcraft_link.py`, `tooling/
  jaw_plate.py` `JawPlate`, `tooling/setters.py` `z_setter()` (Shars
  303-3104, approved; no shop kind, keep-out or tests).
* SolidCraft facts: send `"(3 + 7/8) in"`, never `"3-7/8 in"`;
  always a unit; a covered window is ~10x slower (raise it first).

## Plan

Round tools first (end mill, drill, chamfer, corner rounding, double
angle, countersinks, Z setter); flat tools (parallel, jaw plate) when
`T.oe~6.2` #290 (holes) is done.  New tools from `Details.md` after.
The drill vise waits for the user's measurements (#47).

## Open

* #391 one outline file per kind of tool (letters D, L, LOC, ...),
  each shop tool in `tools.toml` giving only its letter values, or
  one file per tool.  Claude leans to per kind; it is also
  `T.ant~6.7`'s idea 1.  Blocks `T.ant~6.7`.
* #387 whether `model.py`'s `SolidModel` and `SolidCraftLink` stay
  (the user expects live parameters to go).
* #379 the grid plate's holes: to be discussed.
* `Tool_Models.md` pages from the outline files' `.svg` and letters
  (`T.oe~6.2` #314).
