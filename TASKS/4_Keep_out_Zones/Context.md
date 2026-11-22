# LLM Agent Context Log

Squeezed 2026-11-22: what is in force, in today's names (the `SC`
prefix and the old file names are gone since `T.rd~5.1`); the full
history is in `hg` and `git`.

## The User's Decisions

* 2.5D: a line never has Z with X or Y, except ramps.  Only code we
  generate is checked.  A canned cycle is `G0 X Y`, the cycle with no
  X or Y, then `G80`.
* Cutters are vertical cylinders reaching up forever, at their widest
  radius (`machine.py` `widest_radius()`).  The tool holder's zone
  comes much later.
* All comparisons are in XY; Z belongs to the layers.  Grow each zone
  by R + e (`SLOP`, 1e-4) and track only the tip; ramps and helixes
  are lines and arcs in XY tested over their Z range.  Only exterior
  contours: false alarms possible, misses not; exactly touching a
  grown zone reads as entering.
* Rapids belong at Zsafe; rising rapids are always OK; a drill may
  rapid down to Ztop; `G83` is exempt (it rapids back into its hole).
* Every violation is reported with its G-code line and zone.
* MDI: a line moving Z with X or Y is rejected; the operator splits it.
* Work origin: the center of the material's top for now
  (`setups.py` `PlacedWork.work_origin()`).  Turned parts:
  `gcode.py` `CNC.remap(turns, dx, dy)`.
* Keep-outs of a vise (#368, from `T.rps~6.6`): (1) the base bolted
  to the table, (2) the fixed jaw with its jaw plate, (3) the movable
  jaw with its jaw plate, which moves with the gap, as does the
  parallel against it (#359a).
* No optional units (#354).
* Question 5 (finished features as keep-outs on a later setup): let
  slide; do not press it.

## Code Today

* `scraftcam/geometry.py` `RoundedPolygon` (the old, unitless class:
  `z_start`, `z_end`, `children`; `circle()`, `enters()`, `leaves()`,
  `grown()`, `shrunk()`, `hits(move, z, radius)`, `overlaps()`).
* `scraftcam/keepout.py`: `prism_zone()`, `cylinder_zone()`,
  `work_zones()`, `assembly_zones()`, `arc_segments()`,
  `check_program()`, `report()`; kinds `keep out`, `rapid`,
  `unchecked`.  Examples in `examples/setup/`.
* The HMI checks jogs and MDI lines (`hmi/hmi_machine.py`
  `jog_hit()`, `mdi_segments()`; `test_hmi_jog_keepouts`,
  `test_hmi_mdi_keepouts`).
* New (`T.rps~6.6`): `scraftcam/solid.py` (`SolidRoundedPolygon`, a
  tree of `Layer(polygon, dx, dy, z, children, angle=, center=)`;
  `SolidAssembly` of `Placed(solid, placement, appearance)`, flattened
  by `leaves()` into `Leaf`s with composed `Placement`s), the vise
  `tooling/kurt_vise.py` `kurt_dx6(gap)` (parts `vise_base`,
  `fixed_jaw`, `movable_jaw`) and `tooling/vise_setup.py`
  `vise_setup(gap)` (a parallel against each jaw).

## Insights and Traps

* Do not merge zones; overlapping ones are tested one at a time.
* A hole too small for the tool, or a notch closing as it grows, is a
  normal result.  Anything not understood is `unchecked`, so a clean
  report means everything was checked.
* The checker reads the finished `CNC.commands`, independent of how
  the path was made.  A nest of layers is a height field (no
  overhang).  A move across two touching holes is a false alarm.
* The guard is only as good as the work origin, tool length and vise
  position; say so on the screen; a tool inside a zone must be able
  to move back out.
* Old estimates (work Z, tooling plate top 0): jaws to -0.14,
  parallels to -0.375, vise base to -1.875, table to -4.515.

## What Is Left

* #374: build each zone from an assembly's leaves (a
  `SolidRoundedPolygon` placed by its `Placement`) rather than by
  hand.  Many leaves are turned (jaw plates and parallels stand up by
  120 deg about (1, 1, 1)), so a zone is a placed solid, not always a
  vertical prism.
* Move `keepout.py` and `demo.py` onto the new solids; then make the
  old class's `unit` required and fix its ~40 callers.
* Seeing it: violations in the tool path viewer, zones in SolidCraft.
* Nested depths in programs: `CNC` ignores layer heights.
* `tooling/mount.py` stacks: the same treatment.
* A program we did not generate is reported as unchecked.
