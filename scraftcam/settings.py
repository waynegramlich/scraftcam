"""The user's settings: where their shops are (`T.toasl~6.8` #S1).

`~/.scraftcam/settings.toml` lists the directories that hold shops,
searched in order like `PATH` (#433, #702), and the shop shown last
(#704):

```toml
shop_directories = ["~/shops", "~/work/shops"]
last_shop = "~/shops/my_shop"
```

Each directory under a shop directory that has a `shop.toml` is a
shop.  The example shop is always listed first and is never in the
file.  With no file, it is the only shop (#682); the file is written
by the first [Copy Shop].
"""

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .shops import EXAMPLE_SHOP, SHOP_FILE

# The settings file, under the user's home.
SETTINGS: Path = Path(".scraftcam") / "settings.toml"


# Class `SettingsError`:
class SettingsError(ValueError):
    """The settings file can not be read, or says something wrong."""


# Class `Settings`:
@dataclass(frozen=True, slots=True)
class Settings:
    """What `settings.toml` holds.

    Attributes:
    * `shop_directories` (`tuple[Path, ...]`):
      The directories that hold shops, in search order.
    * `last_shop` (`Path | None`):
      The directory of the shop shown last, or `None` for none yet.

    Constructor:
    * `Settings(shop_directories=(), last_shop=None)`
    """

    # Constructor arguments:
    shop_directories: tuple[Path, ...] = field(init=True, default=())
    last_shop: Path | None = field(init=True, default=None)


# Function `settings_file()`:
def settings_file(home: Path | None = None) -> Path:
    """Return where the settings file is.

    Arguments:
    * `home` (`Path | None`):
      The home directory; `None` for the user's (tests give their own).

    Returns:
    * (`Path`): `HOME/.scraftcam/settings.toml`.
    """
    return (Path.home() if home is None else home) / SETTINGS


# Function `read_settings()`:
def read_settings(path: Path) -> Settings:
    """Read the settings file; a missing one is the empty settings.

    Arguments:
    * `path` (`Path`): The settings file.

    Returns:
    * (`Settings`): What it says, its paths with `~` expanded.

    Raises:
    * `SettingsError`: If it is not TOML, or a value is not what it
      should be (the message names the file).
    """
    # No file yet: no shops but the example shop (#682).
    if not path.is_file():
        return Settings()
    try:
        data: dict[str, object] = tomllib.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise SettingsError(f"{path}: {error}") from error

    # `shop_directories`: a list of strings.
    raw: object = data.get("shop_directories", [])
    if not isinstance(raw, list) or not all(
        isinstance(entry, str) for entry in raw
    ):
        raise SettingsError(
            f"{path}: shop_directories must be a list of directories"
        )
    directories: tuple[Path, ...] = tuple(
        Path(str(entry)).expanduser() for entry in raw
    )

    # `last_shop`: a string, if there.
    last: object = data.get("last_shop")
    if last is not None and not isinstance(last, str):
        raise SettingsError(f"{path}: last_shop must be a directory")
    return Settings(
        directories, None if last is None else Path(last).expanduser()
    )


# Function `settings_text()`:
def settings_text(settings: Settings) -> str:
    """Return the settings file's text.

    Arguments:
    * `settings` (`Settings`): What to write.

    Returns:
    * (`str`): The TOML (each path a JSON string, which TOML reads).
    """
    lines: list[str] = [
        "# The directories that hold shops, searched in order, and the",
        "# shop shown last (written by scraftcam).",
        "shop_directories = ["
        + ", ".join(
            json.dumps(str(path)) for path in settings.shop_directories
        )
        + "]",
    ]
    if settings.last_shop is not None:
        lines.append(f"last_shop = {json.dumps(str(settings.last_shop))}")
    return "\n".join(lines) + "\n"


# Function `write_settings()`:
def write_settings(settings: Settings, path: Path) -> None:
    """Write the settings file, making its directory if needed.

    Arguments:
    * `settings` (`Settings`): What to write.
    * `path` (`Path`): The settings file.

    Raises:
    * `OSError`: If it can not be written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(settings_text(settings), encoding="utf-8")


# Function `find_shops()`:
def find_shops(settings: Settings) -> list[Path]:
    """Return every shop's `shop.toml`: the example shop's first.

    Arguments:
    * `settings` (`Settings`): Where to look.

    Returns:
    * (`list[Path]`): The example shop's, then each shop directory's
      shops in name order, the directories in their order; a
      directory that is not there is skipped.
    """
    found: list[Path] = [EXAMPLE_SHOP / SHOP_FILE]
    directory: Path
    for directory in settings.shop_directories:
        if not directory.is_dir():
            continue
        shop: Path
        for shop in sorted(directory.iterdir()):
            if (shop / SHOP_FILE).is_file():
                found.append(shop / SHOP_FILE)
    return found


# Function `start_shop()`:
def start_shop(settings: Settings) -> Path:
    """Return the `shop.toml` to show at start (#704).

    Arguments:
    * `settings` (`Settings`): The settings.

    Returns:
    * (`Path`): The last shop's, while it is still there; else the
      example shop's.
    """
    last: Path | None = settings.last_shop
    if last is not None and (last / SHOP_FILE).is_file():
        return last / SHOP_FILE
    return EXAMPLE_SHOP / SHOP_FILE
