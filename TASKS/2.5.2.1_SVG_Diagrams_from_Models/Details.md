# 2.5.2.1 SVG Diagrams from Models

(Draft by Claude, 2026-11-16, from the user's #72 in `T.cmt~5.3`; the
user's to revise.)

Each `SolidModel` (a part or an assembly, `scraftcam/model.py`) should
have a 2D diagram in `.svg`, with dimension letters that match its
fields, for its documentation (`T.dtm~2.5.2`) and for the GUI's panels
(`T.g~6`): a global panel and one sub-panel per layer, each
with its diagram.

* The models are built from SolidCraft sketches (dimensions tied to
  parameters).  SolidCraft can import SVG (`sketch.insert_svg`) but our
  bindings show no SVG export, so we write the SVG ourselves: from the
  sketch geometry and dimensions read back from SolidCraft, or from
  the model's own numbers.
* Today's diagrams are code written by hand per kind
  (`tool_models.py`, `Tool_Models.md`); one `sketch()` method (or the
  like) per model would make them the "one place per kind" of
  `T.tkis~6.7` idea 1.
* Questions to settle: what the diagram is drawn from; which views;
  how letters and the field labels and help meet; light and dark.
