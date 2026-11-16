# LLM Agent Context Log

## 2026-11-15: Z-axis setter modeled (from `T.cm~5.1.10`)

The Shars magnetic Z-axis zero setter (303-3104, catalog page 414)
is `scraftcam/tooling/setters.py` `z_setter(imperial)`, from the
user's description; the user approved it in SolidCraft.  No shop
kind, keep-out, sketch or tests yet (see `T.cm~5.1.10`).

## 2026-11-15: How new tools get in: `T.ant~5.9`

Hooking a tool in (one place per kind, STEP files as an alternative)
is now `T.ant~5.9`; this task's tools wait on it.
