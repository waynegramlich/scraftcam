"""Tests of `scraftcam.gui.machines`: the `machines/` summary."""

import functools
import shutil
import tempfile
import unittest
from pathlib import Path

from scraftcam.gui import machines, tree
from scraftcam.gui.app import App
from scraftcam.gui.machines import Due, MachineControl
from scraftcam.gui.views import Panel
from scraftcam.gui.window import NewMachineDialog, Window
from tests import qt_app

# The example shop, and its `machines/` directory's item.
SHOP: Path = Path("examples/shop")


# Function `machines_node()`:
def machines_node(shop: Path) -> tree.Node:
    """Return a shop's `machines/` item, as the tree reads it.

    Arguments:
    * `shop` (`Path`): The shop's directory.

    Returns:
    * (`tree.Node`): Its `machines/` item.
    """
    root: tree.Node = tree.shop_tree(shop / "shop.toml")
    found: list[tree.Node] = [
        child for child in root.children if child.path.name == "machines"
    ]
    return found[0]


# Function `control()`:
def control(
    name: str, due: Due | None, busy: list[str] | None = None
) -> MachineControl:
    """Return a machine's controls, with nothing behind them.

    Arguments:
    * `name` (`str`): The machine's name.
    * `due` (`Due | None`): When it next needs its operator.
    * `busy` (`list[str] | None`): Why it is busy, while it holds
      that; not busy when empty or `None`.

    Returns:
    * (`MachineControl`): The controls.
    """
    return MachineControl(
        name,
        Panel(9),
        functools.partial(reason, busy or []),
        nothing,
        nothing,
        functools.partial(answer, due),
    )


# Function `nothing()`:
def nothing(*_arguments: object) -> None:
    """Do nothing: a control's `stop()` and `on_minimal()`."""


# Function `reason()`:
def reason(busy: list[str]) -> str:
    """Return why a machine is busy, while it is.

    Arguments:
    * `busy` (`list[str]`): The reason, or empty.

    Returns:
    * (`str`): The reason, or "".
    """
    return busy[0] if busy else ""


# Function `answer()`:
def answer(due: Due | None) -> Due | None:
    """Return `due`: what a control's `due()` gives.

    Arguments:
    * `due` (`Due | None`): The answer.

    Returns:
    * (`Due | None`): It.
    """
    return due


