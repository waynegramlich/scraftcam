# LLM Agent Context Log

Made 2026-11-22 from `T.tfo~6.5` #460; renamed from "Shop Directory
Layout" and opened 2026-11-24 (#627-#633), taking in `T.tkis~6.7`
(closed).  Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.  The letters table is
`gui/outline_letters.LettersTable` (for #631, #S6).

**Where we are (2026-11-24 evening):** #694 and #S2 done; #S1 half
done (the example shop in the package, read only, `settings.py`),
committed to `git` by the user.  Next, the rest of #S1: the GUI
starts from `settings.start_shop()`, [Copy Shop] (#709, #710),
`open_shop()` over MCP and no `--shop` (#705, #707).  Then #S3.
Round tool bits only for now.  The user has
`scraftcam/example_shop/.allow_edits` (the GUI may edit the example
shop in this checkout).  Undecided, for later: #706 is gone (#711);
#703/#708 checkboxes wait for #S5; #715 (a stray traceback).

## Decided 2026-11-24

* #631 (the user): a kind's outline dimension table is the template
  for the fields of each tool's `.toml` (as #391 in `T.tkis~6.7`:
  one outline file per kind, each tool gives only its letter
  values); one table in the tool's panel (unifies #592/#594's two
  dimension views).
  Begun: `gui/values.set_letters()` puts a tool's values into its
  kind's letters and works out the formula letters (`T.gc~6.10`).
* #615 the tree shows outline files (`gui/tree.py:482` hides them,
  "Until #S7").
