"""The GUI's model: everything its windows show, with no Qt in it.

Every window of the GUI draws from one `App`, and redraws when it
changes, so two windows showing the same thing always agree
(`T.g~6` #3).  Keeping Qt out of it lets the tests run with
no display.  It holds:

* The shop: the one shown last (`~/.scraftcam/settings.toml`), else
  the example shop, or one opened with `open_shop()` (`T.toasl~6.8`
  #704, #705), and the shop's name (#100).
* The design: a Python file, or a package directory, and its name.
* The machines running, which decide when [Stop All] shows (#2) and
  when a window may not close (#67).
* The messages, the latest one shown on the top line (#95).
* The tree of the shop's and the design's files (`tree.py`), read
  again by `reload_tree()` whenever they change.

With no shop, a new one can be made from a few answers (#97, #98,
#104): its name, its units, and the kinds of machines it has, which
`new_shop_text()` writes with the shop writer (`shop_writer.py`).
"""

import json
import re
import shutil
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..settings import Settings, read_settings, write_settings
from ..shop_writer import item_text
from ..shops import (
    ALLOW_EDITS,
    CATALOG,
    CATALOG_PAGES,
    FORMAT_VERSION,
    SHOP_FILE,
    is_read_only,
)
from .tree import DESIGN_LIMIT, Node, design_tree, shop_tree

# Why a shop in the package is not changed (#683, #717).
READ_ONLY: str = (
    "the example shop is read only: [Copy Shop] makes one of your own"
)

# A copied shop's name, which is its directory's too (#710).
COPY_NAME: re.Pattern[str] = re.compile(r"[A-Za-z0-9_.-]+")

# What the top line shows for a shop or a design that is missing.
NONE_NAME: str = "(none)"

# A shop's controller templates (#141).
CONTROLLERS: str = "controllers"

# The kinds of machine [New Machine] makes (#141), and each one's axes;
# the rest is left out, "not initialized yet" (#145).
NEW_MACHINE_KINDS: tuple[str, ...] = ("mill", "router")
NEW_AXES: dict[str, tuple[str, ...]] = {
    "mill": ("X", "Y", "Z"),
    "router": ("X", "Y", "Z"),
}
MACHINES: str = "machines"
CATALOGS: str = "catalogs"

# The version control systems the GUI suggests (#99), and the
# directory each keeps at the top of a repository.
VERSION_CONTROLS: tuple[tuple[str, str], ...] = (
    ("git", ".git"),
    ("hg", ".hg"),
)

# A catalog's `pages/` is never under version control (`T.c~6.3`
# #50, #58): the line that keeps it out, per ignore file, for any
# catalog wherever the shop is in the repository.
IGNORE_LINES: dict[str, str] = {
    ".git": "**/catalogs/*/*/pages/",
    ".hg": "re:(^|/)catalogs/[^/]+/[^/]+/pages/",
}
IGNORE_FILES: dict[str, str] = {".git": ".gitignore", ".hg": ".hgignore"}


# Class `Message`:
@dataclass(frozen=True, slots=True)
class Message:
    """One message for the top line.

    Attributes:
    * `text` (`str`): What it says, one line.
    * `problem` (`bool`): True for a problem (shown in red).

    Constructor:
    * `Message(text, problem)`
    """

    # Constructor arguments:
    text: str = field(init=True)
    problem: bool = field(init=True)


# Function `shop_name()`:
def shop_name(shop: Path) -> str:
    """Return a shop's name: its `name`, or its directory's name.

    Arguments:
    * `shop` (`Path`): The shop's `shop.toml`.

    Returns:
    * (`str`): The name to show.

    Raises:
    * `OSError`: If the file can not be read.
    * `tomllib.TOMLDecodeError`: If it does not read as TOML.
    """
    with shop.open("rb") as file:
        table: dict[str, object] = tomllib.load(file)
    name: object = table.get("name", "")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return shop.resolve().parent.name


# Function `design_name()`:
def design_name(design: Path) -> str:
    """Return a design's name: its file's, less `.py`, or its package's.

    Arguments:
    * `design` (`Path`): A Python file, or a package directory.

    Returns:
    * (`str`): The name to show.
    """
    if design.is_dir():
        return design.resolve().name
    return design.stem


