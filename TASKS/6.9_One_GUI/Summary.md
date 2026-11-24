# Summary of `T.og` One GUI

Done 2026-11-24: `python3 -m scraftcam.run` is the only program with
a window.  The outline editor (`--outline`, `--tutorial`,
`--record`), catxtract (`--pages`) and the HMI (the machine panel)
became panels; `show_demo` and `drive_editor` became `--show-demo`
and `--drive-editor`.  One MCP port (#577, #585, #604) replaced the
GUI's command port and the HMI's line port (`window_exposed.py`,
`hmi_exposed.py`).  A tool's panel has an [Outline] tab, read only
until [Allow Changes] (#587, #588, #590); the editor has no shortcut
keys (#589).  `gui/prompt.py` shows every question inside its panel
(#606).  Active machines keep their window's tree shown and refuse
Exit by name (#609-#611); a machine opens from the machines list
(#607).  The end-to-end suite over MCP found #612 (the HMI's close
check used a stale poll).  The leftovers (#586, #613-#623) moved to
`T.gc~6.10`.

Tags: `T.gc~6.10`, `T.g~6`, `T.mi~7`, `T.toasl~6.8`.
