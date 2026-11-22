# 5.7 Jobs with One Program per Tool Change

(Draft by Claude, 2026-11-13, from the user's request; widened
2026-11-22 to take in `T.npfetc~5.4`.)

A job is a directory of `.nc` files, run in name order, each file
driving one tool change: a tool that cuts twice gets two programs and
two paths.

## A Path per Tool Change

In the demo, T1 (the 1/4 in end mill) cuts twice: the profiles and
pocket, and, after the corner rounding pass (T6), the plate's
finishing outside profile.  `SCPathRack` keeps one sketch per T
number, so T1's last cut shows its whole earlier path too, which
looks like the first path coming back.  Paths are to be kept per
tool change, not per T number.

## The Carousel Plan

Only machines with an automatic tool changer have a carousel.
Whenever a tool is needed that is not in it, it is loaded into a
slot, and the tool it displaces goes back to the shop's rack by
hand.  scraftcam knows the order of all of the job's programs, so it
decides which tool goes back, for the fewest carousel changes.

* With the whole order known, the tool to send back is the one whose
  next use is furthest away (or never comes): Belady's rule.
* The operator is told, before the job and at each change, which
  tool goes into which slot and which goes back to the rack.
* `scraftcam/carousel.py` already plans one program's slots and
  swaps; this extends it to a whole job.

## In the GUI

The machine panel's Job tab loads such a directory (`T.g~6` #165).