class MachineItemTest(unittest.TestCase):
    """Tests of `machine_item()` and `is_machines_directory()`."""

    def test_example_shop(self) -> None:
        """The example's mill and router are CNC, with details."""
        node: tree.Node = machines_node(SHOP)
        self.assertTrue(machines.is_machines_directory(node))
        items: dict[str, machines.MachineItem] = {
            item.name: item
            for item in map(machines.machine_item, node.children)
        }
        mill: machines.MachineItem = items["Shop mill"]
        self.assertEqual(mill.kind, "mill")
        self.assertEqual(mill.controller, "LinuxCNC")
        self.assertEqual(mill.details, "R8, 5000 rpm, 4 slot carousel")
        self.assertEqual(items["Shop router"].details, "ER20, 24000 rpm")

    def test_other_and_error(self) -> None:
        """No controller: not CNC, its notes; a bad file: its problem."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary)
            (top / "shop.toml").write_text('name = "Home"\n')
            (top / "machines").mkdir()
            (top / "machines" / "saw.toml").write_text(
                'name = "Band saw"\nmachine = "bandsaw"\n'
                'notes = "Cuts stock.\\nSecond line."\n'
            )
            (top / "machines" / "bad.toml").write_text("name = \n")
            node: tree.Node = machines_node(top)
            items: dict[str, machines.MachineItem] = {
                item.name: item
                for item in map(machines.machine_item, node.children)
            }
            saw: machines.MachineItem = items["Band saw"]
            self.assertEqual(
                (saw.controller, saw.details), ("", "Cuts stock.")
            )
            self.assertTrue(items["bad"].error)
            self.assertFalse(machines.is_machines_directory(node.children[0]))


class FetchListTest(unittest.TestCase):
    """Tests of `fetch_list()`."""

    def test_order(self) -> None:
        """Waiting first, then soonest; the ends and no program left out."""
        controls: list[MachineControl] = [
            control("Mill", Due("T05", 3.0, 5.0, False)),
            control("Router", Due("T01", 0.0, 2.0, True)),
            control("Lathe", Due("end", 1.0, 5.0, False)),
            control("Laser", None),
        ]
        self.assertEqual(
            machines.fetch_list(controls),
            ["T01 for Router, now", "T05 for Mill, in 3:00"],
        )


class SummaryTest(unittest.TestCase):
    """Tests of the guide, `MachinesView`, and opening a machine."""

    def test_summary(self) -> None:
        """The guide first; a machine shown only once it is clicked."""
        model: App = App(SHOP.resolve() / "shop.toml", None)
        model.program = "/somewhere/demo.nc"
        top: Window = Window(model)
        panel: Panel = top.panels[0]
        self.assertFalse(panel.guide.isHidden())
        self.assertIn("NC program: demo.nc", panel.guide.text())
        self.assertIn("[Stop All]", panel.guide.text())

        # A machine connected, not shown; the summary in the panel.
        busy: list[str] = ["The mill is running"]
        mill: MachineControl = control(
            "Shop mill", Due("T05", 0.5, 2.0, False), busy
        )
        top.connect_machine(mill)
        self.assertFalse(panel.machines)
        node: tree.Node | None = top.tree.nodes.get(
            str(SHOP.resolve() / "machines")
        )
        assert node is not None
        panel.show_node(node)
        summary: machines.MachinesView | None = panel.summary
        assert summary is not None
        self.assertTrue(panel.split.isHidden())
        self.assertTrue(panel.guide.isHidden())
        self.assertEqual(
            summary.states["Shop mill"].text(), "mill, LinuxCNC: running"
        )
        self.assertEqual(
            summary.states["Shop router"].text(),
            "router, LinuxCNC: not connected",
        )
        self.assertEqual(summary.bars["Shop mill"].format(), "▲ 0:30")
        self.assertEqual(summary.fetch.text(), "T05 for Shop mill, in 0:30")

        # Opening the mill shows it; again, its panel is made current;
        # the router is not connected, and is said so.
        top.open_machine("Shop mill")
        self.assertEqual(panel.machines, [mill])
        self.assertIsNone(panel.summary)
        top.add_panel()
        top.open_machine("Shop mill")
        self.assertEqual(top.current, 0)
        top.open_machine("Shop router")
        self.assertIn("not connected", model.latest().text)

        # A tree click on the mill's file opens it too; another item
        # goes to a panel with no machine.
        mill_file: str = str(SHOP.resolve() / "machines" / "shop_mill.toml")
        self.assertEqual(
            top.connected_name(top.tree.nodes[mill_file]), "Shop mill"
        )
        router_file: str = str(
            SHOP.resolve() / "machines" / "shop_router.toml"
        )
        self.assertEqual(top.connected_name(top.tree.nodes[router_file]), "")
        self.assertIs(top.free_panel(), top.panels[1])
        busy.clear()
        qt_app.process_events()
        top.close()


class NewMachineTest(unittest.TestCase):
    """Tests of [New Machine] (#141)."""

    def test_new_machine(self) -> None:
        """Grey with no template; made with its own copy; editing on."""
        with tempfile.TemporaryDirectory() as temporary:
            top: Path = Path(temporary) / "shop"
            shutil.copytree(SHOP, top)
            model: App = App((top / "shop.toml").resolve(), None)
            window: Window = Window(model)
            machines_dir: tree.Node = window.tree.nodes[
                str((top / "machines").resolve())
            ]
            window.panels[0].show_node(machines_dir)
            window.show_actions()
            button = window.buttons["New Machine"]
            self.assertFalse(window.new_machine_row.isHidden())
            self.assertTrue(button.isEnabled())

            # Made: its own controller copy, shown with editing on.
            dialog: NewMachineDialog = NewMachineDialog(window, model)
            dialog.name.setText("Big mill")
            dialog.make_machine()
            path: Path = (top / "machines" / "big_mill.toml").resolve()
            text: str = path.read_text(encoding="utf-8")
            self.assertIn('template = "LinuxCNC"', text)
            self.assertIn("[controller]", text)
            self.assertNotIn("travel", text)
            shown: Panel = window.panels[window.current]
            self.assertTrue(shown.editing)
            self.assertFalse(shown.missing.isHidden())
            self.assertIn("Not initialized yet", shown.missing.text())
            self.assertIn("axes[X].travel", shown.missing.text())

            # In the machines list too.
            window.panels[0].show_node(
                window.tree.nodes[str((top / "machines").resolve())]
            )
            summary: machines.MachinesView | None = window.panels[0].summary
            assert summary is not None
            self.assertEqual(
                summary.states["Big mill"].text(),
                "mill, LinuxCNC: not initialized yet",
            )
            assert model.shop_root is not None
            self.assertFalse(
                [n.error for n in model.shop_root.children if n.error]
            )

            # Again: refused, and said so.
            again: NewMachineDialog = NewMachineDialog(window, model)
            again.name.setText("Big mill")
            again.make_machine()
            self.assertIn("already exists", model.latest().text)

            # No template: grey, saying why.
            shutil.rmtree(top / "controllers")
            window.show_actions()
            self.assertFalse(button.isEnabled())
            self.assertIn("controller template", button.toolTip())
            window.close()


if __name__ == "__main__":
    unittest.main()
