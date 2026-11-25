"""Open the outline editor for Claude to drive, in one command.

This copies an outline file into `~/.scraftcam/drive/` (MCP edits
only copies, `T.mi~7` #489), starts the outline editor on the copy
serving MCP on a free port, and opens a Konsole window running Claude
Code in that directory, already connected to it:
```
python3 -m scraftcam.run --drive-editor [FILE] [--fresh] [--prompt TEXT]
```
The Claude session starts in `~/.scraftcam/drive/`, not in the
project, so it reads none of the project's rules, tasks or memory:
only the short `CLAUDE.md` written there each launch (#12, #13).  Its
MCP tools are allowed for this launch only (#7).  Closing the editor
ends this script; the Claude window stays until it is closed.  The
editor's output goes to `~/.scraftcam/drive/editor.log`.

The tests never need any of this: recordings are replayed by plain
`unittest` (#11).
"""

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .shops import EXAMPLE_SHOP

# The repository's top, where `python3 -m` runs the editor.
TOP: Path = Path(__file__).resolve().parent.parent

# Where the copies, the session's `CLAUDE.md` and its MCP config go.
DRIVE: Path = Path.home() / ".scraftcam" / "drive"

# The outline driven when none is named.
DEFAULT: Path = EXAMPLE_SHOP / "tools" / "end_mill.outline.toml"

# The MCP tools the session may use without asking.
TOOLS: str = (
    "mcp__scraftcam__find,mcp__scraftcam__describe,mcp__scraftcam__call"
)

# The session's first prompt, unless `--prompt` gives another.
PROMPT: str = (
    "Drive the outline editor over the `scraftcam` MCP tools: call "
    "`editors` and `state`, say briefly what you see, then wait for me."
)

# The session's whole `CLAUDE.md` (written each launch, #13).
GUIDE: str = """\
# Driving the scraftcam Outline Editor

(Written by `drive_editor.py` at each launch; edits are lost.)

* You drive a running outline editor over the MCP tools `find`,
  `describe` and `call` (server `scraftcam`).  Start with `call
  editors`, then `call state` with the handle it gives.
* `find ""` lists every exposed function; `describe NAME` gives its
  arguments and docstring.  Gestures (`click`, `drag`, `press`) take
  points in the drawing's own steps, Y up, and return the new state.
* Say in one line what you are about to do before each gesture: the
  user is watching the window.
* The files here are copies.  Never edit scraftcam's source; write
  what you find (bugs, things too hard to use) to `findings.md` here.
"""


def free_port() -> int:
    """Give a port no one is listening on now.

    Returns:
    * (`int`): the port.
    """
    # Port 0 asks the system for a free one.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
    return port


def answers(port: int) -> bool:
    """Say whether the MCP server on `port` answers a `ping`.

    Arguments:
    * `port` (`int`):
        The server's port.

    Returns:
    * (`bool`): True once it answers.
    """
    # A plain JSON-RPC ping; any failure means not yet.
    body: bytes = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "ping"}
    ).encode()
    request: urllib.request.Request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=1):
            return True
    except (urllib.error.URLError, OSError):
        return False


def terminal(command: list[str]) -> list[str]:
    """Wrap `command` to run in a new terminal window.

    Arguments:
    * `command` (`list[str]`):
        The command and its arguments.

    Returns:
    * (`list[str]`): the terminal's command line.

    Raises:
    * `SystemExit`: when no terminal is found.
    """
    # Konsole (KDE) first, then the system's chosen terminal.
    if shutil.which("konsole"):
        return ["konsole", "--workdir", str(DRIVE), "-e", *command]
    if shutil.which("x-terminal-emulator"):
        return ["x-terminal-emulator", "-e", *command]
    raise SystemExit("drive_editor: no terminal (konsole) found")


def main(arguments: list[str]) -> None:
    """Copy the outline, start the editor, open Claude beside it.

    Arguments:
    * `arguments` (`list[str]`): The command line, after
      `--drive-editor`.
    """
    # The file to drive, and the session's first words.
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Open the outline editor for Claude to drive."
    )
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT)
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="copy the file again over an earlier copy",
    )
    parser.add_argument("--prompt", default=PROMPT, help="the first prompt")
    options: argparse.Namespace = parser.parse_args(arguments)
    source: Path = options.path.resolve()
    if not source.is_file():
        raise SystemExit(f"drive_editor: no file {source}")
    claude: str | None = shutil.which("claude")
    if claude is None:
        raise SystemExit("drive_editor: `claude` is not on the path")

    # The copy (kept between launches unless `--fresh`).
    DRIVE.mkdir(parents=True, exist_ok=True)
    copy: Path = DRIVE / source.name
    if options.fresh or not copy.exists():
        shutil.copyfile(source, copy)

    # The editor, serving MCP on a free port.
    port: int = free_port()
    log: Path = DRIVE / "editor.log"
    with log.open("w", encoding="utf-8") as output:
        # It outlives this block: `main()` waits on it at the end.
        editor: subprocess.Popen[bytes] = subprocess.Popen(  # pylint: disable=consider-using-with
            [
                sys.executable,
                "-m",
                "scraftcam.run",
                f"--outline={copy}",
                "--mcp",
                str(port),
            ],
            cwd=TOP,
            stdout=output,
            stderr=subprocess.STDOUT,
        )

    # Wait (up to 30 s) until it answers, or give up if it died.
    deadline: float = time.monotonic() + 30.0
    while not answers(port):
        if editor.poll() is not None or time.monotonic() > deadline:
            editor.kill()
            print(log.read_text(encoding="utf-8"), file=sys.stderr)
            raise SystemExit("drive_editor: the editor did not start")
        time.sleep(0.25)

    # The session's guide and MCP config, then its window.
    (DRIVE / "CLAUDE.md").write_text(GUIDE, encoding="utf-8")
    config: Path = DRIVE / "mcp.json"
    servers: dict[str, object] = {
        "mcpServers": {
            "scraftcam": {
                "type": "http",
                "url": f"http://127.0.0.1:{port}/mcp",
            }
        }
    }
    config.write_text(json.dumps(servers, indent=2), encoding="utf-8")
    # The prompt comes first: the options after it take many values.
    session: list[str] = [
        claude,
        options.prompt,
        "--strict-mcp-config",
        "--mcp-config",
        str(config),
        "--allowedTools",
        TOOLS,
    ]
    # The window is left running: it is the user's to close.
    subprocess.Popen(  # pylint: disable=consider-using-with
        terminal(session), cwd=DRIVE
    )
    print(f"Editing {copy}, MCP on port {port}; close the editor to end.")

    # Until the editor is closed (Control-C closes it too).
    try:
        editor.wait()
    except KeyboardInterrupt:
        editor.terminate()
        editor.wait()
