# 6.5 Tools from Outlines

(Draft by Claude, 2026-11-17; widened 2026-11-22 to take in
`T.cmt~5.3` and `T.tm~2.5`.)

Every tool and piece of tooling, old and new, is made from an outline
drawn in the 2D editor (`T.oe~6.2`: letters, defaults, [Revolve] for
round tools) into `solid.py` solids, not from hand-written Python.
Its `.outline.svg` and letters table are its documentation.  Each
old model is kept until the new one is checked against it (#37a).

## Existing Tools

* Round (revolved): end mill, drill, chamfer mill, corner rounding
  mill, double angle cutter, single and double end countersinks
  (center drills), the Z setter.
* Flat (extruded): parallel, jaw plate, machine vise (an assembly:
  block, jaws, notches), mill table.
* Left off for now: the grid plate (very hard).

## New Tools (Shars catalog examples)

* Drill vise (page 318, 202-1142); vise jaws.
* Hold downs: clamps (page 327); T-slot nuts (page 330, 202-8411;
  page 331, 202-8425); flange nuts (page 330, 202-4805).
* Setup: axis setter (page 314, 303-3104, modeled); edge finder
  (page 415, 202-1781); center finder; Z-axis tool setter (page 414).
* Cutters: countersink (page 25, 415-5457); single angle (page 25,
  430-0336); T-slot (page 54, 404-1700); dovetail (page 55,
  421-3121); double angle (page 55, 430-0584); corner rounding (page
  60, 437-1910); roughing end mills (page 65, 404-9051); fly cutters
  (page 152).

## Done When

* Every tool above is made from an outline file, and
  `Tool_Models.md` comes from those files.
