"""Tests of `scraftcam.gui.app`."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scraftcam import shops
from scraftcam.gui import app
from scraftcam.settings import (
    Settings,
    read_settings,
    settings_file,
    start_shop,
)


class FindShopTest(unittest.TestCase):
    """Tests of `shop_name()` and `design_name()`."""

    def test_names(self) -> None:
        """A shop's `name`, else its directory; a design's file name."""
        with tempfile.TemporaryDirectory() as temporary:
            shop: Path = Path(temporary) / "garage" / "shop.toml"
            shop.parent.mkdir()
            shop.write_text('name = "  Home shop "\n')
            self.assertEqual(app.shop_name(shop), "Home shop")
            shop.write_text("units = 'in'\n")
            self.assertEqual(app.shop_name(shop), "garage")
            self.assertEqual(app.design_name(Path("x/plate.py")), "plate")
            self.assertEqual(app.design_name(shop.parent), "garage")


class VersionControlTest(unittest.TestCase):
    """Tests of `in_repository()` and `version_control_hint()`."""

    def test_hints(self) -> None:
        """No hint in a repository; otherwise what to install or run."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            with mock.patch("shutil.which", return_value=None):
                self.assertIn(
                    "install git or hg", app.version_control_hint(top)
                )
            with mock.patch("shutil.which", return_value="/usr/bin/hg"):
                self.assertIn("`git init`", app.version_control_hint(top))
            (top / ".hg").mkdir()
            (top / "shop").mkdir()
            self.assertTrue(app.in_repository(top / "shop"))
            self.assertEqual(app.version_control_hint(top / "shop"), "")


class AppTest(unittest.TestCase):
    """Tests of `App`."""

    def test_no_shop(self) -> None:
        """With no shop, the names are `(none)`, and it says so."""
        model: app.App = app.App(None, None)
        self.assertEqual(model.title(), "scraftcam: (none) ((none))")
        self.assertTrue(model.latest().problem)
        self.assertIn("No shop.toml", model.latest().text)

    def test_shop_and_design(self) -> None:
        """The title has both names; a bad shop file is a problem."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            (top / ".git").mkdir()
            shop: Path = top / "shop.toml"
            shop.write_text('name = "Home"\n')
            (top / "plate.py").write_text("def main() -> int:\n    return 0\n")
            model: app.App = app.App(shop, top / "plate.py")
            self.assertEqual(model.title(), "scraftcam: Home (plate)")
            self.assertEqual(model.messages, [])

            # Not TOML: reported, never raised.
            shop.write_text("name = \n")
            model = app.App(shop, None)
            self.assertEqual(model.shop_title, app.NONE_NAME)
            self.assertTrue(model.latest().problem)

    def test_listeners_and_messages(self) -> None:
        """Every listener hears every change, until it is forgotten."""
        model: app.App = app.App(None, None)
        heard: list[int] = []

        def redraw() -> None:
            heard.append(len(model.messages))

        model.listen(redraw)
        model.say("one\n  two")
        self.assertEqual(model.latest(), app.Message("one two", False))
        model.forget(redraw)
        model.say("three")
        self.assertEqual(heard, [2])

    def test_machines(self) -> None:
        """[Stop All] with any machine; closing refused while one runs."""
        model: app.App = app.App(None, None)
        self.assertFalse(model.any_running())
        model.start_machine("shop mill")
        self.assertTrue(model.any_running())
        self.assertEqual(
            model.close_refusal({"shop mill"}), "Stop the shop mill first"
        )
        self.assertEqual(model.close_refusal({"router"}), "")
        model.start_machine("router")
        self.assertTrue(model.any_running())
        model.stop_all()
        self.assertFalse(model.any_running())
        self.assertEqual(model.close_refusal({"shop mill"}), "")


class CopyShopTest(unittest.TestCase):
    """[Copy Shop]: where a copy may go, and the copy (#709, #710)."""

    def test_problems(self) -> None:
        """Names and places refused, and one allowed."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            (top / "full").mkdir()
            (top / "full" / "x").write_text("")
            (top / "file").write_text("")
            (top / "empty").mkdir()
            self.assertIn("name", app.copy_problem(str(top), ""))
            self.assertIn("letters", app.copy_problem(str(top), "a/b"))
            self.assertIn("directory", app.copy_problem("", "mine"))
            self.assertIn("not empty", app.copy_problem(str(top), "full"))
            self.assertIn("a file", app.copy_problem(str(top), "file"))
            self.assertIn(
                "not a directory", app.copy_problem(str(top / "file"), "a")
            )
            self.assertEqual(app.copy_problem(str(top), "empty"), "")
            self.assertEqual(app.copy_problem(str(top / "new"), "mine"), "")

    def test_copy(self) -> None:
        """The example shop copied: named, unlocked, found, shown."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            model: app.App = app.App(shops.EXAMPLE_SHOP_FILE, None)
            model.settings = settings_file(top)
            with mock.patch.object(
                shutil, "copytree", wraps=shutil.copytree
            ) as copying:
                copied: Path = model.copy_shop(top / "shops", "mine")
            self.assertEqual(copied, (top / "shops/mine/shop.toml").resolve())
            self.assertEqual(model.shop_title, "mine")
            self.assertIn("Copied to", model.messages[-1].text)
            ignore = copying.call_args_list[0].kwargs["ignore"]
            self.assertEqual(
                ignore(".", [shops.ALLOW_EDITS, "shop.toml"]),
                {shops.ALLOW_EDITS},
            )
            self.assertFalse(shops.is_read_only(copied))
            self.assertTrue(
                (copied.parent / "tools/drills/drill.outline.toml").is_file()
            )

            # Remembered: its directory, and as the last shop.
            remembered: Settings = read_settings(model.settings)
            self.assertEqual(
                remembered.shop_directories, ((top / "shops").resolve(),)
            )
            self.assertEqual(start_shop(remembered), copied)

            # Not twice to one place.
            with self.assertRaises(ValueError):
                model.copy_shop(top / "shops", "mine")


if __name__ == "__main__":
    unittest.main()
