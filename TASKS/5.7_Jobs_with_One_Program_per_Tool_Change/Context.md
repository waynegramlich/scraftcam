# LLM Agent Context Log

## 2026-11-22: Taken in from `T.npfetc~5.4`

* `scraftcam/lcnc/sim_solidcraft.py` (`SCPathRack`): `moves` is a
  `dict[int, list[SCMove]]` by T number, sketches `T{number:02d}
  path`; `show()` switches on the tool in the spindle
  (`stat.tool_in_spindle`) and draws the next tool ahead.  Keying by
  tool change instead needs the sample to know which change it is in:
  count tool changes as samples arrive, or map `stat.motion_line`
  ranges to changes.  With one program per change, the program itself
  says.  It may also explain `I.phpsa~1`.
* `tests/test_sim_path_rack.py` tests `SCPathRack`.
