# LLM Agent Context Log

## 2026-11-15: Created and opened

Created by the user's request from the end of `T.cm~5.1.10`
(suspended); `Details.md` holds the ideas (one place per kind; a
parametric model or a STEP file; assemblies and parts, meaning not yet
settled) and the user's 12 steps to add a tool.  First case: the Shars
Z setter, `scraftcam/tooling/setters.py` `z_setter(imperial)`.
Nothing coded yet.

## 2026-11-15: Idea 1 designed in `T.cmt~5.3`

The model library (plain editable dataclasses, field metadata with
units from which the schema, reader, GUI fields and docs come,
native-unit `Length`, `Placement` with quaternion `Rotation`) is
designed in `T.cmt~5.3`'s `Context.md`; coding starts there with
`scraftcam/model.py`.

## 2026-11-16: Live parameters for models (`T.cmt~5.3`)

Models will subclass `SolidModel`, and their parameters will reach
SolidCraft as live parameters (a GUI edit rebuilds in milliseconds);
step 11 ("See it in SolidCraft from its panel") builds on that.  See
`T.cmt~5.3`'s `Context.md`.

## 2026-11-16: First `SolidModel`

`scraftcam/model.py` (`SolidModel`, `meta()`, `Length`, ...) and
the first model on it, `scraftcam/tooling/jaw_plate.py` `JawPlate`
(live SolidCraft parameters), are in; see `T.cmt~5.3`'s
`Context.md`.  Field metadata (`meta()`) is idea 1's "one place per
kind" start.

## 2026-11-16: `SolidCraftLink`

`scraftcam/solidcraft_link.py` keeps models built in a SolidCraft up
to date (numbered names, one component each, edits as parameter
changes, rebuilds on `shape` fields, placements); step 11 ("See it in
SolidCraft from its panel") will call its `send()`.  See `T.cmt~5.3`.
