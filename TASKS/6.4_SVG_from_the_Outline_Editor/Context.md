# LLM Agent Context Log

Squeezed 2026-11-21 (end of the third coding session): only what is
in force and where things stand; the history is in `hg` and `git`
(last before this squeeze: `7696cef`).

## Goal and Design (decided with the user)

The SVG and the editor's diagram are drawn by the same Qt-free code
(`outline_diagram.py`, `diagram.py`), so they never diverge (#S4).
Editing aids stay Qt only, on top: corner and edge circles,
selection, lighting, warning rings, crossings, the edges' direction
arrowheads, and `DimensionHandle`'s drag math (`ends()`, `at()`,
`arc_point()`).

* The user's rule (#323): we do the best initial placement we can;
  once the user moves something, we respect their choice.  Nothing
  is moved automatically (#317); drawing may adjust, saved values
  never.
* The SVG is drawn as on paper: sizes from the text height h (#277,
  after ASME Y14.2, kept simple): outline 0.2 h, thin lines 0.1 h,
  arrowheads h by h/3, gaps h/2; starting h 1/30 of the larger side
  (#281); letters print 3 mm (`LETTER_MM`, #292).  The SVG is what
  documents show; the [SVG] tab is the check for crowding (#313).
* `.svg` files are always black on white, the drawing standard
  (#285; the dark style rule #287 is gone); the [SVG] tab and the
  editor use the theme's colors (lit, red when extra, broken or a
  fillet too big, faint mirror).
* The editor (#302, #311): points follow the zoom; line widths,
  handles, text and arrowheads keep a fixed pixel size (strokes at
  `TEXT_PIXELS / zoom`, letters 1.5 px, #316).  The zoom is
  `hypot(m11, m12)` (a quarter turn moves it off the diagonal).
* Text as lines: Hershey simplex (#264), `°`, `⌀`, `±` drawn by us.
* Letters carry hover titles (#267).  Firefox adds an ugly square to
  the tooltip; kept until the Markdown table of letters (names,
  values, help) is in, then the user decides (#314).
* Corners are placed from the letters' values and marks, the same
  way for both (#299, `values.placed_corners()`).
* `NAME.outline.svg` is written beside the outline each time the
  editor saves, never mid-drag (#248).  Whether users commit it is
  theirs (#318 closed: `git status` shows it; ignore `*.svg` or add).
* [Rotate Diagram (T)] (#300): a quarter turn clockwise per press,
  one undo step, letters upright (`upright_text()` counter-turns
  labels in the editor; `turned_strokes()` in the SVG); `turns` 0-3
  in the file, the tool axis stays along Y.  Mark glyphs turn with
  the drawing.
* [Font + (])], [Font - ([)] (#273): with nothing selected the
  diagram's `text_height` x or / 1.25 (seen only in [SVG]), else the
  selected dimensions' `font_step` (+-6, `FONT_STEPS`); one undo
  step each.  The user: 1.25 feels right.
* Buttons in tabs (#319, the user's way for every GUI): [Most
  Common], [Draw], [Marks], [View] (`BUTTON_KEYS`, `BUTTON_TABS`);
  each word one `QAction` (`button_actions`) shown as `QToolButton`s,
  so state matches on every tab; keys work on any tab; status line
  under the tabs.  Contents frozen until there are more buttons.
* Letters outside (#321): `along` below 0 or above 1 puts a length's
  or angle's letter past an end: arrows outside pointing in, the line
  or arc whole, run on to the letter, a `TAIL` (2 h) past the far
  arrow; drawn at least an arrow plus half the letter clear (#323).
  Angles are no longer held between their rays (#76 dropped).
  Radii unchanged (letter already past the arc).
* Movable marks (#317): `Dimension.moved` (dx, dy, drawing steps;
  file `moved = [dx, dy]` only when set) shifts a `—`/`|` box;
  its circle drags it, snapped, one undo step.  Right angles stay.
* Hide strips: a strip over any part of a letter or glyph is red
  (#322, `DimensionItem.letter_box()`).
* The example drill lies on its side (`turns = 1`) with two strips
  (flutes and shank), L in the middle piece; the user has tried
  dragging R, A outside and the `—` box (#324: all work).

## Code Today

* `scraftcam/diagram.py`: `Stroke`, `Sheet`, `on_paper()`, `text()`,
  `dimension_line()`, `length_dimension()`, `angle_dimension()`
  (`_arc_half()`), `radius_dimension()`, marks, `note()`,
  `placed()`, `svg()` (no theme style), `TAIL`, `FONT_STEP`.
  `scraftcam/hershey.py`.
* `scraftcam/gui/outline_diagram.py`: `outline_sheet()`,
  `outline_strokes()`, `dimension_strokes()`, `fillet_arcs()`,
  `edge_arc()`, `_reaches()`, `turned_strokes()`, `upright_text()`,
  `_mark()` / `_mark_box()`, `letter_title()`.
* `scraftcam/gui/values.py`, `outline_cuts.py` (hide strips).
* `outline_file.py` version 3: `text_height`, `font_step`, `turns`,
  `moved` (each written only when set).
* `outline_editor.py`: `Snapshot` (with `turns`, `text_height`),
  `OutlineView.turn_view()`, `rotate_diagram()`, `step_font()`,
  `covering()`; `DimensionItem.strokes()`, `letter_box()`,
  `handle_spot()`; `DimensionHandle` (marks too); `OutlineEditor.
  make_buttons()`; tabs [Drawing] and [SVG].
* Tests: `test_diagram`, `test_hershey`, `test_outline_diagram`
  (`plain_drill()` = the example upright and uncut),
  `test_outline_cuts`, `test_outline_file`, `test_outline_editor`,
  `test_values`, `test_dimensions` (all pass at this commit).
* `scratch/shot.py IN OUT [ZOOM]` grabs the editor; `scratch/tip.py
  OUT R_ALONG R_OFFSET A_ALONG A_RADIUS` renders the drill's tip (run
  with `PYTHONPATH=.` and `QT_QPA_PLATFORM=offscreen`).

## Open (numbers sticky; next new one #326)

* #290 next (after the restart): hole drawing: holes in the outline
  file, the editor and the SVG (`outline.py`'s `Profile` has them),
  dimensioned from their centers; first example the drill vise jaw
  (5.3 #47: the user's measurements or Shars 202-1142's numbers).
* The `Profile` sheet for `Parallel` in documents (`T.dtm~2.5.2`).
* #260: no per-model `sketch()` method in Python (`T.ant~5.9` idea
  1).
* Work rules: ~3 minute chunks, several items per chunk when they
  fit; a top 5 after each round; renders for the user in `scratch/`
  with full `file:///` paths.
