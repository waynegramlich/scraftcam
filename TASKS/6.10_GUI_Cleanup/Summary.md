# Summary of `T.gc` GUI Cleanup

Closed 2026-11-24.  The cleanup after `T.og~6.9` merged every program
into `scraftcam.run`, in six Steps (#679), each committed:

* The four checkers clean over `scraftcam/` and `tests/` (#620,
  #636, #640-#647).  #S1: no duplicate code (#648): the
  `lcnc/probe_batch.py` probe went (#649); shared now are
  `plot.py`'s batch helpers, `geometry.draw_segments()`,
  `scraftpybind.connect_cli()`, `outline_cuts.cut_pieces()`.
* #S2: the HMI uses `gui/prompt.py` (#613): `prompt.ASKED`,
  `use_headless(unattended=True)` (`prompt.UNATTENDED`);
  `lcnc_hmi.py` is `hmi/machine_panel.py` (#614).
* #S3: `run.py` lost `--lcnc-port` and `--design` (#621, #685).
* #S4: every panel shows its tab bar; [Guide], [Machines] and
  [Machine] (two rows of tabs) take [Fields]' place
  (`Panel.show_own()`, #586, #684).
* #S5: the letters table is `LettersTable` in
  `gui/outline_letters.py` (#637), for `T.toasl~6.8` #631.
* #S6: tests in `tests/fast`, `qt`, `solidcraft`, `lcnc` by what they
  need (#622, #686); `CLAUDE.md` names `tests.GROUP.test_NAME`
  (#664).

Moved out: the documents (#616-#618, #635) to `T.d~8`; #623 to
`T.c~6.3`; pseudo time (#650) to `T.mi~7` (#687).  Not done: large
module splits beyond `outline_editor.py` (#619).

Tags: `T.og~6.9`, `T.toasl~6.8`, `T.d~8`, `T.c~6.3`, `T.mi~7`.
