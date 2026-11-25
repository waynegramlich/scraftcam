"""Tests of `scraftcam.gui.tree`."""

import tempfile
import unittest
from pathlib import Path

from scraftcam.gui import tree
from scraftcam.shops import EXAMPLE_SHOP


# Function `labels()`:
def labels(node: tree.Node) -> list[object]:
    """Return a tree's labels, nested as the tree is.

    Arguments:
    * `node` (`tree.Node`): The root.

    Returns:
    * (`list[object]`): Its label, then a list per child.
    """
    return [node.label(), *[labels(child) for child in node.children]]


class ShopTreeTest(unittest.TestCase):
    """Tests of `shop_tree()`."""

    def test_shop(self) -> None:
        """Directories first; names from `name`; errors kept, with lines."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            (top / "shop.toml").write_text('name = "Home"\n')
            (top / "machines").mkdir()
            (top / "machines" / "mill.toml").write_text('name = "Mill"\n')
            (top / "a.toml").write_text("x = 1\n")
            (top / "Bad.toml").write_text("x = \n")
            (top / "notes.txt").write_text("not shown\n")
            (top / ".hidden").mkdir()
            root: tree.Node = tree.shop_tree(top / "shop.toml")
            self.assertEqual(
                labels(root),
                [
                    "Home (directory)",
                    ["machines (directory)", ["Mill (file)"]],
                    ["a (file)"],
                    ["Bad.toml (error)"],
                ],
            )
            self.assertIn("syntax error", root.children[2].error)
            self.assertIn("line 1", root.children[2].error)

    def test_catalog_pages(self) -> None:
        """A catalog's `pages/` is not shown; another `pages/` is."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            (top / "shop.toml").write_text('name = "Home"\n')
            edition: Path = top / "catalogs" / "shars" / "2026"
            (edition / "pages").mkdir(parents=True)
            (edition / "catalog.toml").write_text('name = "Shars 2026"\n')
            (top / "catalogs" / "pages").mkdir()
            root: tree.Node = tree.shop_tree(top / "shop.toml")
            self.assertEqual(
                labels(root),
                [
                    "Home (directory)",
                    [
                        "catalogs (directory)",
                        ["pages (directory)"],
                        [
                            "shars (directory)",
                            ["2026 (directory)", ["Shars 2026 (file)"]],
                        ],
                    ],
                ],
            )

    def test_tools(self) -> None:
        """Tools show their function and sizes, sorted by them (#21)."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            (top / "shop.toml").write_text('name = "Home"\n')
            tools: Path = top / "tools"
            tools.mkdir()
            for name, text in (
                ("a.toml", 'D = "1/2 in"\nend = "ball"\n'),
                ("b.toml", 'D = "1/8 in"\nend = "ball"\n'),
                ("c.toml", 'D = "1/4 in"\nend = "square"\n'),
            ):
                (tools / name).write_text(
                    f'kind = "end_mill"\n{text}flutes = 2\nmaterial = "HSS"\n'
                )
            root: tree.Node = tree.shop_tree(top / "shop.toml")
            self.assertEqual(
                labels(root.children[0])[1:],
                [
                    ["Ball end mill (1/8in 2-flute HSS)"],
                    ["Ball end mill (1/2in 2-flute HSS)"],
                    ["End mill (1/4in 2-flute HSS)"],
                ],
            )

    def test_about(self) -> None:
        """Directories and items say what they are, for tooltips (#80)."""
        shop: Path = EXAMPLE_SHOP
        root: tree.Node = tree.shop_tree(shop / "shop.toml")
        about: dict[str, str] = {
            child.name: child.about for child in root.children
        }
        self.assertIn("The tools on hand", about["tools"])
        self.assertIn("controller", about["controllers"])
        self.assertNotIn("`", about["tools"])
        grid: tree.Node = next(
            child for child in root.children if child.name == "tooling"
        ).children[0]
        self.assertIn("A grid plate", grid.about)
        self.assertIn("Aluminum", grid.about)


class OutlineItemTest(unittest.TestCase):
    """A kind's outline file is an item, first in its directory."""

    def test_outline_items(self) -> None:
        """Listed first, by its kind; `.svg` hidden (#615, #731, #732)."""
        drills: list[tree.Node] = tree.shop_children(
            EXAMPLE_SHOP / "tools" / "drills"
        )
        self.assertEqual(
            [node.label() for node in drills],
            [
                "Drill outline",
                "Drill (1/8in cobalt)",
                "Drill (15/64in HSS)",
            ],
        )
        self.assertEqual(drills[0].kind, tree.OUTLINE)
        self.assertEqual(tree.edit_path(drills[0]), drills[0].path)
        self.assertEqual(
            tree.shop_relative(drills[0].path),
            "tools/drills/drill.outline.toml",
        )


class DesignTreeTest(unittest.TestCase):
    """Tests of `design_tree()` and `docstring()`."""

    def test_design(self) -> None:
        """`main()` makes a design; packages; syntax errors; docstrings."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            design: Path = top / "plate.py"
            design.write_text(
                '"""A plate."""\n\ndef main() -> int:\n    return 0\n'
            )
            (top / "helpers.py").write_text("X = 1\n")
            (top / "broken.py").write_text("def (\n")
            (top / "parts").mkdir()
            (top / "parts" / "__init__.py").write_text('"""Parts."""\n')
            (top / "empty").mkdir()
            (top / "__pycache__").mkdir()
            (top / "__pycache__" / "x.py").write_text("")
            root: tree.Node
            clipped: bool
            root, clipped = tree.design_tree(design)
            self.assertFalse(clipped)
            self.assertEqual(
                labels(root),
                [
                    "plate (design)",
                    ["parts (package)", ["__init__ (python)"]],
                    ["broken (error)"],
                    ["helpers (python)"],
                ],
            )
            self.assertEqual(
                root.children[1].error[:23], "syntax error at line 1:"
            )
            self.assertEqual(tree.docstring(design), "A plate.")
            self.assertEqual(tree.docstring(top / "parts"), "Parts.")
            self.assertEqual(
                tree.docstring(top / "helpers.py"), "(no docstring)"
            )

            # A package as the design: what is in it.
            package: tree.Node = tree.design_tree(top / "parts")[0]
            self.assertEqual(
                labels(package), ["parts (package)", ["__init__ (python)"]]
            )

    def test_limit(self) -> None:
        """At most `limit` items, and it says so (#126)."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            index: int
            for index in range(10):
                (top / f"m{index}.py").write_text("")
            root: tree.Node
            clipped: bool
            root, clipped = tree.design_tree(top / "m0.py", limit=5)
            self.assertTrue(clipped)
            self.assertEqual(len(root.children), 5)
            root, clipped = tree.design_tree(top / "m0.py", limit=9)
            self.assertFalse(clipped)


if __name__ == "__main__":
    unittest.main()
