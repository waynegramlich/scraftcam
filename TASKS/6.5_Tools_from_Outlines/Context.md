# LLM Agent Context Log

Squeezed 2026-11-22 (fourth time, before a commit); the history is
in `hg` and `git`.  Issue numbers are shared with `T.oe~6.2` and
`T.sdl~6.8`; the next new one is #484.  Every discussion point takes
the next sticky number, never a fresh 1, 2, 3.

## Ready

* `gui/outline_polygon.py`: `outline_revolved(outline, name)` ->
  `solid.SolidRevolved` (half profile about Z, tip at the origin);
  corners on a straight edge (#434) or repeating a neighbor (#450)
  are left out.  Holes refused until `T.oe~6.2` #290.
* `scraftcam/solid.py`: `RoundedPolygon`, `SolidRoundedPolygon`,
  `SolidRevolved`, `SolidStep`, `SolidAssembly` of `Placed`; used by
  `tooling/kurt_vise.py`, `vise_setup.py`, `parallel.py`.
* Letters may be formulas (#430); `placement_problem()` under the
  letters table (#445, #448).
* Shop files keyed by outline letters (`TableField.short`; the long
  keys stay inside): drills D, FL, OAL, PA (#435); end mills D, LOC,
  OAL, SD (#452); tree labels and panel fields read them (#454).
* `drill.outline.toml`, `end_mill.outline.toml`; their tests match
  the old `cutter_models` to 6 places.
* Marks (#451): not in the SVG; in the editor under [Show Marks (M)];
  made by dragging (a corner snaps to its neighbors' X or Y or an
  axis, its marks remade on release, left out of solving while
  dragged).
* #457 (with #447): an outline file is a template.  Values set only
  `drawing.scale` (`apply_values()`); nothing holds a dragged corner;
  the SVG is drawn as drawn; `values.values_cross()` feeds the
  editor's `crossing_problem()`; undo keeps holes.  Solids still come
  from the values.
* Yellow circles on every vertex and segment (#469-#482):
  * A dimension: a middle circle on its line moves the line (#469);
    an end circle dropped on a corner moves that end
    (`OutlineView.tips`, `corner_near()`, #470); the letter drags by
    itself (#471).  None on extension lines (#472); a diameter is made
    with [Dimension] then [Dim. Kind] (#473).
  * A revolved outline's mirrored half: corner and edge circles
    (`mirror_squares`, `mirror_handles`, `mirrored=True`) act on the
    real half (#474-#477); `placing`, `moving` stop a twin's drag.
  * A mirrored corner is selected alone as `mirror_code(i)`
    (`real_point()` maps back); `dimension_codes()` stores only kinds
    the solver knows: corner + mirror is a diameter (#478).  A
    diameter's mirrored end has a circle; ends may drop on mirrors
    where the value is the same (#480).
  * A vertical dimension at `offset < 0` measures from the mirror
    images (#481); `outline_diagram.clear_foot()` leaves an extension
    line's gap where the outline leaves it (#482).

## Decided

* #449: roughing stays a flag on `end_mill`.  #453: ball end mills
  become `ball_end_mill` (the user draws it), after `T.sdl~6.8`.
  #T7: the Z setter is flat, with the flat tools.
* #387: delete `solidcraft_link.py` and `model.py`'s `SolidModel`
  (only tests and `jaw_plate.py`, `parallel.py` use them); `Length`,
  `Angle`, `Placement`, `Rotation` stay; `JawPlate`, `Parallel`
  become plain dataclasses.
* `T.oe~6.2` #314: `Tool_Models.md` from the outline files after the
  round tools.  #47: the user measures the drill vise after the
  current tools are modeled.

## Where It Stands

* `#S1` (#457, #469-#482) is done; the user is tidying
  `end_mill.outline.toml` in the editor.  Next: `#S2` #387, `#S3`
  #463 (the chamfer mill as an outline file and its test), `#S4`
  #426 (`T.g~6`: two end-to-end tests expect a separate Start
  button).
* The plan: Claude translates each old model into an outline file
  and its test; the user tidies it in the editor (finding GUI bugs).
* `shank_drill.outline.toml`: the user's drawing in progress (#438).
* The editor saves every change: test on a copy, outside
  `examples/shop/tools/` (the shop reader reads any `.toml` there
  not named `*.outline.toml`); checkpoint only named files.

## Open

* #483: end circles cover the arrowhead tips in the editor; draw the
  arrowheads over them (recommended).  #479: a horizontal across the
  axis (a mirror to another corner) needs the solver to add two X's.
* #379 the grid plate's holes.
* Round tools next: chamfer, corner rounding, double angle,
  countersinks; flat tools after `T.oe~6.2` #290 (holes); then the
  new tools in `Details.md`.

## The Old Models (to be replaced one at a time)

* `tooling/tools.py`, `tooling/cutter_models.model_tool()`,
  `tooling/tool_models.py`, `model.py`, `solidcraft_link.py`,
  `tooling/jaw_plate.py`, `tooling/setters.py`.
* SolidCraft: send `"(3 + 7/8) in"`, never `"3-7/8 in"`; always a
  unit; a covered window is ~10x slower.
