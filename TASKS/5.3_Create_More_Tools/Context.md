# LLM Agent Context Log

Squeezed 2026-11-19: only what is in force and where things stand;
the full history is in `hg` and `git`.

## Purpose

5.3 is the excuse to build the library that lets people (and agents)
make parametric parts and assemblies in Python; it is also
`T.ant~5.9`'s idea 1 (one place per kind).  Documented here for now,
later in public `.md` files (`Models.md`, a page per model,
`T.dtm~2.5.2`).

## The Design in Force

* **Plain dataclasses** (`@dataclass(slots=True)`, editable).  Fields
  may be other models to any depth; a tool, like anything, is an
  assembly of parts (a `SolidModel` or a `.step`) in sub-assemblies
  (#71).  Each model is a SolidCraft component; a part is a leaf.
  Rules documented, not guarded.
* **Parameters and results**: `init=True` fields are parameters,
  `init=False` results computed by `update()`; `__post_init__()`
  calls it.  `update()` checks fields together (never per field).
* **Passes until stable**: a parent sets each child's parameters,
  calls its `update()`, reads its results; a child never reads its
  parent.  `settle(seconds=5.0)` repeats until every result moves
  less than 1e-9, else `NotSettledError` naming what still moves
  (`nan` counts as moving).  `build()` is separate.
* **Placement**: each model builds in its own coordinates; the parent
  places a child by a `Placement(translation, rotation)`.  Rotations
  are quaternions only (given as axis and angle in degrees); a 4x4
  matrix is made only at the call to SolidCraft (#45).
* **Units**: `Length` keeps the number as written (`Fraction`) and
  its unit (`in`, `ft`, `mm`, `m`); `Length(3, "in")` takes ints;
  each model sets its own unit (`SolidModel.UNIT`, #53), its results
  use it; composed translations are in mm.  1 in is exactly 25.4 mm.
* **Field metadata**: `meta(unit, label, help_text, shape=False)`,
  `unit` in `UNIT_KINDS` (`length`, `angle`, `count`, `text`,
  `flag`).  From it come the shop schema and reader, GUI fields, JSON
  schema, `Shops.md` and docs; parameters plus source make the cache
  key.  A `shape` field makes a new `build()`.
* **Names**: no `SC` prefix.  SolidCraft parameters by full path,
  `vise__jaw__width`; a model added to a design is numbered,
  `jaw_plate_001__width` (#59); never starting or ending with `_`.
  Users see only our names, never SolidCraft's (#21).
* **One way to SolidCraft** (#15, #22): `update()` settles, the moved
  values go out as one `parameters.change(changes=)` of plain values
  (never expressions: SolidCraft refuses cycles), sent when a GUI
  field is finished, never per keystroke (#28).  Users are told not
  to touch SolidCraft's Parameters panel.
* **Windows** (#35, #38): headless SolidCrafts as many as allowed
  (each about 240 MB); one visible design window unless the user
  turns on more; simulation windows separate, maybe one per machine.
  A window only when the user wants to see (#61).
* **Cache** (#20, #27): the live model is edited, others come from
  the cache, rebuilt in the background with a status bar estimating
  times.
* **Load limits** (#41, agreed): a pool runs headless SolidCrafts one
  at a time by default; Linux `nice -n 10 taskset -c CPUS
  solidcraft-cli mcp --headless ...` (half the cores); Windows
  `BELOW_NORMAL_PRIORITY_CLASS` plus `SetProcessAffinityMask` by
  `ctypes`; settings in `~/.scraftcam/`.  Not built.
* SolidCraft only for now; `build()` calls `PyBind` directly.

## SolidCraft Facts (from experiments)

* `parameters.add(name=, expression="2 in")`; values come back in
  mm; a bare number is in the design's unit.  Send `"(3 + 7/8) in"`,
  never `"3-7/8 in"` (read as 3 mm minus 7/8 in).
* Changes rebuild in 2-5 ms headless (window 90-140 ms); one call is
  all or nothing; unknown names and cycles are refused, but bad
  values are taken (a negative width loses the body), so our checks
  come first.
* Names: letters, digits, `_`; at most 64; case matters; units,
  constants and functions refused.  Parameters are one list for the
  whole design.
* Sketches: `sketch.dimension(entities=["origin", "c1.center"],
  type=...)`; `sketch.create(plane="YZ", offset="PARAM")` takes a
  parameter.
* Occurrences: `NAME:N`; the design's first is grounded
  (`occurrence.ground(..., grounded=False)` first); `occurrence.move
  (matrix=)` is row-major column vectors, relative (composes), rigid
  within 1e-9 (`tolerance` up to 1e-3); its returned `transform` is
  the transpose.  So the link sends quaternion deltas and corrects
  drift past `DRIFT` 1e-8 (#48).
* One design per process; several processes with their own
  `--control PORT` work.  Headless writes only in the project, its
  temporary folder and `allow_paths`.  `component.delete` takes the
  features; parameters are deleted by prefix.  A rebuilt occurrence
  is at identity, so its placement is sent whole.
* Window: the AppImage `../solidcraft/solidcraft-linux-x86_64.AppImage
  --control 8085`; raise it with a KWin script (`loadScript FILE
  NAME`, then `org.kde.kwin.Scripting.start`).

## Code Today

* `scraftcam/model.py`: `parse_number()`, `number_text()`, `Length`,
  `Angle`, `Rotation`, `Placement` (`compose()`, `inverse()`,
  `delta()`, `matrix()`), `SolidModel` (`settle()`, `results()`,
  `parameters()`, `parameter_fields()`, `build()`,
  `solidcraft_values()`), `meta()`, `NotSettledError`.
* `scraftcam/solidcraft_link.py` `SolidCraftLink`: `add(model, base,
  placement)` -> `BASE_NNN`, `send(name)` -> `unchanged`/`changed`/
  `rebuilt`, `place()`, `remove()`.
* `scraftcam/tooling/jaw_plate.py` `JawPlate` (inches, Kurt numbers;
  seen live by the user); `scraftcam/tooling/parallel.py` `Parallel`
  (drawn from a `Profile`, `T.sdfm~2.5.2.1`); the Z setter
  `tooling/setters.py` `z_setter(imperial)` (Shars 303-3104, approved;
  no shop kind, keep-out, sketch or tests).  Old `tools.JawPlate` and
  `tools.Parallel` stay until the GUI is debugged.
* Tests: `test_model`, `test_jaw_plate`, `test_solidcraft_link`,
  `test_parallel`.

## Next

#69 child models as SolidCraft sub-components placed by the parent's
`update()`, composed by `SolidCraftLink`; then the Kurt vise as an
assembly with its jaw plates (#66, the user says what they see); then
`z_setter()` and the old models one at a time.  Not yet: `Angle`
parameters sent, a GUI field calling `send()`.  The drill vise waits
for the user's measurements (#47).

## Rejected (do not bring back)

`attrs`; a `__setattr__` guard or frozen checks; lengths stored in
mm; one pass with no iteration; expressions sent to SolidCraft;
the base class names `Model`, `Model3D`.
