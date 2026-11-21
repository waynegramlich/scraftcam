# LLM Agent Context Log

Squeezed 2026-11-20 (end of the first coding session): only what is
in force and where things stand; the history is in `hg` and `git`.

## Goal and Design (decided with the user, 2026-11-20)

The SVG and the editor's diagram are drawn by the same code, so they
never diverge.  Qt-free shapes, two back ends (SVG text, and later
`QPainter` in the editor, #S4); editing aids (circles, selection,
lighting, warning rings) stay Qt only, on top, at a fixed pixel size
(#269).

* Drawn as on paper (#263): letters, arrowheads and line widths scale
  with the zoom; no 1:N scale (#268).  Sizes from the text height h
  (#277, after ASME Y14.2, kept simple: users do not know ASME, it
  must just work): outline 0.2 h, thin lines 0.1 h, arrowheads h by
  h/3, gaps h/2.  Starting h: 1/30 of the larger side (#281).
* Text as lines: Hershey simplex (#264), `°`, `⌀`, `±` drawn by us.
* Ink only, no colors (#266, #274): light theme black on white, dark
  white on black.  The `.svg` follows the viewer's theme with a style
  rule (#287), black on white when printed; letters print 3 mm
  (`LETTER_MM`, #292).  The `.svg` goes into `.md` files read in a
  browser (#279; the user's Firefox is a snap: files for it go in
  the project's ignored `scratch/`).
* Font buttons, at most 4 (#272, #273): [Font +], [Font -] on
  selected text (`Dimension.font_step`, 1.25x a step) and [All Fonts
  +], [All Fonts -] (`Outline.text_height`); the user zooms out and
  presses until it looks right, judged in the [SVG] tab.  Saved in
  outline file version 3 (#280); not built in the GUI yet.
* #300 (decided): long tools are shown on their side, by turning the
  view only (a saved setting such as `turned = true`, by a button or
  when much taller than wide); the file keeps the tool axis along Y,
  so the simulator never needs a turn.
* Work in ~3 minute chunks, each with a file for the user to look at
  in `scratch/` when there is one (full `file:///` path).

## Code Today

* `scraftcam/diagram.py`: `Stroke` (segments, `Weight`, `filled`,
  `dashed`, `role` `LINE`), `Sheet`, `on_paper()`,
  `starting_height()`, `profile_sheet()`, `text()`,
  `dimension_line()` (feet, ends, `along`), `length_dimension()`,
  `angle_dimension()` (`along`; short arcs whole, letter outside),
  `radius_dimension()`, `center_mark()`, `edge_mark()`, `mark_box()`,
  `right_angle()`, `note()`, `placed()`, `polyline()`, `svg()`
  (`themed`, `letter_mm`), `FONT_STEP`.
* `scraftcam/hershey.py`: `strokes()`, `width()`, `GLYPHS` (credits in
  its docstring, as the font's notice requires).
* `scraftcam/gui/outline_diagram.py`: `outline_sheet(outline)`: the
  outline with true fillet arcs (`fillet_arcs()`, the editor's scale
  rule), the dashed mirror half when revolved, length, horizontal,
  vertical, angle and radius dimensions, marks, the UDF note, font
  steps; then `outline_cuts.cut_strokes()`.
* `scraftcam/gui/outline_cuts.py`: hide strips cut out and closed up
  (`GAP` 2 h), break lines meshing, S's on chopped dimension lines.
* `outline_file.py` version 3: `text_height`, `font_step` (written
  only when set; versions 1, 2 still read).
* `outline_editor.py`: the drawing in tabs [Drawing] and [SVG]
  (`drawing_tabs()`, `show_svg()`: `QSvgWidget`, redrawn when chosen,
  kept to its shape after each load).
* Tests: `test_diagram` 25, `test_hershey` 9, `test_outline_diagram`
  15, `test_outline_cuts` 8, plus `test_outline_file`,
  `test_outline_editor` when touched; 99% coverage of the new
  modules.  Samples: a scratchpad script wrote `scratch/*.svg`
  (`scratch/drill.outline.toml` is a copy to try the editor on).

## Open (numbers sticky; next new one #311)

* #S4 is next (agreed by the user, 2026-11-21: it removes duplicate
  code).  What stands in the way (found 2026-11-21, not yet
  answered by the user):
  * #301: the editor paints per item (`DimensionItem`, lit, hovered,
    selected one by one) but `outline_sheet()` returns one flat
    `Sheet`; give `diagram.py` per-item builders (Claude's choice) or
    tag strokes by owner.
  * #302: the editor's pens are cosmetic (fixed pixels,
    `ARROW_PIXELS / scale`); the shapes scale with the zoom (#263).
    A minimum of about 1 px so lines never vanish?
  * #303: colors: shapes are ink only (#266); the editor lights a
    letter's dimensions, paints crossings and broken marks red, the
    mirror half faint.  Plan: one color per item chosen in Qt;
    warnings stay Qt overlays (#269).
  * #304: the editor needs strokes in drawing steps (before
    `on_paper()`/`placed()`), rebuilt each drag frame (Hershey text
    included): measure the speed.
  * #305: hit areas (`DimensionItem.shape()`) and handle spots
    (`arc_point()`, `ends()`) use the editor's own geometry (#295,
    #297's copies) and could drift from what is drawn.
  * First chunk suggested: #301 and #302 on `OutlineItem` alone (no
    letters, no hit testing), then dimensions.
  * (#306-#310 were the transcript rule, done: `R.ccsr~6`.)
* #S4: the editor draws through the shapes, one item type per chunk;
  then the plain-Python copies of its geometry go (#295 angles:
  `edge_arc()`, `crossing()`, `edge_way()`; #297 fillets:
  `fillet_radii()`, `fillet_ends()`, `first_scale()`).
* #300 build the turned view.  The four font buttons (#273).
* #267: each letter an invisible `<title>` in the SVG (not done).
* #290: holes dimensioned from their centers in outlines (center
  marks exist in `diagram.py`; outlines have no holes yet).
* #296: an angle's extension lines where its arc lies past an edge.
* #299: `examples/shop/tools/drill.outline.toml`'s corners do not
  follow its values (the editor places them; the file was never
  saved after), so #292's "saved corners follow the values" fails
  for it outside the editor.
* #285 (near the end, never dropped): a white-on-black `.svg` chosen
  by `<picture>` (or rely on #287's style rule).
* A `.svg` written beside the outline for documents (#248), and the
  `Profile` sheet for `Parallel` in documents (`T.dtm~2.5.2`).
* #260: no per-model `sketch()` method in Python (`T.ant~5.9` idea
  1).
