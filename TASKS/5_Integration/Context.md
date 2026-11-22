# LLM Agent Context Log

Squeezed 2026-11-22; the history is in `hg` and `git`.  Each
sub-task's own notes hold its details.  The user expects things to
change all over, and missing features to be found as they come.

## The Tree

One repository, run from its top with `python3 -m`, nothing
installed: package `scraftcam/` (`pybind/`, `lcnc/`, `hmi/`,
`tooling/`, `gui/`, `catalog/`), `tests/`, `./show_demo.py`
(`--headless` runs it all with no window).  `mypy.ini`, `ruff.toml`
hold the checkers' settings.  PySide6 comes from
`packages.require()` (`scraftcam/pins.toml`), no venv; Linux is
Wayland only, no macOS; to be published on PyPI.  The LinuxCNC
end-to-end suite (`SCRAFTCNC_LINUXCNC=1`) has not been run since the
reorganization.

## Where the Work Went (2026-11-22)

* Tools, tooling and their models: `T.tfo~6.5` (outline files to
  `solid.py` solids); hooking a tool into the shop: `T.ant~6.7`.
* The GUI, HMI replacement, catalogs, the outline editor: `T.g~6`.
* Keep-outs from the new solids: `T.ikz~4`.
* Left here: `T.npfetc~5.4` to `T.rslsao~5.8`, all Pending, and the
  "Left" list in `Details.md`.
