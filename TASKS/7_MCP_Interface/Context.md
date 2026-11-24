# LLM Agent Context Log

Made 2026-11-23 from `T.oe~6.2` (#485-#505); squeezed 2026-11-23
before a commit (history in `hg` and `git`).  Issue numbers are
shared with `T.tfo~6.5`, `T.oe~6.2` and `T.sdl~6.8`; the next new
one is in `T.tfo~6.5`'s notes.  Every list continues them.

## Decided

* #485 a command layer in the GUI, wrapped by MCP, called directly
  by `unittest`; gestures go through Qt (`QTest`), so hit testing is
  tested; text state, screenshots only when asked.  Expose vast
  swaths of the Python (type hints and docstrings document it); the
  user judges ease of use.  Replaces the HMI in the end-to-end tests
  (`T.g~6` #426).
* #486 `@exposed.reads` / `.changes` (#494), three MCP tools
  `find`, `describe`, `call`; narration from the docstring's first
  line.  #488 handles for live objects, values as text (#508),
  dataclasses as checked JSON.  #489 only copies edited; nothing that
  moves a machine.  #492 our own stdlib server (#500: `initialize`,
  `tools/list`, `tools/call`, `ping`; localhost).  #493 the outline
  editor first, `scraftcam.run` once merged, never the HMI.
* #507 handles counted per class in the order made (`OutlineView
  1`, the same on every replay), held weakly.
* #498 1280 x 800 by default (size and scale settable later); [Fit]
  at start.  #499 no pop-ups: the narration panel at the bottom.
* #501 `--update` replays, shows each changed state as a diff, and
  writes back the accepted ones.  #502 recordings self-contained and
  versioned.  #503 `--record` into `~/.scraftcam/recordings/`; kept
  ones move to `tests/steps/`.  #504 the state text: corners,
  dimensions, letters, selection, colors, problems, undo depth.
* #518 (the user: "a tutorial that runs without needing Claude
  Code"): the recording is the tutorial and the test; Claude is only
  one way to write one.  #517 tests never need Claude.  The user
  tried it: "I love it" (FreeCAD videos go far too fast).
* #520 recordings are Markdown (`NAME.steps.md`), edited by hand in
  Emacs; only a human edits the prose; tools write only the HTML
  comments.  #527 (agreed): each step a `* ` bullet (tight lists,
  never numbered), its call in `<!-- do: CALL -->` on its last line;
  one closing `<!-- recording ... -->` (TOML: format, version, the
  starting outline, `[[states]]` by step number and call, with
  `time`).  `#` title, `##` sections, other text the introduction.
  Readers are not expected on GitHub.
* #544 (2026-11-23, after the user's first spoken recording): the
  script comes first.  The user writes the bullets, then records
  INTO the script: the panel is a teleprompter showing the next
  bullet, and each mouse operation fills that bullet's `do:` and
  advances; an unplanned one gets a new placeholder bullet.  No audio
  (#548: Whisper and `speech.py` are parked, not deleted; #540,
  splitting speech by sentence, dropped).
* #545 a step is one mouse operation: move, click (forefinger only),
  drag, wheel.  Toolbar buttons are clicks on them; keys are not
  used in scripts (the user: they take the hand off the mouse).
* #547/#549 recorded: left press/move/release (click or drag),
  wheel, and a right click marks a move step to that spot (only
  while recording; never a menu, which the user dislikes).
* #546 a drawn cursor in the view (Qt's pointer does not move for
  sent events): it glides to each target, a ring for a click, a
  trail for a drag, +/- for the wheel; a speed slider in the panel;
  skipped `--headless`.
