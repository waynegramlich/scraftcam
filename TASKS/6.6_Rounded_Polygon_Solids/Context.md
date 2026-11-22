# LLM Agent Context Log

## 2026-11-22: Created and opened

Created at the user's request from `T.sfoe~6.4` (#342), after the
discussion of #260, #335, #337 recorded in its `Context.md`.

## Next (#341)

A Qt-free prototype, no GUI:
1. An immutable RP: `scraftcam/outline.py`'s `RoundedPolygon` without
   `z_start`, `z_end`, `children` (#S8); `flip()`, `rotate()`.
   `keepout.py` and `demo.py` use the old Z fields: keep the old
   class until they move to RPS.
2. The RPS tree `(RP, dx, dy, z, children)` and its build into
   SolidCraft (root extruded 0 to `z`; children from the parent's `z`
   to their own, adding or cutting).
3. The 202-1664 jaw as the first case, checked against `JawPlate`.

Related: `scraftcam/screws.py` (#328) will expand "a 1/2 in
counterbore here" into its two RPs; the outline file's `[[holes]]`
(version 4) stay a face view shorthand for now (#343).
