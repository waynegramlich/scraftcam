# LLM Agent Context Log

Squeezed 2026-11-22 (third time, before a `/clear`); the history is
in `hg` and `git`.  Issue numbers are shared with `T.oe~6.2`; the
next new one is #463.  Every discussion point takes the next sticky
number, never a fresh 1, 2, 3.

## Ready

* `gui/outline_polygon.py`: `outline_revolved(outline, name)` ->
  `solid.SolidRevolved` (half profile about Z, tip at the origin);
  corners on a straight edge (`_straight()`, #434) or repeating a
  neighbor (#450) are left out of the solid.  Holes refused until
  `T.oe~6.2` #290.
* `scraftcam/solid.py` (`T.rps~6.6`): `RoundedPolygon`,
  `SolidRoundedPolygon`, `SolidRevolved`, `SolidStep`,
  `SolidAssembly` of `Placed`; used by `tooling/kurt_vise.py`,
  `vise_setup.py`, `parallel.py`.
* Outline letters may be formulas (#430, `HPA = PA / 2`); `DIAMETER`
  dimensions on revolved outlines (#437; its circle placed and
  dragged across, #456); `placement_problem()` under the letters
  table (#445, #448).
* Kinds keyed by outline letters in the shop files
  (`TableField.short`; values kept by the long key, so G-code etc.
  are unchanged): drills `shops.DRILL_LETTERS` D, FL, OAL, PA (#435);
  end mills `END_MILL_LETTERS` D, LOC, OAL, SD (#452).  The tree's
  labels (`shops.long_keys()`) and the panel's fields
  (`gui/fields.py`, `short or key`) read them (#454).  `Shops.md`,
  the schemas and `Tool_Models.md` regenerated.
* Outline files `examples/shop/tools/drill.outline.toml` and
  `end_mill.outline.toml`; `tests/test_drill_outline.py` and
  `test_end_mill_outline.py` match the old `cutter_models` to 6
  places (both drills; the 3 square end mills, the rougher included).
* Marks (#451): never drawn in the SVG; in the editor only under
  [Show Marks (M)] on [View].  Still saved as letterless dimensions,
  but made by dragging: a corner snaps (6 px) to its neighbors' X or
  Y or onto an axis, never onto a neighbor (#455), and on release
  its marks are remade (`dimensions.snapped()`, editor `remark()`).
  While dragged, its own marks are left out of solving (`working()`,
  `dragged`).  The [Horizontal], [Vertical], [Right Angle] buttons
  are gone.

## Decided

* #449: roughing stays a flag on `end_mill`, same outline.
* #453: ball end mills become `ball_end_mill` (own file format and
  outline, drawn by the user); after #460, so files move once.
* #T7: the Z setter is flat (with small revolved parts), not
  revolved: with the flat tools.
* #457 (next to build): an outline file is a template, not one tool.
  (1) The editor never moves corners from values; nothing holds a
  corner.  (2) The template SVG is drawn as drawn (undo #299).  (3)
  The solver still finds floating corners; solids still come from
  values.  (4) Problems say when the defaults make edges cross.
  #461: per-tool SVGs to scale, later (true proportions, a standard
  width, values on the dimensions, `D = 1/4 in`).
* Shop layout (not built): a directory per object.  `shop/Shop.md`
  (generated, indexes everything); `shop/tools/KIND/` holds
  `KIND.outline.toml`, its `.svg` and `README.md` (the kind's page,
  listing its tools), and a sub-directory per tool (`tool.toml`,
  `drawing.svg`, `README.md`, catalog files from `T.c~6.3`).
  Relative links (`../README.md`) work on GitHub.  Changing kind
  moves the directory (`git mv`); `.step` tools under a generic kind.
  Open: #458 generated files committed (recommended), #459 pages
  named `README.md`, #460 the layout as an item of its own (under
  `T.g~6`, with #458, #459, #461, #433).
* #433: shops found from a list of directories in
  `~/.scraftcam/settings.toml` (no environment variables); the
  example shop moves into the package (`scraftcam/shops/example_shop/`,
  found from `Path(__file__)`), `show_demo.py` fixed as we go; no
  fallback across shops (#437.1).

## Where It Stands

* The plan (from the user): Claude translates each old model into an
  outline file and its test; the user tidies it in the editor (to
  find GUI bugs); the user draws the ball end mill from scratch.
* `end_mill.outline.toml` is as Claude wrote it (restored from `hg`
  after the user's try).
  The user's tidying waits for #457: today every corner is held by
  the values, so none can be moved.
* `shank_drill.outline.toml`: the user's drawing in progress (#438).
  `drill.outline.toml` has `turns = 0` and no hides (#440).
* The editor saves every change to its file: test on a copy;
  checkpoint only the files changed (no `hg commit -A`).

## The Old Models (to be replaced one at a time)

* `tooling/tools.py`, `tooling/cutter_models.model_tool()`,
  `tooling/tool_models.py`, `model.py`, `solidcraft_link.py`,
  `tooling/jaw_plate.py`, `tooling/setters.py`.
* SolidCraft: send `"(3 + 7/8) in"`, never `"3-7/8 in"`; always a
  unit; a covered window is ~10x slower.

## Open

* #447: undo snapshots leave out holes.  #387 whether `model.py`'s
  `SolidModel` and `SolidCraftLink` stay; #379 the grid plate's holes;
  `Tool_Models.md` from the outline files (`T.oe~6.2` #314).
* Round tools next: chamfer, corner rounding, double angle,
  countersinks; flat tools when `T.oe~6.2` #290 (holes) is done; new
  tools from `Details.md` after.  The drill vise waits for the
  user's measurements (#47).
