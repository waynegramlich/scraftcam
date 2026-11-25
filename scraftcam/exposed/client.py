#!/usr/bin/env python3
"""Drive a running program's MCP server from the shell (#568).

Claude Code's own MCP client connects only at its start, so Claude
starts a headless outline editor itself and talks to it with this:
```
python3 -m scraftcam.exposed.client start [FILE] [--port PORT]
python3 -m scraftcam.exposed.client start --gui [SHOP] [--port PORT]
python3 -m scraftcam.exposed.client start --gui --shown [SHOP]
python3 -m scraftcam.exposed.client find TEXT
python3 -m scraftcam.exposed.client describe NAME
python3 -m scraftcam.exposed.client call NAME [KEY=VALUE ...]
python3 -m scraftcam.exposed.client stop
```
A `VALUE` is JSON when it reads as JSON (`3`, `-1.5`, `[1, 2]`),
else text (`editor="OutlineEditor 1"` and `word=Undo` both work).
`start` runs `scraftcam.run --headless --mcp PORT --outline [FILE]`
(the outline editor in its first panel, #S5) and waits until it
answers, then lists its editors (handles are given out when first
listed); with `--gui` it runs `scraftcam.run --headless --mcp PORT`
instead (`SHOP` opened over MCP, never remembered), and gives its
`status` (#577);
with `--shown` the window is on the user's screen, not headless, so
the user watches (and can take over) while Claude drives it.
The process number is kept in `~/.scraftcam/drive/PORT.pid`,
which `stop` uses (never `pkill`, which matched its own shell).  A
tool's error prints to standard error, and the exit status is 1.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from scraftcam.exposed.server import PATH

# The port used unless `--port` says otherwise (`.mcp.json` has 8765).
PORT: int = 8766

# Where each started program's process number is kept.
DRIVE: Path = Path.home() / ".scraftcam" / "drive"

# How long `start` waits for the program to answer, in seconds.
WAIT: float = 20.0


class ClientError(Exception):
    """A tool's error, or no server answering."""


