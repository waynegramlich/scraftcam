# LLM Agent Context Log

Squeezed 2026-11-22 (third time): only decisions in force and where
things stand; the history is in `hg` and `git`.  Issue numbers are
sticky (code comments cite them); new ones continue after #210.
Suspended while its children work; its own items resume after
`T.tfo~6.5`'s first tools.

## Decisions in Force

* Qt (PySide6 from `packages.require`, no venv); Linux (Wayland) and
  Windows; no macOS (#21, #52, #55).
* `python3 -m scraftcam.run` (#93, #103): `--shop`, `--design`,
  `--port`, `--headless`; for a machine `--program`, `--hmi-port`,
  `--solidcraft`, `--lcnc-port`, `--dry-run`.  No `--shop`:
  `shop.toml` here or in the parents (#83).  Today `show_demo.py`
  starts `serve_linuxcnc` and the GUI connects (#55).
* Never crash a machine: nothing closes until every machine is
  stopped with its spindle off (#56, #67).
* Top line on every window (#82): [Stop All] (greyed while idle; red,
  bold, boxed while any machine runs, #100), [Tree], latest message
  (red for problems), [+ Panel], [New Window], [Exit].  No right
  click, no icons.  Buttons fitted to their text (`views.narrow()`).
* No shop: "No shop yet: [New Shop]" (#97-#118); never `git init`,
  suggest `git` or `hg`.
* Tree (#119-#128): two roots (shop, design); directories first;
  tools labeled by function and size ("End mill (1/2in 2-flute
  HSS)"); every item a tooltip; bad files red "(error)"; watched.
* Panels: a row per field, `key (L)` with its sketch letter, the
  kind's sketches at the right (#19, #42); [Enable Editing] (checked
  only for a just-created item, #140) and [Edit TOML File] under the
  title (#153); a ▶ per field with how to fill it in (#149); a
  directory's panel explains it (#150).  Values checked as typed, no
  [Save] (#15).  Light and dark from the desktop (`gui/theme.py`).
* Command port (#96, #110): JSON lines on 127.0.0.1 (`status`,
  `press`, `new_shop`, `tree`, `select`, `quit`); `WINDOWS[0]` unless
  a `window` index (#191).  The HMI keeps its port 5007 (#54).
* Shop data: the user's directory under version control, one item
  per `.toml`, `shops.KINDS` the one schema; our writer's order:
  header (`name`, `kind`, `language`, `version`, `notes`), other keys,
  then tables, alphabetically (#146).  Directories `controllers/`,
  `tool_materials/`, `tools/`, `tooling/`, `stock_materials/`,
  `machines/`, `catalogs/`.
* Sketch letters (`shops.dimension_letters()`, #18-#26): a name's
  first letter, else initials of its other words, then other letters.
* Controllers (#139-#145): `controllers/` holds templates (LinuxCNC
  shipped, copied by [New Shop]); a new machine copies one
  (`template = "NAME"`); a template change is followed up at once in
  its panel ([Update], `gui/templates.py`).  Controller fields
  `vendor`, `product`, `vendor_version`, `vendor_triple`,
  `support_ended`.  A key left out is "Not initialized yet", not an
  error; running stops naming them.
* `post_processor`: left out or "linuxcnc", else a command with
  `{input}`/`{output}` (`gcode.post_process()`, not yet called).
* Deferred: installer and PyPI, a panel menu.  `scraftcam/gui/
  README.md` comes at the very end.

## Windows and Panels ("it just works", 2026-11-15)

* Any number of windows sharing one `App` (`WINDOWS`), each its own
  tree and panels side by side; each panel's title line: title, [<]
  [>], [ ] Pin, [Close] (hidden on the last panel).
* A tree click goes to the current panel unless pinned, else the
  first unpinned, else a new one (#201, `free_panel()`).  A running
  machine's panel is pinned; a machine shows in one panel only
  (#203).  [+ Panel]/[Close] widen and narrow the window (#177-#180).
* Closing a window asks to stop its machines; [Exit] asks to stop
  everything (#184).
* Layout per shop in `~/.scraftcam/layouts/HASH16.json`
  (`gui/layout.py`, version 2), restored read only, machines never
  started; never saved by tests or `--headless` (#186, #187).
* Dropped (do not bring back): detached windows and [Attach] (#157,
  #173, #185), [Bring Panel] (#192-#195), machine sections in their
  own panels (#159-#162), the minimal form (#90-#95, #168).

## The Machine Panel

* `machines/` is a list: three lines per CNC machine (name with kind,
  controller, state; details; the next-task bar), one per other
  machine, then the tools to fetch (`gui/machines.py`, #134-#138).
* A machine's panel: header (name over a bar filling as the next
  operator task nears, text the time left, "▲" within a minute, "■
  NOW" blinking: not color alone, #102, #106); strip (one run button
  Start/Pause/Resume/Restart, [Skip Tool], [Stop]); the next tool
  large; progress, position, message; tabs Setup, Tools, G-code,
  Job, Execute.  At most 5 widgets a row; the slider behind [Expert]
  (#79); no speeds-and-feeds table (#72).
* Per machine kind fields (mill only now, #137); a small controller
  interface, LinuxCNC only now (#138).
* LinuxCNC 2.9 changes mode only when stopped: MDI, Set Origin and
  jogs are refused while a program is paused; G54 is not kept
  between starts (from `T.mlcp~3.4`).

## Where Things Are

* `scraftcam/gui/`: `app.py`, `fields.py`, `views.py`, `window.py`,
  `layout.py`, `theme.py`, `tree.py`, `editor.py`, `port.py`,
  `machines.py`, `templates.py`; `scraftcam/run.py`
  (`machine_maker()`); `scraftcam/hmi/lcnc_hmi.py`, `hmi_machine.py`
  (`tool_plan()`, `next_intervention()`).
* `scraftcam/shops.py` (`KINDS`, `tool_label()`, `tool_order()`);
  `tooling/tool_models.py` writes `Tool_Models.md`.
* Tests: `test_gui_window`, `test_gui_machines`, `test_window_exposed`,
  `test_gui_templates`, `test_gui_catalogs`, `test_gui_tree`,
  `test_lcnc_hmi`.  The headless show (~1 min 50 s) passes.

## Open (numbers sticky)

* #207 tests from Claude's offscreen scripts: `test_gui_layout`, and
  in `test_gui_window` the pin rule, [New Window], [<]/[>], widths,
  a save/restore round trip, #166's backlog.
* #208 clean-up from the detach era (`show_rows_buttons()`,
  `all_panels()`, `leaving`).  #209 maybe [Reset Layout].
* #163 tables inside a shop item (axes, spindle) not shown.
* #164 a Tool Table tab: tool lengths by setter, cube or paper, `G10
  L10 P<n> Z<height>` (#80, #81, #83).
* #165 the Job tab: a directory of `.nc` files, one tool each, in
  name order (#74, #77, #78); waits on `T.npfetc~5.4`.
* #426 done 2026-11-23 in `T.og~6.9` #S1: all 10 pass.
* `lcnc_hmi.py` goes once all of it is in the GUI (#57); later the
  GUI starts LinuxCNC itself (#64), one command port (#65).
