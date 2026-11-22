# Summary of `T.sfoe` SVG from the Outline Editor

Folded into `T.oe~6.2` on 2026-11-22 (`T.tfo~6.5` #393): the SVG
and the editor share one Qt-free drawing code, so they are one item.
Done: `scraftcam/diagram.py` and `gui/outline_diagram.py` draw the
outline, dimensions, marks, hide strips, holes and the fillet note as
on paper (sizes from the text height, Hershey lettering, always black
on white), written as `NAME.outline.svg` beside each outline; the
editor's [SVG] tab, [Rotate Diagram], [Font +]/[Font -], buttons in
tabs, letters dragged outside, movable marks; `scraftcam/screws.py`
and `[[holes]]` (outline file version 4).  The part vision (#260)
became `T.rps~6.6`.  Its open items (#290 holes in the editor and as
cutting layers, #314 the letters table) moved to `T.oe~6.2`.

Tags: `T.oe~6.2`, `T.rps~6.6`, `T.tfo~6.5`, `T.sdfm~2.5.2.1`.
