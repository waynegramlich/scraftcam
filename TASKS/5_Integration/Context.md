# LLM Agent Context Log

Squeezed 2026-11-19: where things stand; the dated history is in
`hg` and `git`.  The user expects things to change all over, and
missing features to be found as they come.  Each sub-task's own
`Context.md` holds its details.

## The Tree

One repository (`T.rd~5.1`, closed), run from its top with `python3
-m`, nothing installed: package `scraftcam/` (`pybind/`, `lcnc/`,
`hmi/`, `tooling/`, `gui/`, `catalog/`), `tests/`, `./show_demo.py`.
`mypy.ini`, `ruff.toml` hold the checkers' settings.  The old
`scraftpybind`, `scraftlinuxcnc` repositories are archived
(`I.amgr~2`).  PySide6 comes from `packages.require()`
(`scraftcam/pins.toml`), no venv; Linux is Wayland only, no macOS;
to be published on PyPI.  The LinuxCNC end-to-end suite
(`SCRAFTCNC_LINUXCNC=1`) has not been run since the reorganization.

## Done

* `.nc` setup comments (`T.emsagc~5.2`, closed): the HMI draws the
  mount from them, picks the origin, steps through items, toggles
  keep-outs; `./show_demo.py --headless` (`T.hlp~3.3.1`).
* The HMI is Qt (`T.hs~5.1.5`, closed): `scraftcam/hmi/lcnc_hmi.py`,
  `hmi_machine.py`, and a panel of the one GUI.
* The one GUI (`T.g~6`): the user's shop and designs in
  their own version controlled directories, `~/.scraftcam/` always
  deletable; any number of windows, each a tree driving panels ([<]
  [>] Pin [Close]), no tabs, no [Save]; layouts kept per shop in
  `~/.scraftcam/layouts/`.  Shop item panels edit fields in place
  with sketches, help and [Enable Editing]; a `machines/` list;
  controller templates in `controllers/`; the machine panel (core
  strip over tabs Setup, Tools, G-code, Job, Execute); [Stop All],
  [Exit].  Tests for windows and panels (#207) were next there.
* Tooling ready to integrate: `SCMachineVise` with `SCJawPlate`,
  `SCParallel` with holes, `SCGridPlate` (5 minute build after a
  change to `tools.py`, `mount.py` or `scgeometry.py`, then 1 s from
  the cache), every cutter kind from `examples/shop/tools.toml`, all
  in `Tool_Models.md`.  Stock stays blocks (`T.sm~2.4`).
* SolidCraft's hover translucency is a quirk (`I.mpgtis~3`, in
  `README.md`).

## Under Way

* `T.cmt~5.3`: the parametric model library (`scraftcam/model.py`,
  `SolidModel`, `SolidCraftLink`, live SolidCraft parameters;
  `JawPlate`, `Parallel`).
* `T.sdfm~2.5.2.1`: `scraftcam/outline.py` `Profile`; SVG next.
* `T.oe~6.2`: the outline editor (the current focus).
* `T.cm~6.3` Reference until 5.3 has tools; `T.ant~5.9` Open.
* Pending: `T.npfetc~5.4` (a path per tool change), `T.sm2~5.5`,
  `T.cpfj~5.7`, `T.rslsao~5.8`, `T.cett2e~6.2.1`.
  `T.oacv~6.1` is Open but left as it is.
