# LLM Agent Context Log

Squeezed 2026-11-21 (end of the second coding session, #S4 done):
only what is in force and where things stand; the history is in `hg`
and `git` (last before this squeeze: `e5a9a02`).

## Goal and Design (decided with the user)

The SVG and the editor's diagram are drawn by the same Qt-free code
(`outline_diagram.py`, `diagram.py`), so they never diverge (#S4,
done 2026-11-21).  Editing aids stay Qt only, on top: corner and edge
circles, selection, lighting, warning rings, crossings, the edges'
direction arrowheads, and `DimensionHandle`'s drag math (`ends()`,
`at()`, `arc_point()`).

* The SVG is drawn as on paper: sizes from the text height h (#277,
  after ASME Y14.2, kept simple): outline 0.2 h, thin lines 0.1 h,
  arrowheads h by h/3, gaps h/2; starting h 1/30 of the larger side
  (#281); letters print 3 mm (`LETTER_MM`, #292).  The SVG is what
  documents show; the [SVG] tab is the check for crowding (#313).
* The editor (#302, #311): points follow the zoom; line widths,
  handles, text and arrowheads keep a fixed pixel size (strokes built
  at `TEXT_PIXELS / zoom`, letters `TEXT_PEN_PIXELS` 1.5 px, liked,
  #316).  The unzoomed diagram must be legible.
* Text as lines: Hershey simplex (#264), `°`, `⌀`, `±` drawn by us;
  no cache needed (#304: 8 dimensions' strokes 0.26 ms, a repaint
  12 ms).
* Ink only (#266, #303): the `.svg` follows the viewer's theme by a
  style rule (#287), black on white printed; the editor picks a pen
  per item (lit, red when extra, broken or a fillet too big, faint
  mirror).
* Letters carry hover titles (#267: name, value, help; the user will
  say if unwanted).
* Corners are placed from the letters' values and marks, the same
  way for both (#299, `values.placed_corners()`); saved positions
  count only for corners nothing pins.
* `NAME.outline.svg` is written beside the outline each time the
  editor writes it, never mid-drag (#248), and is committed (#313;
  `examples/shop/tools/drill.outline.svg`).
* #300: [Rotate Diagram] turns a quarter turn clockwise per press,
  four presses back to the start, letters upright; saved as `turns`
  (0-3); the file keeps the tool axis along Y.
* The font buttons are not built (#273); `text_height`, `font_step`
  stay in the file, unused.
* A dimension's circle sits just off its letter's upper right corner
  (#315 (b)); click areas and letter spots come from the drawn
  strokes (#305).

## Code Today

* `scraftcam/diagram.py`: `Stroke` (`segments`, `Weight`, `filled`,
  `dashed`, `role` `LINE`/`TEXT`, `title`), `Sheet`, `on_paper()`,
  `text()`, `dimension_line()`, `length_dimension()`,
  `angle_dimension()`, `radius_dimension()`, marks, `note()`,
  `placed()`, `svg()` (titled strokes grouped in `<g><title>` over
  an unseen box).  `scraftcam/hershey.py` (credits in its docstring).
* `scraftcam/gui/outline_diagram.py`: `outline_sheet()`,
  `outline_strokes()`, `dimension_strokes()`, `fillet_arcs(outline,
  scale)`, `edge_arc()` (`PARALLEL` 1e-6, used by the editor's
  `crossing()`/`edge_arc()` too), `_reaches()` (extension lines out
  to an angle's arc, #296), `turned_strokes()`, `letter_title()`.
* `scraftcam/gui/values.py`: `placed_corners()`, `first_scale()`,
  `letters_bad()` (shared with the editor's `apply_values()`).
* `scraftcam/gui/outline_cuts.py`: hide strips (copies `title`).
* `outline_file.py` version 3: `text_height`, `font_step`, `turns`
  (written only when set).
* `outline_editor.py`: `OutlineItem.paint()` and
  `DimensionItem.paint_strokes()` draw the shared strokes
  (`stroke_path()`, `stroke_box()`); `DimensionItem.strokes()`,
  `handle_spot()`; `svg_path()`; tabs [Drawing] and [SVG].
* Tests: `test_diagram`, `test_hershey`, `test_outline_diagram`,
  `test_outline_cuts`, `test_outline_file`, `test_outline_editor`,
  `test_values` (all pass at `e5a9a02`).
* `scratch/shot.py IN OUT [ZOOM]` grabs the editor offscreen (run
  with `PYTHONPATH=.` and `QT_QPA_PLATFORM=offscreen`).

## Open (numbers sticky; next new one #319)

* #300 next: the editor's [Rotate Diagram] button: turn the view
  (`QGraphicsView.rotate()`), counter-turn each label's strokes
  about its middle so letters stay upright, `turns` in `Snapshot`
  (one undo step), handles placed again.  The SVG side is done.
* #317 next: in the drill the long edge's `|` mark covers the L;
  the user wants marks moved clear of letters automatically (for
  now).
* #318: let end users choose whether derived `.svg` files are
  committed.
* #314: the user to check that hover titles show in Firefox.
* #290: holes dimensioned from their centers (outlines have none).
* #285 (near the end, never dropped): a white-on-black `.svg` chosen
  by `<picture>` (or rely on #287's style rule).
* The `Profile` sheet for `Parallel` in documents (`T.dtm~2.5.2`).
* #260: no per-model `sketch()` method in Python (`T.ant~5.9` idea
  1).
* Work rules: ~3 minute chunks, several items per chunk when they
  fit; a top 5 after each round; renders for the user in `scratch/`
  with full `file:///` paths.
