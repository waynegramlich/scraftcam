# LLM Agent Context Log

Made 2026-11-22 from `T.tfo~6.5` #460; renamed from "Shop Directory
Layout" and opened 2026-11-24 (#627-#633), taking in `T.tkis~6.7`
(closed).  Squeezed 2026-11-24 late, after #S8 (the full history is
in `hg` and `git`: `023dfc7`, `c26ec49`, `eafdb79`, `6ffd104`,
`be44d88`, `7fa072c` and the #S8 commit).  Issue numbers are shared
by every task; the next is in `TASKS/Issue_Counter.md`.

**Where we are (2026-11-24 late):** Steps #694, #S1-#S3, #S5-#S8
done (#S4 dropped, #678).  Next: #726's declaration file (or a task
of its own); then `T.tfo~6.5` reopens for the other round tools
(#690, #727).  Round tool bits only for now; assemblies wait in
`T.sa~6.11` (Suspended, #734).  The user has
`scraftcam/example_shop/.allow_edits`.

## Open

* #715/#764: a stray traceback, `machine_panel.py:1683`
  (`HMI.show_drawing()`, `self.drawer.view.progress` empty), fired
  35 times by `poll()` during `test_outline_editor`, after
  `test_machine_panel`: a machine panel's timer outlives its test.
  Tests still pass.
* #753: [Allow Changes] (still on a tool's panel) can not be pressed
  over MCP.
* #762: 14 closed sets marked for a `StrEnum` (`grep -rn '(#762)'`),
  converted when a Step touches them (#763 is the rule, in
  `aicontexts/rule_sources/Python_Coding_Rules.md`, `R.pcr`).
  Other node-kind tests (`in (SHOP, FILE)`) are not checked by mypy.
* #703/#708 checkboxes and [Copy Marked] (possible since #S5); the
  LinuxCNC suite and `--show-demo` last run at #S1.

## Done 2026-11-24 late (GUI testing over MCP, #S8)

* #750/#751: a panel kept its outline editor for the same file, so
  a second drill showed the first's values and "Drill outline" after
  a drill stayed a tool's table; now per item (`Panel.outline_item`).
* #752/#760/#761: an outline item's text was Python's parse of its
  TOML; `tree.Kind` is a `StrEnum`, `item_text()` a `match` ending
  in `assert_never()` (mypy named the missing case first).
* #S8 (#754-#759): the editor's tabs `ViewTab` [Drawing] (cut out,
  look only), [SVG], [Edit] (overview, changes; letters table too);
  [Overview] gone; `set_read_only()` locks (greys [Edit], tooltip
  `LOCKED_MESSAGE`/`TOOL_MESSAGE`); a press while read only says
  why.  A new editor opens on [Edit]; a shop panel opens an outline
  on [Drawing], with no edit row (#758); a tool's [Outline] has the
  link "Edit the Drill outline" (`offer_outline()`,
  `Panel.open_path`, #757).  MCP `tab(editor, name)`; `state()`
  unchanged (recordings compare it).  `qt` 364, `fast` 417 pass.

## The Shop (decided and built)

* #433/#438 the example shop ships in the package,
  `scraftcam/example_shop/` (`shops.EXAMPLE_SHOP`, #716), read only
  (`shops.is_read_only()`, #699) unless a checkout holds
  `.allow_edits` (in both ignore files, never committed, #717).
* #433 `~/.scraftcam/settings.toml` (`settings.py`):
  `shop_directories` (searched like `PATH`), `last_shop` (#704,
  the shop shown at start; else the example shop).  #437.1 each
  shop has its own copies; nothing is looked up across shops.
* #697/#709/#710 [Copy Shop] copies the whole shop shown (leaving
  out `.allow_edits`) to a name in one of `shop_directories` or a
  typed path ("Other...", red unless usable); [New Shop] is gone.
* #693/#705/#718 no `--shop`: the GUI chooses; tests and the demo
  call `open_shop(shop, remember=False)` over MCP; a `--program` or
  `--hmi` machine waits for it (`window.WAITING`).
* #703/#708 (decided, not built): a second shop's tree shown read
  only under the open one, with checkboxes; [Copy Marked] copies
  the marked nodes into the open shop.

## The Layout (#711-#714, #744-#748; built)

```
SHOP_DIR/
  shop.toml  controllers/  machines/
  tools/             loose tools of kinds with no outline yet (#746)
    drills/          drill.outline.toml (+ .svg), shank_drill.outline.*
                     (#747), one TOOL.toml + TOOL.svg per drill
    end_mills/  chamfer_mills/
    materials/       tool materials: no outline, so no tools (#745)
  tooling/grid_plates/   (#748; tooling sits on the table, #714)
  stock/materials/       materials and cutting_data.toml (#744)
```

* #712 a kind's directory is one holding `KIND.outline.toml`; its
  name is free.  `shops.kind_directory()`; the reader reads
  `tools/*/*.toml` and `tooling/*/*.toml`.
* `shops.SHOP_DIRECTORIES` names `tools/materials`,
  `stock/materials`; the tree's `EXPLANATIONS` and
  `about_directory(path)` go by `tree.shop_relative()` (#749:
  falls back to the outline's kind, the kind above, then
  `EXPLANATIONS`).

## Outlines as Templates (#631; built in #S3, #S6)

* #720 `[letters.X] key = "diameter"` in the outline;
  `shops.outline_keys()` gives `DRILL_LETTERS`, `END_MILL_LETTERS`,
  `CHAMFER_MILL_LETTERS` from the example shop's outlines.
* #721 each tool is checked against its own shop's outline
  (`_Reader.outline_fields()`); `Shops.md` and the JSON schemas come
  from the example shop's.  #724 every default letter required, no
  defaults filled in; #722 a formula letter is refused; #723 a new
  letter is a field measured as its default (#723a any compatible
  unit); #729 a letter named like another field is refused.
* #726 the other fields stay in `shops.KINDS`; #727 kinds with no
  outline keep their fields in code until `T.tfo~6.5`.
  Known limit: a letter with no `key` is checked but not listed in
  `Shops.md` or the schemas (none yet).
* #S5 the tree shows outline files (`tree.OUTLINE`, first in their
  directory, "Drill outline"; `.svg` and hidden files hidden); a
  click opens the editor read only as a tool's [Outline] does; the
  panel title's tooltip is the path from the shop's top (#730-#733).
* #S6 a tool's [Outline] tab has one table, Letter, Name, Default,
  This tool (`ValuesTable.show_tool()`, was `LettersTable`); a value edit writes only
  the tool's file (#735, #736).  Tools are drawn in true
  proportions at the outline's scale, shrunk into its box only when
  bigger (`outline_editor.tool_drawing()`, `tool_svg()`); each
  tool's `.svg` beside it, `python3 -m scraftcam.gui.tool_svgs
  [SHOP]` rewrites a shop's, pairing each tool only with its own
  kind's outline (`kind_tools()`) (#737).
* `tests/qt/test_example_svgs.py` keeps every outline's and tool's
  `.svg` current (#739); the shank drill, a drawing in progress, is
  left out (`IN_PROGRESS`).  The drill's hide strips were laid over
  MCP (`outline_exposed.resize()`, #740, #741); #742 a letter in a
  strip's hidden stretch is flagged; #743 the upright cut view's
  pieces are trimmed (`draw_cut()`).  Letters can not be dragged
  over MCP yet (#559).

## Later (decided earlier, not yet built)

* #458 generated files are committed; #464 a generated
  `SHOP_DIR/README.md` indexing the shop, pages below named after
  their directory; #461 per-tool SVGs with values on the
  dimensions.
* #654/#659 catalogs stay in a directory each, chosen by the shop
  owner; a tool names its catalog, page and part number (`T.c~6.3`).
* Two ways to model a tool: an outline file, or a `.step` under a
  generic kind (`solid.SolidStep`).  #694 every `Solid` answers
  `solids()` and `leaves()`, so one-part and many-part tools are
  walked alike.
