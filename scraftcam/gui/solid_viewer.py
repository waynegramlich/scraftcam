"""The SolidCraft in which a user looks at solids (`T.sa~6.11` #S4).

It is started only when a solid is first shown (#842), or one already
answering on its port is used, so there is never more than one
(#852).  Each solid is made headless into the model cache and its
`.step` put in the design (#831); [Solid] then shows one tool and
hides the rest (#832), replacing a tool whose shape has changed
(#855).  [Exit] stops a SolidCraft that was started here (#844).
"""

from __future__ import annotations

import atexit
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from ..model_cache import Cacheable, InsertedModel, ModelCache
from ..pybind.scraftpybind import JSON, PyBind, connect

# The control port it answers on (the demo's and the HMI's).
SOLIDCRAFT_PORT: int = 8080

# Where SolidCraft keeps its control files, and the AppImage beside
# this project when `solidcraft` is not on the `PATH`.
CONTROL_DIRECTORY: Path = (
    Path.home() / ".local" / "share" / "solidcraft" / "control"
)
SOLIDCRAFT_BESIDE: Path = (
    Path(__file__).resolve().parents[2].parent
    / "solidcraft"
    / "solidcraft-linux-x86_64.AppImage"
)

# How long it may take to come up, and how often to look (seconds).
START_SECONDS: float = 120.0
POLL: float = 0.25


# Class `ViewerError`:
class ViewerError(Exception):
    """SolidCraft could not be found, started or reached."""


# Function `port_open()`:
def port_open(port: int) -> bool:
    """Return whether something answers on a local port.

    Arguments:
    * `port` (`int`): The port.

    Returns:
    * (`bool`): True when a connection is taken.
    """
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


# Function `find_solidcraft()`:
def find_solidcraft() -> str:
    """Return the SolidCraft program: on the `PATH`, or the AppImage
    beside this project.

    Returns:
    * (`str`): The program.

    Raises:
    * `ViewerError`: If there is none.
    """
    found: str | None = shutil.which("solidcraft")
    if found is None and SOLIDCRAFT_BESIDE.is_file():
        found = str(SOLIDCRAFT_BESIDE)
    if found is None:
        raise ViewerError(
            "No SolidCraft found: put `solidcraft` on the PATH "
            f"(looked for {SOLIDCRAFT_BESIDE} too)."
        )
    return found


# Class `SolidViewer`:
@dataclass(slots=True)
class SolidViewer:
    """The SolidCraft window solids are shown in.

    Attributes:
    * `port` (`int`): Its control port.
    * `cache` (`ModelCache`): Where solids' `.step` files are made.
    * `process` (`subprocess.Popen[bytes] | None`): The SolidCraft
      started here, if any (one found running is not ours to stop).
    * `solidcraft` (`PyBind | None`): The connection, once made.
    * `shown` (`dict[str, tuple[Path, InsertedModel]]`): Each solid
      put in the design, by name: its file and what was inserted.

    Constructor:
    * `SolidViewer(port, cache)`
    """

    # Constructor arguments:
    port: int = field(init=True, default=SOLIDCRAFT_PORT)
    cache: ModelCache = field(init=True, default_factory=ModelCache)

    # Attributes filled in later (alphabetized):
    process: subprocess.Popen[bytes] | None = field(init=False, default=None)
    shown: dict[str, tuple[Path, InsertedModel]] = field(
        init=False, default_factory=dict
    )
    solidcraft: PyBind | None = field(init=False, default=None)

    # Method `SolidViewer.start()`:
    def start(self) -> PyBind:
        """Connect, starting SolidCraft first if nothing answers.

        Returns:
        * (`PyBind`): The connection.

        Raises:
        * `ViewerError`: If it can not be found, or does not come up.
        """
        if self.solidcraft is not None:
            return self.solidcraft
        if not port_open(self.port):
            self.launch()
        self.solidcraft = PyBind(connect(str(self.port)))
        return self.solidcraft

    # Method `SolidViewer.launch()`:
    def launch(self) -> None:
        """Start SolidCraft on the port and wait for it: a killed one's
        pid file is cleared first, and the token file comes with the
        port, or just after it.

        Raises:
        * `ViewerError`: If it can not be found, or does not come up.
        """
        pid_file: Path = CONTROL_DIRECTORY / f"{self.port}.pid"
        if pid_file.is_file():
            words: list[str] = pid_file.read_text(encoding="utf-8").split()
            if not words or not Path(f"/proc/{words[0]}").exists():
                pid_file.unlink()
        self.process = subprocess.Popen(  # pylint: disable=consider-using-with
            [find_solidcraft(), "--control", str(self.port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        token: Path = CONTROL_DIRECTORY / f"{self.port}.token"
        end: float = time.monotonic() + START_SECONDS
        while not (port_open(self.port) and token.is_file()):
            if self.process.poll() is not None:
                raise ViewerError("SolidCraft stopped as it started")
            if time.monotonic() > end:
                raise ViewerError(
                    f"SolidCraft did not answer on port {self.port}"
                )
            time.sleep(POLL)

    # Method `SolidViewer.show()`:
    def show(self, model: Cacheable) -> None:
        """Show one solid, alone: put it in the design if it is not
        there (made headless into the cache), replacing an older shape
        of it, and hide every other.

        Arguments:
        * `model` (`Cacheable`): The solid.

        Raises:
        * `ViewerError`: If SolidCraft can not be reached, or the
          solid can not be put in.
        """
        solidcraft: PyBind = self.start()
        path: Path = self.cache.path(model)
        old: tuple[Path, InsertedModel] | None = self.shown.get(model.name)
        if old is not None and old[0] != path:
            solidcraft.component.delete(component=old[1].component)
            del self.shown[model.name]
        if model.name not in self.shown:
            inserted: InsertedModel | None = self.cache.insert(
                solidcraft, model
            )
            if inserted is None:
                raise ViewerError(f"{model.name}: not put in SolidCraft")
            self.shown[model.name] = (path, inserted)
        others: list[str] = [
            body
            for name, (_, inserted) in self.shown.items()
            if name != model.name
            for body in inserted.bodies
        ]
        if others:
            solidcraft.browser.visibility(
                visible=False, items=cast(JSON, others)
            )
        solidcraft.browser.visibility(
            visible=True,
            items=cast(JSON, self.shown[model.name][1].bodies),
        )

    # Method `SolidViewer.stop()`:
    def stop(self) -> None:
        """Stop the SolidCraft started here, if any (#844)."""
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.solidcraft = None
        self.shown.clear()


# The one viewer of the program (#852): started by the first [Solid],
# stopped when the program ends ([Exit], #844) if it started it.
VIEWER: SolidViewer = SolidViewer()
atexit.register(VIEWER.stop)