# Function `in_repository()`:
def in_repository(directory: Path) -> bool:
    """Tell whether a directory is inside a `git` or `hg` repository.

    Arguments:
    * `directory` (`Path`): The directory.

    Returns:
    * (`bool`): True when it, or a parent, holds `.git` or `.hg`.
    """
    top: Path
    for top in (directory.resolve(), *directory.resolve().parents):
        marker: str
        for _command, marker in VERSION_CONTROLS:
            if (top / marker).exists():
                return True
    return False


# Function `version_control_hint()`:
def version_control_hint(directory: Path) -> str:
    """Suggest version control for a shop, when it has none (#107).

    Arguments:
    * `directory` (`Path`): The shop's directory.

    Returns:
    * (`str`): One line suggesting `git` or `hg`, or "" when the shop
      is already in a repository.
    """
    # Already in a repository: nothing to say.
    if in_repository(directory):
        return ""

    # Not installed at all, or installed and not used yet.
    installed: list[str] = [
        command
        for command, _marker in VERSION_CONTROLS
        if shutil.which(command)
    ]
    if not installed:
        return (
            "No version control is installed; "
            "install git or hg to keep the shop's history."
        )
    return (
        f"The shop is not under version control; "
        f"e.g. `{installed[0]} init` in {directory}."
    )


# Function `ignores_needed()`:
def ignores_needed(directory: Path) -> list[tuple[Path, str]]:
    """Return the ignore lines a shop's catalogs still need (#51).

    Arguments:
    * `directory` (`Path`): The shop's directory.

    Returns:
    * (`list[tuple[Path, str]]`): Each ignore file of the nearest
      repository (`.gitignore`, `.hgignore`) that lacks its line,
      with the line; `[]` outside a repository.
    """
    top: Path
    for top in (directory.resolve(), *directory.resolve().parents):
        found: list[str] = [
            marker for marker in IGNORE_LINES if (top / marker).exists()
        ]
        if found:
            needed: list[tuple[Path, str]] = []
            marker: str
            for marker in found:
                path: Path = top / IGNORE_FILES[marker]
                text: str = (
                    path.read_text(encoding="utf-8") if path.exists() else ""
                )
                if IGNORE_LINES[marker] not in text.splitlines():
                    needed.append((path, IGNORE_LINES[marker]))
            return needed
    return []


# Function `add_ignores()`:
def add_ignores(needed: list[tuple[Path, str]]) -> None:
    """Add ignore lines at the end of their files (#51).

    Arguments:
    * `needed` (`list[tuple[Path, str]]`): From `ignores_needed()`.

    Raises:
    * `OSError`: If a file can not be written.
    """
    path: Path
    line: str
    for path, line in needed:
        text: str = path.read_text(encoding="utf-8") if path.exists() else ""
        if text and not text.endswith("\n"):
            text += "\n"
        text += f"# Catalog PDFs and their pages (scraftcam).\n{line}\n"
        path.write_text(text, encoding="utf-8")


# Function `pdf_pages()`:
def pdf_pages(pdf: Path) -> int:
    """Return how many pages a PDF has.

    Arguments:
    * `pdf` (`Path`): The PDF.

    Returns:
    * (`int`): Its page count.

    Raises:
    * `ValueError`: If it can not be read as a PDF.
    """
    # Imported here: it fetches the PDF packages on first use.
    from ..catalog.pdf import Document  # pylint: disable=import-outside-toplevel

    # The PDF libraries raise their own errors, of no common class.
    try:
        return len(Document(pdf))
    except Exception as error:
        raise ValueError(f"{pdf} can not be read as a PDF: {error}") from error


# Function `new_catalog_text()`:
def new_catalog_text(vendor: str, edition: str, pdf: str, pages: int) -> str:
    """Write a new catalog's `catalog.toml` (`T.c~6.3` #61).

    Arguments:
    * `vendor` (`str`): Who publishes it (not empty).
    * `edition` (`str`): Which edition (not empty).
    * `pdf` (`str`): The PDF's file name, in `pages/`.
    * `pages` (`int`): How many pages it has.

    Returns:
    * (`str`): The file's text.

    Raises:
    * `ValueError`: If the vendor or edition is empty.
    """
    vendor = " ".join(vendor.split())
    edition = " ".join(edition.split())
    if not vendor or not edition:
        raise ValueError("the catalog needs a vendor and an edition")
    return item_text(
        {
            "name": f"{vendor} {edition}",
            "kind": "catalog",
            "language": "English",
            "version": FORMAT_VERSION,
            "vendor": vendor,
            "edition": edition,
            "pdf": pdf,
            "pages": pages,
        }
    )


