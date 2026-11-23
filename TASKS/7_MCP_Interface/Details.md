# 7 MCP Interface

(Draft by Claude, 2026-11-23, from the user's discussion in
`T.oe~6.2`; the user's to revise.)

The user is the bottleneck in testing the GUI: every bug is found by
hand, described, fixed and tried again.  A Model Context Protocol
(MCP) interface lets Claude drive the program itself, and makes
recorded sessions into tests and living documentation (far better
than videos that are stale minutes after they are posted).

* Vast swaths of the Python interfaces are exposed (`@exposed`):
  their type hints and docstrings already document them.
* Gestures go through Qt's own events, so what a click hits is
  tested too; method calls set up states quickly.
* Claude narrates each step in a panel at the bottom of the GUI,
  with [Backward], [Forward] and [Pause]; the user can take over at
  any time, and judges what is too hard to use.
* The user's own sessions are recorded the same way: a bug report
  is made by doing it.
* Recordings (`.steps.toml`) are versioned, self-contained, replayed
  `--headless` as tests, and repaired with `--update`.

## Done When

* The outline editor, then the unified GUI (`scraftcam.run`), can
  be driven over MCP and recorded, and the recordings run as tests.
