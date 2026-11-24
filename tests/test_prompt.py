"""Tests of `scraftcam.gui.prompt`: dialogs inside a widget (#606)."""

import unittest

from scraftcam.gui import prompt
from scraftcam.packages import require
from tests import qt_app

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QWidget,
)

# pylint: enable=wrong-import-position,wrong-import-order


class PromptTest(unittest.TestCase):
    """A prompt waits inside its host; the rest stays usable."""

    def setUp(self) -> None:
        """A window of two halves: the host, and something else."""
        qt_app.process_events()
        self.window: QWidget = QWidget()
        row: QHBoxLayout = QHBoxLayout(self.window)
        self.host: QWidget = QWidget()
        self.other: QPushButton = QPushButton("Other")
        row.addWidget(self.host)
        row.addWidget(self.other)
        self.window.resize(800, 400)
        self.window.show()
        qt_app.process_events()
        self.addCleanup(self.window.deleteLater)
        self.seen: dict[str, object] = {}

    def look(self) -> None:
        """Note where the prompt is, and what else may be used."""
        shade: prompt.Shade | None = self.host.findChild(prompt.Shade)
        self.seen["shade"] = shade
        self.seen["covers"] = (
            shade is not None and shade.geometry() == self.host.rect()
        )
        self.seen["other"] = self.other.isEnabled()
        box: QMessageBox | None = self.host.findChild(QMessageBox)
        self.seen["window"] = box is not None and not box.isWindow()

    def test_yes_no(self) -> None:
        """Yes, pressed in the host, answers True; the shade goes."""

        def answer() -> None:
            """Look, then press Yes."""
            self.look()
            box: QMessageBox | None = self.host.findChild(QMessageBox)
            assert box is not None
            box.button(QMessageBox.StandardButton.Yes).click()

        QTimer.singleShot(50, answer)
        self.assertTrue(prompt.ask_yes_no(self.host, "Title", "Sure?"))
        self.assertTrue(self.seen["covers"])
        self.assertTrue(self.seen["other"])
        self.assertTrue(self.seen["window"])
        left: prompt.Shade | None = self.host.findChild(prompt.Shade)
        self.assertTrue(left is None or not left.isVisible())

    def test_item_cancelled(self) -> None:
        """A choice cancelled is `None`."""

        def cancel() -> None:
            """Reject the choice."""
            box: QInputDialog | None = self.host.findChild(QInputDialog)
            assert box is not None
            box.reject()

        QTimer.singleShot(50, cancel)
        self.assertIsNone(
            prompt.ask_item(self.host, "Tool", "Which?", ["T1", "T2"])
        )


if __name__ == "__main__":
    unittest.main()
