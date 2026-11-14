# LLM Agent Context Log

Trimmed 2026-11-13: only decisions still in force and where things
stand.  The full history is in `hg` and `git`.  Issue numbers are
sticky (code comments cite them); new ones continue after #146.

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
* Top line (#82): [Stop All] first, always shown: greyed while no
  machine runs, red, bold and heavily boxed while any does (#100);
  [Tree], shop and design names, latest message (red for problems,
  #95), [+ Panel], narrow [x] (#114).  Action rows under it (#73);
  no right click; no icons, a kind in parentheses.
* No shop: "No shop yet: [New Shop]", the dialog at start (#97-#118).
  Never `git init`; suggest `git` or `hg` (#99, #107).
* Tree (#119-#128): two roots (shop, design); directories first;
  files sorted by what they show; tools labeled by function and
  sizes, e.g. "End mill (1/2in 2-flute HSS)", sorted by function then
  size (#21); every item has a tooltip saying what it is (#80); bad
  files red "(error)"; watched (no [Refresh]); fitted to its labels,
  refitted on open/close (#22, #43).
* Panels (#122): a click shows the item in the current panel, never
  in a machine's (#58).  A shop item: a row per field, `key (L)` with
  its sketch letter (#19), all of its kind's sketches to the right,
  top view first (#42), the rest as TOML below.  The lines between
  them fit themselves to what is there on each new item (#43); every
  line has a grip and highlights on hover (#25, #44).  [Edit] opens
  `$VISUAL`/`$EDITOR`/the desktop's editor (#77, #124).
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
  menu (#71), per-user layout file (#78.1).
* `scraftcam/gui/README.md` (#10) comes at the very end of this task,
  after the LinuxCNC GUI and the catalog work are merged in.

## The Machine Panel (step 5), decided so far

* A panel holds a tab per machine (#101); each tab header is the
  machine's name over a bar that fills from black as the operator's
  next tool task comes (a carousel swap, or with no tool changer
  every change), full when due, black again after (#102, #106); its
  text the time left, "▲" within a minute, "■ NOW" blinking while
  waiting: not color alone (color blind operators).
* Inside a machine (the HMI, `lcnc_hmi.py`, to be redone completely):
  at the top, one run button named Start / Pause / Resume / Restart
  (#96), [Skip Tool] (#97), [Stop], [Minimal]/[Full] (#94); the
  position with S rpm and F in/min (#86, #98); the tool plan, now and
  the next few with times (#85, #87, #91); the View check boxes
  (#73, #92); the message only when there is one (#88).  Tabs
  [Configure] (origin, jogs, Set X/Y/Z, G-code windows, MDI,
  -Tool/+Tool, carousel plan), [NC Files] (placeholder), [Execute]
  (the slider behind [Expert] with a confirming question, #79;
  progress; next tool).  The speeds-and-feeds table is gone (#72).
* Minimal form: Start goes minimal, a run's end goes full; the window
  shows only [Stop All], message, [x] and the machine panel, and asks
  to stay on top (Wayland may ignore it; GNOME's own Always on Top
  works) (#90-#95).
* Machines view vs machine view (#134-#138, 2026-11-14; replaces
  #101's tabs, the bar of #102 kept):
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
  * Second cut (2026-11-14, after the user found the first "kind of
    broken"; awaiting a GUI run): the shop's root item is a splash
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
* To come: the inside of a machine tab (the user's next topic; #105:
  "did not look right", details from the user); [NC Files] as a job:
  a directory of `.nc` files, one tool each, run in name order,
  loaded from the tree (#74, #77, #78); [Tool Table] work inside
  [Configure]: a tool's length (spindle nose to tip) by setter, dial
  indicator cube (2 in) or paper and micrometer, all `G10 L10 P<n>
  Z<height>` (#80, #81); our data keeps the offsets and shows them
  for other controllers (#83).  `lcnc_hmi.py` goes once all of it is
  in the GUI (#57).  Later: the GUI starts LinuxCNC itself (#64), one
  command port (#65), the catalog work (#66, `T.cm~5.1.10`).

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
  `Stopper`, `CommandServer`, `NewShopDialog`), `theme.py`, `tree.py`
  (`about_item()`, `about_directory()`), `editor.py`, `port.py`.
* `scraftcam/run.py`: `machine_maker()` makes the HMI for a panel
  (imports `scraftcam.hmi` only with `--program`).
* `scraftcam/hmi/lcnc_hmi.py`: `make_hmi()`, `HMI.busy()`, `quit()`,
  `set_minimal()`, `intervention()`; `hmi_machine.py`:
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
