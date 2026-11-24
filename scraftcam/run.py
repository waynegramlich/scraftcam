#!/usr/bin/env python3
"""Start the `scraftcam` GUI (`T.g~6`).

```
python3 -m scraftcam.run [--shop=SHOP] [--design=DESIGN] [--mcp=PORT]
./scraftcam/run.py [--shop=SHOP] [--design=DESIGN] [--mcp=PORT]
```

`SHOP` is a shop's `shop.toml` or its directory; with none, the first
`shop.toml` in the current directory or one of its parents is used
(#83).  `DESIGN` is a Python file, or a package directory.  With
`--headless`, Qt draws offscreen, so no display is needed.  With
`--mcp PORT`, the GUI serves MCP on that port of 127.0.0.1
(`gui/window_exposed.py`; `scraftcam.exposed.client` drives it):

```
python3 -m scraftcam.exposed.client start --gui --port 8765
python3 -m scraftcam.exposed.client call status --port 8765
```

With `--outline FILE`, the first panel edits an outline file, saving
every change; `--record [FILE]` records what is done as steps (and,
unless `--no-speech`, what is said).  With `--pages CATALOG` (a shop's
`catalog.toml`), the first panel opens the catalog's pages in
`catxtract`, in its [Pages] tab.  With `--tutorial FILE`, the
first panel plays a recording
(`NAME.steps.md`, `T.og~6.9` #595) in an outline editor, with its
narration panel; with `--headless` too, every step is checked, the
mismatches printed, and the exit status is 1 if any:

```
cd tests/steps
python3 -m scraftcam.run --headless --tutorial move_a_corner.steps.md
```

With `--program`, the first panel controls the machine (step 5,
`T.g~6` #52, #53): the HMI (`scraftcam.hmi.machine_panel`), a
client of a `serve_linuxcnc` already running (`--lcnc-port`), opens
the program, stopped, and draws the program's setup in the
SolidCraft on `--solidcraft`; `--hmi` makes it with no program.  It
is driven over `--mcp` (`hmi_exposed.py`).  Nothing closes while the
machine runs, or its spindle or coolant is on (#56, #609):

```
python3 -m scraftcam.run --shop examples/shop --program demo.ngc \
    --solidcraft 8080
```

`--show-demo` (`show_demo.py`) brings up LinuxCNC, SolidCraft and
this GUI for the demo, and `--drive-editor` (`drive_editor.py`)
opens an outline for Claude to drive beside a Claude window; the
rest of the command line is theirs (`--show-demo -h`).
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

# Run as a script, Python puts `scraftcam/` on `sys.path`, not the
# directory above it, so that one is added (#103).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraftcam.gui import prompt, window
from scraftcam.gui.app import App, find_shop
from scraftcam.gui.machines import Due, MachineControl, Report
from scraftcam.gui.outline_panel import (
    NEW_OUTLINE,
    RECORDINGS,
    OutlinePanel,
)
from scraftcam.lcnc.lcnc_client import PORT as LINUXCNC_PORT
from scraftcam.shops import SHOP_FILE

# pylint: enable=wrong-import-position


# Function `shop_file()`:
def shop_file(shop: str) -> Path | None:
    """Find the shop's `shop.toml` from `--shop`, or from here (#83).

    Arguments:
    * `shop` (`str`): `--shop`: a file, a directory, or "".

    Returns:
    * (`Path | None`): The `shop.toml`, or None when there is none.
    """
    if not shop:
        return find_shop(Path.cwd())
    path: Path = Path(shop)
    if path.is_dir():
        path = path / SHOP_FILE
    return path.resolve() if path.is_file() else None


# Function `main()`:
def main(arguments: list[str]) -> int:
    """Start the GUI, and run it until its last window closes.

    Arguments:
    * `arguments` (`list[str]`): The command line, less the program.

    Returns:
    * (`int`): 0 when the GUI closed normally.
    """
    # The old programs, now flags of this one (`T.og~6.9` #603): the
    # rest of the command line is theirs.
    if arguments[:1] == ["--show-demo"]:
        # Imported only for its flag, so the GUI starts without it.
        # pylint: disable-next=import-outside-toplevel
        from scraftcam import show_demo

        return show_demo.main(arguments[1:])
    if arguments[:1] == ["--drive-editor"]:
        # Imported only for its flag, so the GUI starts without it.
        # pylint: disable-next=import-outside-toplevel
        from scraftcam import drive_editor

        drive_editor.main(arguments[1:])
        return 0

    # The command line.
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="scraftcam", description="The scraftcam GUI."
    )
    parser.add_argument("--shop", default="", help="shop.toml or its dir")
    parser.add_argument("--design", default="", help="design .py or dir")
    parser.add_argument(
        "--headless", action="store_true", help="draw offscreen"
    )
    parser.add_argument(
        "--mcp", type=int, default=0, help="MCP port (0: none)"
    )
    parser.add_argument(
        "--outline",
        nargs="?",
        const=NEW_OUTLINE,
        type=Path,
        default=None,
        metavar="FILE",
        help="edit an outline file (none: a new outline, kept nowhere)",
    )
    parser.add_argument(
        "--pages",
        type=Path,
        default=None,
        metavar="CATALOG",
        help="open a catalog's pages (its catalog.toml) in catxtract",
    )
    parser.add_argument(
        "--tutorial",
        type=Path,
        default=None,
        help="play a recording (.steps.md); --headless checks it",
    )
    parser.add_argument(
        "--record",
        nargs="?",
        const=RECORDINGS,
        type=Path,
        default=None,
        metavar="FILE",
        help="record what you do as steps, into FILE (by default, a "
        "new file in ~/.scraftcam/recordings/)",
    )
    parser.add_argument(
        "--no-speech",
        action="store_true",
        help="with --record, leave the microphone off",
    )
    parser.add_argument(
        "--show-demo",
        action="store_true",
        help="first: bring up LinuxCNC, SolidCraft and the GUI for the "
        "demo (`--show-demo -h` for its options)",
    )
    parser.add_argument(
        "--drive-editor",
        action="store_true",
        help="first: open an outline for Claude to drive, beside a "
        "Claude window (`--drive-editor -h`)",
    )
    parser.add_argument("--program", default="", help="G-code to run")
    parser.add_argument(
        "--hmi",
        action="store_true",
        help="the machine panel's HMI, opening no program (LinuxCNC "
        "keeps the one it had)",
    )
    parser.add_argument(
        "--solidcraft", type=int, default=0, help="SolidCraft port"
    )
    parser.add_argument(
        "--lcnc-port",
        type=int,
        default=LINUXCNC_PORT,
        help="serve_linuxcnc's port (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="use no LinuxCNC"
    )
    options: argparse.Namespace = parser.parse_args(arguments)
    if options.record is not None and options.tutorial is not None:
        parser.error("--record and --tutorial cannot be used together")
    if options.pages is not None and (
        options.outline or options.tutorial or options.record
    ):
        parser.error("--pages cannot be used with an outline option")
    outline: OutlinePanel = OutlinePanel(
        options.outline,
        options.tutorial,
        options.record,
        not options.no_speech,
        options.headless,
    )

    # The model, and a shop that was named but is not there.
    design: Path | None = Path(options.design) if options.design else None
    model: App = App(shop_file(options.shop), design)
    if options.shop and model.shop is None:
        model.say(f"No {SHOP_FILE} at {options.shop}.", problem=True)
    model.program = options.program or ""
    model.keep_layout = not options.headless

    # Qt, then the first window, until the last one closes.
    return window.run(
        model,
        headless=options.headless,
        mcp_port=options.mcp,
        first_panel=(
            window.CatalogPanel(options.pages)
            if options.pages is not None
            else outline
            if outline.wanted()
            else None
        ),
        makers=window.MachineMakers(
            (
                machine_maker(model, options, program=options.program)
                if options.program or options.hmi
                else None
            ),
            machine_maker(model, options, program=""),
        ),
    )


# Function `machine_maker()`:
def machine_maker(
    model: App, options: argparse.Namespace, *, program: str
) -> Callable[[str], MachineControl | None]:
    """Return what makes a machine's controls, once Qt is up.

    Arguments:
    * `model` (`App`): The GUI's model, for its shop and messages.
    * `options` (`argparse.Namespace`): The command line.
    * `program` (`str`): The G-code to open, or "" for none.

    Returns:
    * (`Callable[[str], MachineControl | None]`): Makes the HMI, for
      the machine named (else the program's), the program open; on
      failure, says why and gives `None`.
    """

    # Function `make()`:
    def make(name: str = "") -> MachineControl | None:
        """Make the HMI for the machine `name`, the program open."""
        # Only now: it needs LinuxCNC's client, which the GUI does not.
        # pylint: disable=import-outside-toplevel
        from scraftcam.hmi import machine_panel
        from scraftcam.hmi.hmi_machine import Intervention

        # pylint: enable=import-outside-toplevel

        if model.shop is None:
            model.say("--program needs a shop", problem=True)
            return None
        if options.headless:
            prompt.use_headless(unattended=True)
        try:
            hmi: machine_panel.HMI = machine_panel.make_hmi(
                lcnc_port=options.lcnc_port,
                solidcraft=options.solidcraft,
                shop=model.shop,
                dry_run=options.dry_run,
            )
        except machine_panel.HMIStartError as error:
            model.say(f"The machine did not start: {error}", problem=True)
            return None
        hmi.quit_button.hide()

        # Reached over MCP (#604): importing registers the functions.
        # pylint: disable-next=import-outside-toplevel
        from scraftcam.hmi import hmi_exposed

        hmi_exposed.HMIS.add(hmi)
        hmi.on_quit = window.close_all

        # Function `due()`:
        def due() -> Due | None:
            """Return when the HMI next needs its operator (#102)."""
            found: Intervention | None = hmi.intervention()
            if found is None:
                return None
            return Due(found.what, found.left, found.span, found.waiting)

        # Function `report()`:
        def report() -> Report:
            """Return the HMI's program, progress and next tools (#154)."""
            if not hmi.lines:
                return Report("", 0.0, "", "")
            total: float = hmi.sums[-1]
            done: float = hmi.sums[min(hmi.at, len(hmi.sums) - 1)]
            progress: str = hmi.progress_line(hmi.at)
            return Report(
                Path(hmi.lines_file).name,
                done / total if total > 0.0 else 0.0,
                progress.split("  ", 1)[1] if "  " in progress else "",
                hmi.plan.text(),
            )

        if program:
            try:
                hmi.open(program)
            except (ValueError, OSError) as error:
                hmi.message.setText(str(error))
        return MachineControl(
            name or hmi.program_machine or "Machine",
            hmi,
            hmi.busy,
            hmi.on_stop,
            due,
            report,
        )

    return make


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