* #550/#557 steps name what they act on, not (X, Y): `click Vertex
  2`, `click Button "Undo"`, `drag Vertex 2 -> (5, 3.5)` (the
  snapped point when the drop lands on nothing), `drag Vertex 2 ->
  Vertex 0`, `click background (1, 2)`; replay checks the same thing
  is hit.  #558: names are as of that step (vertices renumber).
  #559 `wheel N at TARGET` (Qt notches, negative zooms out).
  #561 (to design with #550): vertex names that follow their vertex,
  kept in the outline like letters, for readable, robust scripts.
* Testing (the user: keep track of what makes excellent tests):
  #541/#551 exact replay: a fixed window, the view (zoom, centre)
  recorded per step and restored before it.  #552 a failure gives
  the step's number, bullet and only the changed lines.  #553 `<!--
  expect: ... -->` checks per step; full states stay for
  `--update`.  #554 on a headless failure save a picture and the
  SVG to `~/.scraftcam/failures/`.  #555 list the buttons and
  exposed functions no recording uses.  #556 recordings as bug
  reports and regression tests (by the user, or Claude over MCP).

## The Plan (agreed 2026-11-23)

1. #542 (words joined with extra spaces: "two -dimensional"; moot
   while speech is parked) and #543 (no file when nothing was
   recorded).
2. #541/#551 the view per step.
3. #544 with #547/#549: recording into a script; move, wheel, the
   right-click mark.  Format 3; `move_a_corner` converted again.
4. #550 named targets (#557-#559), #552 differences.
5. #546 the drawn cursor and speed slider.
6. Later: #553-#556, #561, #522 (3) `--update` (#501), #508/#514.

## Built (all four checkers clean)

* `scraftcam/exposed/`: `exposed.py` (registry; `call()` checks
  JSON kinds; `isolated()` for tests, #529), `server.py` (stdlib
  MCP; alone it serves `samples.py` on 8765, `.mcp.json`),
  `qt_runner.py` (`QtRunner`, #512), `handles.py` (#507),
  `steps.py` (format 2 Markdown: `recording_from_markdown()`,
  `recording_markdown()`, `parse_call()`/`call_text()` with values
  in signature order and `->` before `to_`; `Step.time`; `Player`
  forward/back/`mismatches()`).
* `gui/outline_exposed.py`: `HANDLES`, `EDITORS` (a `WeakSet`: run
  with `-m` the editor is `__main__`, its class not importable);
  `editors()`, `state()`, `click`, `drag(..., *, to_x, to_y)`,
  `press(keys)`, `button(word)`, each returning the new state.
* `gui/narration.py` (`NarrationPanel`: step list, the next step's
  Markdown, [Backward]/[Forward]/[Play]), `gui/tutorial.py`,
  `gui/recorder.py` (application-wide event filter; viewport
  click/drag, `QShortcut.activated`, `QToolButton.clicked`; a step
  is filed when the next gesture starts or Qt is idle; `speech=`,
  `finish()`).
* `scraftcam/speech.py` (parked, #548): `Microphone` (`pw-record`,
  #533), `transcribe()` (faster-whisper 1.2.1, `base.en` in
  `~/.scraftcam/models/`; samples via `wave`, its PyAV path broken,
  #538; `condition_on_previous_text=False` stops loops), `split()`,
  `gain_problems()` (#537).  The user's USB boom mic needs `amixer
  -c 1 set 'Auto Gain Control' on` (#536).  #539 open: `mypy.ini`
  could see `faster_whisper` (now `import-not-found` ignores).
* `outline_editor.main()`: `--mcp PORT`, `--headless` (1280 x 800),
  `--tutorial FILE`, `--record [FILE]` (`~/.scraftcam/recordings/`
  by default; speech unless `--no-speech`).
* Tests: `test_steps` (6), `test_speech` (3), `test_outline_exposed`
  (4), `test_exposed*` (14), `test_outline_editor` (78); all pass
  together.  `tests/steps/move_a_corner.steps.md`.
* #516 `./drive_editor.py` (Claude beside the editor with no project
  context): not yet run by the user; waits.
* The user's first live recording (spoken, 7 steps):
  `~/.scraftcam/recordings/new_2026-11-23_16-34-48.steps.md`; its
  replay differs at step 2 (snap depends on zoom: #541).

## Notes

* A launched editor's command line holds its own text: find it with
  `ps -eo pid,args | grep "[o]utline_editor" | grep -v "bash -c"`,
  not `pkill -f` (it matched the calling shell twice).
* `ls` is aliased (to `ls -l`); use paths or `\ls` in scripts.
