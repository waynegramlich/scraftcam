#!/usr/bin/env python3
"""A small MCP server for the exposed functions (`T.mi~7` #S2).

Only what Claude Code needs (#500): JSON-RPC posted to one address
(`/mcp`), answered with plain JSON (no streaming, no login), on this
computer only.  The methods are `initialize`, `ping`, `tools/list`
and `tools/call`; notifications are accepted and ignored.  The tools
are the three ways in: `find`, `describe` and `call`
(`exposed.py`).

Each call is handed to a runner (#510): by default it runs in the
server's own thread; the GUI hands it to Qt's main thread.

Run alone, for trying the protocol:

    python3 -m scraftcam.exposed.server [--port PORT] [MODULE...]

which exposes whatever the named modules mark (by default
`scraftcam.exposed.samples`).
"""

from __future__ import annotations

import argparse
import importlib
import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scraftcam import __version__
from scraftcam.exposed import exposed

# A runner runs one call and returns its result (#510).
Runner = Callable[[Callable[[], object]], object]

# The protocol version answered when the client names none.
PROTOCOL_VERSION: str = "2025-06-18"

# The address JSON-RPC is posted to.
PATH: str = "/mcp"

# The JSON-RPC error codes used.
METHOD_NOT_FOUND: int = -32601
PARSE_ERROR: int = -32700
INVALID_REQUEST: int = -32600

# The three tools, as `tools/list` gives them.
TOOLS: list[dict[str, object]] = [
    {
        "name": "find",
        "description": (
            "Find the exposed scraftcam functions whose name or "
            "narration (first docstring line) contains `text` "
            "(any case; empty lists all).  One `NAME (KIND): "
            "NARRATION` line each; KIND is `reads` or `changes`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
        },
    },
    {
        "name": "describe",
        "description": (
            "Give an exposed function's signature (with type hints), "
            "kind and whole docstring.  `name` is its full name or "
            "any unique dotted ending of it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "call",
        "description": (
            "Run an exposed function.  `arguments` holds its "
            "arguments by name, checked against its type hints; "
            "the result is given as JSON when it can be."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "arguments": {"type": "object"},
            },
            "required": ["name"],
        },
    },
]


def run_here(work: Callable[[], object]) -> object:
    """Run `work` in the calling thread: the default runner.

    Arguments:
    * `work` (`Callable[[], object]`):
        The call to run.

    Returns:
    * (`object`): its result.
    """
    return work()


def as_text(value: object) -> str:
    """Give a result as text: JSON when it can be, else `repr()`.

    Arguments:
    * `value` (`object`):
        A call's result.

    Returns:
    * (`str`): the text.
    """
    # A string is given as it is, not quoted.
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return repr(value)


class Server:
    """Answers MCP requests, whatever carries them.

    Attributes:
    * `runner` (`Runner`):
        Runs each tool call (#510).
    """

    def __init__(self, runner: Runner = run_here) -> None:
        """Make a server that runs its calls with `runner`.

        Arguments:
        * `runner` (`Runner`):
            Runs each tool call.
        """
        self.runner: Runner = runner

    def tool(self, name: str, arguments: dict[str, object]) -> str:
        """Run one of the three tools.

        Arguments:
        * `name` (`str`):
            `find`, `describe` or `call`.
        * `arguments` (`dict[str, object]`):
            The tool's arguments.

        Returns:
        * (`str`): the tool's answer.

        Raises:
        * `exposed.ExposedError`: when the tool or its arguments are
          bad.
        """
        # Each tool's arguments are checked before it is run.
        text: object = arguments.get("text", "")
        function: object = arguments.get("name", "")
        given: object = arguments.get("arguments", {})
        if name == "find" and isinstance(text, str):
            return "\n".join(exposed.find(text)) or "(nothing found)"
        if name == "describe" and isinstance(function, str):
            return exposed.describe(function)
        if (
            name == "call"
            and isinstance(function, str)
            and isinstance(given, dict)
        ):
            checked: dict[str, object] = {
                str(key): value for key, value in given.items()
            }

            def work() -> object:
                """Run the exposed function."""
                return exposed.call(function, checked)

            return as_text(self.runner(work))
        raise exposed.ExposedError(f"bad tool call `{name}`: {arguments}")

    def answer(self, message: object) -> dict[str, object] | None:
        """Answer one JSON-RPC message.

        Arguments:
        * `message` (`object`):
            The parsed message.

        Returns:
        * (`dict[str, object] | None`): the response, or `None` for a
          notification.
        """
        # A message without an `id` is a notification: no answer.
        if not isinstance(message, dict) or "method" not in message:
            return _error(None, INVALID_REQUEST, "not a JSON-RPC request")
        identifier: object = message.get("id")
        if identifier is None:
            return None
        method: object = message["method"]
        params: object = message.get("params", {})
        if not isinstance(params, dict):
            params = {}

        # The four methods.
        result: dict[str, object]
        if method == "initialize":
            version: object = params.get("protocolVersion")
            result = {
                "protocolVersion": (
                    version if isinstance(version, str) else PROTOCOL_VERSION
                ),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "scraftcam", "version": __version__},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            result = self._tools_call(params)
        else:
            return _error(identifier, METHOD_NOT_FOUND, f"no {method}")
        return {"jsonrpc": "2.0", "id": identifier, "result": result}

    def _tools_call(self, params: dict[str, object]) -> dict[str, object]:
        """Answer `tools/call`; a failure is a result marked an error.

        Arguments:
        * `params` (`dict[str, object]`):
            The request's `name` and `arguments`.

        Returns:
        * (`dict[str, object]`): the MCP tool result.
        """
        # Errors go back to the model as text, so it can correct them.
        name: object = params.get("name", "")
        arguments: object = params.get("arguments", {})
        text: str
        failed: bool = False
        try:
            if not isinstance(arguments, dict):
                raise exposed.ExposedError("`arguments` is not an object")
            text = self.tool(
                str(name), {str(key): arguments[key] for key in arguments}
            )
        except exposed.ExposedError as error:
            text, failed = str(error), True
        # Any failure in an exposed function is reported, not allowed
        # to kill the server.
        # pylint: disable-next=broad-exception-caught
        except Exception as error:  # noqa: BLE001
            text, failed = f"{type(error).__name__}: {error}", True
        return {"content": [{"type": "text", "text": text}], "isError": failed}


