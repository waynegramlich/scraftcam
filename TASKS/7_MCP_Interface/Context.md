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
* #520 recordings move from TOML to Markdown, edited by hand in
  Emacs with spelling and grammar checking; the `.md` is the source
  (reverses #497).  Only a human edits the prose; tools write only
  calls and states.  Steps are `* ` bullets (tight lists; never
  numbered lists, which renumber); read with the standard library,
  errors by line; the panel renders the prose with Qt's Markdown.
  Readers are not expected on GitHub.
* #521 speech: the microphone recorded with the steps; local Whisper
  (word times) gives each step its draft narration, which the user
  edits.  The user has a working microphone; wants help installing.
* #522 order: (1) the `.md` format, `move_a_corner` converted;
  (2) `--record` writing `.md`, a time per step; (3) `--update`;
  (4) microphone and Whisper.  #508 and #514 (colors and values in
  the state) when tutorials need them.

## Proposed, awaiting the user (defaults if unanswered)

* #523 a step's call is a code span alone on its bullet's last line
  (`` `click -4, -3` ``, `` `drag 0, 4 -> 1, 6` ``); continuation
  lines indented 2; nested bullets belong to the step; a bullet with
  no call is a pause to read.
* #524 `#` title, `##` sections (chapter breaks in the panel);
  paragraphs outside the list are an introduction; the starting
  outline under `## Start` in a ```` ```toml ```` block.
* #525 states in a sidecar `NAME.states.toml` beside
  `NAME.steps.md`, written only by tools, matched by position and
  call (an inserted step is "no state yet").
* #526 Whisper: `faster-whisper` through `packages.require()`;
  model `base.en` (~140 MB) or `small.en` (~470 MB); check Qt sees
  the microphone.  At #522 (4) only.

## Built (all four checkers clean)

* `scraftcam/exposed/`: `exposed.py` (registry, `call()` checks
  JSON kinds; refusals say ``is not of type `float` ``, #513),
  `server.py` (`Server(runner)`, `serve(port)`; alone it serves
  `samples.py` on 8765, named in `.mcp.json`; tried from Claude
  Code, #509), `qt_runner.py` (`QtRunner`: calls handed to Qt's main
  thread, 60 s timeout, #512), `handles.py` (`Handles`), `steps.py`
  (format 1 TOML, `Player` forward/back/`mismatches()`,
  `recording_text()`).
* `scraftcam/gui/outline_exposed.py`: `HANDLES`, `EDITORS` (a
  `WeakSet` filled by whoever makes an editor: run with `-m` the
  editor module is `__main__`, so its class cannot be imported to
  find it); `editors()`, `state(editor)`, gestures `click`, `drag(...,
  *, to_x, to_y)`, `press(keys)`, `button(word)` (#515), each
  returning the new state; points in drawing steps, Y up.
* `gui/narration.py` (`NarrationPanel`), `gui/tutorial.py`,
  `gui/recorder.py` (`Recorder`: application-wide event filter;
  viewport click/drag, `QShortcut.activated`, `QToolButton.clicked`;
  a step is filed with its state when the next gesture starts or Qt
  is idle; skips a deleted viewport).  Not recorded: the letters
  table, wheel, panning, held modifiers.
* `outline_editor.main()`: `--mcp PORT`, `--headless`, `--tutorial
  FILE` (never saved; `--headless` checks, exit 0/1), `--record
  [FILE]`.  #519 fixed: `drawing_from_text()` keeps `holes`.
* `tests/steps/move_a_corner.steps.toml`; `test_steps` (6, incl.
  record-then-replay), `test_outline_exposed` (4), `test_exposed*`
  (14), `test_outline_editor` (78).
* #516 `./drive_editor.py`: the editor `--mcp` on a free port beside
  a Konsole running `claude` in `~/.scraftcam/drive/` (its own
  `CLAUDE.md`, `mcp.json`, three tools allowed), with no project
  context.  Not yet run by the user; waits.

## Next

* #522 (1): the `.md` format, after the user's answers to #523-#526.

## Notes

* A launched editor's command line holds its own text: find it with
  `ps -eo pid,args | grep "[o]utline_editor" | grep -v "bash -c"`,
  not `pkill -f` (it matched the calling shell twice).
