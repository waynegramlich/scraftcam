# Summary of `T.tm` Tool Models

3D models of tooling in SolidCraft (2026-10-30 to 2026-11-02),
closed for good 2026-11-22 (#402) with its children `T.ctfs~2.5.1`
and `T.dtm~2.5.2`: the way tools are modeled is now
`T.tfo~6.5`'s (outline files to `solid.py` solids).  Done then:
`tooling/tools.py` (Tormach mill tables, keep-out prisms and
cylinders, the Kurt style machine vise and jaw plate, parallels with
holes, the grid plate, double end countersinks from Shars page 24),
`tooling/cutter_models.model_tool()` (a plain revolved body, flute
lines, one component per tool), holders as banded cones in the
resistor color code, and the STEP cache (`model_cache.py`).
Left: the old `SCDrill` grooves and `SCDoubleEndCountersink`'s own
body, now to be replaced by outline files in `T.tfo~6.5`.

Tags: `T.tfo~6.5`, `T.ctfs~2.5.1`, `T.dtm~2.5.2`, `T.rps~6.6`.
