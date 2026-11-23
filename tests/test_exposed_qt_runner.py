"""Tests for `scraftcam.exposed.qt_runner`: calls cross to Qt's main
thread (#512)."""

import threading
import unittest

from scraftcam.packages import require

# `PySide6` is put on `sys.path` before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order,ungrouped-imports
from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402

from scraftcam.exposed.exposed import ExposedError  # noqa: E402
from scraftcam.exposed.qt_runner import QtRunner  # noqa: E402


def application() -> QCoreApplication:
    """Give the one Qt application, making it if need be."""
    existing: QCoreApplication | None = QCoreApplication.instance()
    return existing if existing is not None else QCoreApplication([])


class TestQtRunner(unittest.TestCase):
    """A `QtRunner` runs work on the thread that made it."""

    def run_from_worker(
        self, runner: QtRunner, work: object
    ) -> dict[str, object]:
        """Call `runner(work)` from a worker thread while the main
        thread runs Qt's event loop; give what happened."""
        # The worker calls; the main thread's loop quits when it ends.
        outcome: dict[str, object] = {}

        def worker() -> None:
            """Call the runner, keeping its result or error."""
            try:
                outcome["result"] = runner(work)  # type: ignore[arg-type]
            except ExposedError as error:
                outcome["error"] = error
            except ValueError as error:
                outcome["error"] = error

        thread: threading.Thread = threading.Thread(target=worker)
        app: QCoreApplication = application()
        timer: QTimer = QTimer()

        def check() -> None:
            """Quit the loop once the worker has finished."""
            if not thread.is_alive():
                app.quit()

        timer.timeout.connect(check)
        timer.start(10)
        thread.start()
        app.exec()
        timer.stop()
        thread.join()
        return outcome

    def test_runs_on_main_thread(self) -> None:
        """The work runs on the main thread; its result comes back."""
        application()
        runner: QtRunner = QtRunner()
        main: threading.Thread = threading.current_thread()

        def work() -> object:
            """Say whether this is the main thread."""
            return threading.current_thread() is main

        self.assertEqual(self.run_from_worker(runner, work), {"result": True})
        self.assertIs(runner(work), True)

    def test_error_comes_back(self) -> None:
        """What the work raises is raised again in the caller."""
        application()
        runner: QtRunner = QtRunner()

        def work() -> object:
            """Fail."""
            raise ValueError("bad corner")

        error: object = self.run_from_worker(runner, work)["error"]
        self.assertIsInstance(error, ValueError)
        self.assertEqual(str(error), "bad corner")

    def test_timeout(self) -> None:
        """With no event loop running, the caller gives up in time."""
        application()
        runner: QtRunner = QtRunner(timeout=0.1)
        outcome: dict[str, object] = {}

        def worker() -> None:
            """Call with nobody to answer."""
            try:
                runner(int)
            except ExposedError as error:
                outcome["error"] = str(error)

        thread: threading.Thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        self.assertIn("did not answer", str(outcome["error"]))


if __name__ == "__main__":
    unittest.main()
