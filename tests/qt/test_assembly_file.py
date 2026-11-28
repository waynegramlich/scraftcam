"""Tests of `scraftcam.gui.assembly_file`: outlines put together
(`T.sa~6.11` #S6)."""

import shutil
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest import mock

from scraftcam.gui import solid_viewer
from scraftcam.gui.assembly_file import (
    Assembly,
    assembly_cacheable,
    assembly_from_text,
    assembly_solid,
    assembly_text,
    move_outline,
    used_by,
)
from scraftcam.gui.assembly_panel import AssemblyView
from scraftcam.gui.outline_file import OutlineError
from scraftcam.gui.tree import ASSEMBLY, Node, shop_children
from scraftcam.gui.views import Panel
from scraftcam.model_cache import Cacheable
from scraftcam.shops import EXAMPLE_SHOP
from scraftcam.solid import SolidAssembly
from tests import qt_app

# The shipped Z setter: a block and a plunger standing on it.
Z_SETTERS: Path = EXAMPLE_SHOP / "tooling" / "z_setters"
Z_SETTER: Path = Z_SETTERS / "z_setter.assembly.toml"


# Function `z_setter()`:
def z_setter() -> Assembly:
    """Return the shipped Z setter's assembly."""
    return assembly_from_text(Z_SETTER.read_text(), str(Z_SETTER))


# Class `AssemblyTest`:
class AssemblyTest(unittest.TestCase):
    """Reading assemblies and placing their parts."""

    def test_read(self) -> None:
        """Its letters and parts, the plunger standing on the block."""
        assembly: Assembly = z_setter()
        self.assertEqual(
            [letter.letter for letter in assembly.letters],
            ["H", "W", "PD", "PR"],
        )
        self.assertEqual(
            [(part.name, part.on, part.at) for part in assembly.parts],
            [("block", "", ""), ("plunger", "block", "V5")],
        )
        self.assertEqual(assembly.parts[0].letters["BH"], "H - PR")

    def test_round_trip(self) -> None:
        """The Z setter is written back exactly as it is read."""
        self.assertEqual(assembly_text(z_setter()), Z_SETTER.read_text())

    def test_refused(self) -> None:
        """A part on no earlier part, or on one with no vertex, is
        named."""
        text: str = Z_SETTER.read_text()
        with self.assertRaisesRegex(OutlineError, "not an earlier part"):
            assembly_from_text(text.replace('on = "block"', 'on = "x"'))
        with self.assertRaisesRegex(OutlineError, "needs at"):
            assembly_from_text(text.replace('at = "V5"\n', ""))

    def test_placed(self) -> None:
        """The plunger stands on the block's top, 1-3/4 in up; changing
        the assembly's height moves it."""
        solid: SolidAssembly = assembly_solid(z_setter(), "z", Z_SETTERS)
        self.assertEqual(
            [part.solid.name for part in solid.parts], ["z_block", "z_plunger"]
        )
        self.assertAlmostEqual(solid.parts[1].placement.mm()[2], 44.45)
        assembly: Assembly = z_setter()
        assembly.letters[0].default = "3 in"
        moved: SolidAssembly = assembly_solid(assembly, "z", Z_SETTERS)
        self.assertAlmostEqual(moved.parts[1].placement.mm()[2], 69.85)

    def test_bad_mate(self) -> None:
        """A vertex or face its parent does not have is named."""
        assembly: Assembly = z_setter()
        assembly.parts[1].at = "V9"
        with self.assertRaisesRegex(ValueError, "no such vertex"):
            assembly_solid(assembly, "z", Z_SETTERS)
        assembly = z_setter()
        assembly.parts[1].face = "top"
        with self.assertRaisesRegex(ValueError, "no such shape"):
            assembly_solid(assembly, "z", Z_SETTERS)

    def test_cacheable(self) -> None:
        """Its model is hashed on where each part is placed."""
        shape: dict[str, object] = cast(
            dict[str, object],
            assembly_cacheable(z_setter(), "z", Z_SETTERS).shape,
        )
        self.assertEqual(shape["kind"], "assembly")
        parts: list[dict[str, object]] = cast(
            list[dict[str, object]], shape["parts"]
        )
        self.assertAlmostEqual(cast(list[float], parts[1]["at"])[2], 44.45)


# Class `MoveTest`:
class MoveTest(unittest.TestCase):
    """ "Used by", and moving an outline (#783h)."""

    def test_used_by_and_move(self) -> None:
        """The plunger is used by the Z setter; moved, the assembly
        names it where it went, and still builds."""
        with tempfile.TemporaryDirectory() as scratch:
            shop: Path = Path(scratch)
            here: Path = shop / "tooling" / "z_setters"
            shutil.copytree(Z_SETTERS, here)
            plunger: Path = here / "z_setter_plunger.outline.toml"
            assembly: Path = here / "z_setter.assembly.toml"
            self.assertEqual(used_by(plunger, shop), [assembly])
            moved: Path = shop / "parts" / "plunger.outline.toml"
            self.assertEqual(move_outline(plunger, moved, shop), [assembly])
            self.assertTrue(moved.with_suffix(".svg").exists())
            self.assertIn(
                'outline = "../../parts/plunger.outline.toml"',
                assembly.read_text(),
            )
            self.assertEqual(used_by(moved, shop), [assembly])
            assembly_solid(assembly_from_text(assembly.read_text()), "z", here)
            with self.assertRaises(FileExistsError):
                move_outline(moved, assembly, shop)


# Class `PanelTest`:
class PanelTest(unittest.TestCase):
    """An assembly in the shop's tree and its panel."""

    def test_tree_and_panel(self) -> None:
        """The tree shows "Z setter assembly" first in its directory;
        its panel's [Assembly] tab lists the parts, and [Solid] shows
        the assembly (SolidCraft stood in for)."""
        nodes: list[Node] = shop_children(Z_SETTERS)
        self.assertEqual(nodes[0].kind, ASSEMBLY)
        self.assertEqual(nodes[0].label(), "Z setter assembly")
        panel: Panel = Panel(1)
        panel.show_node(nodes[0], "in")
        view: object = panel.summary
        assert isinstance(view, AssemblyView)
        self.assertEqual(panel.tabs.tabText(0), "Assembly")
        self.assertEqual(view.table.rowCount(), 2)
        shown: list[Cacheable] = []

        # Function `show()`:
        def show(_viewer: solid_viewer.SolidViewer, model: Cacheable) -> None:
            """Keep what would be shown, with no SolidCraft."""
            shown.append(model)

        with mock.patch.object(
            solid_viewer.SolidViewer, "show", autospec=True, side_effect=show
        ):
            view.solid_button.click()
        self.assertEqual([model.name for model in shown], ["z_setter"])
        self.assertEqual(view.message.text(), "")
        panel.deleteLater()
        qt_app.process_events()


if __name__ == "__main__":
    unittest.main()
