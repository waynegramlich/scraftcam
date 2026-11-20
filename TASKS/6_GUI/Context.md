# LLM Agent Context Log

Trimmed 2026-11-13 and 2026-11-15: only decisions still in force and
where things stand.  The full history is in `hg` and `git`.  Issue
numbers are sticky (code comments cite them); new ones continue after
#210.

## Decisions in Force

* Toolkit and platforms: Qt (PySide6, fetched by `packages.require`,
  no venv); Linux (Wayland) and Windows; no macOS (#21, #52, #55).
* One GUI, `python3 -m scraftcam.run` (#93, #103): `--shop`,
  `--design`, `--port`, `--headless`, and for a machine `--program`,
  `--hmi-port`, `--solidcraft`, `--lcnc-port`, `--dry-run` (#53).
  With no `--shop`, `shop.toml` is looked for here and in the parents
  (#83).  LinuxCNC only when needed (#1; today `show_demo.py` starts
  `serve_linuxcnc`, the GUI connects, #55).
* Windows: one model shared by all windows (#3); pop-ups allowed;
  720 x 480 at start (#109).  Never crash a machine: nothing closes
  (window, GUI, `SIGTERM`/`SIGINT`) until every machine is stopped
  with its spindle off (#56, #67).
* Top line (#82), on every window: [Stop All] first, always shown:
  greyed while no machine runs, red, bold and heavily boxed while any
  does (#100); [Tree], latest message (red for problems, #95),
  [+ Panel], [New Window], [Exit] (see "Windows and Panels").  Action
  rows under it (#73); no right click; no icons, a kind in
  parentheses.
* No shop: "No shop yet: [New Shop]", the dialog at start (#97-#118).
  Never `git init`; suggest `git` or `hg` (#99, #107).
* Tree (#119-#128): two roots (shop, design); directories first;
  files sorted by what they show; tools labeled by function and
  sizes, e.g. "End mill (1/2in 2-flute HSS)", sorted by function then
  size (#21); every item has a tooltip saying what it is (#80); bad
  files red "(error)"; watched (no [Refresh]); fitted to its labels,
  refitted on open/close (#22, #43).
* Panels (#122): a click shows the item in a panel by the pin rule
  (#201).  A shop item: a row per field, `key (L)` with its sketch
  letter (#19), all of its kind's sketches to the right, top view
  first (#42).  The lines between them fit themselves to what is
  there on each new item (#43); every line has a grip and highlights
  on hover (#25, #44).  [Edit TOML File] opens `$VISUAL`/`$EDITOR`/
  the desktop's editor (#77, #124).
* Light and dark follow the desktop (`gui/theme.py`), no hard-coded
  colors, sketches recolored (#24).
* Command port (#96, #110): JSON lines on 127.0.0.1: `status`,
  `press`, `new_shop`, `tree`, `select` (answers `fields` too),
  `quit`.  The HMI keeps its own line port (5007) for now (#54).
* Shop data (#4-#19, #64, #129-#133): the user's shop is a directory
  under their version control; one item per `.toml`; `shops.KINDS` is
  the one schema (JSON Schemas from it); our writer orders keys.
  Directories: `controllers/`, `tool_materials/` (`tool_material`:
  `speed_factor`, HSS 100 %), `tools/`, `tooling/`, `stock_materials/`
  (cutting data and the materials cut), `machines/` (#23).
* Sketch letters (#18-#20, #26): `shops.dimension_letters()`: a
  name's first letter; taken -> a lower case letter from its other
  words' initials, then its other letters; fewer words choose first;
  `part.size` -> the part's letters plus the size's.  `KINDS` letters
  follow it (a key may differ between kinds: `corner_radius` C on
  cutters, Cr on the grid plate).
* Grid plate (#28-#38, #45): `GridPlate(rows, columns, pitch, edge,
  thickness, hole_diameter, corner_radius, chamfer_width,
  edge_chamfer, tooling_pitch, tooling_tap_diameter,
  tooling_close_diameter)`; length and width from the grid; tooling
  holes as many as fit, checkerboard, tapped lower left.  Its sketch
  is a made-up 16 x 12 plate broken into four 4 x 4 corners (meshing
  long break lines, the edge chamfer line), cut A-A across the upper
  left corner; "SECTION A-A" at 2x, hatched.
* Values (#15): checked as typed, never written bad; no [Save].
* Catalogs (#87, #88): tables and text under version control.
* Deferred: #90-#92, installer and PyPI (#54, #56, #57, #89), panel
  menu (#71).
* `scraftcam/gui/README.md` (#10) comes at the very end of this task,
  after the LinuxCNC GUI and the catalog work are merged in.

## The Machine Panel (step 5), decided so far

* A machine's header: its name over a bar that fills from black as
  the operator's next tool task comes (a carousel swap, or with no
  tool changer every change), full when due, black again after
  (#102, #106); its text the time left, "▲" within a minute, "■ NOW"
  blinking while waiting: not color alone (color blind operators).
* Inside a machine: one run button named Start / Pause / Resume /
  Restart (#96), [Skip Tool] (#97), [Stop]; S rpm and F in/min (#86,
  #98); the slider behind [Expert] with a confirming question (#79);
  no speeds-and-feeds table (#72).  The layout today: "The Machine
  Panel (in force 2026-11-15)" below.
* Machines view vs machine view (#134-#138, 2026-11-14):
  * `machines/` directory view: a row per CNC machine (name, kind,
    state, job progress, next-task bar, a field or two per kind);
    non-CNC machines one line each; a short list of the next tools
    to fetch across all machines (#134).
  * A click opens one machine (today's tab insides) in its own
    panel; the per-machine tabs (#101) go; expect iteration (#135).
  * The bar is the next operator task: tool or carousel change
    (mill, router, lathe), filament or print end (3D printer),
    material or focus (laser) (#136).
  * Per kind fields and a `KINDS` entry per machine kind: mill,
    router, lathe, laser, 3D printer; only the mill now (#137).
  * A small controller interface (status, load, start, pause,
    resume, stop, jog, MDI, next task); LinuxCNC only now; later
    GRBL/FluidNC, Moonraker, OPC UA; MTConnect is read only, so
    view only, and [Stop All] reports it cannot stop it (#138).
  * Second cut (2026-11-14): the shop's root item is a splash
    (scraftcam, the shop, the NC program; `App.program`), and the
    first panel starts on it; `machines/` is a list: three lines per
    CNC machine (name button with kind, controller, state; details;
    bar), one per other machine, then the tools to fetch
    (`gui/machines.py`).  A window holds its machines
    (`Window.machines`, `connect_machine()`) and shows one only when
    it is clicked, in the list or the tree (`open_machine()`,
    `connected_name()`); [Stop All], busy, the stopper use
    `Window.machines`.  A machine file with no `controller` counts as
    not CNC, but the schema still requires one (#137 to do).  Tests:
    `tests.test_gui_machines`.
* Controllers and machines (#139-#142, 2026-11-14):
  * A machine file needs `controller` (kept required).  No blank
    start: the first panel shows a short guide ([Tree]; controller
    templates; [Stop All]; click an item) until something else is
    shown; the shop's root shows `shop.toml`'s fields (#139).
  * `Enable Editing: [ ]` per panel, in the action row: checked only
    for an item just created; otherwise read only, and [Edit] (the
    editor) greyed while unchecked.  No accidental edits (#140).
  * `controllers/` holds controller templates; scraftcam ships a
    LinuxCNC one, copied in by [New Shop].  [New Machine] is greyed
    until a template exists; a new machine picks one and gets its own
    `[controller]` copy plus `template = "NAME"`; the shop code reads
    the machine's copy.  [New Shop] no longer makes machines (#141).
  * A template change is followed up by whoever makes it, at once,
    in the template's panel: the machines from it, each changed
    field's value; old value -> [Update] (one or all), own value ->
    shown for the editor to update or keep.  Never pushed onto the
    operator: no marks on machines.  Old values: known in the panel,
    or kept from the last read for [Edit]-ed files; edits with the
    GUI closed are left to version control (#142).
  * Coded 2026-11-14, awaiting the user's GUI run: #139 (`GUIDE`,
    `Panel.show_guide()`); #140 (`Panel.editing`, `set_editing()`,
    `Window.editing_box`, `App.created`); #141 (a name in place of a
    table is refused in `shops._Reader.table()`; `controller` kind's
    `template`; `scraftcam/templates/controllers/linuxcnc.toml`,
    copied by `create_shop()`; `App.new_machine()`,
    `NewMachineDialog`, starting axes/spindle `NEW_AXES`/
    `NEW_SPINDLES`; example machines converted; `Shops.md` and the
    JSON schemas regenerated); #142 (`gui/templates.py`:
    `follow_ups()`, `update_machine()`, `FollowUpView`; `Panel.write()`
    and an outside change of a shown template).  Not touched:
    `scripts/convert_shop.py` (old one-off, still writes a controller
    by name).  Tests: `test_gui_templates`, `test_gui_machines`, and
    the shop-reading suites (not the slow model-building ones).
* Versions, not initialized, key order (#143-#146, 2026-11-14):
  * `scripts/convert_shop.py` deleted (#143).
  * A controller (template and copy): `vendor`, `product`,
    `vendor_version` (the vendor's text, as written),
    `vendor_triple` (our analysis of it, `[MAJOR, MINOR, PATCH]`,
    filled in when `vendor_version` is entered, editable, `[0, 0, 0]`
    unknown), `support_ended` (a date or "unknown").  No template
    revision for now (#142 follows a change up at once) (#144).
  * A key left out means "Not initialized yet": not an error.  Fields
    needed only to run (axis `travel`, `max_feed`; the spindle) are
    no longer required; the panel shows a row for each missing one,
    "Not initialized yet", quiet; the machines list says so; running
    a program stops, naming them.  Still errors: the header,
    `machine`, `controller`, unknown keys.  A new machine gets only
    its kind, axis letters and controller copy (#145).
  * Our writer's key order: the header first (`name`, `kind`,
    `language`, `version`, `notes`), then the other keys
    alphabetically, then the tables alphabetically (#146).
  * Tests: checkers and the small test files only, until the user has
    run the demo.
  * Coded 2026-11-14, awaiting the user's demo run: `TableField.needed`
    (axis `travel`, `max_feed`; `spindle`, its `interface`,
    `max_rpm`), `shops.not_initialized()` (also in `cnc_machine()`),
    the `triple` form, `shops.vendor_triple()`, the controller's
    vendor fields (the LinuxCNC templates have `vendor`, `product`);
    the panel's quiet "Not initialized yet:" line
    (`Panel.show_missing()`, nested fields are not rows), the
    machines list's state; `shop_writer.ordered()`.  Example files
    are hand written, not rewritten in the new order.
* To come: the Job tab as a job:
  a directory of `.nc` files, one tool each, run in name order,
  loaded from the tree (#74, #77, #78); a Tool Table tab: a tool's
  length (spindle nose to tip) by setter, dial
  indicator cube (2 in) or paper and micrometer, all `G10 L10 P<n>
  Z<height>` (#80, #81); our data keeps the offsets and shows them
  for other controllers (#83).  `lcnc_hmi.py` goes once all of it is
  in the GUI (#57).  Later: the GUI starts LinuxCNC itself (#64), one
  command port (#65), the catalog work (#66, `T.cm~6.3`).

## Step Order (#13)

1. Top line: done.  2. Tree: done.  3. Shop schema and files: done.
4. Tool documentation: done (sketches in panels, tooltips; the
   directory documentation page was tried and dropped, #80).
5. Machine control: under way (above).

Each step: offscreen tests, checkers, the user's GUI run; done only
when the user likes it (#85, #112).

## Where Things Are

* `scraftcam/gui/`: `app.py` (model), `fields.py` (field rows,
  `sketches()`), `views.py` (`TreeView`, `Panel`, `MachineControl`,
  `Due`, `MachineTab`, `GripSplitter`), `window.py` (`Window`,
  `Stopper`, `CommandServer`, `NewShopDialog`), `layout.py` (the kept
  layout), `theme.py`, `tree.py`
  (`about_item()`, `about_directory()`), `editor.py`, `port.py`.
* `scraftcam/run.py`: `machine_maker()` makes the HMI for a panel
  (imports `scraftcam.hmi` only with `--program`).
* `scraftcam/hmi/lcnc_hmi.py`: `make_hmi()`, `HMI.busy()`, `quit()`,
  `intervention()`, `narrow()`; `hmi_machine.py`:
  `HMIStatus.spindle/rpm/feed`, `tool_plan()`, `next_intervention()`,
  `Intervention`.
* `scraftcam/shops.py`: `KINDS`, `dimension_letters()`,
  `tool_label()`, `tool_order()`, `_tool_material()`;
  `scraftcam/tooling/tool_models.py`: sketches (`SKETCH_GRID`,
  `_Broken`, `_grid_section()`, `Cut`, `_hatch()`), run as a module
  to write `Tool_Models.md` and `docs/tool_models/`.
* `show_demo.py` starts `scraftcam.run --program ...`; the headless
  show (`--headless`, about 1 min 50 s) passes.  The chamfered
  `GRID_PLATE` is in the model cache.
* Never hand the user a `./show_demo.py` run while Claude's headless
  show still runs (same box and ports).
* Not run: the whole test suite; the LinuxCNC end-to-end suite.
* Related tasks made: `T.cpfj~5.7` (carousel planning for a job),
  `T.rslsao~5.8` (several LinuxCNC simulators at once), both Pending.

## Shop and Controller Panels (#147-#153, 2026-11-14)

* #147: every directory is "(directory)", "(folder)" on Windows, the
  shop's root included (`Node.label()`).
* #148: every shop item gets its `.toml` (`edit_path()`); `units` is
  a drop-down "imperial (in)" / "metric (mm)" (`_choice_entry()`,
  `CHOICE_LABELS`); [Edit TOML File] (`EDIT`); no TOML text in panels.
* #149: a ▶/▼ per field row with how to fill it in (`TableField.how`,
  `field_help()`; only `tool_change`, `post_processor` have it yet).
* #150: a directory's panel explains what it holds
  (`tree.EXPLANATIONS`; all but `controllers/` are Claude's drafts);
  `machines/` keeps its list.
* #151: `post_processor`: left out or "linuxcnc" built in, else a
  command with `{input}`/`{output}` (`gcode.post_process()`, not yet
  called); a machine's controller copy shows "Copied from: NAME"
  (`templates.copied_from()`).
* #152, #153: no "Shop:/Design:" on the top line; [Enable Editing]
  and [Edit TOML File] under each panel's title (`Panel.edit_row`).
* Help texts, explanations, `rpm` "overrides for every material" and
  `tooling_pitch` "a multiple of `pitch`" are drafts, not checked
  against the code.

## Windows and Panels (in force 2026-11-15; the user: "it just works")

* Any number of windows (PanelRow in the code: `Window`, all in
  `WINDOWS`), all sharing one `App`.  Each has the top line [Stop
  All] [Tree] message [+ Panel] [New Window] [Exit], its own tree,
  and one or more panels side by side.
* #200: [New Window] opens one with an empty panel ("Click an item in
  the tree.", `Panel.hide_guide()`) and its tree; the first window
  starts with the guide.
* Each panel's title line: its title (the tree's label, wrapped; a
  machine's too, #183), then, packed right (#182): [<] [>] (#174,
  greyed at the ends), [ ] Pin (#201), [Close] (#156, hidden on a
  window's last panel; an active machine's asks to stop it first,
  and closes once stopped).
* #201: a tree click goes to the current panel unless pinned; else
  the first unpinned; else a new one on the right (`free_panel()`).
  A running machine's panel is pinned, the box checked and greyed,
  until it stops (`Panel.pinned`, `is_pinned()`, `show_pin()`).
* #202: a file or directory may show in several panels and windows.
  #203: a machine in one panel only; clicking it elsewhere brings
  that window to the front (`open_machine()`).
* #177-#180: [+ Panel] widens the window by the panels' average,
  [Close] narrows it; the other panels keep their widths; not when
  maximized or full screen; never past the screen or below the
  minimum (`fit_width()`, `resize_to_wanted()`, `wanted`, `FIT_MS`).
* #184: closing a window asks "Stop and close this window?" for its
  running machines (`ask_to_leave()`, `leaving`); its machine
  controls go to the oldest window left; [Exit] (and the last
  window's close) asks to stop everything, then closes every window
  (`close_rows()`).  `busy()` of a window with others left counts
  only its panels' machines.
* #186, #187: the layout is kept per shop in
  `~/.scraftcam/layouts/HASH16.json` (`gui/layout.py`,
  `LAYOUT_VERSION` 2; other versions skipped): each window's size,
  tree (shown, width, open branches), panels (width, `pinned`, `path`
  or `machine`).  Written on change, every `STOP_MS`, by the first
  window (`Window.snapshot()`, `save_layout()`); restored before the
  event loop (`restore_layout()`, `Window.restore()`,
  `restore_panels()`: read only, machines shown never started,
  anything gone skipped).  Only when `App.keep_layout` (`run.py`
  unless `--headless`; tests never save).  No window positions
  (Wayland).
* Narrow: buttons fitted to their text (`views.narrow()`,
  `lcnc_hmi.narrow()`; Qt's are at least 80 px): top line [Bring]/
  [Exit] style short names with long tooltips (#196, #197; [Stop
  All] kept, with `STOP_ROOM` for its running look, #199; [+ Panel]
  kept, #198).  A window is at least 297 px, a panel 235.
* #191: the command port addresses `WINDOWS[0]` unless a `window`
  index is given.
* Tried and dropped (do not bring back): [Detach]/[Reattach] into
  `DetachedWindow`s (#157, #173); [Attach] back to a window of origin
  (#185, #189); [Bring Panel] pulling a chosen lone panel (#192-#195);
  machine sections in panels of their own (#159-#162); the minimal
  form (#90-#95, #168).

## The Machine Panel (in force 2026-11-15)

* Header (name, next-task bar), strip (run button, [Skip Tool],
  [Stop]), the next tool large (#170, `next_tool_text()`, "■ NOW"),
  the progress line, the position in three lines, the message; then
  tabs Setup, Tools, G-code, Job, Execute (the user liked them).
* At most 5 widgets to a row; a row per axis (`[-X] [+X] [entry]
  [Set X]`); G-code windows `GCODE_WIDTH` (32) characters, `elided()`.
* #176: tabs about half as wide (573 -> 255 px): fitted buttons, the
  Job text wraps, View check boxes two to a row; G-code is the widest.
* #169: `machines/` is the power operator's home; #172 [Stop] per
  strip, [Stop All] on every top line.

## Where Things Stand (2026-11-15, end of session)

Open items (numbers sticky):
1. #207: tests for today's work, from Claude's offscreen scripts:
   `tests.test_gui_layout` (path, write on change, version, bad
   file), and in `test_gui_window`: the pin rule, [New Window],
   [<]/[>], widths, a save/restore round trip; with #166's backlog
   (exit question, drop-downs, field help, `elided()`, next tool).
2. #208: clean-up left from the detach era: `show_rows_buttons()`,
   `all_panels()` (same as `panels`), `leaving`.
3. #209: maybe [Reset Layout] on the guide, or `--fresh`.
4. #163: tables inside a shop item (axes, spindle, ...) not shown;
   proposed ▶ headings.
5. #164: a Tool Table tab (#80, #81, #83).
6. #165: the Job tab as a directory of `.nc` files (#74, #77, #78).
7. `gcode.post_process()` not called yet; renaming the Execute tab
   much later.
Tests run this session: `test_gui_window`, `test_gui_machines`,
`test_gui_port` (two stale expectations fixed), `test_lcnc_hmi`;
all pass.  Not run: the whole suite; the LinuxCNC end-to-end suite.

## 2026-11-15: Changes from `T.cm~6.3`

A shop item's panel may have [Open Pages] beside [Edit TOML File]
(catalogs only, `Panel.pages_button`); the action rows gained
"catalogs/: [New Catalog]" (for the shop's root and `catalogs/`).
`fields.PLAIN` has the new `page_ranges` form.  Tests copying
`examples/shop` leave `catalogs/` out.
