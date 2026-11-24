"""Tests of [New Catalog] and its helpers (`T.c~6.3`)."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scraftcam import shops
from scraftcam.catalog.catxtract import App as Pages
from scraftcam.gui import app, prompt
from scraftcam.gui import window as window_module
from scraftcam.gui.app import App
from scraftcam.gui.views import Panel
from scraftcam.gui.window import NewCatalogDialog, Window, index_start
from tests import qt_app
from tests.test_catalog_pdf import READY, write_pdf

# The example shop.
SHOP: Path = Path("examples/shop")


class IgnoreTest(unittest.TestCase):
    """Tests of `ignores_needed()` and `add_ignores()` (#51)."""

    def test_ignores(self) -> None:
        """Each repository's file gets its line once; none outside one."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            shop: Path = top / "sub" / "shop"
            shop.mkdir(parents=True)
            self.assertEqual(app.ignores_needed(shop), [])
            (top / ".git").mkdir()
            (top / ".hg").mkdir()
            (top / ".hgignore").write_text("^\\.git/", encoding="utf-8")
            needed: list[tuple[Path, str]] = app.ignores_needed(shop)
            self.assertEqual(
                [path.name for path, _line in needed],
                [".gitignore", ".hgignore"],
            )
            app.add_ignores(needed)
            self.assertEqual(app.ignores_needed(shop), [])
            self.assertEqual(
                (top / ".hgignore").read_text(encoding="utf-8"),
                "^\\.git/\n# Catalog PDFs and their pages (scraftcam).\n"
                + app.IGNORE_LINES[".hg"]
                + "\n",
            )

    def test_catalog_text(self) -> None:
        """A vendor and an edition are needed; spaces are tidied."""
        with self.assertRaises(ValueError):
            app.new_catalog_text("Shars", " ", "a.pdf", 3)
        self.assertIn(
            'name = "Shars 2026"',
            app.new_catalog_text(" Shars ", "2026", "a.pdf", 3),
        )


class NewCatalogTest(unittest.TestCase):
    """Tests of [New Catalog] (#61)."""

    def test_new_catalog(self) -> None:
        """Shown for the shop; grey until answered; made, linked, read."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary) / "shop"
            shutil.copytree(
                SHOP, top, ignore=shutil.ignore_patterns("catalogs")
            )
            (top / ".git").mkdir()
            pdf: Path = Path(temporary) / "catalog.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            model: App = App((top / "shop.toml").resolve(), None)
            window: Window = Window(model)
            assert model.shop_root is not None
            window.panels[0].show_node(model.shop_root)
            window.show_actions()
            qt_app.process_events()
            self.assertFalse(window.new_catalog_row.isHidden())

            # Grey until the vendor, edition and PDF are given.
            dialog: NewCatalogDialog = NewCatalogDialog(window, model)
            dialog.vendor.setText("Shars")
            dialog.edition.setText("2026")
            self.assertFalse(dialog.make_button.isEnabled())
            self.assertIn("a PDF", dialog.make_button.toolTip())
            dialog.pdf.setText(str(pdf))
            self.assertTrue(dialog.make_button.isEnabled())

            # Made: linked, the ignore line added (answered "yes" in
            # the panel, #606), shown, read.
            prompt.ANSWERS.append("yes")
            with mock.patch(
                "scraftcam.gui.window.pdf_pages", return_value=456
            ):
                dialog.make_catalog()
            self.assertEqual(prompt.ANSWERS, [])
            edition: Path = top / "catalogs" / "shars" / "2026"
            self.assertTrue((edition / "pages" / "catalog.pdf").is_symlink())
            self.assertIn(
                app.IGNORE_LINES[".git"],
                (top / ".gitignore").read_text(encoding="utf-8"),
            )
            shown: Panel = window.panels[window.current]
            self.assertTrue(shown.editing)
            catalogs: object = shops.read(top)["catalogs"]
            assert isinstance(catalogs, list)
            self.assertEqual(catalogs[0]["pages"], 456)

            # Again: refused, and said so.
            again: NewCatalogDialog = NewCatalogDialog(window, model)
            again.vendor.setText("Shars")
            again.edition.setText("2026")
            again.pdf.setText(str(pdf))
            with mock.patch(
                "scraftcam.gui.window.pdf_pages", return_value=456
            ):
                again.make_catalog()
            self.assertIn("already exists", model.latest().text)
            window.close()


class OpenPagesTest(unittest.TestCase):
    """Tests of [Open Pages] (#68)."""

    def test_index_start(self) -> None:
        """The first index page plus the offset; 0 with no index."""
        self.assertEqual(index_start({}), 0)
        self.assertEqual(index_start({"index_pages": [[451, 455]]}), 451)
        self.assertEqual(
            index_start({"index_pages": [7, [9, 10]], "page_offset": 4}), 11
        )

    @unittest.skipUnless(READY, "pdfplumber or pypdfium2 missing")
    def test_open_pages(self) -> None:
        """Beside [Edit TOML File] for a catalog; one window each."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary) / "shop"
            shutil.copytree(
                SHOP, top, ignore=shutil.ignore_patterns("catalogs")
            )
            pdf: Path = Path(temporary) / "catalog.pdf"
            write_pdf(pdf)
            model: App = App((top / "shop.toml").resolve(), None)
            path: Path = model.new_catalog(
                "Shars", "2026", pdf, link=False, pages=1
            )
            with path.open("a", encoding="utf-8") as file:
                file.write("index_pages = [1]\n")
            model.reload_tree()
            window: Window = Window(model)
            panel: Panel = window.panels[0]
            panel.show_node(window.tree.nodes[str(path)])
            self.assertFalse(panel.pages_button.isHidden())

            # Opened once, at the index, in the panel's [Pages] tab
            # (#600); pressed again, the same one.
            panel.pages_button.click()
            opened: Pages = window_module.CATALOG_WINDOWS[str(path)]
            self.assertEqual(opened.page_no, 0)
            self.assertIs(panel.pages, opened)
            self.assertFalse(opened.isWindow())
            self.assertEqual(panel.tabs.tabText(1), "Pages")
            panel.pages_button.click()
            self.assertEqual(len(window_module.CATALOG_WINDOWS), 1)
            self.assertIs(window_module.CATALOG_WINDOWS[str(path)], opened)

            # The PDF gone: said so, nothing opened.
            window_module.close_catalogs()
            self.assertTrue(opened.closed)
            (path.parent / "pages" / "catalog.pdf").unlink()
            panel.pages_button.click()
            self.assertIn("is missing", model.latest().text)
            self.assertEqual(window_module.CATALOG_WINDOWS, {})

            # Not for another item, which closes the [Pages] tab.
            assert model.shop_root is not None
            panel.show_node(model.shop_root)
            self.assertTrue(panel.pages_button.isHidden())
            self.assertIsNone(panel.pages)
            window.close()


if __name__ == "__main__":
    unittest.main()
