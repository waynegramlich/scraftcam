# LLM Agent Context Log

Made 2026-11-24 (#651), Open so that reminders can be added.  Issue
numbers are shared by every task; the next is in
`TASKS/Issue_Counter.md`.

## Reminders

* #616 `README.md:200-211` and "Trying It" name `lcnc_hmi.py` (now
  `hmi/machine_panel.py`, #614),
  `show_demo.py`, `drive_editor.py`.
* #617 `scraftcam/gui/README.md` never mentions the machine panel,
  the HMI, MCP or `prompt.py`.
* #618 stale `show_demo.py` in `tests/test_setups.py:272` (move to
  `T.gc~6.10` if it is code, not prose) and
  `Tool_Models.md:1472,1627`.
* `T.toasl~6.8` #653-#656 change the shop layout: describe it once
  it lands.
* `README.md` names `tests.test_*`: now `tests.GROUP.test_*`
  (`fast`, `qt`, `solidcraft`, `lcnc`; `T.gc~6.10` #622).
* `T.toasl~6.8` (2026-11-24): the example shop is now
  `scraftcam/example_shop/` (read only; `.allow_edits` for
  developers, #717); `~/.scraftcam/settings.toml` (`settings.py`);
  tools in a directory per kind (`tools/drills/`, #711).  Paths
  are updated; `scraftcam/gui/README.md` has [Copy Shop] and the
  settings (#S1 done); `README.md`'s "Trying It" still to check.
* `T.toasl~6.8` #S3: tools are in kind directories (`tools/drills/`,
  `end_mills/`, `chamfer_mills/`), written by their outline's
  letters (`key = ...` in the outline); describe for shop owners.
* `T.toasl~6.8` #S6: each tool's `.svg` beside its `.toml` (true
  proportions, the outline's scale); `python3 -m
  scraftcam.gui.tool_svgs [SHOP]` rewrites a shop's; the outline
  editor's MCP `resize`; a tool's [Outline] tab table (Default /
  This tool).
* `T.toasl~6.8` #S8: an outline is changed in its [Edit] tab (no
  [Allow Changes]; [Overview] is gone); a tool's [Outline] links to
  its kind's outline.  `T.toasl~6.8` #S7: the shop's `stock/`,
  `tools/materials/`, `tooling/grid_plates/` layout.
* `T.sa~6.11` #S1: outline files are format 5, corners named
  `[[vertices]]`; older files are refused (#773).  The [Draw] tab's
  "Vertex:" field renames the chosen corner (#795).
* `T.sa~6.11` #S2: several polygons per outline ([New Polygon],
  overlaps refused, shared corners), letters' scopes (outline,
  internal, a polygon's); the letters' table is now the Values
  table, with a [Polygons] tab.
* `T.sa~6.11` #S3: materials' `color` (`R13% G32% B78% T40%`) and
  `hatch` (`A45 S2mm T0.25mm`, `+` for a crosshatch) fields; a
  polygon's material hatches it in drawings (monochrome, #812), a
  standard hatch given when none; a polygon's own colour (for
  solids) in the [Polygons] tab's picker.
