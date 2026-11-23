# LLM Agent Context Log

Squeezed 2026-11-22 (second time, before a `/clear`); the history is
in `hg` and `git`.  Issue numbers are shared with `T.oe~6.2`; the
next new one is #449.

## Ready

* `gui/outline_polygon.py`: `outline_polygon()`,
  `outline_revolved(outline, name)` -> `solid.SolidRevolved` (half
  profile about Z, tip at the origin, shank up +Z, tips cut flat,
  fillets as arcs); corners on a straight edge are left out of the
  solid (`_straight()`, #434).  Holes refused until `T.oe~6.2` #290.
* `scraftcam/solid.py` (`T.rps~6.6`): `RoundedPolygon`,
  `SolidRoundedPolygon` of `Layer`s, `SolidRevolved`, `SolidStep`,
  `SolidAssembly` of `Placed(solid, placement, appearance)`;
  `Rotation(x, y, z, w)`.  Used by `tooling/kurt_vise.py`,
  `vise_setup.py`, `parallel.py`.
* Outline files and the editor, built this session:
  * Formula letters (#430): `Letter.formula` (`HPA = PA / 2`), worked
    out exactly by `values.letter_values()` from letters given values
    only; `refresh_formulas()` fills their `default`; written as
    `formula =`; typed `= PA / 2` in the editor's Value cell.
  * `DIAMETER` dimensions (#437): from a corner's mirror image to the
    corner, X = `(D / 2)`; [Dim. Kind] on a revolved outline cycles
    horizontal, diameter, length, vertical (`next_kind()`).
  * `dimensions.placement_problem()` (#445, #448) under the letters
    table: a revolved tip off the origin, else floating corners;
    [Revolve] marks a corner drawn at the origin onto both axes.
  * Editor fixes: zoom about the wheel event's position (#439,
    Wayland gives no cursor position); renaming a letter renames its
    uses (#441, `rename()`); length dimensions honor `along` (#442);
    grid drawn in the cut view (#443); [Horizontal]/[Vertical] mean
    what is seen on a turned drawing (#444); hide strips keep to their
    corners on insert/delete (#446).
* Shop drills by letters (#435): `TableField.short` is the file key
  (values kept by the long `key`, so G-code etc. are unchanged);
  `shops.DRILL_LETTERS` = D, FL, OAL, PA; `kind = "drill"` names
  `drill.outline.toml` (#429).  `Shops.md`, the schemas and
  `Tool_Models.md` are regenerated from it.
* `tests/test_drill_outline.py` (#436): the outline drill matches
  `cutter_models.profile("drills", ...)` to 6 places for both example
  drills.  The old drill model may now go.

## The Old Models (to be replaced one at a time)

* `tooling/tools.py`, `tooling/cutter_models.model_tool()`,
  `tooling/tool_models.py` (`Tool_Models.md`, old one-meaning letters
  A, C, D, K, L, M, N, P, R, S, T, W), `model.py`,
  `solidcraft_link.py`, `tooling/jaw_plate.py`, `tooling/setters.py`.
* SolidCraft: send `"(3 + 7/8) in"`, never `"3-7/8 in"`; always a
  unit; a covered window is ~10x slower.

## Where It Stands

* The user is drawing `examples/shop/tools/shank_drill.outline.toml`
  from scratch in the editor (letters OAL, HPA, SL, FL, SR, DR; two
  hide strips; `turns = 1`), reporting bugs as found (#438).  Its tip
  is not yet on the origin and edges 2-3, 3-4, 5-6 are unmarked, so
  it has no real sizes yet.  Snapshot before strips: `hg` rev 1173.
* `examples/shop/tools/drill.outline.toml` is the reference drill
  (D, PA, HPA, FL, OAL), set to `turns = 0` and no hides for
  debugging (#440); put the turn and strips back once the editor
  works.  The editor saves every change: trying things on it
  overwrites it (restored once from rev 1164).  Checkpoint only the
  files changed (no `hg commit -A`).
* With hide strips the working view takes no clicks; edit in
  [Overview] (`O`).

## Open

* #433 decided, not built: shops found from a list of directories in
  `~/.scraftcam/settings.toml` (no environment variables); each
  shop's `tools/` holds its kinds' outline files, copied in by [New
  Shop] (#437.1: no fallback across shops); the example shop moves
  into the package (`scraftcam/shops/example_shop/`, found from
  `Path(__file__)`), `show_demo.py` fixed as we go.  (Claude gave
  #437 and #438 twice: #437 is both "kinds in each shop's `tools/`"
  and the diameter dimension; #438 both "the example shop in the
  package" and "the editor broken on the new drill".)
* #447: undo snapshots leave out holes (no hole button yet).
* LOC for end mills (#428), the next round tools after the drill.
* #387 whether `model.py`'s `SolidModel` and `SolidCraftLink` stay;
  #379 the grid plate's holes; `Tool_Models.md` from the outline
  files (`T.oe~6.2` #314).

Round tools first (end mill, drill, chamfer, corner rounding, double
angle, countersinks, Z setter); flat tools when `T.oe~6.2` #290
(holes) is done.  New tools from `Details.md` after.  The drill vise
waits for the user's measurements (#47).