* From `T.tkis~6.7`: idea 1 began as `meta()` field metadata in
  `scraftcam/model.py` (`T.cmt~5.3`); a per-model `sketch()` was
  dropped (#260), the outline's `.svg` is the sketch.  Idea 2's
  STEP route exists (`solid.SolidStep`, `T.rps~6.6`).  The Z setter
  (`tooling/setters.py`) has no shop kind yet.

## Decided 2026-11-24 (late)

* #678 (the user): no assemblies; every tool is a single part.
  #S4 is dropped; what becomes of `T.sa~6.11` is #689.
* The user: round tool bits only, for now.  #689 settled: some
  tools are assemblies, so a simple `Solid` answers as one: #694
  (agreed) moves `leaves()` and `solids()` to the base `Solid`
  (`solid.py`), a plain solid being one leaf at the origin; #695
  (one-part wrappers) dropped for it.  `T.sa~6.11` waits.
* #696 (the user): the drill is the first round tool; the order is
  #694, then #S2 (the drill's outline directory in the package and
  the example shop's `drill.toml`), then #S1.  #690: `T.tfo~6.5`
  stays Suspended until after #S3.  #691 agreed: `settings.toml`
  has `shops = [...]` and `copy_to = "..."`; written by the first
  [New Shop] or [Copy to My Shops].
* #693 (the user's wish, being discussed): the shop is the only
  positional argument of `scraftcam.run` (no `--shop`); without
  it, the current directory.  #692 explained again.
* #692 (the user): #433 stands.  A user starts in an empty, read
  only example shop in the package, then copies it somewhere it can
  be changed.  Top 5 given: #693, #697-#700.
* Confirmed by the user (from `2026-11-22_12:56_scraftcam.md`
  lines 300-362): #433 `~/.scraftcam/settings.toml` lists
  directories holding shops, searched like `PATH` (#702: so no
  `copy_to`; #691's form is replaced).  #437.1 each shop has its
  own copies; nothing is looked up elsewhere (#701: wins over
  #653/#655's shipped-only outlines).  #438 the example shop ships
  in the package (PyPI; no Snaps or Dockers), read only by our
  software (Windows has no real read-only bit).  #700: one button,
  [New Shop], copies the example shop to a read/write shop.
* #697 (the user): no empty shops; [New Shop] copies the full
  example shop and the user deletes what they do not want.  #693
  (the user): choosing the shop on the command line is wrong; the
  GUI chooses, and imports from another shop.  Open: #703 what an
  import copies, #704 the shop shown at start, #705 `--shop`.
* #704 agreed: the last shop open, kept in `settings.toml`; with
  none, the example shop.  #703 (the user's idea): mark a node in
  the other shop's tree, "copy this node and its children"
  (needs #S5).  #705 (the user, asking): drop `--shop`, tests
  through MCP (`open_shop()` exposed)?  Claude: #706 a tool inside
  a shared `KIND.toml`; #707 tests must not touch the user's
  `settings.toml`.
* #705 agreed: no `--shop`; tests open shops through MCP
  (`open_shop()`), with a scratch `HOME` (#707).  #703 (the user):
  a checkbox after each node; with any checked, [Copy Marked]
  shows in the tree.  #708 (Claude): where the other shop's tree
  is shown, and the copy's target.
* #708 agreed: a second shop's tree shown read only under the open
  one, checkboxes only there; [Copy Marked] copies into the open
  shop.  No [Copy Shop] exists today: [New Shop] (`gui/window.py`
  action row, only while there is no shop) opens `NewShopDialog`.
  #709 (Claude): one [Copy Shop] copying the open shop, replacing
  [New Shop], in the panel (no dialog).
  The user: try it; which shop, and where to?  Claude's proposal:
  #709a the source is the shop whose tree the button is in;
  #709b the target is a name plus one of `shop_directories` (or a
  new directory, added to the list), checked as typed.
* #710 agreed (the user): "Other..." is a typed path, no file
  chooser; red unless the shop's directory is empty or can be made.
* #694 agreed again (the user): coding starts with it.  #711
  (Claude): with #437.1, the drill's outline directory for #S2 is
  in the example shop (`SHOP_DIR/outlines/drill/`), not
  `scraftcam/outlines/`.
* #711 (the user, replacing #653/#656's layout): `SHOP_DIR/` has
  `tools/`, `tooling/`, `stock/`; `tools/end_mills/` holds the
  kind's outline file and one `.toml` per tool (e.g.
  `1_4_in_end_mill.toml`), all of a kind in one directory.  So
  #706 goes (a tool is a file).  Open: #712 telling the outline
  file from the tools' files; #713 the shop's other directories.
* #712 agreed: `KIND.outline.toml` (and `.svg`) marks the kind;
  the directory's name is free.  #713 (the user): deeper trees,
  shorter names.  `controllers/`, `machines/` stay; `stock/` has
  `materials/`, `shapes/`; `tools/` has `materials/` and a
  directory per kind (`end_mills/`, `fly_cutters/`, ...).  Tooling
  (`vises/`, `vise_jaws/`, `toe_clamps/`): #714 top level or under
  `tools/`?  A kind directory is one holding an outline file.
* #714 (the user): `SHOP_DIR/tooling/` at the top: a tool goes in
  the spindle, tooling on the work surface (the Z setter is
  tooling; an edge finder a tool).

## Steps (revised 2026-11-24 late)

Order: #694, #S2, #S1, #S3, #S5, #S6, #S7 (#S4 dropped, #678).
* #694 done 2026-11-24: `solids()` and `leaves()` on the base
  `Solid` (`TestPlainSolid` in `tests/solidcraft/test_solid.py`).
* #S2 done 2026-11-24: `examples/shop/tools/drills/` (`git mv`):
  `drill.outline.toml`, `.svg`, both drills; `shops.ITEM_PATTERNS`
  reads `tools/*.toml` and `tools/*/*.toml`; `outline_of()` finds
  the outline beside the tool; `Shops.md` regenerated.
  `shank_drill.outline.toml` (no code uses it) stays in `tools/`.
* #715: one run of ten Qt test files printed a traceback from
  `hmi/machine_panel.py:1682` (`view.progress` empty) but passed;
  not seen again alone or at `HEAD`.
* #S1 begun 2026-11-24: `shops.EXAMPLE_SHOP` (and `_FILE`) is the
  one place naming the example shop, used by `setups`, `demo`,
  `hmi_machine`, `sim_linuxcnc`, `cutter_models` (its own
  `EXAMPLE_SHOP` is the file; tests still import it),
  `tool_models`, `drive_editor` and 18 tests.  `scraftcam/settings.py`
  (`Settings`, `read_settings()`, `write_settings()`,
  `find_shops()`, `start_shop()`; `tests/fast/test_settings.py`).
  Not wired into the GUI yet.  Left: the move (#716), read only
  (#699, #717), [Copy Shop], `open_shop()`, no `--shop`.
* #716 (Claude): `scraftcam/shops/` beside `shops.py` is confusing
  (a directory without `__init__.py` loses to the module); another
  name, e.g. `scraftcam/example_shop/`?  #717: with the example
  shop read only in the GUI, how do developers change it (#64)?
* #716 agreed: `scraftcam/example_shop/`.  #717 (the user): a
  marker file in both `.gitignore` and `.hgignore`, never a
  setting.  Claude: `scraftcam/example_shop/.allow_edits`; never
  committed, so never on PyPI; [Copy Shop] leaves it out.
* Done 2026-11-24 (#717:1-3 agreed): `git mv examples/shop
  scraftcam/example_shop` (`shops.EXAMPLE_SHOP`; docs, `Shops.md`,
  `Tool_Models.md`, `README.md` follow); `.allow_edits` in both
  ignore files; `shops.is_read_only(path, package=)` (#699): the
  panel greys [Allow Changes], `App.new_machine()` and
  `new_catalog()` refuse (`app.READ_ONLY`).  Tests:
  `test_settings.TestReadOnly`, `test_gui_window.test_read_only_shop`.
  Left for #S1: the GUI starting from `settings.start_shop()`,
  [Copy Shop] (#709, #710; leaves `.allow_edits` out), `open_shop()`
  over MCP, no `--shop` (#705), the outline editor's own save.
* #S2 the drill: `examples/shop/tools/drills/` with
  `drill.outline.toml`, its `.svg` and one `.toml` per drill.
* #S1 #433/#437.1/#438: the example shop into the package, read
  only; `settings.toml` (`shop_directories`, `last_shop`);
  [Copy Shop] (#709, #710); `open_shop()` over MCP, no `--shop`,
  tests with a scratch `HOME` (#705, #707).
* #S5 the tree shows the files; then #703/#708 checkboxes and
  [Copy Marked].
* Top 5 given: #689-#693 (6.11's fate, 6.5's tool list, the
  settings file, the example shop's move, finding a shop).

## The Layout (decided, not built)

* #653 (the user, 2026-11-24; replaces the directory per tool
  below): a directory per tool outline (kind); most outlines ship
  in the package (`scraftcam/outlines/KIND/`) and are not edited.
  #655 a shop's own (`SHOP_DIR/outlines/KIND/`) reusing a shipped
  name is an error.  #656 one `KIND.toml` per kind in the shop,
  listing all its tools of that kind.  #654 catalog files stay in
  one directory per catalog (e.g. a new 2027 Shars catalog is a new
  directory); a tool names its catalog, page and part number.
  #657 Steps reworded (below).
* #658 the shop's `KIND.toml` files are in `SHOP_DIR/tools/`; a
  tool's name is unique across the shop's kinds (a repeat is an
  error).  #659 the shop owner chooses its catalogs (in the shop);
  scraftcam only gives the tools for getting facts out of them.
* #683 a package shop opens read only, with [Copy to My Shops] into
  a directory of `~/.scraftcam/settings.toml`.  #682 with no
  settings file, only the package's example shop is listed; the
  file is written on the first [Add Shop] or [Copy to My Shops].
* #660-#663, #665-#667: assemblies are `T.sa~6.11` (its
  `Details.md`); every tool is an assembly.  #661 #S2 uses the drill.

* A directory per object.  `SHOP_DIR/README.md` (generated, indexes
  everything; #464).  `tools/KIND/` holds `KIND.outline.toml`, its
  `.svg` and `KIND.md` (the kind's page, listing its tools), and a
  directory per tool (`tool.toml`, `drawing.svg`, `TOOL.md`, catalog
  files from `T.c~6.3`).
* #458: generated files are committed (always for us; recommended to
  end users).  #459, #464: `README.md` only at the top; pages below
  are named after their directory (to start; expect a dozen tweaks).
  TOML nests too: weigh nested tables against more directories.
* Relative links work on GitHub.  Changing kind moves the directory
  (`git mv`); `.step` tools go under a generic kind.
* #433: shops found from directories listed in
  `~/.scraftcam/settings.toml` (no environment variables); the
  example shop moves into the package (`scraftcam/shops/example_shop/`,
  found from `Path(__file__)`); no fallback across shops (#437.1).
* #461: per-tool SVGs to scale, later (true proportions, a standard
  width, values on the dimensions).
* `T.tfo~6.5` #453's `ball_end_mill` waits for this.

## Steps (#638, first form; see the revised Steps above)

* #S1 shops from `~/.scraftcam/settings.toml`; the example shop into
  the package (#433).  #S2 the Z setter's (303-3104) outline
  directory in the package, and its entry in the example shop's
  `KIND.toml`.  #S3 the letters table as the template for a tool's
  entry (#631).  #S4 assemblies, the Z setter then the vise
  (`T.sa~6.11`, #668).  #S5 the tree shows the files (#615).  #S6
  the tool panel's one table (after #586).  #S7 the rest of the
  example shop.
