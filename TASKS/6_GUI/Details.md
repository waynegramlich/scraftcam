# 6 GUI

(Draft by Claude, 2026-11-20, when the GUI became a top-level task;
the user's to revise.)

One program, `python3 -m scraftcam.run`, through which a user sets up
and runs a shop without editing TOML or writing Python: it manages the
shop's files (in the user's own version controlled directories) and
drives the machines (the LinuxCNC simulator today).

## What It Holds

* **Windows and panels**: any number of windows, each a tree of the
  shop and the design driving panels; [Stop All] and [Exit] on every
  window; never close while a machine runs.
* **Shop data entry**: one panel per item, its fields checked as
  typed (never written bad), with its sketch, letters and help.
* **Machines**: the machines list and each machine's panel (Setup,
  Tools, G-code, Job, Execute), replacing the HMI (`lcnc_hmi.py`).
* **Outline editor** (`T.oe~6.2`): parametric 2D outlines with
  letters, so users model their own tools and parts; its SVG
  (`T.sfoe~6.4`) is the diagram in panels and documents; the
  existing tools move onto it (`T.cett2e~6.5`).
* **Catalogs** (`T.cm~6.3`): vendors' catalogs, marked with
  `catxtract`, from which shop items are made.
* **Original and changed values** (`T.oacv~6.1`).
* Later: the GUI starting LinuxCNC itself, several simulators at once
  (`T.rslsao~5.8`), a job's carousel plan (`T.cpfj~5.7`), operator
  instructions and the time to the next intervention.

## Done When

* A new user can make a shop, add machines and tools (from a catalog
  or the outline editor), load a job and run it on the simulator, all
  from the GUI.
* `lcnc_hmi.py` is gone, and `scraftcam/gui/README.md` describes the
  GUI.
