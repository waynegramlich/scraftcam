# LLM Agent Context Log

Made 2026-11-24 from `T.toasl~6.8` #660-#668; reopened 2026-11-25
by the user, whose own text is now `Details.md`.  Designed
2026-11-25 (#765-#791).  Squeezed 2026-11-27 after #S6; the full
history is in `hg` and `git` (`52529b5`, `587c97a`, `56c63fd`,
`c60b13d`, `4cc0fc3`, `d0d2771` #S5, `a98c394` and the #S6
commit).  Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.

**Where we are (2026-11-27):** #S1-#S6 done; checkers clean over
the package.  None of #S5/#S6's GUI has been tried on screen by the
user yet ([New Circle], [Cut Line], [Polygons] Parent/Z, the
[Assembly] tab, "Used by", the File field, [Solid] on flat outlines
and assemblies).  The user is short of weekly tokens: 10 minute
chunks, timed with `date`.

## Outline Files (format 6, only 6 read, #773)

* `[[vertices]]` (`V1`, ... in the order made, never reused,
  #787); dimension ends, hide strips, angle edges (`"V2-V3"`) by
  name.  `[[polygons]]`: `name`, `role` (`Role`: cutting, support,
  keep_out, other), `vertices`, and for a flat outline `parent`
  and `z` (a formula: extruded from the parent's `z`, 0 for a root,
  up adds, down cuts, #766; `offers`, #783l, was this, #865).
  `[[circles]]`: name, role, `center` vertex, `diameter`, parent,
  z (#789; a counterbore is two).  `[[cuts]]`: capital letters, 3
  vertices (ends, then the side it looks toward), no dimensions
  needed (#776, #861).  No `material`/`color` on polygons (#840).
  Revolved outlines refuse parent, z, circles, cuts.  Old
  `[[holes]]` remain, refused by solids (#290).
* Letters have scopes (`Letter.polygon`, `internal`); formulas take
  `deg`, `mm` and `in` (#862, `values._python()`).
* Editor: [New Polygon], [New Circle], [Cut Line]; shared corners
  not deleted or filleted; overlaps red (#790), a child not wholly
  inside its parent red (#868, `parent_problem()`); "Vertex:"
  rename; [Show Names]; Values table [Dimensions], [Fillets],
  [Polygons] (Name, Role, Parent, Z, Corners / Diameter).  Deleting
  a center takes its circle, a cut vertex its cut.  "Used by:"
  links to assemblies; the File field (in [Edit], inside a shop)
  moves or renames the outline, its `.svg` and users following
  (#783h).  MCP: `Vertex V3`, `rename()`, `tab()`, `solid()`.

## Drawings and Looks

* `scraftcam/appearance.py`: `Color` (`R13% G32% B78% T40%`),
  `Hatch` (`A45 S2mm T0.25mm`, `+` crosshatch), `STANDARD_HATCHES`,
  `material_look()`; materials have `color` and `hatch` (#802); HSS
  black oxide (#822).
* Drawings are monochrome (#812): hatched only for a material (a
  tool's, HSS by default); SVG `<pattern>`s turned within 45
  degrees (#815); hide strips clip hatches.  A shared edge thin in
  drawings, thick in [Edit] (#845).  Circles thick with a center
  mark.  Sections (`gui/outline_section.py`, no Qt): slab by slab
  along the cut, hatched, beside the plan, "SECTION A-A", turned to
  look toward the side point.

## Solids

* `gui/outline_polygon.py`: `outline_solid()` = `outline_revolved()`
  (a `SolidRevolved` per polygon, cutting parts 20% clear, #826) or
  `outline_extruded()` (`Layer` tree -> `SolidRoundedPolygon`,
  several roots an assembly).  `solid_cacheable()` hashes each
  leaf's shape and placement (`.step` parts by contents).
  `real_corners(..., needed=solid_corners())`: cut vertices free.
* Viewer `gui/solid_viewer.py` (`VIEWER`, port 8080): uses or starts
  SolidCraft, shows the cached `.step` alone (#832, #855), stops it
  at exit if started here (#844).  [Solid] on any outline and on an
  assembly's tab; `prepare_solid()` builds in the background.
* Shipped: the drill (flutes + shank); `tooling/vises/`
  (`vise_block` with slot, counterbores, cut A; `vise_jaw`,
  keep_out); `tooling/z_setters/` (`z_setter_block`,
  `z_setter_plunger`).  `.step`s checked headless.

## Assembly Files (#S6, `gui/assembly_file.py`, no Qt)

* `KIND.assembly.toml` (`shops.ASSEMBLY_SUFFIX`, skipped by the shop
  reader), version 1: `[letters]` (exported, #783b), `[[parts]]`:
  `name`, `outline` (beside the file, `library:PATH` in the example
  shop #791, or a `.step`, #783f), `letters` (formulas in the
  assembly's), `on` (an earlier part), `at` (its vertex), `face`
  (its shape whose `z` it stands at), `turn`, `flip`, `slide`
  (along its own X: motions, #783d).  Placed in order, no solver
  (#783c, #769b); revolved parent: drawing Y is Z (#783k).
* `assembly_solid()`, `assembly_cacheable()`, `assembly_text()`,
  `used_by()`, `move_outline()`, `keep_out_zones()` (#783g: placed
  `geometry.RoundedPolygon`s in mm; `keepout.py` grows them by the
  cutter radius).  Tree `Kind.ASSEMBLY`, panel [Assembly] tab
  (`gui/assembly_panel.py`).
* Shipped `z_setter.assembly.toml` (plunger on the block's top) and
  `vise.assembly.toml` (jaws on the slot's floor, the moving one
  `slide = "JT + OPEN"`).
* Tests: `tests/qt/test_outline_tree.py`, `test_assembly_file.py`.

## Not Yet Built

* An [Alignment] gesture for mates (#769b, two points or a point and
  a vector); mates on side walls (the setter's dial, a vise jaw's
  face); anything standing on a `.step` (aligned by numbers, #783f);
  a part's material from its assembly entry (#840: one colour for
  the whole assembly now); assembly zones fed to a setup's checks
  (`T.kz~4`); editing assemblies in the GUI (the tab is read only).
* Deferred: ISO chain line on cutting edges (#830); a revolved
  outline's mirror half not hatched (#782); clicking a [Polygons]
  row does not light the polygon; same-named letters in different
  polygons.
* #681/#690: `T.tfo~6.5` waits to convert the other round tools
  (end mills, chamfer mills) like the drill.
