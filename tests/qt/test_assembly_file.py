"""Tests of `scraftcam.gui.assembly_file`: outlines put together
(`T.sa~6.11` #S6)."""

import shutil
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest import mock

from scraftcam.geometry import RoundedPolygon
from scraftcam.gui import solid_viewer
from scraftcam.gui.assembly_file import (
    Assembly,
    assembly_cacheable,
    assembly_from_text,
    assembly_solid,
    assembly_text,
    keep_out_zones,
    move_outline,
    used_by,
)
from scraftcam.gui.assembly_panel import AssemblyView
from scraftcam.gui.outline_editor import OutlineEditor, ViewTab, drawing_from
from scraftcam.gui.outline_file import OutlineError
from scraftcam.gui.tree import ASSEMBLY, Node, outline_node, shop_children
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

    def test_library(self) -> None:
        """A part may name an outline shipped with `scraftcam`."""
        with tempfile.TemporaryDirectory() as scratch:
            assembly: Assembly = z_setter()
            assembly.parts[
                0
            ].outline = "library:tooling/z_setters/z_setter_block.outline.toml"
            assembly.parts[
                1
            ].outline = (
                "library:tooling/z_setters/z_setter_plunger.outline.toml"
            )
            solid: SolidAssembly = assembly_solid(assembly, "z", Path(scratch))
            self.assertAlmostEqual(solid.parts[1].placement.mm()[2], 44.45)

    def test_vise_slide(self) -> None:
        """The vise's jaws stand on its slot's floor; the moving one
        slides along it as the opening changes (#783d)."""
        vises: Path = EXAMPLE_SHOP / "tooling" / "vises"
        path: Path = vises / "vise.assembly.toml"
        assembly: Assembly = assembly_from_text(path.read_text(), str(path))
        self.assertEqual(assembly_text(assembly), path.read_text())
        solid: SolidAssembly = assembly_solid(assembly, "vise", vises)
        inches: list[list[float]] = [
            [round(value / 25.4, 6) for value in part.placement.mm()]
            for part in solid.parts
        ]
        self.assertEqual(
            inches, [[0, 0, 0], [1.25, 1.375, 1.0], [4.0, 1.375, 1.0]]
        )
        assembly.letters[-1].default = "1 in"
        closer: SolidAssembly = assembly_solid(assembly, "vise", vises)
        self.assertAlmostEqual(closer.parts[2].placement.mm()[0], 3 * 25.4)

    def test_keep_out_zones(self) -> None:
        """The vise's jaws are its keep-outs, placed, each from the
        slot's floor to its top (#783g)."""
        vises: Path = EXAMPLE_SHOP / "tooling" / "vises"
        path: Path = vises / "vise.assembly.toml"
        zones: list[RoundedPolygon] = keep_out_zones(
            assembly_from_text(path.read_text()), vises
        )
        self.assertEqual(
            [zone.name for zone in zones], ["fixed_jaw_jaw", "moving_jaw_jaw"]
        )
        inches: list[float] = [
            round(value / 25.4, 6)
            for value in (*zones[1].box, zones[1].z_start, zones[1].z_end)
        ]
        self.assertEqual(inches, [4.0, 4.75, 1.375, 2.625, 1.0, 2.0])
        self.assertEqual(keep_out_zones(z_setter(), Z_SETTERS), [])

    def test_step_part(self) -> None:
        """A `.step` part is put in as it is, hashed by its contents;
        nothing may stand on it yet (#783f)."""
        with tempfile.TemporaryDirectory() as scratch:
            here: Path = Path(scratch)
            (here / "bought.step").write_text("ISO-10303-21;\n")
            assembly: Assembly = z_setter()
            assembly.parts[0].outline = "bought.step"
            with self.assertRaisesRegex(ValueError, "is a .step"):
                assembly_solid(assembly, "z", here)
            del assembly.parts[1]
            shape: dict[str, object] = cast(
                dict[str, object],
                assembly_cacheable(assembly, "z", here).shape,
            )
            parts: list[dict[str, object]] = cast(
                list[dict[str, object]], shape["parts"]
            )
            self.assertIn("step", parts[0])

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

    def test_file_field(self) -> None:
        """Typing a new place in the editor's File field moves the
        outline, the assembly following; a bad place is refused."""
        with tempfile.TemporaryDirectory() as scratch:
            shop: Path = Path(scratch)
            (shop / "shop.toml").write_text("", encoding="utf-8")
            here: Path = shop / "tooling" / "z_setters"
            shutil.copytree(Z_SETTERS, here)
            plunger: Path = here / "z_setter_plunger.outline.toml"
            editor: OutlineEditor = OutlineEditor(
                drawing_from(plunger), path=plunger
            )
            moved: list[Path] = []
            editor.moved = moved.append
            editor.show_tab(ViewTab.EDIT)
            self.assertTrue(editor.file_field.isVisibleTo(editor))
            self.assertEqual(
                editor.file_field.text(), "tooling/z_setters/z_setter_plunger"
            )
            editor.file_field.setText("no good!")
            editor.file_field.returnPressed.emit()
            self.assertIn("is not a place", editor.view.message)
            editor.file_field.setText("parts/plunger")
            editor.file_field.returnPressed.emit()
            new: Path = shop / "parts" / "plunger.outline.toml"
            self.assertEqual(moved, [new])
            self.assertEqual(editor.path, new)
            self.assertIn(
                "../../parts/plunger.outline.toml",
                (here / "z_setter.assembly.toml").read_text(),
            )
            editor.deleteLater()
            qt_app.process_events()


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

    def test_used_by_link(self) -> None:
        """The plunger's outline says it is used by the Z setter, and
        the link opens the assembly."""
        panel: Panel = Panel(1)
        opened: list[str] = []
        panel.open_path = opened.append
        plunger: Path = Z_SETTERS / "z_setter_plunger.outline.toml"
        panel.show_node(outline_node(plunger), "in")
        editor: OutlineEditor | None = panel.outline
        assert editor is not None
        link: str = editor.users_link.text()
        self.assertIn("Z setter assembly", link)
        editor.follow_user_link(str(Z_SETTER))
        self.assertEqual(opened, [str(Z_SETTER)])
        panel.deleteLater()
        qt_app.process_events()


if __name__ == "__main__":
    unittest.main()
