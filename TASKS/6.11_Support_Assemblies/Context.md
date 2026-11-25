# LLM Agent Context Log

Made 2026-11-24 from `T.toasl~6.8` #660-#668; reopened 2026-11-25
by the user, whose own text is now `Details.md`.  Designed
2026-11-25 (#765-#791, the step by step answers are in `hg`).
Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.

**Where we are (2026-11-25):** every design issue settled; next is
#S1.  Nothing built yet.

## What Exists

* `scraftcam/solid.py` already has the extrude/cut tree
  (`SolidRoundedPolygon`, `Layer`: higher `z` adds, lower cuts;
  children inside the parent, siblings apart; touching allowed
  today, #790 forbids it), `SolidRevolved`, `Appearance` (r, g, b,
  t), `SolidAssembly`/`Placed`/`Placement` (nested assemblies walk),
  `SolidStep`, `RoundedPolygon.circle()`.  SolidCraft builds them
  and shows all 3D (it rotates; no arcball, #788).
* The outline editor is all one polygon (#787): `Outline.points`
  (`gui/outline_file.py`) is one list; dimensions, hide strips,
  fillets, `OutlineView.chosen_points` (clicked order; `ORIGIN`,
  mirrored as `MIRRORED - index`) point into it by index.  The file
  has `version`; `Hole` (#290) is round through holes, counterbored.

## Outline Files (decided)

* #765 one outline file holds several polygons, named by the user
  (#767), each with a role (#767a: cutting, support, keep_out,
  other; a `StrEnum`).  #780 a file is revolved or extruded, not
  both.
* #787 one pool of named vertices per file; polygons are lists of
  them and may share them (#770: the flutes/shank split is the
  shared vertices).  #790 polygons never partly overlap; a child
  lies wholly inside its parent and shares no vertex with it
  (touching an edge refused too).  Hide strips and keep-out
  polygons are exempt.
* #777 deleting a shared vertex is refused, naming the polygons.
* #772 [New Polygon]: two adjacent vertices of one polygon selected,
  makes an equilateral triangle on that edge, outside it, sharing
  the two.
* #766 extruded: each polygon names its parent and its `z` (a
  formula in letters).  #789 holes and pegs are circle polygons
  (centre, diameter) cutting down or extruding up; `Hole` becomes
  circles, a counterbore two nested ones.
* #783b letters: a global table plus one per polygon (seen only by
  its own vertices and dimensions); a polygon letter named like a
  global one is an error (#783b1).  #783b2 a global letter is
  exported (filled in by the shop's tool entries, the template
  #631, and set by assemblies) or internal; polygon letters are
  internal.  A dimension across polygons uses a global letter.
* #768/#779 colour and transparency: the polygon's material's, or
  chosen by hand (`QColorDialog`, alpha).  #781 2D hatch from the
  material; one without gets its own; no two materials share a
  hatch in one drawing.
* #776/#776b sections: a cut line is a special 3-vertex item (a
  triangle inside): two the line, the third the view side; [Cut
  Line] on two selected points, the arrows dragged, a click ends;
  named ("Section A-A"); dimensioned like vertices; several per file
  in time.  The section is a second view: material hatched, air
  blank.  #782 a revolved outline is its own section, no line.
* #773 the shipped outlines are converted once, no old reader;
  `version` kept.
* #769b mates (Claude's proposal; the user may change it): [Alignment]
  on two selected points: the alignment point and the alignment
  vector, named.  Extruded: on the face at its polygon's `z`, facing
  up (a pocket's floor); the root may flip to its bottom face.
  Revolved: from the axis, along it, out of a flat end (roll free).
  Mated: points meet, vectors align, faces press (normals opposed).
* #771 a `.step` is 1-to-1 with a `Solid`, colour and transparency
  in it; a two-polygon bit is one assembly `Solid`.  #784 [Solid]
  shows it in SolidCraft.  #783j cached by a hash of every
  character that affects it.  #783k frames: extruded drawing XY is
  solid XY, heights Z; revolved, the drawing's Y axis is solid Z.

## Assembly Files (decided, #783)

* a only when parts move, mix revolved and extruded, repeat, or are
  a `.step`; the drill stays one outline file.
* c a tree of mates, one root at the origin, each other part placed
  by exactly one mate to an earlier one; no solver.
* d a mate may `slide` (a letter, along the alignment vector) and
  `turn` (a letter, about the face normal): jaws, plungers,
  rotating vises.
* b an assembly sets its parts' exported letters by formulas in its
  own; unset ones take the part's defaults.  #673 is dropped.
* e repeated parts are named entries on the same file, each with its
  own letters, mate and (i) colour override.
* f a vendor's `.step` gets its alignment as numbers with units in
  its own coordinates; no letters (#663 changed).
* g keep-out zones are `keep_out` polygons in the part's outline
  (convex, circles give cylinders), riding with the part; grown by
  the cutter's radius in X/Y only, nothing more.  Never in the
  `.step`.
* l assemblies nest; an outer one uses only what an inner one
  `offers` (alignments) and its exported letters.
* h `KIND/KIND.assembly.toml`, parts beside or below it (seeing
  down, #660a); forward relative paths only; "used by" is computed
  by scanning, shown in the part's panel; GUI [Move]/[Rename]
  rewrite references; a dangling one is reported at shop load with
  file and entry.  The shop's tools of the kind in `KIND.toml`.
* #791 shared parts: a named library root (`library:...`, the
  shop's `parts/` and the package's), kept by a librarian; built
  when the first shared part appears.

## Steps

* #S1 the vertex pool alone: named vertices, still one polygon;
  dimensions, hide strips, fillets, mirrors, selection by name;
  shipped outlines converted; every test passes.
* #S2 several polygons: names, roles, materials, [New Polygon], the
  overlap check (#790), shared-vertex delete refused, letters per
  polygon and exported/internal; the drill split into flutes and
  shank.
* #S3 colours (material, `QColorDialog`) and hatches.
* #S4 [Solid] and the `.step`, shown in SolidCraft, cached.
* #S5 extruded trees, circles for holes and pegs, cut lines and the
  section view (a vise block).
* #S6 assembly files: mates with `slide`/`turn`, keep-out polygons,
  `offers`, [Move]/[Rename], "used by" (the Z setter, then the
  vise).

## Still Open

* #681/#690: `T.tfo~6.5` waits to convert each round tool.
* Later: mates on side walls (the vise jaw, if #769b's faces are not
  enough).

## The First Draft (2026-11-24; superseded where above differs)

Kept from it: #660a/#671 seeing down; #662 moving parts are
letters; #665 one letters table at the top is the template;
#666/#669/#672/#675/#677 keep-out zones are the user's design, the
cutter a point; #674/#676 the cached `.step`.  Changed: #660 (an
outline file holds several polygons), #670 (a one-file tool is an
outline file), #663 (`.step` alignment by numbers), #673 (dropped).
First cases then: the drill, the Shars magnetic Z setter 303-3104
(`scraftcam/tooling/setters.py`), the vise.
