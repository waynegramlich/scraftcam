"""Tests for `settings.py` (where the shops are) and read only shops."""

import tempfile
import unittest
from pathlib import Path

from scraftcam.settings import (
    Settings,
    SettingsError,
    find_shops,
    read_settings,
    settings_file,
    start_shop,
    write_settings,
)
from scraftcam.shops import ALLOW_EDITS, EXAMPLE_SHOP_FILE, is_read_only


class TestSettings(unittest.TestCase):
    """Reading, writing and searching, in a scratch home."""

    def setUp(self) -> None:
        """Make a scratch home, never the user's (removed after)."""
        # `enterContext()` is the `with`: it cleans up after the test.
        folder: str = self.enterContext(
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        self.home: Path = Path(folder)
        self.file: Path = settings_file(self.home)

    def shop(self, directory: Path) -> Path:
        """Make a shop (just its `shop.toml`) and return its directory."""
        directory.mkdir(parents=True)
        (directory / "shop.toml").write_text('name = "x"\n', encoding="utf-8")
        return directory

    def test_no_file(self) -> None:
        """With no file, only the example shop, which is shown (#682)."""
        settings: Settings = read_settings(self.file)
        self.assertEqual(settings, Settings())
        self.assertEqual(find_shops(settings), [EXAMPLE_SHOP_FILE])
        self.assertEqual(start_shop(settings), EXAMPLE_SHOP_FILE)
        self.assertFalse(self.file.exists())

    def test_round_trip(self) -> None:
        """What is written reads back the same."""
        settings: Settings = Settings(
            (self.home / "shops", self.home / 'odd "name"'),
            self.home / "shops" / "mine",
        )
        write_settings(settings, self.file)
        self.assertEqual(read_settings(self.file), settings)

    def test_find_and_start(self) -> None:
        """Shops in directory order, then name order; the last shown."""
        first: Path = self.home / "a"
        second: Path = self.home / "b"
        zebra: Path = self.shop(first / "zebra")
        apple: Path = self.shop(first / "apple")
        (first / "not_a_shop").mkdir()
        other: Path = self.shop(second / "other")
        settings: Settings = Settings(
            (first, self.home / "missing", second), other
        )
        self.assertEqual(
            find_shops(settings),
            [
                EXAMPLE_SHOP_FILE,
                apple / "shop.toml",
                zebra / "shop.toml",
                other / "shop.toml",
            ],
        )
        self.assertEqual(start_shop(settings), other / "shop.toml")

        # A last shop that is gone: the example shop.
        gone: Settings = Settings((first,), self.home / "gone")
        self.assertEqual(start_shop(gone), EXAMPLE_SHOP_FILE)

    def test_tilde(self) -> None:
        """`~` is the user's home."""
        self.file.parent.mkdir(parents=True)
        self.file.write_text(
            'shop_directories = ["~/shops"]\n', encoding="utf-8"
        )
        self.assertEqual(
            read_settings(self.file).shop_directories,
            (Path.home() / "shops",),
        )

    def test_bad(self) -> None:
        """A bad file is refused, naming it."""
        self.file.parent.mkdir(parents=True)
        text: str
        for text in (
            "shop_directories = [",
            'shop_directories = "~/shops"\n',
            "shop_directories = [1]\n",
            "last_shop = 3\n",
        ):
            self.file.write_text(text, encoding="utf-8")
            with self.assertRaises(SettingsError) as caught:
                read_settings(self.file)
            self.assertIn(str(self.file), str(caught.exception))


class TestReadOnly(unittest.TestCase):
    """A shop in the package is read only, but for `.allow_edits`."""

    def test_read_only(self) -> None:
        """In a scratch package: locked, then unlocked by the marker."""
        with tempfile.TemporaryDirectory() as folder:
            top: Path = Path(folder)
            package: Path = top / "scraftcam"
            shop: Path = package / "example_shop"
            (shop / "tools").mkdir(parents=True)
            (shop / "shop.toml").write_text("", encoding="utf-8")
            tool: Path = shop / "tools" / "drill.toml"
            outside: Path = top / "shops" / "mine" / "shop.toml"

            # Locked, with everything else in the package.
            self.assertTrue(is_read_only(shop, package=package))
            self.assertTrue(is_read_only(tool, package=package))
            self.assertTrue(
                is_read_only(package / "solid.py", package=package)
            )
            self.assertFalse(is_read_only(outside, package=package))

            # The marker unlocks the shop, and only the shop.
            (shop / ALLOW_EDITS).touch()
            self.assertFalse(is_read_only(tool, package=package))
            self.assertTrue(
                is_read_only(package / "solid.py", package=package)
            )


if __name__ == "__main__":
    unittest.main()
