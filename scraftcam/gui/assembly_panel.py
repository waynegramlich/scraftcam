"""An assembly file's panel tab (`T.sa~6.11` #S6): its parts and how
each stands on another, and [Solid], which shows it in SolidCraft.
"""

from pathlib import Path

from ..packages import require

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView,
    QApplication,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..shops import ASSEMBLY_SUFFIX  # noqa: E402
from .assembly_file import (  # noqa: E402
    Assembly,
    Part,
    assembly_cacheable,
    assembly_from_text,
)
from .outline_file import OutlineError  # noqa: E402
from .solid_viewer import VIEWER, ViewerError  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order

# The parts table's columns.
PART_COLUMNS: tuple[str, ...] = ("Part", "Outline", "On", "At", "Face")


# Class `AssemblyView`:
class AssemblyView(QWidget):
    """An assembly's parts, read only, and [Solid].

    Attributes:
    * `path` (`Path`): The assembly file.
    * `assembly` (`Assembly | None`): What it holds; `None` when it
      can not be read.
    * `table` (`QTableWidget`): A row per part.
    * `solid_button` (`QPushButton`): [Solid].
    * `message` (`QLabel`): What [Solid] or reading said.
    """

    # Method `AssemblyView.__init__()`:
    def __init__(self, path: Path) -> None:
        """Make the view of an assembly file.

        Arguments:
        * `path` (`Path`): The `KIND.assembly.toml`.
        """
        super().__init__()
        self.path: Path = path
        self.assembly: Assembly | None = None
        self.table: QTableWidget = QTableWidget(0, len(PART_COLUMNS))
        self.table.setHorizontalHeaderLabels(list(PART_COLUMNS))
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.solid_button: QPushButton = QPushButton("Solid")
        self.solid_button.setToolTip("Show this as a solid in SolidCraft")
        self.solid_button.clicked.connect(self.show_solid)
        self.message: QLabel = QLabel("")
        self.message.setWordWrap(True)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(self.solid_button)
        layout.addWidget(self.message)
        self.read()

    # Method `AssemblyView.read()`:
    def read(self) -> None:
        """Read the file and show its parts, or what is wrong."""
        try:
            self.assembly = assembly_from_text(
                self.path.read_text(encoding="utf-8"), str(self.path)
            )
        except (OSError, OutlineError) as error:
            self.assembly = None
            self.message.setText(str(error))
            self.solid_button.setEnabled(False)
            return
        self.table.setRowCount(len(self.assembly.parts))
        row: int
        part: Part
        for row, part in enumerate(self.assembly.parts):
            column: int
            text: str
            for column, text in enumerate(
                (part.name, part.outline, part.on, part.at, part.face)
            ):
                self.table.setItem(row, column, QTableWidgetItem(text))

    # Method `AssemblyView.name()`:
    def name(self) -> str:
        """Return the solid's name: the file's, before its suffix.

        Returns:
        * (`str`): The name.
        """
        return self.path.name.removesuffix(ASSEMBLY_SUFFIX)

    # Method `AssemblyView.show_solid()`:
    def show_solid(self) -> None:
        """[Solid]: show the assembly in SolidCraft, started if need
        be, saying so below."""
        if self.assembly is None:
            return
        self.message.setText("Building the solid...")
        QApplication.processEvents()
        try:
            VIEWER.show(
                assembly_cacheable(
                    self.assembly, self.name(), self.path.parent
                )
            )
        except (OutlineError, ValueError, ViewerError) as error:
            self.message.setText(f"No solid: {error}")
        else:
            self.message.setText("")
