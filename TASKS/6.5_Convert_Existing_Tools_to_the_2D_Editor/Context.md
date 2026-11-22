# LLM Agent Context Log

## 2026-11-22: Opened

Opened by the user after `T.rps~6.6` closed, with the goal: most tool
bits made through the GUI (outline editor) into `solid.py` solids.

* Ready: `gui/outline_polygon.py` `outline_revolved(outline, name)`
  -> `solid.SolidRevolved` (half profile about the axis, tip at the
  origin, shank up +Z, tips cut flat, fillets as arcs); the example
  drill builds live (volume within 2e-3 of Pappus).
* Plan (Claude's suggestion, #390): round tools first (end mill,
  drill, chamfer, corner rounding, double angle, countersinks, Z
  setter); flat tools (parallel, jaw plate) need holes, so
  `T.sfoe~6.4` #290 is reopened when the first one is reached.
* Open: #391 one outline file per kind of tool (letters D, L, LOC,
  ...), each shop tool in `tools.toml` giving only its letter values,
  or one file per tool.  Each old model kept until the new one is
  checked against it (#37a).
* Issue numbers continue from `T.rps~6.6`: next new one #393.
