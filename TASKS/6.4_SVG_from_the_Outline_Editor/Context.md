# LLM Agent Context Log

Squeezed 2026-11-20: only what is in force and where things stand;
the history is in `hg` and `git`.  Nothing coded yet.

## Scope

One SVG writer with two inputs: the outline file (`outline_file.py`,
the editor's, the main one) and a `scraftcam/outline.py` `Profile`.
`T.sdfm~2.5.2.1` (SVG diagrams from the models) was merged in here
(#259); its SolidCraft solver facts are in `T.oe~6.2`'s `Context.md`.
The editor drawn from is described there ("The Editor Today").

## Open Questions

* #247 drawn how: (a) plain Python from the geometry, no Qt (Claude
  leans here: documents without a display, and a `Profile` has no Qt
  scene), or (b) Qt painting the scene through `QSvgGenerator`.
* #248 where seen: an [SVG] tab redrawn when clicked (#189), a `.svg`
  written beside the outline for documents, or both.

## Starting Points

* `outline_editor.py` draws the outline (`OutlineItem.paint()`,
  `fillet_ends()`, `rounded_path()`), the dimensions and marks
  (`DimensionItem`: `paint_angle()`, `draw_letter()`, `paint_mark()`,
  `right_box()`), the hide cuts (`draw_cut()`) and the UDF note
  (`drawForeground()`); `values.py` has the real coordinates;
  `theme.py` the light and dark colors.
* `Profile(name, outer, holes, unit)` of `geometry.Loop`s, checked in
  `__post_init__()` (closed, no segment under `MIN_LENGTH` 1e-6 mm,
  arcs on their circles, no crossings, holes inside, apart, not
  nested; islands wait); messages in the user's units.
  `structure()`, `values(prefix)`, `sketch()`, `add_parameters()`,
  `send_changes(old, new, limit=500)`.  Tests `test_outline` (8).
* `scraftcam/tooling/parallel.py` `Parallel`: its side is a `Profile`
  on YZ; `python3 -m scraftcam.tooling.parallel headless`; tests
  `test_parallel` (3).  The old `tools.Parallel` stays until the GUI
  is debugged.

## Next and Decided

* After #247 and #248: #38, `Profile` to SVG (lines and arcs as path
  commands, holes by the fill rule, light and dark), first tried on
  `Parallel().side`; then the outline file's dimensions, marks, hide
  cuts and UDF note.
* #260: no per-model `sketch()` method in Python (`T.ant~5.9` idea
  1); once tools are outlines (`T.cett2e~6.5`) it stops mattering.
* Numbers sticky; next new one #261.
