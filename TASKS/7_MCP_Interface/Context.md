# LLM Agent Context Log

Made 2026-11-23 from `T.oe~6.2` (#485-#505); squeezed again
2026-11-23 late (history in `hg` and `git`).  Issue numbers are
shared with `T.tfo~6.5`, `T.oe~6.2` and `T.toasl~6.8`; the next new
one is in `TASKS/Issue_Counter.md`.  Every list continues them.

## Decided

* #485/#486 a command layer of `@exposed.reads` / `.changes`
  functions (type hints and docstrings document them), three MCP
  tools `find`, `describe`, `call`, also called straight from
  `unittest`; gestures go through Qt (`QTest`), so hit testing is
  tested.  #488/#507 live objects by counted handles (`OutlineEditor
  1`), given out when first listed.  #489 nothing that moves a
  real machine (`hmi_exposed._may_move()`, simulators only).
  #492/#500 our own stdlib server.  #493 done: `scraftcam.run` is
  the only target; the HMI's functions are exposed too (#604).
* #518/#517 a recording is the tutorial and the test; tests never
  need Claude.  #520/#527 recordings are Markdown (`NAME.steps.md`),
  each step a `* ` bullet with `<!-- do: CALL -->`, one closing
  `<!-- recording ... -->` (TOML: format 2, the starting outline,
  `[[states]]` by step and call with `time`, `view`).  Only a human
  edits the prose.
* #544 the finished tutorial is script first: the user writes the
  bullets, then records into them with the panel as a teleprompter.
  #562 Whisper stays: a spoken `--record` is a notes session, the
  raw material the user rewrites (reverses #548's parking).
* #545 a step is one mouse operation (move, click, drag, wheel); no
  keys in scripts.  #547/#549 a right click marks a move step (only
  while recording; never a menu).  #546 a drawn cursor and a speed
  slider, skipped `--headless`.
* #564 no tutorial prose until the outline editor and
  `scraftcam.run` merge; recordings as regression tests now.
* Testing (the user: keep track of what makes excellent tests):
  #553 `<!-- expect: ... -->` per step; #554 a picture and the SVG
  to `~/.scraftcam/failures/` on a headless failure; #555 buttons
  and exposed functions no recording uses; #556 recordings as bug
  reports.  #561 vertex names that follow their vertex.

## Built (all four checkers clean)

* `scraftcam/exposed/`: `exposed.py` (registry, `isolated()`),
  `server.py` (MCP on 8765 alone; `.mcp.json`), `qt_runner.py`,
  `handles.py`, `client.py` (#568, below), `steps.py` (recordings;
  `parse_call()` keeps `(x, y)` as one value; `Player` forward,
  back, `place` restores a step's view (#566), `mismatches()` gives
  `step N: CALL`, the bullet and only `-`/`+` lines (#552), a step
  that raises ends the run as `failed:`).
* `gui/outline_exposed.py`: `editors()`, `state()`, `click(target)`,
  `drag(target, *, to)` (#550: `Vertex N`, `Mirror N`, `Origin`,
  `background (x, y)`, a drop also `(x, y)`; `_hit()` refuses a
  target that is not what is there), `press(keys)`, `button(word)`,
  `screenshot(name)` (#567: PNG in `~/.scraftcam/screenshots/`,
  read with Read); `view_of()`, `place_view()` (the centre within ~1
  pixel).
* `gui/recorder.py` (names the target at the press, a dropped
  vertex's snapped point, `Recorder.snapped()`; the view at each
  gesture), `gui/narration.py`, `gui/tutorial.py`.
* `scraftcam/speech.py`: `Microphone` (`pw-record`), `transcribe()`
  (faster-whisper 1.2.1, `base.en` in `~/.scraftcam/models/`),
  `split()`, `gain_problems()`.  The user's USB mic needs `amixer -c
  1 set 'Auto Gain Control' on` (#536).  #539 `mypy.ini` and
  `faster_whisper`, open.
* The standalone editor is gone (`T.og~6.9` #S5): `scraftcam.run
  --outline [FILE]`, `--tutorial FILE`, `--record [FILE]`
  (`--no-speech`), `--mcp PORT`, `--headless`
  (`gui/outline_panel.py`).  `OutlineView.fit()` fits the
  dimensions too (#572).  The GUI's and HMI's functions are on the
  same port (`window_exposed.py`, `hmi/hmi_exposed.py`).
* Tests: `test_steps`, `test_outline_exposed`, `test_outline_editor`
  (`FitTest`), `test_exposed`, `test_exposed_server`,
  `test_exposed_client`: 107 pass.  `tests/steps/move_a_corner`.

## Driving the Editor (#568)

```
python3 -m scraftcam.exposed.client start FILE      # port 8766, scraftcam.run --outline
python3 -m scraftcam.exposed.client start --gui --shown [SHOP]   # the whole GUI, on screen
python3 -m scraftcam.exposed.client call click editor="OutlineEditor 1" target="Vertex 3"
python3 -m scraftcam.exposed.client call screenshot editor="OutlineEditor 1" name=x
python3 -m scraftcam.exposed.client stop
```
PID and log in `~/.scraftcam/drive/`; use a copy of an outline in
the scratchpad (the editor saves every change).

## Open

* The #565 plan is done (#566, #568, #550, #567, #552, and #572).
  The merge (`T.og~6.9`) closed 2026-11-24: one MCP port for
  everything (#577, #585); cleanup in `T.gc~6.10`.
* #569 `find corner` finds nothing (narrations lack plain words).
* #571 the user's two live recordings use the old (x, y) form and
  no longer load: record again.
* #559 the wheel; edges, dimensions, letters as targets.
* #650 (from `T.gc~6.10`, #687): pseudo time for runs that wait on
  a machine (the LinuxCNC end-to-end suite, `tests/lcnc/`);
  headless replays already never wait.
* Later: #544 with #547/#549, #542, #543, #546, #553-#556, #561,
  #501 `--update`, #508/#514.  #516 `scraftcam.run --drive-editor` waits.

## Notes

* Never `pkill -f` an editor (it matched its own shell); the client
  stops by PID.  `ls` is aliased to `ls -l`: use `\ls` in scripts.
