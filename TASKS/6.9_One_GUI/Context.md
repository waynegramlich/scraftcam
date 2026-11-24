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
* #S2 done (#577, #585): `scraftcam.run --mcp PORT` serves MCP
  (`window.run()`, `QtRunner`); `gui/window_exposed.py` has
  `status`, `top_button(label, window_number)`, `new_shop`, `tree`,
  `select`, `quit_all`.  `CommandServer`, `port.py` and
  `test_gui_port` are gone (`test_window_exposed`, 4 tests, replaces
  it).  `client start --gui [SHOP] --port N` starts the GUI headless
  (`parse_intermixed_args()`).  Checked live on `examples/shop`.
* #S3 the editor as a panel: #578, #579, #587, #588, #589.
  * Done #589: no `QShortcut`s (`BUTTON_WORDS`, labels without
    keys); `outline_exposed.press` and the recorder's `press` gone;
    `move_a_corner` uses `button Undo`.
  * Done #587/#588 (first cut): `Panel.tabs` ([Fields], and
    [Outline] when `views.outline_of()` finds `KIND.outline.toml`
    beside the tool); `Panel.show_outline()` keeps the editor for
    the same file, greys it unless [Enable Editing], adds it to
    `outline_exposed.EDITORS` (#579's first half).  Loaded by
    `importlib` (outline_editor -> window -> views cycle).
    `tests/test_panel_outline.py`.
  * Done #590 (#590a-c agreed): [Enable Editing] is now [Allow
    Changes] (unchecked = read only).  `OutlineEditor.set_read_only()`
    greys `CHANGE_WORDS` (Undo, Redo, Delete, Dimension, Dim. Kind,
    New Letter, Revolve, Hide, Rotate Diagram) and [New Fillet
    Dimension], stops table typing and arming; `OutlineView.read_only`
    swallows drags in `mouseMoveEvent` ("Check [Allow Changes]
    first.").  Zoom, pan, choosing, Fit, Grid, Snap, Overview, Show
    Marks, Font +/- stay live.
  * Done #593 (#579's second half): `tutorial.mismatches()` sizes
    `editor.window()`; `steps.compared()` skips `UNCOMPARED` state
    lines (`file: `, which depends on where a replay runs);
    `test_panel_outline.ReplayInPanelTest` replays every
    `tests/steps/` recording in a tool panel's editor.
  * Done #595: `scraftcam.run --tutorial FILE [--headless]`
    (`gui/run_tutorial.py`, `window.open_tutorial()`,
    `Panel.hold_editor()` / `drop_outline()`); tests in
    `test_window_exposed.RunTest.test_tutorial`.  Also
    `client start --gui --shown`, `panel_tab`, `to_front` (#596
    found live: the drawing is cramped in a panel).
  * #592/#594 (the user): leave [Outline] and the tree as they are;
    things will change (two dimension views to unify) once the other
    GUIs are gone.  Usability issues wait until the steps are done.
  * Left: the user trying
    the tab live; the tree still hides outline files (`tree.py`,
    "Until #S7").
* #S4 folded into #S7.  Decided (#597-#603): nothing else until
  exactly one GUI; old programs become `scraftcam.run` flags (#603,
  e.g. `--show-demo`); test suites stay separate files (#0);
  SolidCraft does not count (#602: STEP import and geometry queries
  deferred to `T.c~6.3`, McMaster-Carr `.step` downloads).
* #S5 (#599) done: `outline_editor.main()` is gone (not executable
  now); `gui/outline_panel.py` (was `run_tutorial.py`) has
  `OutlinePanel` (`--outline [FILE]`, `--tutorial`, `--record
  [FILE]`, `--no-speech`; `window.FirstPanel` protocol, `finish()`
  after Qt) and `record_path()`.  `client start [FILE]` runs
  `scraftcam.run --outline`; `drive_editor.py` too.  Unit tests
  still build `OutlineEditor` widgets directly (fine: no window).
* #S6 (#600) done: [Open Pages] puts `catxtract.App` in the
  catalog panel's [Pages] tab (`Panel.show_pages()`/`drop_pages()`;
  leaving the item closes it, saving marks); `scraftcam.run --pages
  CATALOG` (`window.CatalogPanel`); `catxtract.main()` gone.  Not
  tried live with a real PDF (tests use a written one).