def _error(identifier: object, code: int, message: str) -> dict[str, object]:
    """Make a JSON-RPC error response.

    Arguments:
    * `identifier` (`object`):
        The request's `id` (`None` when it could not be read).
    * `code` (`int`):
        The JSON-RPC error code.
    * `message` (`str`):
        What went wrong.

    Returns:
    * (`dict[str, object]`): the response.
    """
    return {
        "jsonrpc": "2.0",
        "id": identifier,
        "error": {"code": code, "message": message},
    }


def make_handler(server: Server) -> type[BaseHTTPRequestHandler]:
    """Make the HTTP handler class that passes requests to `server`.

    Arguments:
    * `server` (`Server`):
        Answers the messages.

    Returns:
    * (`type[BaseHTTPRequestHandler]`): the handler class.
    """

    class Handler(BaseHTTPRequestHandler):
        """Passes each `POST /mcp` to the server."""

        def do_POST(self) -> None:  # pylint: disable=invalid-name
            """Answer one posted JSON-RPC message (the name is
            `http.server`'s)."""
            # Read the message; anything else at another path is 404.
            if self.path.split("?")[0] != PATH:
                self.send_error(404)
                return
            length: int = int(self.headers.get("Content-Length", "0"))
            body: bytes = self.rfile.read(length)
            response: dict[str, object] | None
            try:
                response = server.answer(json.loads(body))
            except json.JSONDecodeError as error:
                response = _error(None, PARSE_ERROR, str(error))

            # A notification gets 202 and no body.
            if response is None:
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            data: bytes = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # pylint: disable=invalid-name
            """Refuse the event stream: none is offered (#500)."""
            self.send_error(405)

        def log_message(  # pylint: disable=arguments-differ
            self, format: str, *args: object
        ) -> None:
            """Keep quiet: the GUI's terminal is the user's."""
            del format, args

    return Handler


def serve(
    port: int, server: Server | None = None
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Start serving on `localhost:port` in a thread of its own.

    Arguments:
    * `port` (`int`):
        The port; 0 picks a free one (`http.server_address[1]`).
    * `server` (`Server | None`):
        Answers the messages; by default one running calls here.

    Returns:
    * (`tuple[ThreadingHTTPServer, threading.Thread]`): the HTTP
      server (`shutdown()` stops it) and its thread.
    """
    # Only this computer may connect (#500).
    http: ThreadingHTTPServer = ThreadingHTTPServer(
        ("127.0.0.1", port), make_handler(server or Server())
    )
    thread: threading.Thread = threading.Thread(
        target=http.serve_forever, name="mcp", daemon=True
    )
    thread.start()
    return http, thread


def main() -> None:
    """Serve the functions the named modules expose, until killed."""
    # Import the modules, which registers what they mark.
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Serve scraftcam's exposed functions over MCP."
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "modules", nargs="*", default=["scraftcam.exposed.samples"]
    )
    options: argparse.Namespace = parser.parse_args()
    module: str
    for module in options.modules:
        importlib.import_module(module)

    # Serve until interrupted.
    http: ThreadingHTTPServer
    thread: threading.Thread
    http, thread = serve(options.port)
    print(f"MCP on http://127.0.0.1:{options.port}{PATH}", flush=True)
    try:
        thread.join()
    except KeyboardInterrupt:
        http.shutdown()


if __name__ == "__main__":
    main()
