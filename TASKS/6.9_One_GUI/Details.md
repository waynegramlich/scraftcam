# 6.9 One GUI

(Draft by Claude, 2026-11-23, from the user's #573-#575; the user's
to revise.)

Every program a user runs becomes one: `python3 -m scraftcam.run`.
All the merging happens in this task, in whatever order works.

* **The outline editor** (`gui/outline_editor.py`, run alone today)
  becomes a panel of the GUI, opened from a tool kind or tool in the
  shop tree; its MCP calls, recordings and tests (`T.mi~7`) carry
  over.
* **The HMI** (`hmi/lcnc_hmi.py`): what is left of it moves into the
  machine panel (`T.g~6` #57), and the LinuxCNC end-to-end tests
  drive the GUI over MCP instead (#426).
* `scraftcam.run` is exposed over MCP (`--mcp PORT`, `--headless`),
  so Claude can drive and test the whole GUI.

Suggested order: the outline editor first (its MCP testing already
works), then the HMI.

## Done When

* One program, `scraftcam.run`; `lcnc_hmi.py` and the standalone
  outline editor are gone (or kept only as thin entry points).
* The recordings and end-to-end tests run against it, headless.
