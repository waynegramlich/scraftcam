# LLM Agent Context Log

Made 2026-11-24 from `T.toasl~6.8` #660-#668; reopened 2026-11-25
by the user, whose own text is now `Details.md`.  Designed
2026-11-25 (#765-#791); #S1-#S4 built the same day (squeezed
2026-11-25 late; the chunk by chunk history is in `hg`, the
commits `52529b5`, `587c97a`, `56c63fd`, `c60b13d` and #S4's).
Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.

**Where we are (2026-11-27):** #S1-#S5 done (#S5 built 2026-11-27,
after the user's Kubuntu 26.04.1 upgrade; checkers clean, outline
tests pass; committed `d0d2771`).  #S6 under way (below).  Deferred: the ISO
chain line on cutting edges (#830, "fun to have"); a revolved
outline's mirror half is not hatched (#782).  The user is short of
weekly tokens: small chunks, timed with `date`.

## Built

* Outline files, format 6 (only 6 read, #773): `[[vertices]]`
  (`V1`, `V2`, ... in the order made, never reused, #787, #799),
  `[[polygons]]` (`name`, `role` a `Role` `StrEnum`, `vertices`;
  no `material` or `color`: refused, #840, #854).  Dimension ends,
  hide strips, angle edges (`"V2-V3"`) by name.  `Letter.polygon`,
  `Letter.internal` (#783b).
* Model and geometry by polygon (`gui/outline_file.py`:
  `Outline.loops()`, `edges()`, `sharing()`, ...;
  `dimensions.Edge`, `solve(..., loops)`); editor [New Polygon]
  (#772), shared corners not deleted or filleted (#777, #798),
  overlaps in red (#790), "Vertex:" rename (#795), [Show Names];
  Values table (`gui/outline_values.py`): [Dimensions], [Fillets],
  [Polygons] (Name, Role, Corners), a Scope column.  MCP: `Vertex
  V3`, `rename()`, `tab()`, `solid()`.
* `scraftcam/appearance.py`: `Color` (`R13% G32% B78% T40%`),
  `Hatch`/`HatchLines` (`A45 S2mm T0.25mm`, `+` a crosshatch; page
  lengths mm/in/pt), `STANDARD_HATCHES`, `material_look()`.
  Materials (stock and tool) have `color` and `hatch` fields; a name
  in both lists is refused (case-blind, #802).  HSS is
  `R16% G17% B19%` (black oxide, #822).
* Drawings are monochrome (#812, #820): a drawing is hatched only
  when drawn for a material (a tool's `material`, HSS by default,
  `ToolValues.material`, `tool_svg(outline, values, material)`,
  `tool_hatch()`); a bare outline is not.  `diagram.svg()` writes a
  `<pattern>` per `HatchLines`, turned within 45 degrees (Qt drops
  more, #815); hide strips clip hatched areas
  (`outline_cuts._clipped_area()`).  The editor hatches with Qt
  brushes (`hatch_style()`, fixed on screen, #810).  A shared edge
  is thin in drawings, thick in [Edit] (`outline_strokes(...,
  thin_shared=)`, #845, #851); the mirror draws each edge once.
* The drill (`example_shop/tools/drills/drill.outline.toml`): V6 on
  the axis at FL; `flutes` (cutting) V1 V2 V3 V6, `shank` (support)
  V6 V3 V4 V5.  The shank drill (in progress) is untouched.
* Solids (`gui/outline_polygon.py`): `outline_revolved(outline,
  name, *, color=)` is a `SolidRevolved` per polygon in a
  `SolidAssembly`, parts `NAME_POLYGON` (SolidCraft names take no
  `.`), cutting parts `CUTTING_TRANSPARENCY` 0.2 (#817, #826); flat
  outlines are still one polygon (#S5).  `outline_cacheable()` gives
  a `model_cache.Cacheable` keyed on shape alone (#837);
  `Cacheable.opacity_of`.  A headless session starts in hundredths
  of a second, so none is kept (#836 not needed).
* Viewer (`gui/solid_viewer.py`, `VIEWER`, port 8080): uses a
  SolidCraft answering or launches `solidcraft --control 8080`;
  `show(model)` inserts the cached `.step`, replaces a changed
  shape, hides the others (#832, #855); stopped at exit if started
  here (#844).  [Solid] (`OutlineEditor.solid_button`, any
  outline since #S5) -> `show_solid()`; a tool's solid is named after its file
  (`drill_15_64_in_hss_jobber_drill`); `prepare_solid()` builds in a
  background thread when a tool opens (#843).  Checked live over
  MCP (`exposed.client start FILE`, `call solid`).

* #S5 (2026-11-27): a flat outline is a tree.  `Polygon.parent`,
  `Polygon.z` (a formula; file keys `parent`, `z`, written only when
  set); `[[circles]]` (`Circle`: name, role, `center` vertex,
  `diameter` formula, parent, z, #789); `[[cuts]]` (`Cut`: capital
  letters, 3 vertices: ends, then a point on the side it looks
  toward, #776, #861).  The reader checks parents exist and do not
  loop; revolved outlines refuse parents, z, circles and cuts.
  `Outline.nested()` spares parent/child from the overlap warning;
  `solid_corners()` (polygons' corners, circles' centers): cut
  vertices need no dimensions (`real_corners(..., needed=)`, the
  editor's orange rings).  `outline_extruded()` /
  `outline_solid()` (`outline_polygon.py`) build `Layer` trees into
  `SolidRoundedPolygon` (several roots: an assembly); cached
  (`"outline_extruded"`).  `gui/outline_section.py` (no Qt): spans,
  material per slab, hatched section beside the plan ("SECTION
  A-A", turned to look toward the side point), cut line marks.
  Editor: [New Circle], [Cut Line] (Draw tab), [Polygons] tab
  columns Name, Role, Parent, Z, Corners / Diameter; deleting a
  center takes its circle (children move to its parent), a cut's
  vertex its cut; [Solid] on flat outlines too.  #862 formulas take
  inches (`1/2 in`; `in_` inside, `values._python()`).  Shipped
  `example_shop/tooling/vises/vise_block.outline.toml` (+ `.svg`):
  block, slot, two counterbored holes, cut A; its `.step` checked
  headless (17 faces).  Tests: `tests/qt/test_outline_tree.py`.
  The old `[[holes]]` remain, still refused by solids (#290).

* #S6 so far (2026-11-27): `gui/assembly_file.py` (no Qt):
  `KIND.assembly.toml` (`shops.ASSEMBLY_SUFFIX`, skipped by the
  shop reader), version 1: `[letters]` (exported, #783b) and
  `[[parts]]` (`Part`: name, `outline` relative to the file,
  `letters` = formulas in the assembly's, `on`, `at` a vertex of
  `on`'s outline, `face` a polygon/circle whose `z` it stands at,
  `turn`, `flip`).  Placed in order, no solver (#783c); revolved
  parent: drawing Y is Z.  `assembly_solid()`,
  `assembly_cacheable()` (via `outline_polygon.solid_cacheable()`,
  hashed on each leaf's shape and placement), `assembly_text()`,
  `used_by()`, `move_outline()` (moves the `.svg` too, rewrites the
  assemblies).  Tree `Kind.ASSEMBLY` ("Z setter assembly", first in
  its directory); a panel's own [Assembly] tab
  (`gui/assembly_panel.py` `AssemblyView`: parts table, [Solid]),
  `Panel.show_summary()` / `show_assembly()`.  Shipped
  `tooling/z_setters/`: `z_setter_block` (flat), `z_setter_plunger`
  (revolved, chamfered), `z_setter.assembly.toml`; its `.step`
  checked headless (block to 44.45, plunger top 50.8 mm).  Tests:
  `tests/qt/test_assembly_file.py`.
* #S6 left: [Move]/[Rename] buttons and "used by" in the GUI;
  keep-out polygons grown by the cutter radius (#783g); `offers`
  (#783l); `slide`/`turn` motions (#783d); `library:` root (#791);
  a `.step` part (#783f); the vise as an assembly; the setter's dial
  (a side-wall mate, Later).

## Decided, Not Yet Built

* #769b mates: [Alignment] on two points, a point and a vector;
  extruded on the face at its `z`, revolved along the axis.
  #783k frames: extruded XY is solid XY; revolved, drawing Y is Z.
* Assembly files (#783): a only when parts move, mix kinds, repeat
  or are a `.step`; c a tree of mates, no solver; d `slide`/`turn`;
  b parts' exported letters by formulas; e repeated parts named; f a
  vendor `.step` aligned by numbers; g keep-out polygons grown by
  the cutter radius; l nesting through `offers`; h
  `KIND/KIND.assembly.toml`, [Move]/[Rename] rewrite references;
  #791 a `library:` root.  The material of a part comes from its
  assembly entry (#840).

## Steps

* #S1-#S5 done.
* #S6 assembly files: mates, keep-out polygons, `offers`,
  [Move]/[Rename], "used by" (the Z setter, then the vise).

## Still Open

* #681/#690: `T.tfo~6.5` waits to convert each round tool (end
  mills, chamfer mills: split them like the drill).
* Not built: clicking a [Polygons] row does not light the polygon.
* Later: mates on side walls (the vise jaw); same-named letters in
  different polygons (not allowed now).
