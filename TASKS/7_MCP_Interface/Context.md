# LLM Agent Context Log

Made 2026-11-23 from the discussion in `T.oe~6.2` (#485-#505).
Issue numbers are shared with `T.tfo~6.5`, `T.oe~6.2` and
`T.sdl~6.8` (next new one in `T.tfo~6.5`'s notes).

## Decided

* #485 (agreed): a command layer inside the GUI, wrapped by MCP and
  called directly by `unittest`; events go through Qt (`QTest`), so
  hit testing is tested.  The user starts the GUI with `--mcp PORT`
  (localhost, HTTP); both see the same window.  Text state by
  default, screenshots only when asked.  Covers the whole GUI, and
  replaces the HMI in the end-to-end tests (`T.g~6` #426).  First
  step: the outline editor, about six commands.
* The user wants it stronger: expose vast swaths of the Python
  interfaces, since type hints and docstrings document them.  The
  user's role stays judging ease of use ("too hard to use").
* The narration says what Claude is doing, with [Forward] and
  [Backward] tied to [Undo] and [Redo] (a panel, not a pop-up: #499).
* #486 `@exposed` marks what MCP reaches, found by three
  tools (`find`, `describe`, `call`).  #487 (b): each step is one
  narrated line; [Backward] undoes to the step's start, [Forward]
  replays the next recorded step (sessions become demos and tests).
  #488 handles for live objects (`window 1 editor`); values as text
  (`"(3 + 7/8) in"`), dataclasses as checked JSON.  #489 under MCP
  only copies (in `~/.scraftcam/`) are edited; nothing that moves a
  machine is exposed; each function marked reading or changing.
  #490 `--mcp PORT` for shared sessions, `--headless` for tests,
  once the GUIs are one program.
* #491 gestures (`click`, `drag`, `press`, in outline
  units, as `QTest` events) by default, calls for quick setups; a
  fixed window size.  #492 our own stdlib server, no `mcp`
  package (no pydantic, starlette, uvicorn); package
  `scraftcam/exposed/` (`exposed.py`, `server.py`).  #493 the
  outline editor first, `scraftcam.run` once merged, never the HMI.
  #494 `@exposed.reads` / `@exposed.changes`; narration from the
  docstring's first line, arguments filled in.  #495
  `tests/steps/NAME.steps.toml` (call, arguments, narration,
  expected state text), replayed `--headless`; state text stable.
  The user: far better than out-of-date videos.
* #496 `--record FILE` writes the user's own gestures as
  steps (bug reports by doing).  #497 no generated `.md` pages: the
  `.steps.toml` is kept; a changed interface makes it fail loudly.
  #498 1280 x 800 at scale 1 by default, but the size and scale are
  settings of a session (some bugs show only at other scales);
  start with [Fit].  #499 no pop-ups: the unified GUI is tab panels
  stacked one on another, the narration panel at the bottom
  (steps, [Backward], [Forward], [Pause]).  #500 minimal MCP:
  `initialize`, `tools/list`, `tools/call`, `ping`, plain JSON, no
  streaming, localhost.
* #501 `--update` replays a failing recording, shows each changed
  step (old state, new, difference) and writes back the accepted
  ones.  #502 recordings are stable and self-contained (the starting
  outline file copied in as the first table) and versioned (a format
  number and the scraftcam version they were made with), since code
  changes will break them.  #503 `--record` writes to
  `~/.scraftcam/recordings/` by default; kept ones move to
  `tests/steps/`.  #504 the editor's state text (a start; it will
  change): corners, dimensions (letter, kind, ends, value), the
  letters table, the selection, each item's color (black, red,
  orange), the problems, the undo depth; no pixels.

## The Plan (Steps added, removed and changed at will, #505)

* #S1 `scraftcam/exposed/`: decorators, registry, `find`,
  `describe`, `call`; tests without Qt.
* #S2 `server.py` (stdlib, minimal MCP), its `urllib` test, the
  `.mcp.json` entry.
* #S3 the outline editor's `--mcp` and `--headless`, gestures, state
  text.
* #S4 the narration panel.
* #S5 `--record`, replay, `--update`; the first recording in
  `tests/steps/` (#479, the dimension across the axis).
