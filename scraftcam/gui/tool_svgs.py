#!/usr/bin/env python3
"""Write each tool's diagram beside it (`T.toasl~6.8` #737b, #737c).

```
python3 -m scraftcam.gui.tool_svgs [SHOP_DIR]
```

For every kind's directory in the shop's `tools/` that holds an
outline (`drills/drill.outline.toml`), each tool there gets a `.svg`
beside its `.toml`: the outline drawn for the tool's values, in its
true proportions, at the outline's own scale (`tool_svg()`).  The
panel writes one when a tool's value is typed in; this writes them
all, as after an outline changes.  A shop that may not be changed
(the example shop, but for `.allow_edits`) is refused.  With no
`SHOP_DIR`, the example shop.
"""

import sys
import tomllib
from pathlib import Path

from scraftcam.gui.outline_editor import tool_svg
from scraftcam.shops import EXAMPLE_SHOP, OUTLINE_SUFFIX, is_read_only


# Function `tool_values()`:
def tool_values(tool: Path, outline: Path) -> dict[str, str]:
    """Return a tool's values for its outline's letters.

    Arguments:
    * `tool` (`Path`): The tool's `.toml`.
    * `outline` (`Path`): Its kind's `.outline.toml`.

    Returns:
    * (`dict[str, str]`): Its values, by letter, for the outline's
      letters that it gives.
    """
    with outline.open("rb") as file:
        letters: object = tomllib.load(file).get("letters", {})
    with tool.open("rb") as file:
        item: dict[str, object] = tomllib.load(file)
    names: list[str] = list(letters) if isinstance(letters, dict) else []
    return {name: str(item[name]) for name in names if name in item}


# Function `write_svgs()`:
def write_svgs(shop: Path) -> list[Path]:
    """Write every tool's diagram that is missing or out of date.

    Arguments:
    * `shop` (`Path`): The shop's directory.

    Returns:
    * (`list[Path]`): The `.svg` files written.

    Raises:
    * `ValueError`: If the shop may not be changed.
    """
    if is_read_only(shop):
        raise ValueError(f"{shop} is read only (no .allow_edits)")
    written: list[Path] = []
    outline: Path
    for outline in sorted((shop / "tools").glob(f"*/*{OUTLINE_SUFFIX}")):
        tool: Path
        for tool in sorted(outline.parent.glob("*.toml")):
            if tool.name.endswith(OUTLINE_SUFFIX):
                continue
            text: str = tool_svg(outline, tool_values(tool, outline))
            picture: Path = tool.with_suffix(".svg")
            if not picture.is_file() or (
                picture.read_text(encoding="utf-8") != text
            ):
                picture.write_text(text, encoding="utf-8")
                written.append(picture)
    return written


# Function `main()`:
def main(arguments: list[str]) -> int:
    """Write a shop's tool diagrams, saying which.

    Arguments:
    * `arguments` (`list[str]`): The command line, less the program.

    Returns:
    * (`int`): 0, or 1 when the shop may not be changed.
    """
    shop: Path = Path(arguments[0]) if arguments else EXAMPLE_SHOP
    try:
        written: list[Path] = write_svgs(shop)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    path: Path
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
