# LLM Agent Context Log

Made 2026-11-23 (#573-#575); squeezed 2026-11-23 (history in `hg`
and `git`).  Issue numbers are shared with `T.tfo~6.5`, `T.oe~6.2`,
`T.sdl~6.8` and `T.mi~7`; the next is in `TASKS/Issue_Counter.md`.

## Starting Points

* `T.mi~7`'s notes (Reference): the MCP layer, recordings, and
  driving a headless editor with `scraftcam.exposed.client`.
* `T.g~6` (Suspended): `scraftcam/run.py`, `gui/window.py`,
  `gui/views.py` (`Panel`), `gui/machines.py`, `gui/tree.py`.

## Decided

* #577/#585 one MCP port only (several risk races): `scraftcam.run`
  gets `--mcp PORT` (8765) and `--headless`, the client starts it,
  tests take a free port.  `window.py`'s `CommandServer` (JSON lines,
  `port.py`: `new_shop`, `press`, `quit`, `select`, `status`,
  `tree`) becomes `@exposed` functions and goes.
* #578 one tree holds everything; one window now, more later, each
  with [Tree] to show or hide it; one uniform panel architecture in
  every window; horizontal tabs to condense content.  The outline
  editor is a panel of the tree like any other.
* #583 the tree is 100% shared, its view is not (already so:
  `Window.model` shared, `Window.tree` per window).
* #584 tools live in the shop's directory tree; an outline file sits
  with its tool, and the tree shows it.
* #578c the editor saves every change, no [Save].  #578d the
  standalone editor stays until the tests are cleaned up.
* #587 (to try) the tool's panel gets an [Outline] tab holding the
  editor.  #588 (to try) [Enable Editing] applies to the editor; the
  user dislikes checking it all the time, so watch for that.
* #589 the editor's shortcut keys go entirely (a key can reach the
  wrong panel); buttons only.  Typing into the letters table stays.
* #579 the exposed outline functions find an editor in a panel, and
  the recordings replay there (part of #S3).
* #581 list what the HMI has that the machine panel lacks (#57),
  after the editor is merged.

## Found (#582)

* `OutlineEditor` (`gui/outline_editor.py`) is a `QWidget`, so it
  embeds; `main()` shows it alone (1280 x 800).  Its tabs: buttons
  (#319), Drawing/SVG, Dimensions/Fillets.  Keys are `QShortcut`s.
* `Panel` (`gui/views.py`) is one column (title, [Enable Editing] /
  [Edit TOML File], fields, read-only text), no tabs.
* The tree has no outline node kind; `tree.edit_path()` opens
  `.toml`/`.py` outside.

## Steps

* #S1 done (#580, `T.g~6` #426): all 10 of `test_lcnc_end_to_end`
  pass (135 s).  The tests wait for Start (`start()`) and follow
  the one run button.  HMI bug fixed: any return to idle (Home, MDI,
  Set Origin) set `ended`, so a new program showed [Restart]; now
  only a program run (`program_run`) ends a run.  Run: `podman start
  lcnc`, then `SCRAFTCAM_LINUXCNC=1 QT_QPA_PLATFORM=offscreen
  python3 -m unittest -v tests.test_lcnc_end_to_end` (allow 200 s).
* #S2 next: #577 + #585.
* #S3 the editor as a panel: #578, #579, #587, #588, #589.
* #S4 #581.

## Open

* #586 tabs in every panel: the user leans yes (a second tab then
  changes the documentation little); not final.