def request(port: int, method: str, params: dict[str, object]) -> object:
    """Send one JSON-RPC request and give its result.

    Arguments:
    * `port` (`int`):
        The server's port on `127.0.0.1`.
    * `method` (`str`):
        The method (`tools/call`, `ping`, ...).
    * `params` (`dict[str, object]`):
        Its parameters.

    Returns:
    * (`object`): the response's `result`.

    Raises:
    * `ClientError`: when nothing answers, or the answer is an error.
    """
    # One POST, answered with one JSON object.
    body: bytes = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode("utf-8")
    sent: urllib.request.Request = urllib.request.Request(
        f"http://127.0.0.1:{port}{PATH}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(sent, timeout=30.0) as reply:
            answer: object = json.loads(reply.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        raise ClientError(f"no server on port {port}: {error}") from error
    if not isinstance(answer, dict) or "result" not in answer:
        raise ClientError(f"a bad answer: {answer!r}")
    return answer["result"]


def tool(port: int, name: str, arguments: dict[str, object]) -> str:
    """Run one of the server's tools (`find`, `describe`, `call`).

    Arguments:
    * `port` (`int`):
        The server's port.
    * `name` (`str`):
        The tool.
    * `arguments` (`dict[str, object]`):
        Its arguments.

    Returns:
    * (`str`): its text.

    Raises:
    * `ClientError`: when the tool reports an error.
    """
    # The text of its one content item.
    result: object = request(
        port, "tools/call", {"name": name, "arguments": arguments}
    )
    if not isinstance(result, dict):
        raise ClientError(f"a bad result: {result!r}")
    content: object = result.get("content")
    text: str = ""
    if isinstance(content, list) and content:
        first: object = content[0]
        if isinstance(first, dict):
            text = str(first.get("text", ""))
    if result.get("isError"):
        raise ClientError(text)
    return text


def value(text: str) -> object:
    """Give a `KEY=VALUE` argument's value: JSON, or else the text.

    Arguments:
    * `text` (`str`):
        What follows the `=`.

    Returns:
    * (`object`): the JSON value, or `text` itself.
    """
    try:
        found: object = json.loads(text)
    except ValueError:
        return text
    return found


def arguments_of(pairs: list[str]) -> dict[str, object]:
    """Give the arguments named by `KEY=VALUE` words.

    Arguments:
    * `pairs` (`list[str]`):
        The words.

    Returns:
    * (`dict[str, object]`): each key's value.

    Raises:
    * `ClientError`: when a word has no `=`.
    """
    given: dict[str, object] = {}
    pair: str
    for pair in pairs:
        key: str
        equals: str
        rest: str
        key, equals, rest = pair.partition("=")
        if not equals or not key:
            raise ClientError(f"`{pair}` is not KEY=VALUE")
        given[key] = value(rest)
    return given


def pid_file(port: int) -> Path:
    """Give the file holding the process number for `port`.

    Arguments:
    * `port` (`int`):
        The port.

    Returns:
    * (`Path`): `~/.scraftcam/drive/PORT.pid`.
    """
    return DRIVE / f"{port}.pid"


def start(
    port: int,
    outline: Path | None,
    *,
    gui: bool = False,
    shown: bool = False,
) -> str:
    """Start an outline editor (or GUI) serving MCP on `port`.

    Headless unless `shown`.

    Arguments:
    * `port` (`int`):
        The port.
    * `outline` (`Path | None`):
        The outline file to open, or `None` for a new outline; with
        `gui`, the shop (opened over MCP, not remembered), or `None`
        for the shop shown last.
    * `gui` (`bool`):
        True to start `scraftcam.run` rather than the editor.
    * `shown` (`bool`):
        True to show its window on the screen, rather than headless.

    Returns:
    * (`str`): what was started.

    Raises:
    * `ClientError`: when one is already running there, it does not
      answer in time, or (with `gui`) the shop has no `shop.toml`.
    """
    # Refuse to start a second one on a port that answers.
    try:
        request(port, "ping", {})
    except ClientError:
        pass
    else:
        raise ClientError(f"a server already answers on port {port}")

    # Started in its own session, so it outlives this command.
    # Always the one GUI (#S5): an outline in its first panel, unless
    # `gui` (then `outline` is the shop).
    command: list[str] = [
        sys.executable,
        "-m",
        "scraftcam.run",
        *([] if shown else ["--headless"]),
        "--mcp",
        str(port),
    ]
    if outline is not None and not gui:
        command.append(f"--outline={outline}")
    elif not gui:
        command.append("--outline")
    DRIVE.mkdir(parents=True, exist_ok=True)
    log: Path = DRIVE / f"{port}.log"
    with log.open("w", encoding="utf-8") as output:
        # Not waited for: it is meant to keep running.
        # pylint: disable-next=consider-using-with
        process: subprocess.Popen[bytes] = subprocess.Popen(
            command,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_file(port).write_text(f"{process.pid}\n", encoding="utf-8")

    # Wait until it answers, or give up and stop it.
    deadline: float = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pid_file(port).unlink(missing_ok=True)
            raise ClientError(
                f"it exited ({process.returncode}): "
                + log.read_text(encoding="utf-8").strip()
            )
        try:
            request(port, "ping", {})
        except ClientError:
            time.sleep(0.2)
            continue
        # The shop, over MCP, leaving the user's settings alone (#718);
        # none there stops it again.
        if gui and outline is not None:
            try:
                tool(
                    port,
                    "call",
                    {
                        "name": "open_shop",
                        "arguments": {"shop": str(outline), "remember": False},
                    },
                )
            except ClientError:
                stop(port)
                raise

        # Handles are given out when first listed (#507).
        first: str = "status" if gui else "editors"
        listed: str = tool(port, "call", {"name": first, "arguments": {}})
        return (
            f"started process {process.pid} on port {port} (log {log});"
            f" {first}: {listed}"
        )
    stop(port)
    raise ClientError(f"no answer on port {port} after {WAIT} s")


def stop(port: int) -> str:
    """Stop the program `start` began on `port`.

    Arguments:
    * `port` (`int`):
        The port.

    Returns:
    * (`str`): what was stopped.

    Raises:
    * `ClientError`: when none was started there.
    """
    # Its process number, then a polite signal.
    path: Path = pid_file(port)
    try:
        pid: int = int(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ClientError(f"nothing started on port {port}") from error
    path.unlink()
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return f"process {pid} had already exited"
    return f"stopped process {pid}"


def main() -> None:
    """Run one command from the command line."""
    # The commands and their words.
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Drive a scraftcam MCP server from the shell."
    )
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument(
        "--gui", action="store_true", help="start scraftcam.run"
    )
    parser.add_argument(
        "--shown", action="store_true", help="on the screen, not headless"
    )
    parser.add_argument(
        "command", choices=("start", "stop", "find", "describe", "call")
    )
    parser.add_argument("words", nargs="*")
    options: argparse.Namespace = parser.parse_intermixed_args()
    port: int = options.port
    words: list[str] = options.words

    # Each command prints its text; a failure goes to standard error.
    try:
        text: str
        if options.command == "start":
            text = start(
                port,
                Path(words[0]) if words else None,
                gui=options.gui,
                shown=options.shown,
            )
        elif options.command == "stop":
            text = stop(port)
        elif options.command == "find":
            text = tool(port, "find", {"text": " ".join(words)})
        elif not words:
            raise ClientError(f"`{options.command}` needs a NAME")
        elif options.command == "describe":
            text = tool(port, "describe", {"name": words[0]})
        else:
            text = tool(
                port,
                "call",
                {"name": words[0], "arguments": arguments_of(words[1:])},
            )
    except ClientError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    print(text)


if __name__ == "__main__":
    main()
