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
