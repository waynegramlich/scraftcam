# LLM Agent Context Log

## 2026-11-19: Created and opened

Created at the user's request from `T.prg~5.1.9.2` (#S5) and opened;
`Details.md` is Claude's draft.  The editor it draws from is described
in `T.prg~5.1.9.2`'s `Context.md` ("The Editor Today").  Nothing coded.

Open questions (numbers continue `T.prg~5.1.9.2`'s, next new #250):
* #247 drawn how: (a) from the outline file in plain Python, no Qt
  (Claude leans here: documents without a display), or (b) Qt
  painting the scene through `QSvgGenerator` (looks like the screen,
  less control, needs Qt).
* #248 where seen: an [SVG] tab redrawn when clicked (#189), and a
  `.svg` written beside the outline for documents; both?

Starting points: `outline_editor.py` draws the outline
(`OutlineItem.paint()`, `fillet_ends()`, `rounded_path()`), the
dimensions and marks (`DimensionItem`: `paint_angle()`,
`draw_letter()`, `paint_mark()`, `right_box()`), the hide cuts
(`draw_cut()`) and the UDF note (`drawForeground()`); `values.py`
has the real coordinates; `theme.py` the light and dark colors.
Related: `T.sdfm~2.5.2.1` (`Profile` to SVG, not started).
