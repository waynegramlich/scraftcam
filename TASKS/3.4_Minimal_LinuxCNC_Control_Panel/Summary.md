# Summary of `T.mlcp` Minimal LinuxCNC Control Panel

`lcnc_panel.py`, a small `tkinter` panel in place of AXIS, with a
command port on 127.0.0.1; it drove whole demo runs with SolidCraft
following (the user: "It was perfect", 2026-10-28).  It comes up
stopped; the user starts runs.  LinuxCNC 2.9 changes mode only when
stopped, so MDI, Set Origin and jogs are grey during a run, and G54
is not kept between starts.  Closed for good 2026-11-22 (#406): the
panel became the HMI (`T.hs~5.1.5`, now Qt) and is being replaced by
the GUI's machine panel (`T.g~6`).

Tags: `T.rlg~3.3`, `T.hs~5.1.5`, `T.g~6`.
