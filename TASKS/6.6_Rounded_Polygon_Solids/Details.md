# 6.6 Rounded Polygon Solids

(Draft by Claude, 2026-11-22, from the user's vision in
`T.sfoe~6.4` #260, #335, #337; the user's to revise.)

Parts are made from 2D outlines, so one file (the letters table plus
the editor's sketch) gives both the diagram (`.svg`) and the solid.

* **RP** (`RoundedPolygon`): a planar XY polygon of lines and
  fillets, with no Z, depth or children (`T.oe~6.2` #S8).  Immutable
  once made: an outline file is its recipe, and its letters' values
  make one RP.  `RP.flip(flip_line) -> RP` and `RP.rotate((x, y),
  angle) -> RP` make new ones.
* **RPS** (Rounded Polygon Solid, the equivalent of a `.step`): a
  tree of `(RP, dx, dy, z, children)`.  The root is placed from the
  origin (0, 0, 0) and extruded from 0 to its `z`; each child is
  placed by (dx, dy) from its parent and spans from its parent's `z`
  to its own: higher adds material, lower cuts it away.  `z` is
  absolute, so equal `z` means a matching level (exact `Fraction`
  lengths).  An RP may be used more than once.
* **Assembly**: RPSs (or `.step` files), each placed by a position
  (X, Y, Z) and a rotation (quaternion w, i, j, k; `model.py`'s
  `Placement`).

## First Case

Shars 202-1664, a 6 in reversible vise jaw
(`SharsMD/page_316/page_316.md:60`: L 6, W 1, H 2, D 3-7/8, E 1/2,
F 0.937 in): the plate `z = 1 in`; two counterbores (13/16 in,
`z = 0.47 in`), each with its clearance hole (17/32 in, `z = 0`) as
its child; checked against `JawPlate` in SolidCraft.

## Not Yet

* Building RPSs in the GUI (a tree of RPs); first in Python.
