"""The test suites.

`PySide6` lives in `~/.scraftcam/packages/`, so it is put on
`sys.path` here, before any suite runs, and each suite imports it at
its top like any other package.
"""

from scraftcam.packages import require

require("PySide6")
