"""Tests of `scraftcam.gui.window` (offscreen) and `scraftcam.run`."""

import functools
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from scraftcam import run
from scraftcam.gui.app import App
from scraftcam.gui.machines import Due, MachineControl
from scraftcam.gui.outline_panel import READ_ONLY_OUTLINE, OutlinePanel
from scraftcam.gui.theme import colors
from scraftcam.gui.views import Panel, TreeWatcher
from scraftcam.gui.window import EXIT, CopyShopDialog, Window
from scraftcam.settings import Settings, settings_file, write_settings
from scraftcam.shops import EXAMPLE_SHOP, EXAMPLE_SHOP_FILE
from tests import qt_app


# Function `settle()`:
def settle(window: Window, expected: list[object]) -> bool:
    """Run Qt's events until the first tree root shows `expected`.

    Arguments:
    * `window` (`Window`): The window.
    * `expected` (`list[object]`): The root's labels, nested.

    Returns:
    * (`bool`): True when it did, within about 3 seconds.
    """
    _try: int
    for _try in range(300):
        qt_app.process_events()
        if window.tree.labels()[:1] == [expected]:
            return True
        time.sleep(0.01)
    return False


class WindowTest(unittest.TestCase):
    """Tests of `Window`."""

    def test_top_line(self) -> None:
        """The names, the message, and [Stop All] active while any runs."""
        model: App = App(None, Path("plate.py"))
        first: Window = Window(model)
        second: Window = Window(model)
        self.assertEqual(first.windowTitle(), "scraftcam: (none) (plate)")
        self.assertIn(colors().problem, first.message_label.styleSheet())

        # Both windows follow the model.
        model.say("hello")
        self.assertEqual(second.message_label.text(), "hello")
        self.assertEqual(first.message_label.styleSheet(), "")
        self.assertFalse(first.buttons["Stop All"].isHidden())
        self.assertFalse(first.buttons["Stop All"].isEnabled())
        model.start_machine("shop mill")
        self.assertTrue(second.buttons["Stop All"].isEnabled())
        self.assertIn("bold", second.buttons["Stop All"].styleSheet())
        second.buttons["Stop All"].click()
        self.assertFalse(first.buttons["Stop All"].isEnabled())

    def test_tree_and_panels(self) -> None:
        """[Tree] toggles the tree; [+ Panel] adds a panel."""
        top: Window = Window(App(None, None))
        self.assertFalse(top.tree.isHidden())
        top.buttons["Tree"].click()
        self.assertTrue(top.tree.isHidden())
        top.buttons["Tree"].click()
        self.assertFalse(top.tree.isHidden())
        top.buttons["+ Panel"].click()
        self.assertEqual(len(top.panels), 2)
        self.assertEqual(top.splitter.count(), 3)

    def test_close_refused(self) -> None:
        """A window controlling a running machine refuses to close."""
        model: App = App(None, None)
        top: Window = Window(model, {"shop mill"})
        top.show()
        model.start_machine("shop mill")

        # [Exit] is refused, naming the machine; no question (#611).
        top.buttons[EXIT].click()
        self.assertTrue(top.isVisible())
        self.assertIn("Stop first: shop mill is running", model.latest().text)
        self.assertTrue(model.latest().problem)
        model.stop_machine("shop mill")
        top.buttons[EXIT].click()
        self.assertFalse(top.isVisible())
        self.assertNotIn(top.redraw, model.listeners)

    def test_machine_panel(self) -> None:
        """A machine's panel: never replaced, and busy refuses."""
        top: Window = Window(App(None, None))
        top.show()
        busy: list[str] = ["The mill is running"]
        stops: list[str] = []

        # Function `reason()`:
        def reason() -> str:
            """Return why it is busy, while it is."""
            return busy[0] if busy else ""

        # The controls: any widget (a panel will do).
        control: MachineControl = MachineControl(
            "Mill",
            Panel(9),
            reason,
            functools.partial(stops.append, "stop"),
            functools.partial(Due, "T05", 0.5, 2.0, False),
        )
        top.connect_machine(control)
        top.open_machine("Mill")
        self.assertIs(top.free_panel(), top.panels[1])
        top.panels[0].show_dues(True)
        assert top.panels[0].header is not None
        meter = top.panels[0].header.meter
        self.assertEqual(meter.format(), "▲ 0:30")
        self.assertEqual(meter.value(), 750)
        self.assertEqual(top.busy(), "The mill is running")

        # Active: the tree is forced on and [Tree] greyed (#610); a
        # refused [Exit] names it (#611).
        top.buttons["Tree"].click()
        self.assertTrue(top.tree.isHidden())
        top.show_active()
        self.assertFalse(top.tree.isHidden())
        self.assertFalse(top.buttons["Tree"].isEnabled())
        self.assertEqual(top.tree.active, {"Mill"})
        top.buttons[EXIT].click()
        self.assertIn("The mill is running", top.model.latest().text)
        self.assertTrue(top.isVisible())

        # Stopped: [Tree] usable again, and it closes.
        busy.clear()
        top.show_active()
        self.assertTrue(top.buttons["Tree"].isEnabled())
        self.assertEqual(top.tree.active, set())
        top.close()
        self.assertFalse(top.isVisible())

    def test_select(self) -> None:
        """A clicked item shows in the current panel; red for errors."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            (top / "shop").mkdir()
            shop: Path = top / "shop" / "shop.toml"
            shop.write_text('name = "Home"\n')
            (top / "shop" / "bad.toml").write_text("x = \n")
            design: Path = top / "plate.py"
            design.write_text(
                '"""A plate."""\n\ndef main() -> int:\n    return 0\n'
            )
            window: Window = Window(App(shop, design))
            self.assertEqual(
                window.tree.labels(),
                [
                    ["Home (directory)", ["bad.toml (error)"]],
                    ["plate (design)"],
                ],
            )

            # The design, in the first panel.
            item = window.tree.item_at_path(design)
            assert item is not None
            window.select_item(item)
            self.assertEqual(window.panels[0].text.toPlainText(), "A plate.")

            # A new panel is current; the bad file shows there, in red.
            window.buttons["+ Panel"].click()
            self.assertEqual(window.current, 1)
            item = window.tree.item_at_path(top / "shop" / "bad.toml")
            assert item is not None
            window.select_item(item)
            self.assertIn("syntax error", window.panels[1].text.toPlainText())
            self.assertIn("#c00000", window.panels[1].title.styleSheet())
            self.assertEqual(window.panels[0].text.toPlainText(), "A plate.")

            # Clicking the first panel makes it current again.
            window.panels[0].clicked.emit()
            self.assertEqual(window.current, 0)

    def test_edit(self) -> None:
        """[Edit] for Python; `VISUAL` run; else the default, hinted once."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            design: Path = top / "plate.py"
            design.write_text("def main() -> int:\n    return 0\n")
            (top / "notes").mkdir()
            (top / "notes" / "a.py").write_text("")
            model: App = App(None, design)
            window: Window = Window(model)
            self.assertTrue(window.panels[0].edit_row.isHidden())

            # A directory: no [Edit].
            item = window.tree.item_at_path(top / "notes")
            assert item is not None
            window.select_item(item)
            self.assertTrue(window.panels[0].edit_row.isHidden())

            # The design: [Edit] runs `VISUAL`.
            item = window.tree.item_at_path(design)
            assert item is not None
            window.select_item(item)
            self.assertFalse(window.panels[0].edit_row.isHidden())
            self.assertFalse(window.panels[0].edit_button.isEnabled())
            window.panels[0].editing_box.setChecked(True)
            self.assertTrue(window.panels[0].edit_button.isEnabled())
            with (
                mock.patch.dict(os.environ, {"VISUAL": "kate"}),
                mock.patch("subprocess.Popen") as popen,
            ):
                window.panels[0].edit_button.click()
            self.assertEqual(popen.call_args.args[0], ["kate", str(design)])

            # Neither set: the desktop's default, the hint only once.
            with (
                mock.patch.dict(os.environ, {"VISUAL": "", "EDITOR": ""}),
                mock.patch(
                    "PySide6.QtGui.QDesktopServices.openUrl",
                    return_value=True,
                ),
            ):
                window.panels[0].edit_button.click()
                self.assertIn("environment variable", model.latest().text)
                model.say("later")
                window.panels[0].edit_button.click()
                self.assertEqual(model.latest().text, "later")

    def test_read_only_shop(self) -> None:
        """A read only shop: [Allow Changes] greyed, nothing new (#683)."""
        model: App = App(EXAMPLE_SHOP_FILE, None)
        window: Window = Window(model)
        drill: Path = (
            EXAMPLE_SHOP / "tools/drills/15_64_in_hss_jobber_drill.toml"
        )
        item = window.tree.item_at_path(drill)
        assert item is not None

        # Read only, whatever `.allow_edits` says in this checkout.
        with (
            mock.patch("scraftcam.gui.views.is_read_only", return_value=True),
            mock.patch("scraftcam.gui.app.is_read_only", return_value=True),
        ):
            window.select_item(item)
            panel: Panel = window.panels[0]
            self.assertFalse(panel.edit_row.isHidden())
            self.assertFalse(panel.editing_box.isEnabled())
            self.assertFalse(panel.editing)
            with self.assertRaises(ValueError):
                model.new_machine("x", "mill", "linuxcnc")

        # A shop that may be changed: [Allow Changes] works.
        with mock.patch(
            "scraftcam.gui.views.is_read_only", return_value=False
        ):
            window.select_item(item)
            panel.set_editing(False)
            self.assertTrue(panel.editing_box.isEnabled())

    def test_copy_shop(self) -> None:
        """[Copy Shop]: red until the place is right, then copied."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            model: App = App(EXAMPLE_SHOP_FILE, None)
            model.settings = settings_file(top)
            window: Window = Window(model)
            self.assertFalse(window.copy_shop_row.isHidden())
            dialog: CopyShopDialog = CopyShopDialog(window, model)

            # No name, then a bad one: [Copy] grey, saying why.
            dialog.directory.setEditText(str(top / "shops"))
            self.assertFalse(dialog.copy_button.isEnabled())
            dialog.name.setText("my/shop")
            self.assertIn("letters", dialog.problem.text())
            dialog.name.setText("mine")
            self.assertEqual(dialog.problem.text(), "")

            # [Copy]: the copy is shown, and offered next time.
            dialog.copy_button.click()
            self.assertEqual(model.shop_title, "mine")
            self.assertTrue((top / "shops/mine/shop.toml").is_file())
            again: CopyShopDialog = CopyShopDialog(window, model)
            self.assertEqual(
                again.directory.itemText(0), str((top / "shops").resolve())
            )
            again.directory.setEditText(str(top / "shops"))
            again.name.setText("mine")
            self.assertIn("not empty", again.problem.text())

    def test_outline_read_only(self) -> None:
        """`--outline` on an outline in the package: read only (#683)."""
        drill: Path = EXAMPLE_SHOP / "tools/drills/drill.outline.toml"
        locked: bool
        for locked in (True, False):
            model: App = App(None, None)
            window: Window = Window(model)
            opener: OutlinePanel = OutlinePanel(
                drill, None, None, speech=False, headless=True
            )
            with mock.patch(
                "scraftcam.gui.outline_panel.is_read_only",
                return_value=locked,
            ):
                self.assertIsNone(opener.open(window))
            editor = window.panels[0].outline
            assert editor is not None
            self.assertEqual(editor.read_only, locked)
            self.assertEqual(
                "read only" in window.panels[0].title.text(), locked
            )
            self.assertEqual(model.latest().text == READ_ONLY_OUTLINE, locked)
            window.close()

    def test_outline_item(self) -> None:
        """A kind's outline in the tree opens its editor (#730, #733)."""
        model: App = App(EXAMPLE_SHOP_FILE, None)
        window: Window = Window(model)
        outline: Path = EXAMPLE_SHOP / "tools/drills/drill.outline.toml"
        item = window.tree.item_at_path(outline)
        assert item is not None
        with mock.patch("scraftcam.gui.views.is_read_only", return_value=True):
            window.select_item(item)
            panel: Panel = window.panels[0]
            self.assertEqual(panel.title.text(), "Drill outline")
            self.assertEqual(
                panel.title.toolTip(), "tools/drills/drill.outline.toml"
            )
            editor = panel.outline
            assert editor is not None
            self.assertIs(panel.tabs.currentWidget(), editor)
            self.assertTrue(editor.read_only)
            self.assertFalse(panel.editing_box.isEnabled())
        window.close()

    def test_watcher(self) -> None:
        """A file added, broken or removed outside shows in the tree."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            shop: Path = top / "shop.toml"
            shop.write_text('name = "Home"\n')
            model: App = App(shop, None)
            window: Window = Window(model)
            watcher: TreeWatcher = TreeWatcher(model)
            self.addCleanup(model.forget, watcher.follow)

            # Added, then broken, then removed.
            (top / "mill.toml").write_text('name = "Mill"\n')
            self.assertTrue(
                settle(window, ["Home (directory)", ["Mill (file)"]])
            )
            (top / "mill.toml").write_text("name = \n")
            self.assertTrue(
                settle(window, ["Home (directory)", ["mill.toml (error)"]])
            )
            (top / "mill.toml").unlink()
            self.assertTrue(settle(window, ["Home (directory)"]))


class RunTest(unittest.TestCase):
    """Tests of `run.start_file()`."""

    def test_start_file(self) -> None:
        """The last shop in the settings, else the example shop (#704)."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            shop: Path = top / "shop.toml"
            shop.write_text('name = "Home"\n')

            # A scratch home's settings; never a search up (#693).
            settings: Path = settings_file(top)
            with mock.patch("scraftcam.run.settings_file") as where:
                where.return_value = settings
                self.assertEqual(run.start_file(), EXAMPLE_SHOP_FILE)
                write_settings(Settings((), top), settings)
                self.assertEqual(run.start_file(), shop)
                settings.write_text("last_shop = [")
                self.assertEqual(run.start_file(), EXAMPLE_SHOP_FILE)


if __name__ == "__main__":
    unittest.main()
