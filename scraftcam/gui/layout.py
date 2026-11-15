"""The windows' layout, kept so it comes back the next day (#186).

Each shop has its own layout file in `~/.scraftcam/layouts/`, named
from its `shop.toml`'s path: the rows (windows), each with its size,
its tree (shown, width, open branches) and its panels, left to right
(width, and what each shows).  `~/.scraftcam/` is always deletable;
losing the file only loses the layout (#187).

A layout is plain data (`dict` and `list` from JSON), made by the
windows (`Window.snapshot()`) and read back by them.
"""

import hashlib
import json
from pathlib import Path

from ..home import HOME_DIRECTORY, make_directory

# Where the layouts are kept.
LAYOUT_DIRECTORY: Path = HOME_DIRECTORY / "layouts"

# The layout file's own version: a file of another is skipped quietly
# (#187).  2: windows built from their trees, with pins (#200-#205).
LAYOUT_VERSION: int = 2

# The text last written to each file, so it is written only on change.
WRITTEN: dict[Path, str] = {}


# Function `layout_path()`:
def layout_path(shop: Path, directory: Path | None = None) -> Path:
    """Return the layout file of a shop (#187).

    Arguments:
    * `shop` (`Path`): The shop's `shop.toml`.
    * `directory` (`Path | None`): Where the layouts are kept, or
      `None` for `LAYOUT_DIRECTORY`.

    Returns:
    * (`Path`): Its file, named from the shop's absolute path.
    """
    digest: str = hashlib.sha256(str(shop.resolve()).encode()).hexdigest()
    kept: Path = LAYOUT_DIRECTORY if directory is None else directory
    return kept / f"{digest[:16]}.json"


# Function `layout_text()`:
def layout_text(shop: Path, rows: list[dict[str, object]]) -> str:
    """Return a layout as the text of its file.

    Arguments:
    * `shop` (`Path`): The shop's `shop.toml`, written in the file so
      a person can tell which shop it is for.
    * `rows` (`list[dict[str, object]]`): Each row's snapshot,
      oldest first.

    Returns:
    * (`str`): The JSON text.
    """
    layout: dict[str, object] = {
        "version": LAYOUT_VERSION,
        "shop": str(shop.resolve()),
        "rows": rows,
    }
    return json.dumps(layout, indent=2) + "\n"


# Function `save_layout()`:
def save_layout(
    shop: Path, rows: list[dict[str, object]], path: Path | None = None
) -> bool:
    """Write a shop's layout, only when it has changed (#187).

    Arguments:
    * `shop` (`Path`): The shop's `shop.toml`.
    * `rows` (`list[dict[str, object]]`): Each row's snapshot,
      oldest first.
    * `path` (`Path | None`): The file, or `None` for the shop's own
      (`layout_path()`).

    Returns:
    * (`bool`): True if the file was written.
    """
    # Nothing new: nothing written.
    file: Path = layout_path(shop) if path is None else path
    text: str = layout_text(shop, rows)
    if WRITTEN.get(file) == text:
        return False

    # Written whole, then renamed, so a crash leaves the old one.
    try:
        make_directory(file.parent)
        partial: Path = file.with_suffix(".partial")
        partial.write_text(text, encoding="utf-8")
        partial.replace(file)
    except OSError:
        return False
    WRITTEN[file] = text
    return True


# Function `read_layout()`:
def read_layout(
    shop: Path, path: Path | None = None
) -> list[dict[str, object]]:
    """Read a shop's layout back: its rows, oldest first (#186).

    Arguments:
    * `shop` (`Path`): The shop's `shop.toml`.
    * `path` (`Path | None`): The file, or `None` for the shop's own.

    Returns:
    * (`list[dict[str, object]]`): Each row's snapshot; empty when
      there is no file, or it does not read (skipped quietly, #187).
    """
    file: Path = layout_path(shop) if path is None else path
    try:
        text: str = file.read_text(encoding="utf-8")
        layout: object = json.loads(text)
    except (OSError, ValueError):
        return []
    if not isinstance(layout, dict):
        return []
    rows: object = layout.get("rows")
    if layout.get("version") != LAYOUT_VERSION or not isinstance(rows, list):
        return []
    WRITTEN[file] = text
    return [row for row in rows if isinstance(row, dict)]