# Function `copy_problem()`:
def copy_problem(directory: str, name: str) -> str:
    """Say what is wrong with where [Copy Shop] would put a copy (#710).

    The copy goes in `directory/name`, which must be empty or not
    there yet, and makeable.

    Arguments:
    * `directory` (`str`): The directory that holds shops (`~` is
      the home directory).
    * `name` (`str`): The copy's name, also its directory's.

    Returns:
    * (`str`): The problem, or "" when there is none.
    """
    # The name: one directory's name; then a directory.
    if not name.strip():
        return "the copy needs a name"
    if not COPY_NAME.fullmatch(name) or not directory.strip():
        return (
            "the copy needs a directory"
            if COPY_NAME.fullmatch(name)
            else "a name of letters, digits, `_`, `-` and `.`"
        )

    # The place: empty or not there, and under something makeable.
    target: Path = Path(directory).expanduser() / name
    if target.is_file():
        return f"{target} is a file"
    if target.is_dir() and any(target.iterdir()):
        return f"{target} is not empty"
    above: Path = target
    while not above.exists():
        above = above.parent
    if not above.is_dir():
        return f"{above} is not a directory"
    return ""


# Function `controller_templates()`:
def controller_templates(shop: Path) -> dict[str, Path]:
    """Return a shop's controller templates (#141).

    Arguments:
    * `shop` (`Path`): Its `shop.toml`.

    Returns:
    * (`dict[str, Path]`): Each template's file, by its name; a file
      that does not read, or is not a controller, is left out.
    """
    templates: dict[str, Path] = {}
    path: Path
    for path in sorted((shop.parent / CONTROLLERS).glob("*.toml")):
        try:
            with path.open("rb") as file:
                item: dict[str, object] = tomllib.load(file)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if item.get("kind") == "controller" and "name" in item:
            templates[str(item["name"])] = path
    return templates


# Function `file_name()`:
def file_name(name: str) -> str:
    """Return the file an item of a name is kept in.

    Arguments:
    * `name` (`str`): E.g. "Shop lathe".

    Returns:
    * (`str`): E.g. `shop_lathe.toml`.
    """
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + ".toml"


# Function `new_machine_text()`:
def new_machine_text(name: str, kind: str, template: dict[str, object]) -> str:
    """Write a new machine's file, with its own copy of a controller.

    Only what is known: its kind, its axes' letters, and a copy of the
    controller template, naming it (`template`, #141); the rest is left
    out, "not initialized yet" (#145).

    Arguments:
    * `name` (`str`): The machine's name (not empty).
    * `kind` (`str`): One of `NEW_MACHINE_KINDS`.
    * `template` (`dict[str, object]`): The controller template, as
      read.

    Returns:
    * (`str`): The file's text.

    Raises:
    * `ValueError`: If the name is empty or the kind unknown.
    """
    # The answers.
    if not name.strip():
        raise ValueError("the machine needs a name")
    if kind not in NEW_MACHINE_KINDS:
        raise ValueError(
            f"a new machine is one of {', '.join(NEW_MACHINE_KINDS)}"
        )

    # The machine's own controller: the template's, less its header.
    controller: dict[str, object] = {
        key: value
        for key, value in template.items()
        if key not in ("kind", "language", "version", "template")
    }
    controller["template"] = template.get("name", "")
    return item_text(
        {
            "name": " ".join(name.split()),
            "kind": "machine",
            "language": "English",
            "version": FORMAT_VERSION,
            "machine": kind,
            "axes": [{"letter": letter} for letter in NEW_AXES[kind]],
            "controller": controller,
        }
    )


