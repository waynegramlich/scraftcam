# LLM Agent Context Log

Made 2026-11-24 from `T.toasl~6.8` #660-#668; reopened 2026-11-25
by the user, whose own text is now `Details.md`.  Designed
2026-11-25 (#765-#791); #S1 (`52529b5`) and #S2 built the same day
(squeezed 2026-11-25; the chunk by chunk history is in `hg`).
Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.

**Where we are (2026-11-25):** #S1 and #S2 done.  Next: #S3; #S4
starts with the drill split (#800 (a)).

## Built (#S1, #S2)

* Outline files are format 6 (only 6 is read, #773):
  `[[vertices]]` (`name` `V1`, `V2`, ... in the order made, never
  reused, #787, #799), `[[polygons]]` (`name`, `role` a `Role`
  `StrEnum`, optional `material`, `vertices` by name).  Dimension
  ends, hide strips and angle edges (`"V2-V3"`, #797) by name.
  `Letter.polygon` / `Letter.internal` (`polygon = "..."`,
  `internal = true`, only when set); letter names unique in the
  whole outline.
* Model (`gui/outline_file.py`): `Outline.names`, `polygons`,
  `loops()`, `edges()`, `neighbours()`, `sharing()`,
  `reset_corners()`, `new_name()`, `new_polygon_name()`;
  `letter_scope_problems()` (#783b: a polygon letter measures only
  its polygon, formulas stay in scope, a `key` is never internal).
  `Dimension.start_to`/`end_to`: the corner an angle's edge reaches
  (-1 = the next in `points`; `Drawing.explicit_angles()` fills them
  before corners change).
* Geometry by polygon: `dimensions.Edge`, `Loops`, `ring_edges()`,
  `edges_at()`, `angle_edges()`; `solve(..., loops)` keys edge
  directions by directed `Edge`; marks, snapping, fillets, placing,
  `values.crossings()`/`overlaps()` (#790), `hides.inside_spans()`
  all take `loops`; strokes and fillets per polygon.
* Editor: `Drawing.insert(point, edge) -> int` appends; deleting a
  shared corner refused (#777), a fillet on one too (#798); edge
  handles carry both ends; `chosen_edges` is `list[Edge]`; [New
  Polygon] (#772, an equilateral triangle outside a chosen edge);
  overlaps said in red (#790); the [Draw] tab's "Vertex:" field
  renames a corner (#795); [Show Names] (#796).  The letters' table
  is the Values table, `ValuesTable` in `gui/outline_values.py`, the
  editor's `.values` (#802): tabs [Dimensions], [Fillets],
  [Polygons] (`PolygonsTable`: name, role, material, corners, #801);
  a "Scope" column (`outline`, `internal`, a polygon's name).
* MCP: targets `Vertex V3`, `Mirror V3`; `state()` by name;
  `rename(editor, name)` (#792).  `shops` never asks a tool for an
  internal or polygon letter.  `outline_polygon` refuses several
  polygons until #S4.
* Not built: clicking a [Polygons] row does not light the polygon.

## Outline Files (decided)

* #765 one outline file holds several polygons, named by the user
  (#767), each with a role (#767a).  #780 a file is revolved or
  extruded, not both.
* #787 one pool of named vertices; polygons may share them (#770:
  the flutes/shank split).  #790 polygons never partly overlap; a
  child lies wholly inside its parent, sharing no vertex.  Hide
  strips and keep-out polygons are exempt.
* #766 extruded: each polygon names its parent and its `z` (a
  formula in letters).  #789 holes and pegs are circle polygons;
  `Hole` becomes circles, a counterbore two nested ones.
* #783b2 a global letter is exported (the tool template #631, set
  by assemblies) or internal; polygon letters are internal; a
  dimension across polygons uses a global letter.
* #768/#779 colour and transparency: the material's, or chosen
  (`QColorDialog`, alpha).  #781 2D hatch from the material; one
  without gets its own; no two materials share a hatch in a drawing.
* #776/#776b sections: a cut line is a 3-vertex item (two the line,
  the third the view side); [Cut Line] on two points; named
  ("Section A-A"); the section is a second view, material hatched.
  #782 a revolved outline is its own section.
* #769b mates (Claude's proposal): [Alignment] on two points, a
  point and a vector, named.  Extruded: on the face at its polygon's
  `z`, facing up; revolved: from the axis, along it.  Mated: points
  meet, vectors align, faces press.
* #771 a `.step` is 1-to-1 with a `Solid` (colour in it); a
  two-polygon bit is one assembly `Solid`.  #784 [Solid] shows it in
  SolidCraft.  #783j cached by a hash.  #783k frames: extruded
  drawing XY is solid XY; revolved, the drawing's Y is solid Z.

## Assembly Files (decided, #783)

* a only when parts move, mix revolved and extruded, repeat, or are
  a `.step`.  c a tree of mates from one root, no solver.  d a mate
  may `slide` and `turn` (letters).  b an assembly sets its parts'
  exported letters by formulas.  e repeated parts are named entries
  (own letters, mate, colour).  f a vendor's `.step` aligns by
  numbers with units.  g keep-out zones are `keep_out` polygons,
  grown by the cutter radius in X/Y.  l assemblies nest through
  `offers` and exported letters.  h `KIND/KIND.assembly.toml`,
  parts beside or below; [Move]/[Rename] rewrite references.
* #791 shared parts: a named library root (`library:...`).

## Steps

* #S1, #S2 done (above).
* #S3 colours (material, `QColorDialog`) and hatches.
* #S4 the drill split into flutes and shank (#800 (a)); [Solid] and
  the `.step` (several polygons make an assembly), shown in
  SolidCraft, cached.
* #S5 extruded trees, circles for holes and pegs, cut lines and the
  section view (a vise block).
* #S6 assembly files: mates, keep-out polygons, `offers`,
  [Move]/[Rename], "used by" (the Z setter, then the vise).

## Still Open

* #681/#690: `T.tfo~6.5` waits to convert each round tool.
* Later: mates on side walls (the vise jaw); same-named letters in
  different polygons (not allowed now).
