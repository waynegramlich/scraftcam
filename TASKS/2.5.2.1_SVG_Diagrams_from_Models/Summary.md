# Summary of `T.sdfm` SVG Diagrams from Models

Merged into `T.sfoe~6.4` (the user, 2026-11-20, #259): both write SVG
from lines and arcs with dimensions, light and dark, and once
`T.tfo~6.5` moves every tool onto the outline editor, the outline
file is the main source; a `Profile` becomes a second input to the
same writer.  Done here: SolidCraft 2D solver experiments (their facts
now in `T.oe~6.2`'s `Context.md`), `scraftcam/outline.py` `Profile`
(checked lines, arcs and holes; `values()`, `sketch()`,
`send_changes()`), `geometry.check_crossings()`, and
`scraftcam/tooling/parallel.py` `Parallel` drawn from a `Profile`
(tests `test_outline`, `test_parallel`).  Not done: #38, `Profile` to
SVG, carried to `T.sfoe~6.4`.  A per-model `sketch()` method
(`T.ant~6.7` idea 1) is dropped as a task (#260).

Tags: `T.sfoe~6.4`, `T.oe~6.2`, `T.cmt~5.3`, `T.dtm~2.5.2`,
`T.ant~6.7`.
