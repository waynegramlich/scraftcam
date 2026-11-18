# 5.1.9.2.1 Convert Existing Tools to the 2D Editor

(Draft by Claude, 2026-11-17, from the user's request in
`T.prg~5.1.9.2`; the user's to revise.)

When `T.prg~5.1.9.2` is done, every tool is made from an outline drawn
in the one 2D editor (letters, defaults, [Revolve] for round tools),
not from hand-written Python.  Each tool is moved over one at a time,
its old model kept until the new one is checked against it (#37a).

* Round tools (revolved): end mill, drill, chamfer mill, corner
  rounding mill, double angle cutter, single and double end
  countersinks (center drills), the Z setter.
* Flat tools (extruded): parallel, jaw plate, machine vise (an
  assembly: block, jaws, notches), mill table.
* Left off for now: the grid plate (very hard).
