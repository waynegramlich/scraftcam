"""Tests of `scraftcam.gui.window_exposed` and `scraftcam.run --mcp`."""

import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from scraftcam.exposed import client, exposed
from scraftcam.exposed.exposed import ExposedError
from scraftcam.gui import window, window_exposed
from scraftcam.gui.app import App
from scraftcam.shops import EXAMPLE_SHOP
from tests import qt_app

# What the module exposes, under the names a caller uses.
NAMES: tuple[str, ...] = (
    "status",
    "top_button",
    "new_shop",
    "tree",
    "select",
    "panel_tab",
    "open_machine",
    "to_front",
    "quit_all",
)


# Function `free_port()`:
def free_port() -> int:
    """Return a port that is free now.

    Returns:
    * (`int`): The port.
    """
    with socket.socket() as unused:
        unused.bind(("127.0.0.1", 0))
        port: int = unused.getsockname()[1]
        return port


class ExposedTest(unittest.TestCase):
    """Tests of the functions, called as the MCP server calls them."""

    def setUp(self) -> None:
        """One window, with no shop."""
        window.WINDOWS.clear()
        self.model: App = App(None, None)
        self.top: window.Window = window.Window(self.model, {"shop mill"})
        self.top.show()
        self.addCleanup(window.WINDOWS.clear)

    def test_registered(self) -> None:
        """Every function is found by its short name."""
        name: str
        for name in NAMES:
            self.assertTrue(
                exposed.lookup(name).name.startswith(window_exposed.__name__),
                name,
            )

    def test_status_press_quit(self) -> None:
        """`status`, `top_button` (hidden refused), `quit_all`."""
        status: object = exposed.call("status", {})
        assert isinstance(status, dict)
        self.assertEqual(status["shop"], "(none)")
        self.assertEqual(
            status["windows"],
            [
                {
                    "buttons": [
                        "Stop All",
                        "Tree",
                        "+ Panel",
                        "New Window",
                        "Exit",
                        "New Shop",
                    ],
                    "tree": True,
                    "panels": 1,
                }
            ],
        )
        self.assertEqual(
            exposed.call("top_button", {"label": "Tree"}), "pressed Tree"
        )
        self.assertTrue(self.top.tree.isHidden())
        with self.assertRaises(ExposedError):
            exposed.call("top_button", {"label": "Stop All"})
        with self.assertRaises(ExposedError):
            exposed.call("top_button", {"label": "Tree", "window_number": 3})

        # `quit_all` refused while the window's machine runs, then done.
        self.model.start_machine("shop mill")
        with self.assertRaisesRegex(ExposedError, "Stop the shop mill"):
            exposed.call("quit_all", {})
        self.model.stop_machine("shop mill")
        self.assertEqual(exposed.call("quit_all", {}), "quitting")
        _try: int
        for _try in range(100):
            qt_app.process_events()
            if not self.top.isVisible():
                break
            time.sleep(0.01)
        self.assertEqual(window.WINDOWS, [])

    def test_panel_tab_to_front(self) -> None:
        """`panel_tab` shows a tab, refusing one that is not there."""
        # A new window's panel shows only its guide (#586).
        self.assertEqual(
            exposed.call("panel_tab", {"label": "Guide"}), "showing Guide"
        )
        with self.assertRaisesRegex(ExposedError, "there are: Guide$"):
            exposed.call("panel_tab", {"label": "Outline"})
        self.assertEqual(exposed.call("to_front", {}), "in front")
        # No connector (`run()` gives one): said so (#607).
        opened: object = exposed.call("open_machine", {"name": "Mill"})
        assert isinstance(opened, dict)
        self.assertIn("Mill is not connected", str(opened["message"]))

    def test_new_shop_tree_select(self) -> None:
        """`new_shop` makes a shop; `tree` lists it; `select` clicks."""
        with tempfile.TemporaryDirectory() as temporary:
            # A shop, and one refused for a bad machine kind.
            directory: Path = Path(temporary) / "shop"
            made: object = exposed.call(
                "new_shop",
                {
                    "directory": str(directory),
                    "name": "Lab",
                    "units": "in",
                    "machines": [],
                },
            )
            self.assertTrue(str(made).endswith("shop.toml"))
            self.assertEqual(self.model.shop_title, "Lab")
            with self.assertRaises(ExposedError):
                exposed.call(
                    "new_shop",
                    {
                        "directory": str(directory),
                        "name": "Lab",
                        "units": "in",
                        "machines": [3],
                    },
                )

            # The tree, then a click on the shop.
            self.assertEqual(
                exposed.call("tree", {}),
                [
                    [
                        "Lab (directory)",
                        ["controllers (directory)", ["LinuxCNC (file)"]],
                    ]
                ],
            )
            shown: object = exposed.call(
                "select", {"path": str(directory / "shop.toml")}
            )
            assert isinstance(shown, dict)
            self.assertEqual(shown["label"], "Lab (directory)")
            fields: object = shown["fields"]
            assert isinstance(fields, dict)
            self.assertEqual(fields["name"], "Lab")
            with self.assertRaises(ExposedError):
                exposed.call("select", {"path": "/nowhere"})


class RunTest(unittest.TestCase):
    """`scraftcam.run --headless --mcp PORT`, through the client."""

    def test_start_call_stop(self) -> None:
        """The client starts the GUI, calls `status`, and stops it."""
        port: int = free_port()
        with tempfile.TemporaryDirectory() as temporary:
            # No shop here, so that none is found from the directory.
            started: str = client.start(
                port, Path(temporary) / "none", gui=True
            )
            self.addCleanup(client.stop, port)
            self.assertIn("status:", started)
            status: object = json.loads(
                client.tool(port, "call", {"name": "status", "arguments": {}})
            )
            assert isinstance(status, dict)
            self.assertEqual(len(status["windows"]), 1)

    def test_tutorial(self) -> None:
        """`--headless --tutorial` checks a recording (#595)."""
        # The kept recording matches; a missing one is refused.
        recording: Path = (
            Path(__file__).resolve().parents[1]
            / "steps/move_a_corner.steps.md"
        )
        command: list[str] = [
            sys.executable,
            "-m",
            "scraftcam.run",
            "--headless",
            "--tutorial",
        ]
        done: subprocess.CompletedProcess[str] = subprocess.run(
            [*command, str(recording)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("all match", done.stdout)
        done = subprocess.run(
            [*command, "/nowhere.steps.md"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(done.returncode, 1)

    def test_pages_refused(self) -> None:
        """`--pages` with no such catalog says so, and stops (#600)."""
        done: subprocess.CompletedProcess[str] = subprocess.run(
            [
                sys.executable,
                "-m",
                "scraftcam.run",
                "--headless",
                f"--shop={EXAMPLE_SHOP}",
                "--pages=/nowhere/catalog.toml",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(done.returncode, 1)
        self.assertIn("No catalog", done.stderr)


if __name__ == "__main__":
    unittest.main()
