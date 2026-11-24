# LLM Agent Context Log

Made 2026-11-22 from `T.tfo~6.5` #460; renamed from "Shop Directory
Layout" and opened 2026-11-24 (#627-#633), taking in `T.tkis~6.7`
(closed).  Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.  `T.gc~6.10` closed 2026-11-24: next is
#S1 (#680), then `T.sa~6.11`, then #S2 on.  The letters table is
`gui/outline_letters.LettersTable` (for #631, #S6).

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

## Steps (#638, agreed 2026-11-24; reworded by #657)

* #S1 shops from `~/.scraftcam/settings.toml`; the example shop into
  the package (#433).  #S2 the Z setter's (303-3104) outline
  directory in the package, and its entry in the example shop's
  `KIND.toml`.  #S3 the letters table as the template for a tool's
  entry (#631).  #S4 assemblies, the Z setter then the vise
  (`T.sa~6.11`, #668).  #S5 the tree shows the files (#615).  #S6
  the tool panel's one table (after #586).  #S7 the rest of the
  example shop.
