# 5.5 Stock and Materials

(Draft by Claude, 2026-11-04, from `T.emsagc~5.2` #35; widened
2026-11-22 to take in `T.sm~2.4`, Stock Models.)

## Materials

* A standard list of materials ships with `scraftcam`.  A shop may
  define its own; when it does not, the standard list is used.
* Each material has a short name (e.g. `aluminum_6061`), a display
  name, a default color, and later its cutting data, for speeds and
  feeds.
* A starting list: 6061 and 7075 aluminum, 1018 mild steel, 303/304
  stainless, 360 brass, acetal (Delrin), HDPE, acrylic, MDF, hardwood.
* `.nc` setup comments and model cache keys hold the short name only.

## Stock

* The raw material on hand: each material's standard sizes and
  thicknesses, plus a minimum cut around the outside, so the stock
  for a part can be chosen (as `../Fab/`'s `FabStock.enclose()`).
