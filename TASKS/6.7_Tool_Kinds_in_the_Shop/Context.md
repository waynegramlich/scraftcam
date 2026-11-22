# LLM Agent Context Log

Squeezed 2026-11-22: moved from 5.9 to 6.7 and Suspended until a
few round tools are made from outlines in `T.tfo~6.5`.  #391 is
decided (the user): one outline file per tool kind; each shop tool
gives only its letter values.

* Idea 1 (one place per kind) began as `meta()` field metadata in
  `scraftcam/model.py` (`T.cmt~5.3`, closed); with outline files, a
  kind may become an outline file plus a short declaration (name,
  label, shop fields).  A per-model `sketch()` method was dropped
  (#260): the outline's `.svg` is the sketch.
* Idea 2's STEP route exists: `solid.SolidStep` inserts a `.step` as
  its own component (`T.rps~6.6`).
* The first case, the Shars Z setter (`tooling/setters.py`), still
  has no shop kind.
