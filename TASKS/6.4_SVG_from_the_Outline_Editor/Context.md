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

## Decided 2026-11-21 (before #S4)

* #301: `diagram.py` gets per-item builders; the SVG joins them.
* #302, #311 (replace #263 in the editor only): the editor's points
  follow the zoom, but line widths, handles, text and arrowheads
  keep a fixed pixel size (text anchored at its point); the SVG
  keeps its sizes on paper.  The unzoomed diagram must be legible.
* #303: shapes ink only; the editor picks a pen per item (lit,
  red warnings, faint mirror).
* #304: Hershey strokes built once per letter and size, relative to
  an anchor, and only moved while dragging.
* #305: hit areas and handles come from the drawn strokes.
* #300: a [Rotate Diagram] toggle (90 degrees, letters upright),
  saved in the file; the drawer's choice, never automatic.
* #273: the font buttons are not built; `text_height`, `font_step`
  stay in the file, unused.
* #312: #S4 in ~3 minute chunks, several items per chunk when they
  fit.
* #299: the SVG writer solves corners from the values and marks as
  the editor does; saved positions only for unpinned corners.
* #313: the SVG is what documents show; the [SVG] tab is the check
  for crowding (the editor's fixed-pixel text may differ).
* #248: the `.svg` is written beside the outline every time the
  editor writes the outline (after each change, never mid-drag).
* #267: each letter gets an invisible `<title>` (name, help); the
  user will say if it is unwanted.
* #296: extension lines out to an angle's arc past an edge (yes).

## Done 2026-11-21 (four chunks while the user was at lunch)

* #299: `values.placed_corners()` (with `first_scale()`,
  `letters_bad()`, moved from the editor) places corners from the
  values; `outline_sheet()` and the editor's `apply_values()` share
  it.
* #S4 chunk 1: `outline_diagram.outline_strokes()` (the outline and
  the mirror half) drawn by `OutlineItem.paint()` through
  `stroke_path()` with cosmetic pens; `fillet_arcs(outline, scale)`
  takes the editor's scale.  The editor's mirror half now follows
  the fillets, as the SVG's.  `fillet_ends()`, `rounded_path()` and
  friends still serve `fillet_middle()` and the handles; they go when
  the dimensions move over.
* #248: `OutlineEditor.save()` writes `svg_path()`
  (`NAME.outline.svg`, themed) with the outline, and when missing.
* #267: `Stroke.title`, text strokes role `TEXT`; `svg()` groups
  titled strokes in `<g><title>` over an unseen box
  (`pointer-events="all"`); `letter_title()`.
* #S4 chunks 2-4 (same day, second round): `DimensionItem` draws
  lengths, horizontals, verticals, angles and marks through
  `outline_diagram.dimension_strokes()` at `TEXT_PIXELS / zoom`
  (#311), `paint_strokes()`; `shape()`, `boundingRect()` and
  `letter_spot()` come from the strokes (`stroke_box()`, #305).
  Removed: `paint_angle()`, `draw_reach()`, `draw_letter()`,
  `reach_path()`, `letter_side()`, `mark_spot()`, `right_box()`,
  `mark_box()`, `paint_mark()`, `MARK_PIXELS`, `MARK_GAP_PIXELS`,
  `OVERSHOOT_PIXELS`.
* #304 measured: all 8 drill dimensions' strokes 0.26 ms, shapes and
  boxes 0.94 ms, a full repaint 12 ms: no Hershey cache needed.
* #296: `outline_diagram._reaches()` extension lines out to an
  angle's arc (the editor's old `reach_path()` moved there).
* Third round (chunks 9-12): #315 (b) the circle sits off the
  letter's upper right corner (`handle_spot()`, `DimensionHandle.grab`
  keeps drags from jumping); #316 letters 1.5 px
  (`TEXT_PEN_PIXELS`); fillets through `dimension_strokes()` (their
  dashes moved from `OutlineItem`), the editor's fillet copies gone
  (#297); #295 one Qt-free `outline_diagram.edge_arc()` (`PARALLEL`
  1e-6) used by the editor's `crossing()`/`edge_arc()`; #300 SVG
  side: `Outline.turned` (file `turned = true`, written only when
  set), `turned_strokes()` turns clockwise, labels kept upright.
  Next for #300: the editor's [Rotate Diagram] button (view rotated,
  text strokes counter-turned, an undo step, `Snapshot` field).
  #317: in the drill the long edge's `|` mark covers the L.

## Open (numbers sticky; next new one #319)

#S4 is done (2026-11-21): the editor draws everything (outline,
dimensions, marks, fillets) through `outline_diagram.py`; its
duplicate geometry is gone (#295, #297); #301-#305 settled (see the
decisions above).  Still the editor's own: editing aids (circles,
selection, lighting, warning rings, crossings, edge arrowheads), and
`DimensionHandle`'s drag math (`ends()`, `at()`, `arc_point()`).

* #300 next: the editor's [Rotate Diagram] button, a quarter turn
  clockwise each press, four presses back to the start (the user,
  2026-11-21).  The file field is `turns` (0-3, written only when
  set); the SVG side is done (`turned_strokes()` applied `turns`
  times).  The editor: turn the view (`QGraphicsView.rotate()`),
  counter-turn each label's strokes about its middle so letters stay
  upright, `turns` in `Snapshot` (one undo step), handles placed
  again.
* #317 next: in the drill the long edge's `|` mark covers the L;
  the user wants marks moved clear of letters automatically (for
  now).
* #318: the user would like end users to choose whether derived
  `.svg` files are committed (#313: the shop's own are committed;
  `examples/shop/tools/drill.outline.svg` is).
* #316 settled: letters at 1.5 px look fine (`TEXT_PEN_PIXELS`).
* #273: the font buttons are not built (fields kept, unused).
* #290: holes dimensioned from their centers (outlines have none).
* #285 (near the end, never dropped): a white-on-black `.svg` chosen
  by `<picture>` (or rely on #287's style rule).
* #314: the user to check that hover titles (#267) show in Firefox.
* The `Profile` sheet for `Parallel` in documents (`T.dtm~2.5.2`).
* #260: no per-model `sketch()` method in Python (`T.ant~5.9` idea
  1).
* Work rules: ~3 minute chunks, several items per chunk when they
  fit; a top 5 after each round; renders for the user in `scratch/`
  (`scratch/shot.py IN OUT [ZOOM]` grabs the editor offscreen, run
  with `PYTHONPATH=.`).
