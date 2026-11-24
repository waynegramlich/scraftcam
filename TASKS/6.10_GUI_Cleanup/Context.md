# LLM Agent Context Log

Made 2026-11-24 from `T.og~6.9` (closed); squeezed 2026-11-24
(history in `hg` and `git`).  Issue numbers are shared by every
task; the next is in `TASKS/Issue_Counter.md`.

## Starting Points

* `T.og~6.9`'s summary; `T.mi~7`'s notes (Reference) for driving
  the GUI over MCP (`scraftcam.exposed.client start --gui`).
* `scraftcam/run.py`, `gui/window.py`, `gui/views.py`,
  `gui/prompt.py`, `hmi/lcnc_hmi.py`, `hmi/hmi_exposed.py`.

## Done: the Checkers (#620, #636, #640-#647)

* All four clean over `scraftcam/` and `tests/`.  `tests/__init__.py`
  puts `PySide6` on `sys.path`, so tests import it at their tops.
  Shared test helpers: `tests/solidcraft_checks.py`,
  `test_drill_outline.assert_same()`; `gui/values.set_letters()`
  (for `T.toasl~6.8` #631).  Every suppression is fixed or gives its
  reason; `setUpModule` is in `.pylintrc`'s `good-names` (#642).
* ruff 0.17.6's default rules include `BLE`, `TRY`, `SIM`: those
  `noqa` codes are live (#647).
* `pylint -j 4` misses `duplicate-code`; check it with `-j 1`.

## Open

* #648 9 `duplicate-code` pairs in the package: `lcnc/probe_batch.py`
  and `plot.py` (5: `path_steps()`, `sketch_steps()`, `send_batch()`;
  the probe's take `arcs`, `hide`; `lcnc/sim_solidcraft.py` imports
  them).  Proposed: `plot.py` owns them, with keyword options.  Also
  `geometry.py:1085-1103`/`solid.py:622-640` (2),
  `demo.py:257-265`/`lcnc/sim_move.py:233-241`,
  `gui/outline_cuts.py:96-101`/`gui/outline_editor.py:3755-3760`.
* #649 keep or drop `lcnc/probe_batch.py` (a `T.rlg~3.3` probe).
* #613 `hmi/lcnc_hmi.py:189-290` duplicates `gui/prompt.py`
  (`ANSWERS`, `ASKED`, `use_headless()`, `ask_*()`); tests use them.
  Proposed: the HMI uses `prompt.py`, tests `prompt.ANSWERS`.
* #614 rename `lcnc_hmi.py` (the machine panel's widget), e.g.
  `hmi/hmi_panel.py`; after #613.
* #616 `README.md:200-211` and "Trying It" name `lcnc_hmi.py`,
  `show_demo.py`, `drive_editor.py`.  #617 `scraftcam/gui/README.md`
  never mentions the machine panel, HMI, MCP or `prompt.py`.  #618
  stale `show_demo.py` in `tests/test_setups.py:272`,
  `Tool_Models.md:1472,1627`.  #635 (proposed): write #616/#617
  after `T.toasl~6.8`'s layout lands.
* #619 large modules (`outline_editor.py` 5159 lines, `window.py`,
  `views.py`); the user decides.  #637 (proposed): split only
  `outline_editor.py`, along the seam `T.toasl~6.8` #631 needs.
* #621 prune `run.py`'s 16 options (#607: flags are for Claude only).
* #622 sort the test files: fast widget tests, and MCP recordings
  (`T.mi~7` #555).
* #623 #606's prompts at the exact part; [Pages] with a real PDF.
* #586 tabs in every panel (the user leans yes).  #639 (proposed):
  decide before `T.toasl~6.8`'s tool panel.

## Order (agreed, #634)

This task first, then `T.toasl~6.8`.  Within it (proposed): #648,
#649, #613, #614, #621, the documents, then #619/#622.