# Class `App`:
# The model holds everything every window shows.
@dataclass(slots=True)
class App:  # pylint: disable=too-many-instance-attributes
    """Everything the GUI's windows show, shared by all of them.

    Each window calls `listen()` once, and redraws from the `App`
    whenever its function is called.

    Attributes:
    * `shop` (`Path | None`): The shop's `shop.toml`, if any.
    * `design` (`Path | None`): The design, if any.
    * `listeners` (`list[Callable[[], None]]`): The functions called
      on each change.
    * `created` (`set[str]`): The paths of the items made this
      session, which open with editing enabled (#140).
    * `messages` (`list[Message]`): Every message, oldest first.
    * `program` (`str`): The NC program run (`--program`), or "".
    * `running` (`set[str]`): The names of the machines running.
    * `settings` (`Path | None`): The settings file that
      `open_shop()` remembers the shop in (#704); `None` (a test's)
      remembers nothing.
    * `shop_title` (`str`): The shop's name, or `NONE_NAME`.
    * `editor_hinted` (`bool`): True once the hint about `VISUAL` and
      `EDITOR` has been given (once a session, #124).
    * `keep_layout` (`bool`): True to save the windows' layout in
      `~/.scraftcam/layouts/` (#186, #187); a GUI run's, never a
      test's or the headless show's.
    * `design_root` (`Node | None`): The design's tree, if any.
    * `shop_root` (`Node | None`): The shop's tree, if any.
    * `tree_version` (`int`): Counts the times the trees were read,
      so windows rebuild their trees only when it changes.

    Constructor:
    * `App(shop, design)`
    """

    # Constructor arguments:
    shop: Path | None = field(init=True)
    design: Path | None = field(init=True)

    # Remaining attributes (alphabetized):
    created: set[str] = field(init=False, default_factory=set)
    editor_hinted: bool = field(init=False, default=False)
    keep_layout: bool = field(init=False, default=False)
    listeners: list[Callable[[], None]] = field(
        init=False, default_factory=list
    )
    messages: list[Message] = field(init=False, default_factory=list)
    program: str = field(init=False, default="")
    running: set[str] = field(init=False, default_factory=set)
    settings: Path | None = field(init=False, default=None)
    shop_title: str = field(init=False, default=NONE_NAME)

    # The trees (alphabetized):
    design_root: Node | None = field(init=False, default=None)
    shop_root: Node | None = field(init=False, default=None)
    tree_version: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        """Read the shop's name and the trees; say what is missing."""
        # Absolute paths, so the tree's items are found by them.
        if self.design is not None:
            self.design = self.design.resolve()
        if self.shop is None:
            self.reload_tree()
            self.say(f"No {SHOP_FILE} found here or above.", problem=True)
        else:
            self.use_shop(self.shop)

    def use_shop(self, shop: Path, done: str = "") -> None:
        """Show a shop: its name, or the problem reading it.

        Arguments:
        * `shop` (`Path`): Its `shop.toml`.
        * `done` (`str`): What was done, to say before the version
          control hint (e.g. "Created ...").
        """
        self.shop = shop.resolve()
        self.reload_tree()
        try:
            self.shop_title = shop_name(shop)
        except (OSError, tomllib.TOMLDecodeError) as error:
            self.shop_title = NONE_NAME
            self.say(f"{shop}: {error}", problem=True)
            return
        text: str = " ".join(
            part for part in (done, version_control_hint(shop.parent)) if part
        )
        if text:
            self.say(text)
        else:
            self.changed()

    def open_shop(self, shop: Path, *, remember: bool = True) -> Path:
        """Show another shop, and remember it as the last (#704).

        Arguments:
        * `shop` (`Path`): Its directory or its `shop.toml`.
        * `remember` (`bool`): False to leave the settings alone (a
          test's or the demo's, #718).

        Returns:
        * (`Path`): Its `shop.toml`.

        Raises:
        * `ValueError`: If it has no `shop.toml`.
        * `SettingsError`: If the settings file can not be read.
        * `OSError`: If the settings file can not be written.
        """
        # The shop's file.
        file: Path = shop / SHOP_FILE if shop.is_dir() else shop
        if file.name != SHOP_FILE or not file.is_file():
            raise ValueError(f"no {SHOP_FILE} at {shop}")
        self.use_shop(file)

        # Remembered for the next start, unless it is a test's model.
        if remember and self.settings is not None:
            old: Settings = read_settings(self.settings)
            write_settings(
                Settings(old.shop_directories, file.parent.resolve()),
                self.settings,
            )
        return file.resolve()

    def copy_shop(self, directory: Path, name: str) -> Path:
        """Copy the shop shown to `directory/name`, and show the copy.

        [Copy Shop] (#709, #710): the copy leaves `.allow_edits` out
        (#717), takes `name` as its name, adds `directory` to the
        settings' shop directories, and is remembered as the last.

        Arguments:
        * `directory` (`Path`): A directory that holds shops.
        * `name` (`str`): The copy's name, also its directory's.

        Returns:
        * (`Path`): The copy's `shop.toml`.

        Raises:
        * `ValueError`: With no shop, or a problem (`copy_problem()`).
        * `SettingsError`: If the settings file can not be read.
        * `OSError`: If it can not be written.
        """
        if self.shop is None:
            raise ValueError("there is no shop to copy")
        problem: str = copy_problem(str(directory), name)
        if problem:
            raise ValueError(problem)

        # The copy, named (its first `name =` line), never unlocked.
        holder: Path = directory.expanduser().resolve()
        target: Path = holder / name
        if target.is_dir():
            target.rmdir()  # Empty: `copy_problem()` said so.
        shutil.copytree(
            self.shop.parent,
            target,
            ignore=shutil.ignore_patterns(ALLOW_EDITS),
        )
        file: Path = target / SHOP_FILE
        text: str = file.read_text(encoding="utf-8")
        file.write_text(
            re.sub(
                r"^name = .*$",
                f"name = {json.dumps(name)}",
                text,
                count=1,
                flags=re.MULTILINE,
            ),
            encoding="utf-8",
        )

        # Its directory among the shop directories, then shown.
        if self.settings is not None:
            old: Settings = read_settings(self.settings)
            if holder not in old.shop_directories:
                write_settings(
                    Settings((*old.shop_directories, holder), old.last_shop),
                    self.settings,
                )
        self.open_shop(file)
        self.say(
            " ".join(
                part
                for part in (
                    f"Copied to {target}.",
                    version_control_hint(target),
                )
                if part
            )
        )
        return file

    def reload_tree(self) -> None:
        """Read the shop's and the design's trees again."""
        # The shop's.
        self.shop_root = None if self.shop is None else shop_tree(self.shop)

        # The design's, or why there is none.
        self.design_root = None
        if self.design is not None and not self.design.exists():
            self.say(f"No design at {self.design}.", problem=True)
        elif self.design is not None:
            clipped: bool
            self.design_root, clipped = design_tree(self.design)
            if clipped:
                self.say(
                    f"The design's directory has more than {DESIGN_LIMIT} "
                    "Python files; only the first are shown.  Give the "
                    "design a directory of its own."
                )
        self.tree_version += 1
        self.changed()

    def new_machine(self, name: str, kind: str, template: str) -> Path:
        """Make a new machine from a controller template, and show it.

        Arguments:
        * `name` (`str`): The machine's name.
        * `kind` (`str`): One of `NEW_MACHINE_KINDS`.
        * `template` (`str`): The controller template's name.

        Returns:
        * (`Path`): The new machine's file.

        Raises:
        * `ValueError`: With no shop, a read only one, no such
          template, an answer not allowed, or a machine there already.
        * `OSError`: If it can not be written.
        """
        if self.shop is None:
            raise ValueError("there is no shop")
        if is_read_only(self.shop):
            raise ValueError(READ_ONLY)
        templates: dict[str, Path] = controller_templates(self.shop)
        if template not in templates:
            raise ValueError(f'no controller template "{template}"')
        with templates[template].open("rb") as file:
            copied: dict[str, object] = tomllib.load(file)
        text: str = new_machine_text(name, kind, copied)
        directory: Path = self.shop.parent / MACHINES
        path: Path = directory / file_name(name)
        if path.exists():
            raise ValueError(f"{path} already exists")
        directory.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.created.add(str(path.resolve()))
        self.reload_tree()
        self.say(f"Created {path}.")
        return path.resolve()

    def new_catalog(
        self, vendor: str, edition: str, pdf: Path, *, link: bool, pages: int
    ) -> Path:
        """Make a new catalog, its PDF copied or linked into `pages/`.

        Arguments:
        * `vendor` (`str`): Who publishes it.
        * `edition` (`str`): Which edition.
        * `pdf` (`Path`): The catalog's PDF.
        * `link` (`bool`): True to link to the PDF, False to copy it.
        * `pages` (`int`): How many pages it has (`pdf_pages()`).

        Returns:
        * (`Path`): The new `catalog.toml`.

        Raises:
        * `ValueError`: With no shop, a read only one, an empty
          answer, no such PDF, or a catalog there already.
        * `OSError`: If it can not be written.
        """
        if self.shop is None:
            raise ValueError("there is no shop")
        if is_read_only(self.shop):
            raise ValueError(READ_ONLY)
        if not pdf.is_file():
            raise ValueError(f"{pdf} is not a file")
        text: str = new_catalog_text(vendor, edition, pdf.name, pages)
        directory: Path = (
            self.shop.parent
            / CATALOGS
            / Path(file_name(vendor)).stem
            / Path(file_name(edition)).stem
        )
        path: Path = directory / CATALOG
        if path.exists():
            raise ValueError(f"{path} already exists")
        (directory / CATALOG_PAGES).mkdir(parents=True, exist_ok=True)
        placed: Path = directory / CATALOG_PAGES / pdf.name
        if link:
            placed.symlink_to(pdf.resolve())
        else:
            shutil.copyfile(pdf, placed)
        path.write_text(text, encoding="utf-8")
        self.created.add(str(path.resolve()))
        self.reload_tree()
        self.say(f"Created {path}.")
        return path.resolve()

    def listen(self, function: Callable[[], None]) -> None:
        """Call `function` after every change from now on.

        Arguments:
        * `function` (`Callable[[], None]`): Typically a window's
          redraw.
        """
        self.listeners.append(function)

    def forget(self, function: Callable[[], None]) -> None:
        """Stop calling `function` (its window has closed).

        Arguments:
        * `function` (`Callable[[], None]`): A function given to
          `listen()`.
        """
        if function in self.listeners:
            self.listeners.remove(function)

    def changed(self) -> None:
        """Tell every listener that something changed."""
        function: Callable[[], None]
        for function in list(self.listeners):
            function()

    def say(self, text: str, *, problem: bool = False) -> None:
        """Add a message for the top line.

        Arguments:
        * `text` (`str`): The message; white space runs become one
          space, so it fits on one line.
        * `problem` (`bool`): True for a problem (shown in red).
        """
        self.messages.append(Message(" ".join(text.split()), problem))
        self.changed()

    def latest(self) -> Message:
        """Return the latest message.

        Returns:
        * (`Message`): The latest message, or an empty one.
        """
        return self.messages[-1] if self.messages else Message("", False)

    def design_title(self) -> str:
        """Return the design's name for the top line.

        Returns:
        * (`str`): The design's name, or `NONE_NAME`.
        """
        return NONE_NAME if self.design is None else design_name(self.design)

    def title(self) -> str:
        """Return the window's title (#109).

        Returns:
        * (`str`): "scraftcam: SHOP (DESIGN)".
        """
        return f"scraftcam: {self.shop_title} ({self.design_title()})"

    def start_machine(self, name: str) -> None:
        """Note that a machine is running.

        Arguments:
        * `name` (`str`): The machine's name, e.g. "shop mill".
        """
        self.running.add(name)
        self.changed()

    def stop_machine(self, name: str) -> None:
        """Note that a machine has stopped.

        Arguments:
        * `name` (`str`): The machine's name.
        """
        self.running.discard(name)
        self.changed()

    def stop_all(self) -> None:
        """Stop every machine ([Stop All])."""
        self.running.clear()
        self.say("Stopped all machines.")

    def any_running(self) -> bool:
        """Tell whether [Stop All] is active: any machine runs (#100).

        Returns:
        * (`bool`): True while at least one machine runs.
        """
        return bool(self.running)

    def close_refusal(self, controls: set[str]) -> str:
        """Say why a window may not close, if it may not (#67).

        Arguments:
        * `controls` (`set[str]`): The machines the window controls.

        Returns:
        * (`str`): E.g. "Stop the shop mill first", or "" when the
          window may close.
        """
        busy: list[str] = sorted(controls & self.running)
        if not busy:
            return ""
        return f"Stop the {' and the '.join(busy)} first"
