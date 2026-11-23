# LLM Agent Context Log

Made 2026-11-22 from `T.tfo~6.5` #460; Open while `T.tfo~6.5` runs,
as the layout will be tweaked often.  Issue numbers are shared with
`T.tfo~6.5` and `T.oe~6.2`.

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
