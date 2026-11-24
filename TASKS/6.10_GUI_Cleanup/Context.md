# LLM Agent Context Log

Made 2026-11-24 from `T.og~6.9` (closed).  Issue numbers are shared
by every task; the next is in `TASKS/Issue_Counter.md`.

## Starting Points

* `T.og~6.9`'s summary; `T.mi~7`'s notes (Reference) for driving
  the GUI over MCP (`scraftcam.exposed.client start --gui`).
* `scraftcam/run.py`, `gui/window.py`, `gui/views.py`,
  `gui/prompt.py`, `hmi/lcnc_hmi.py`, `hmi/hmi_exposed.py`.

## Issues (as found 2026-11-24)

* #613 `hmi/lcnc_hmi.py:189-290` keeps its own `ANSWERS`, `ASKED`,
  `use_headless()`, `ask_yes_no()`, `ask_choice()`,
  `ask_open_file()`, duplicating `gui/prompt.py`; the tests
  (`tests/qt_app.py`, `test_lcnc_hmi`, `test_hmi_qt_widgets`) use
  them.  Proposed: the HMI uses `prompt.py`, tests answer through
  `prompt.ANSWERS`.
* #614 rename `lcnc_hmi.py` (only the machine panel's widget, 1992
  lines), e.g. `hmi/hmi_panel.py`; after #613.
* #616 `README.md:200-211` (and "Trying It") name `lcnc_hmi.py`,
  `show_demo.py`, `drive_editor.py`.
* #617 `scraftcam/gui/README.md` (83 lines) never mentions the
  machine panel, HMI, MCP or `prompt.py` (`T.g~6`'s Done When).
* #618 stale "`show_demo.py`" in `tests/test_show_demo.py`,
  `tests/test_setups.py:272`, `Tool_Models.md:1472,1627`.
* #619 large modules: `outline_editor.py` 5159 lines, `window.py`
  1984, `views.py` 1733.  The user decides whether to split.
* #620 the four checkers over all of `scraftcam/` (each step checked
  only its changed files).
* #621 `run.py` has 16 options; list them and prune the dead (#607:
  flags are for Claude only).
* #622 sort the 141 test files: direct-widget tests that stay fast,
  and those that become MCP recordings (`T.mi~7` #555).
* #623 #606's prompts placed at the exact part (e.g. the dimensions
  table); `T.og~6.9` #S6's [Pages] tab not tried with a real PDF.
* #586 tabs in every panel: the user leans yes; not final.
* #615 (the tree hides outline files, `gui/tree.py:482`, "Until
  #S7") moved to `T.toasl~6.8`.

## Order (agreed, #634)

This task first, then `T.toasl~6.8`.  Within it (proposed): #613,
#614, #616-#618, #620/#621, then #619/#622.
