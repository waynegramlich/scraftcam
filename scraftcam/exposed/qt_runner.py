"""Run MCP calls on Qt's main thread (#512).

The server answers each request on a thread of its own, but Qt's
widgets may only be touched from the main thread.  A `QtRunner`,
made on the main thread, is the server's runner: it hands each call
across with a queued signal and waits for the answer.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from scraftcam.exposed.exposed import ExposedError
from scraftcam.packages import require

# `PySide6` lives in `~/.scraftcam/packages/`, so it is put on
# `sys.path` (and fetched, the first time) before it is imported.
require("PySide6")
# pylint: disable=wrong-import-position,wrong-import-order
from PySide6.QtCore import QObject, Qt, Signal  # noqa: E402

# pylint: enable=wrong-import-position,wrong-import-order

# How long a call may take on the main thread before it is given up.
TIMEOUT: float = 60.0


@dataclass(slots=True)
class Job:
    """One call waiting to run on the main thread.

    Constructor:
    * `Job(work)`

    Attributes:
    * `work` (`Callable[[], object]`):
        The call to run.
    * `done` (`threading.Event`):
        Set once it has run.
    * `error` (`BaseException | None`):
        What it raised, if anything (absent is a real state).
    * `result` (`object`):
        What it returned.
    """

    # Constructor arguments:
    work: Callable[[], object] = field(init=True)

    # Filled in when it runs (alphabetized):
    done: threading.Event = field(init=False, default_factory=threading.Event)
    error: BaseException | None = field(init=False, default=None)
    result: object = field(init=False, default=None)


class QtRunner(QObject):
    """Runs each call on the thread it was made on (Qt's main one).

    Attributes:
    * `arrived` (`Signal`):
        Carries a `Job` across to the main thread.
    * `timeout` (`float`):
        Seconds a call may take before the caller gives up.
    """

    arrived: Signal = Signal(object)

    def __init__(self, timeout: float = TIMEOUT) -> None:
        """Make the runner; call it on Qt's main thread.

        Arguments:
        * `timeout` (`float`):
            Seconds a call may take before the caller gives up.
        """
        super().__init__()
        self.timeout: float = timeout
        self.arrived.connect(self._run, Qt.ConnectionType.QueuedConnection)

    def __call__(self, work: Callable[[], object]) -> object:
        """Run `work` on the main thread, waiting for its answer.

        Arguments:
        * `work` (`Callable[[], object]`):
            The call to run.

        Returns:
        * (`object`): its result.

        Raises:
        * `ExposedError`: when the main thread does not answer in
          time (it is busy, or its event loop is not running).
        * Whatever `work` raised, raised again here.
        """
        # On the main thread already: queuing would wait on itself.
        if self.thread().isCurrentThread():
            return work()

        # Hand it across, then wait for it.
        job: Job = Job(work)
        self.arrived.emit(job)
        if not job.done.wait(self.timeout):
            raise ExposedError(
                f"the GUI did not answer within {self.timeout} s"
            )
        if job.error is not None:
            raise job.error
        return job.result

    def _run(self, job: object) -> None:
        """Run one `Job` (on the main thread) and wake its caller.

        Arguments:
        * `job` (`object`):
            The `Job` (signals carry plain objects).
        """
        # Anything it raises goes back to the caller's thread.
        if isinstance(job, Job):
            try:
                job.result = job.work()
            # Every error belongs to the caller, not the event loop.
            except Exception as error:  # noqa: BLE001  # pylint: disable=broad-except
                job.error = error
            finally:
                job.done.set()
