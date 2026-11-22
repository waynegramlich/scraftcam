# Summary of `T.cmt` Create More Tools

Closed 2026-11-22 (#395): its design, a library of editable
`SolidModel` dataclasses with live SolidCraft parameters, was
replaced by `T.rps~6.6`'s `scraftcam/solid.py` solids made from
outline files, and its next steps (child models placed by a parent;
the Kurt vise as an assembly) were done there as `SolidAssembly` and
`tooling/kurt_vise.py`.  Built here and still in use: `scraftcam/
model.py` (`Length`, `Angle`, `Rotation`, `Placement`, `SolidModel`,
`meta()`), `solidcraft_link.py` (`SolidCraftLink`), `tooling/
jaw_plate.py`, `tooling/setters.py` `z_setter()` (Shars 303-3104).
Whether `model.py` and `SolidCraftLink` stay (#387), the Shars list
of tools to make and moving `JawPlate` and `z_setter()` onto outlines
went to `T.tfo~6.5`; the drill vise waits for the user's
measurements (#47).  SolidCraft facts learned here are in `hg`.

Tags: `T.tfo~6.5`, `T.rps~6.6`, `T.tkis~6.7`.
