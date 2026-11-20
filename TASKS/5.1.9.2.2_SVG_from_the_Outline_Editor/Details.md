# 5.1.9.2.2 SVG from the Outline Editor

(Draft by Claude, 2026-11-19, from the user's request in
`T.prg~5.1.9.2` (#S5); the user's to revise.)

Make an SVG of an outline that resembles what the editor shows, so the
drawing a user makes in the editor is the diagram in the documentation
(`T.dtm~2.5.2`) and in the GUI's panels (`T.osiade~5.1.9`).

* What it shows: the same meaning as the screen (#61): the outline
  (fillets as true arcs, a revolved outline's mirrored half), the
  dimensions with their letters, the marks (`—`, `|`, the right
  angle's square), the hide strips cut out with break lines, and the
  note "All undimensioned fillets are radius UDF".  Not the editing
  aids: no grid, circles, selection, lighting or warning rings.
* Light and dark, as `gui/theme.py`.
* Where it is seen: the user leans to an [SVG] tab in the editor,
  redrawn when clicked (#189); written to a file beside the outline
  for documents.
* Related: `T.sdfm~2.5.2.1` (SVG diagrams of the parametric models,
  from a `Profile`).
* Questions to settle: drawn from the outline file alone (no Qt), or
  from what Qt paints (`QSvgGenerator`); the size and fonts; how
  letters and the table's names and help meet in a document.
