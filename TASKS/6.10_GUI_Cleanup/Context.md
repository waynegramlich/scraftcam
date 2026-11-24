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

## Decided 2026-11-24 (to do)

* #S1 done (#649, #648): `lcnc/probe_batch.py` and its test deleted;
  `sim_solidcraft.py` uses `plot.py`'s `path_steps()`,
  `sketch_steps(..., hide=)`, `send_batch(transport, steps)` (callers
  pass `solidcraft.transport`); polyline tests moved to
  `test_plot.py`.  Shared now: `geometry.draw_segments()`,
  `scraftpybind.connect_cli(where, *, always)` (with
  `SOLIDCRAFT_CLI`; test in `test_scraftpybind`),
  `outline_cuts.cut_pieces()` (one `FAR`, 1e9).  `pylint -j 1
  --enable=duplicate-code` is clean over `scraftcam/` and `tests/`.
* #613 the HMI uses `gui/prompt.py`, not its own copy
  (`hmi/lcnc_hmi.py:189-290`: `ANSWERS`, `ASKED`, `use_headless()`,
  `ask_*()`); tests use `prompt.ANSWERS`.
* #586/#639 tabs in every panel: every panel alike, new tabs (and
  their documentation) easy to add.  Before `T.toasl~6.8`'s tool
  panel.
* #614 rename `hmi/lcnc_hmi.py` to `hmi/machine_panel.py`; after
  #613.
* #621 prune `run.py`'s 16 options to those tests, the MCP client and
  the end-to-end suite use (#607: flags are for Claude only).
* #637 (for #619) split only `gui/outline_editor.py` (5159 lines),
  along #631's seam (letters table and values versus drawing and
  editing); `window.py`, `views.py` stay.
* #622 sort the test files: fast widget tests, and MCP recordings
  (`T.mi~7` #555); last, after #613/#614.  Recordings may run in
  pseudo time (#650, agreed: `steps.Player` moves a clock on by each
  step's recorded `time`; measure the saving on `move_a_corner`
  first).  Three sub-packages: `tests/widgets/` (fast, no MCP or
  LinuxCNC), `tests/recordings/` (MCP replays), `tests/lcnc/` (the
  end-to-end suite); the `CLAUDE.md` test command changes (#664, agreed).

## Deferred

* #635: documents wait until much further along; moved to
  `T.d~8` (#616-#618).
* #623 #606's prompts at the exact part; [Pages] with a real PDF:
  until more tools use the catalog (the user).

## Order (agreed, #634)

This task, then `T.toasl~6.8` #S1, then `T.sa~6.11` (the drill as
a one-part assembly), then `T.toasl~6.8` #S2 on (#680, agreed).

Steps (#679, agreed): #S1 #649, #648.  #S2 #613, #614.  #S3 #621.
#S4 #586.  #S5 #637.  #S6 #622, #650, #664.  Claude suggests each
Step's commit message.
