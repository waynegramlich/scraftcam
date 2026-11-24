# 6.10 GUI Cleanup

(Draft by Claude, 2026-11-24, from the user's #625/#626; the user's
to revise.)

Cleaning up after `T.og~6.9` merged every program into
`python3 -m scraftcam.run`: leftovers of the old programs, stale
documents, and the checkers and tests over the whole package.

* The HMI's own prompts go; it uses `gui/prompt.py` (#613), and
  `lcnc_hmi.py` is renamed for what it is now (#614).
* `README.md`, `scraftcam/gui/README.md` and the other documents
  describe the one GUI (#616-#618).
* The checkers run over all of `scraftcam/`; dead code and dead
  `scraftcam.run` flags go (#620, #621).
* Large modules are split where it helps (#619); the test suites are
  sorted into widget tests and MCP tests (#622).
* The loose ends of `T.og~6.9`: tabs in every panel (#586), in-panel
  prompts placed at the exact part, catxtract tried with a real PDF
  (#623).

## Done When

* No code, test or document names a program other than
  `scraftcam.run`, and `scraftcam/gui/README.md` describes the GUI.
* All four checkers are clean over the whole package.
