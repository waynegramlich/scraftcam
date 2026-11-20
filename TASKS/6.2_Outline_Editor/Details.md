# 6.2 Outline Editor

(Draft by Claude, 2026-11-17, from the user's #43 in `T.sdfm~2.5.2.1`;
the user's to revise.)

A GUI in which a user makes a parametric 2D outline (a
`RoundedPolygon`, or more generally a `Profile` of lines and arcs with
holes, `scraftcam/outline.py`) without writing Python, for their own
tools and parts.

* What it builds on: `T.sdfm~2.5.2.1`'s experiments (SolidCraft's 2D
  solver follows points and arc centers given as parameters; arc
  centers are always given) and `Profile`'s checks for what SolidCraft
  takes silently (crossings, holes touching the outline, arcs too big
  for their edges), with errors in the user's own units.
* Questions to settle: how a user names the dimensions (the letters on
  the diagram, #43, still open), how corners and radii are tied to
  them, how the outline is shown while edited (its SVG, light and
  dark), and how it is saved into the user's shop.
