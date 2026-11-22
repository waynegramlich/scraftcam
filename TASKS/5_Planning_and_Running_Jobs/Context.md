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
end-to-end suite: `podman start lcnc` first (the server quits at once
if the container is stopped), then `SCRAFTCAM_LINUXCNC=1
QT_QPA_PLATFORM=offscreen python3 -m unittest -v
tests.test_lcnc_end_to_end` (about 30 s).  2026-11-22: 8 of 10 pass;
see `T.g~6` #426.

## Where the Work Went (2026-11-22)

* Tools, tooling and their models: `T.tfo~6.5` (outline files to
  `solid.py` solids); hooking a tool into the shop: `T.tkis~6.7`.
* The GUI, HMI replacement, catalogs, the outline editor: `T.g~6`.
* Keep-outs from the new solids: `T.kz~4`.
* Left here: `T.npfetc~5.4` to `T.rslsao~5.8`, all Pending, and the
  "Left" list in `Details.md`.
