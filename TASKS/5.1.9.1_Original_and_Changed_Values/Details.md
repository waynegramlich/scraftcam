# 5.1.9.1 Original and Changed Values

(Draft by Claude, 2026-11-16, from the user's #73 in `T.cmt~5.3`; the
user's to revise.)

A user tweaks a tool (or later a design) in the GUI and saves the
result into their shop.  Keep the original values and the changes, and
highlight in the panel each value that differs from the original.

* "Original" is to be settled: the model's defaults (e.g. the Kurt
  plate's numbers), a catalog's numbers (`T.cm~5.1.10`), or the values
  when the item was first saved.
* Each value is saved in the units it was written in (`3-7/8 in`,
  `Length` in `scraftcam/model.py`).
* With both kept, "back to the original" per field comes nearly free.
* Edits reach SolidCraft through `SolidCraftLink.send()`
  (`scraftcam/solidcraft_link.py`) once a field is finished.
