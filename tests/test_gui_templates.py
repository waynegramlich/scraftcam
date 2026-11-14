"""Tests of `scraftcam.gui.templates`: following up a template change."""

import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from scraftcam.gui import templates
from scraftcam.gui.app import App
from scraftcam.gui.fields import read_item
from scraftcam.gui.tree import FILE, Node
from scraftcam.gui.views import Panel
from tests import qt_app

# The example shop, and the new `tool_change` the tests give LinuxCNC.
SHOP: Path = Path("examples/shop")
NEW: str = "T{number:02d} M6"


# Function `tool_change()`:
def tool_change(path: Path) -> object:
    """Return a machine's own `tool_change`.

    Arguments:
    * `path` (`Path`): The machine's file.

    Returns:
    * (`object`): Its `[controller]`'s `tool_change`.
    """
    with path.open("rb") as file:
        item: dict[str, object] = tomllib.load(file)
    controller: object = item["controller"]
    assert isinstance(controller, dict)
    return controller.get("tool_change")


class FollowUpTest(unittest.TestCase):
    """Tests of `follow_ups()`, `update_machine()` and the panel's list."""

    def setUp(self) -> None:
        """Copy the example shop; the router given its own value."""
        # `enterContext()` removes it after the test (pylint does not know).
        temporary: str = self.enterContext(
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        self.top: Path = Path(temporary).resolve() / "shop"
        shutil.copytree(SHOP, self.top)
        self.template: Path = self.top / "controllers" / "linuxcnc.toml"
        self.mill: Path = self.top / "machines" / "shop_mill.toml"
        self.router: Path = self.top / "machines" / "shop_router.toml"
        text: str = self.router.read_text(encoding="utf-8")
        self.router.write_text(
            text.replace("T{number:02d} M6 G43", "T{number:02d} M6 G43 (own)"),
            encoding="utf-8",
        )

    def test_follow_ups(self) -> None:
        """The old value: stale; its own: not; unchanged keys: none."""
        old: dict[str, object] = read_item(self.template)[0]
        new: dict[str, object] = dict(old, tool_change=NEW)
        found: list[templates.FollowUp] = templates.follow_ups(
            self.template, old, new
        )
        self.assertEqual(
            [(f.machine, f.key, f.stale) for f in found],
            [
                ("Shop mill", "tool_change", True),
                ("Shop router", "tool_change", False),
            ],
        )
        self.assertEqual(templates.follow_ups(self.template, old, old), [])
        self.assertEqual(
            templates.follow_ups(self.template, old, dict(old, notes="x")),
            [],
        )
        templates.update_machine(found[0])
        self.assertEqual(tool_change(self.mill), NEW)

    def test_panel(self) -> None:
        """A change in the template's panel lists them, to update."""
        model: App = App(self.top / "shop.toml", None)
        model.new_machine("Big mill", "mill", "LinuxCNC")
        big: Path = self.top / "machines" / "big_mill.toml"
        panel: Panel = Panel(1)
        panel.show_node(Node("linuxcnc.toml", FILE, self.template, ""))
        panel.set_editing(True)
        panel.typed("tool_change", NEW)
        panel.write("tool_change")
        view: templates.FollowUpView | None = panel.follow_up
        assert view is not None
        self.assertEqual(
            [f.machine for f in view.follow_ups],
            ["Big mill", "Shop mill", "Shop router"],
        )

        # [Update All]: the two with the old value; the router kept.
        view.update_stale()
        self.assertEqual(tool_change(big), NEW)
        self.assertEqual(tool_change(self.mill), NEW)
        self.assertNotEqual(tool_change(self.router), NEW)
        view.settle(2, keep=True)
        self.assertEqual(
            [state.text() for state in view.states],
            ["updated", "updated", "kept"],
        )

        # Another item: the list goes.
        panel.show_node(Node("shop_mill.toml", FILE, self.mill, ""))
        self.assertIsNone(panel.follow_up)
        qt_app.process_events()
        panel.deleteLater()


class VersionTest(unittest.TestCase):
    """Tests of a template's `vendor_triple`, filled in (#144)."""

    def test_triple(self) -> None:
        """Entering `vendor_version` fills in `vendor_triple`."""
        top: Path = Path(
            self.enterContext(
                tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
            )
        )
        shutil.copytree(SHOP, top / "shop")
        template: Path = top / "shop" / "controllers" / "linuxcnc.toml"
        panel: Panel = Panel(1)
        panel.show_node(Node("linuxcnc.toml", FILE, template, ""))
        panel.set_editing(True)
        panel.typed("vendor_version", "v2.9.4 (Debian)")
        panel.write("vendor_version")
        item: dict[str, object] = read_item(template)[0]
        self.assertEqual(item["vendor_triple"], "2.9.4")
        self.assertEqual(panel.row("vendor_triple").text, "2.9.4")
        qt_app.process_events()
        panel.deleteLater()


if __name__ == "__main__":
    unittest.main()
