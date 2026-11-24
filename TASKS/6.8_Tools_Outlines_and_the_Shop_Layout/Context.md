# LLM Agent Context Log

Made 2026-11-22 from `T.tfo~6.5` #460; renamed from "Shop Directory
Layout" and opened 2026-11-24 (#627-#633), taking in `T.tkis~6.7`
(closed).  Issue numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.  Waits for `T.gc~6.10` (#634).

## Decided 2026-11-24

* #631 (the user): a kind's outline dimension table is the template
  for the fields of each tool's `.toml` (as #391 in `T.tkis~6.7`:
  one outline file per kind, each tool gives only its letter
  values); one table in the tool's panel (unifies #592/#594's two
  dimension views).
* #615 the tree shows outline files (`gui/tree.py:482` hides them,
  "Until #S7").
* From `T.tkis~6.7`: idea 1 began as `meta()` field metadata in
  `scraftcam/model.py` (`T.cmt~5.3`); a per-model `sketch()` was
  dropped (#260), the outline's `.svg` is the sketch.  Idea 2's
  STEP route exists (`solid.SolidStep`, `T.rps~6.6`).  The Z setter
  (`tooling/setters.py`) has no shop kind yet.

## The Layout (decided, not built)

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
