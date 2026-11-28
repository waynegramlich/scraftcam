# LLM Agent Context Log

Made 2026-11-22 from `T.tfo~6.5` #460; opened 2026-11-24
(#627-#633), taking in `T.tkis~6.7`.  Squeezed again 2026-11-27
(history in `hg` and `git`: `023dfc7` ... `7fa072c` and the #S8
commit).  Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.

**Where we are (2026-11-27):** #694, #S1-#S3, #S5-#S8 done (#S4
dropped, #678).  Next: #726's declaration file (or a task of its
own); then `T.tfo~6.5` reopens for the other round tools (#690,
#727).  What concerns polygons together (roles, trees, solids,
assemblies, mates) is in `T.sa~6.11` (reopened 2026-11-25, #858;
#S1-#S6 done 2026-11-27); this task keeps where a tool's facts
live and the outline as template.  The user has
`scraftcam/example_shop/.allow_edits`.

## Open

* #715/#764: a stray traceback at `machine_panel.py`
  (`HMI.show_drawing()`), fired by a machine panel's timer that
  outlives `test_machine_panel` into `test_outline_editor`; tests
  pass.
* #753: [Allow Changes] (a tool's panel) can not be pressed over MCP.
* #762: closed sets marked for a `StrEnum` (`grep -rn '(#762)'`),
  converted when a Step touches them (rule `R.pcr`).
* #703/#708 checkboxes and [Copy Marked]; the LinuxCNC suite and
  `--show-demo` last run at #S1.

## The Shop

* The example shop ships in the package, `scraftcam/example_shop/`
  (`shops.EXAMPLE_SHOP`), read only (`shops.is_read_only()`) unless
  a checkout holds `.allow_edits` (ignored, never committed, #717).
* `~/.scraftcam/settings.toml` (`settings.py`): `shop_directories`
  (like `PATH`), `last_shop` (#704).  Each shop has its own copies;
  nothing is looked up across shops (#437.1).
* [Copy Shop] copies the shop shown to one of `shop_directories` or
  a typed path (#697, #709, #710).  No `--shop`: tests and the demo
  call `open_shop(shop, remember=False)` over MCP (#693, #718).
* Decided, not built: a second shop's tree shown read only with
  checkboxes, [Copy Marked] into the open one (#703, #708).

## The Layout

```
SHOP_DIR/
  shop.toml  controllers/  machines/
  tools/           loose tools of kinds with no outline yet (#746)
    drills/        drill.outline.toml (+ .svg), shank_drill.outline.*,
                   one TOOL.toml + TOOL.svg per drill
    end_mills/  chamfer_mills/  materials/ (no outline, no tools)
  tooling/         grid_plates/, vises/, z_setters/ (outlines and
                   KIND.assembly.toml, `T.sa~6.11`)
  stock/materials/ materials and cutting_data.toml (#744)
```

* A kind's directory holds `KIND.outline.toml`; its name is free
  (#712, `shops.kind_directory()`).  The reader skips outline and
  assembly files.  `about_directory()` explains by
  `tree.shop_relative()` (#749).
* The tree shows outline files ("Drill outline", first, opened read
  only on [Drawing]) and assemblies ("Vise assembly"); the panel
  title's tooltip is the path from the shop's top (#730-#733).

## Outlines as Templates (#631)

* `[letters.X] key = "diameter"` names a tool field (#720);
  `shops.outline_keys()` gives the kinds' letters from the example
  shop's outlines.  Each tool is checked against its own shop's
  outline (#721): defaults required (#724), no formula letters
  (#722), new letters measured as their default (#723), no clash
  with other fields (#729).  #726 the other fields stay in
  `shops.KINDS`; #727 kinds with no outline keep fields in code.
* A tool's [Outline] tab: one table Letter, Name, Default, This
  tool (`ValuesTable.show_tool()`); an edit writes only the tool's
  file (#735, #736); a link "Edit the Drill outline" (#757).  The
  editor's tabs [Drawing], [SVG], [Edit] (#755-#759).
* Each tool's `.svg` beside it, true proportions at the outline's
  scale (`python3 -m scraftcam.gui.tool_svgs [SHOP]`, #737);
  `tests/qt/test_example_svgs.py` keeps them current (#739).

## Later (decided)

* #458 generated files committed; #464 a generated
  `SHOP_DIR/README.md`; #461 per-tool SVGs with values on the
  dimensions.  #654/#659 catalogs in a directory each; a tool names
  its catalog, page and part number (`T.c~6.3`).
