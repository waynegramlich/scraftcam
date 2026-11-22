# LLM Agent Context Log

Squeezed 2026-11-22 at closing: what was built and decided; the
history is in `hg` and `git`.  Issue numbers were shared with
`T.sfoe~6.4` (next new one #390).

## Decided with the User

* `Solid` base class; subclasses `SolidStep` (one `.step` file),
  `SolidRoundedPolygon` (RPS), `SolidRevolved` (round tools, #339),
  `SolidAssembly` (an assembly is a solid, so they nest, #347).
* An assembly is a sequence of `Placed(solid, placement, appearance)`:
  rotate the child about its own origin, then move it (#348, #350).
  `Rotation(x, y, z, w)` (ROS and SciPy order, #349); `xyzw()` and
  `wxyz()` on `Rotation` and `Placement`.
* One solid placed many times is one SolidCraft component with
  several occurrences (#351); the nesting is kept in SolidCraft's tree
  so users can hide parts (#364, "good SolidCraft citizens").
* SolidCraft colors whole components, so one color per solid (#365);
  `Appearance(r, g, b, t)`, `t` sent as `opacity = 1 - t` (#358, #353).
* A `SolidModel` produces a `Solid`, it is not one (#352); the vise
  needs no `SolidModel` (#371: moved only in setup).
* No optional units (#354): the old `geometry.RoundedPolygon` stays
  unitless; `solid.in_unit()` hands it numbers in one unit and marks
  its messages `(lengths in in)`.
* The vise is symmetric about the plane across its jaws and is drawn
  as a half with a dashed mirror, like the drill (#366);
  `RoundedPolygon.mirrored()` mirrors about the Y axis as the editor's
  [Revolve] does (#373).
* Keep-outs of a vise: base, fixed jaw, movable jaw (#368); the
  movable jaw, its jaw plate and the parallel against it move with
  the gap (#359a).  Parallels stand flat against the jaws, a tooling
  plate on top (#370, #380).
* The user's view (#387): SolidCraft is a solid modeling engine and a
  renderer; the 2D models come from the GUI.  Live SolidCraft
  parameters (`SolidCraftLink`) are kept for now but are not expected
  to last; `gui/outline_solid.py` (letters as design-wide parameters)
  was deleted, replaced by `SolidRevolved`.

## Code

* `scraftcam/solid.py`: `check_name()`, `Appearance`, `Solid`,
  `SolidStep` (`insert()`: the insert is its own component),
  `RoundedPolygon` (immutable, planar, mm corners plus `unit`;
  `flip()`, `rotate()`, `mirrored()`, `circle()`, `renamed()`,
  `draw()`), `in_unit()`, `Layer(polygon, dx, dy, z, children,
  angle=, center=)`, `Frame`, `SolidRoundedPolygon`, `flat_tips()`,
  `SolidRevolved` (tip at the origin, shank up +Z, #385), `Placed`,
  `Leaf`, `SolidAssembly` (`solids()`, `leaves()`, `colors()`,
  `build()`).
* `scraftcam/gui/outline_polygon.py`: `outline_polygon()`,
  `outline_revolved()`, `polygon_from_file()` (holes refused until
  `T.sfoe~6.4` #290).
* `scraftcam/tooling/kurt_vise.py` (`kurt_dx6(gap)`, Shars 202-1007's
  sizes; jaw blocks' lengths guessed), `vise_setup.py`
  (`vise_setup(gap)`: two parallels), `parallel.py` (`Parallel.solid`,
  every size a rebuild).
* `Profile` (`outline.py`) removed (#383); `send_changes()` lives in
  `solidcraft_link.py`.
* Tests: `test_solid`, `test_outline_polygon`, `test_kurt_vise`,
  `test_vise_setup`, `test_parallel`, `test_model`,
  `test_solidcraft_link`, `test_diagram` (live ones skip without
  `solidcraft-cli`).

## Left for Other Tasks

* Keep-outs from the vise's parts, `keepout.py` and `demo.py` onto
  the new solids, the old class's `unit` made required: `T.ikz~4`.
* The editor's Mirror flag (#373a): `T.oe~6.2`.
* Holes as cutting layers (#290): `T.sfoe~6.4`.
* The tooling plate's grid of holes (#379): to be discussed.
