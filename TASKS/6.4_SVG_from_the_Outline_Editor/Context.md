# LLM Agent Context Log

## 2026-11-19: Created and opened

Created at the user's request from `T.oe~6.2` (#S5) and opened;
`Details.md` is Claude's draft.  The editor it draws from is described
in `T.oe~6.2`'s `Context.md` ("The Editor Today").  Nothing coded.

Open questions (numbers continue `T.oe~6.2`'s, next new #250):
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

## 2026-11-20: Renumbered

The GUI became top-level task `T.g~6` (was 5.1.9); this item moved
from 5.1.9.2.2 to 6.4, its parent editor is `T.oe~6.2`.  Still
nothing coded; next is to settle #247 and #248 above.  Numbers on
from #257 (#250-#256 were the reorganization and the transcript
rule, all done).
