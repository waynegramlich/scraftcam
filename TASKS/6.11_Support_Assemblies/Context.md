# LLM Agent Context Log

Made 2026-11-24 from `T.toasl~6.8` #660-#668; reopened 2026-11-25
by the user, whose own text is now `Details.md`.  Designed
2026-11-25 (#765-#791); #S1-#S4 built the same day (squeezed
2026-11-25 late; the chunk by chunk history is in `hg`, the
commits `52529b5`, `587c97a`, `56c63fd`, `c60b13d` and #S4's).
Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.

**Where we are (2026-11-25):** #S1-#S4 done.  Next: #S5 (extruded
trees, circles, cut lines, the section view).  Deferred: the ISO
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
  here (#844).  [Solid] (`OutlineEditor.solid_button`, revolved
  only) -> `show_solid()`; a tool's solid is named after its file
  (`drill_15_64_in_hss_jobber_drill`); `prepare_solid()` builds in a
  background thread when a tool opens (#843).  Checked live over
  MCP (`exposed.client start FILE`, `call solid`).

## Decided, Not Yet Built

* #766 extruded: each polygon names its parent and its `z` (a
  formula in letters); #789 holes and pegs are circle polygons, a
  counterbore two nested.  #790 a child lies wholly inside its
  parent.  #776 sections: a cut line is a 3-vertex item ([Cut
  Line], "Section A-A"), the section a second view, hatched; #782 a
  revolved outline is its own section.
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

* #S1-#S4 done.
* #S5 extruded trees, circles for holes and pegs, cut lines and the
  section view (a vise block).
* #S6 assembly files: mates, keep-out polygons, `offers`,
  [Move]/[Rename], "used by" (the Z setter, then the vise).

## Still Open

* #681/#690: `T.tfo~6.5` waits to convert each round tool (end
  mills, chamfer mills: split them like the drill).
* Not built: clicking a [Polygons] row does not light the polygon.
* Later: mates on side walls (the vise jaw); same-named letters in
  different polygons (not allowed now).
