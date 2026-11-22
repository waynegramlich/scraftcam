# LLM Agent Context Log

## 2026-11-05: Two names for one material (from `T.hs~5.1.5` #37)

The demo's setup comments name the part's material `"6061 aluminum"`
(the shop's name) and the stock's `aluminum_6061` (the short name this
task plans, which the shop does not know).  The HMI takes whichever
the shop knows.  The user expects swapping designs between shops to be
messy here, and put it off until this task.

## 2026-11-22: Stock taken in from `T.sm~2.4`

`../Fab/` (2022, FreeCAD): `FabStock` (`FabSolids.py`) gives stock in
X/Y increments and a list of standard thicknesses, plus a minimum cut
on the outside; `enclose()` picks the stock for a part's bounding
box.  `FabMount` gives a work plane per setup (orientation and CNC
origin) for re-fixturing.  Stock today is a plain block
(`setups.py`, `assembly.SCStock`).