* #S7 (#598, #581, #426) the HMI into the machine panel; LinuxCNC
  tests over MCP; `lcnc_hmi.main()` goes.  #581 found: the HMI
  widget already sits in the machine panel (`scraftcam.run
  --program`), so what is left is its plumbing, #604-#608 (for the
  user to sort): #604 its line port (`hmi_machine.CommandPort`,
  `HMI.answer_line()` words: ping run start pause stop reset tool+
  tool- quit press origin tab type show answer open speed status
  messages log) -> `@exposed` on the one MCP port; #605
  `lcnc_hmi.main()` and its options (scraftcam.run already has
  --program --hmi-port --solidcraft --lcnc-port --dry-run); #606
  its pop-up dialogs (`ask_yes_no`, `ask_choice`, `ask_open_file`;
  headless `answer`); #607 opening a machine's HMI from the
  machines list, not only `--program` at start (maybe `T.g~6`);
  #608 `test_lcnc_hmi`, `test_lcnc_end_to_end`, `show_demo.py
  --headless` drive the port -> MCP.
  Decided (the user): #604 MCP port only; #605 gone; #606 no
  screen-wide pop-ups: a prompt pops up inside the panel (or the
  part of it, e.g. the dimensions table) where the fix is made,
  greying only that; #607 users run `scraftcam.run` with no flags,
  flags are for Claude only, so all a user does is in the GUI
  (opening a machine's HMI from the machines list); #608 one port.
  #489 (`T.mi~7`) read as "no real machine": machine-moving calls
  go through one simulator-only check (told the user).
  * Done #604 (first half): `hmi/hmi_exposed.py` (`hmis`, `hmi_show`,
    `hmi_status`, `hmi_messages`, `hmi_log`, `hmi_press`,
    `hmi_origin`, `hmi_tab`, `hmi_type`, `hmi_open`, `hmi_speed`,
    `hmi_answer`), each through `HMI.handle()`; `run.py` registers
    the HMI (`HMIS`).  `_may_move()` is the simulator check (allows
    all today).  Tried live: `--headless --dry-run --program
    demo.ngc --mcp 8772`.
  * Done #605: `lcnc_hmi.main()` and `run()` gone (not executable).
  * #608: `test_lcnc_hmi` (`TestMakeSolidCraft` via `make_hmi()`,
    `TestHeadlessProgram` via `scraftcam.run --dry-run --mcp`, 63
    pass) and `test_lcnc_end_to_end` (`start_hmi()` runs
    `scraftcam.run --headless --shop examples/shop --program demo.ngc
    --mcp`, `ask_hmi()` -> `hmi_line`) switched.  The end-to-end
    suite is NOT yet run (needs `podman start lcnc`, ~135 s; ask).
  * #612 fixed (a real bug the suite found): `HMI.busy()` answered
    from the last poll, so a Quit just after LinuxCNC went idle was
    refused ("is running"); it polls first now.  `make_hmi()` polls
    once at start (before the drawer), so the spindle (on until
    known) is known.  `status` answers `spindle=` and `rpm=`.
    `scraftcam.run --hmi`: the machine panel with no program
    (LinuxCNC keeps its own), used by `start_hmi()`.
  * Decided (#609-#611): "safe" is per machine kind (spindle, flood/
    mist coolant, motion; a laser's laser); a window with an active
    machine forces its tree on ([Tree] greyed), active machines drawn
    like [Stop All] and expanded; a refused Exit names every active
    machine and why, brings their windows forward, no pop-up.
  * Done #609: `HMIStatus.coolant` (flood, mist) refuses closing.
  * Done #610/#611: `Window.show_active()` (each `STOP_MS`): tree
    forced on, [Tree] greyed, `TreeView.mark_active()` draws active
    machines' items like [Stop All]; `active_reasons()`,
    `refuse_exit()`: a refused [Exit]/close says "Stop first: ..."
    and brings their windows forward.  `ask_to_stop()`,
    `ask_to_leave()`, `exiting`, `leaving` gone (no questions).
  * Done #606: `gui/prompt.py` (`Shade`, `run_in()` waits in a local
    loop, `show_in()` for forms, `ask_yes_no`, `ask_item`,
    `ask_open_file`, `ask_directory`; `ANSWERS` queue for tests and
    MCP).  The HMI's three questions, Close Panel's question, the
    ignores offer, [New Shop]/[New Machine]/[New Catalog] (shown in
    the current panel) and their file pickers (inside the form).  No
    `QMessageBox`/`QFileDialog`/`exec()` left outside `prompt.py`.
  * Done #607: `window.MachineMakers(first, connect)` (run.py's
    `machine_maker(..., program=)`, `make(name)`); opening a machine
    that is not connected connects it (`Window.open_machine()`,
    `CONNECT`), one LinuxCNC so far (a second is refused, naming
    `T.rslsao~5.8`).  `open_machine(name)` over MCP.  Tried live.
  * Left: the line port (`CommandPort`, `--hmi-port`) goes with
    `show_demo` (#S8); #606 in-panel prompts; #607 HMI from the
    machines list.
* #S8 (#601) done: `scraftcam/show_demo.py` and
  `scraftcam/drive_editor.py` (moved in, not executable; `main(
  arguments)`), run as `scraftcam.run --show-demo ...` and
  `--drive-editor ...` (the rest of the line is theirs).  show_demo
  drives the HMI over MCP (`hmi_line`, default port 8765).  The
  HMI's line port is gone (`CommandPort`, `--hmi-port`, `HMI(...,
  port)`, `make_hmi(port=)`).  `--show-demo --headless` run
  2026-11-24: exit 0 in 107 s (setup drawn 11 s, program 100 s, 57
  bodies, Quit closed everything, nothing left running).  The
  LinuxCNC end-to-end suite passed again after the port removal.

## Open

* #586 tabs in every panel: the user leans yes (a second tab then
  changes the documentation little); not final.
