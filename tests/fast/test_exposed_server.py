"""Tests for `scraftcam.exposed.server`, over real HTTP."""

import json
import threading
import unittest
import urllib.error
import urllib.request
from collections.abc import Callable
from http.server import ThreadingHTTPServer

from scraftcam.exposed import samples, server

# `samples` is imported for what it exposes.
del samples


class TestServer(unittest.TestCase):
    """The four methods, notifications and errors, over `urllib`."""

    http: ThreadingHTTPServer
    url: str
    ran_in: list[str]

    @classmethod
    def setUpClass(cls) -> None:
        """Serve on a free port, noting which thread runs calls."""
        cls.ran_in = []

        def runner(work: Callable[[], object]) -> object:
            """Note the thread, then run the call."""
            cls.ran_in.append(threading.current_thread().name)
            return work()

        thread: threading.Thread
        cls.http, thread = server.serve(0, server.Server(runner))
        del thread
        cls.url = f"http://127.0.0.1:{cls.http.server_address[1]}/mcp"

    @classmethod
    def tearDownClass(cls) -> None:
        """Stop serving."""
        cls.http.shutdown()
        cls.http.server_close()

    def post(self, message: object) -> tuple[int, object]:
        """Post `message`; return the status and the parsed body."""
        request: urllib.request.Request = urllib.request.Request(
            self.url,
            data=json.dumps(message).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            body: bytes = response.read()
            status: int = response.status
        return status, json.loads(body) if body else None

    def result(self, method: str, params: object = None) -> object:
        """Post a request; return its `result`."""
        status: int
        body: object
        status, body = self.post(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        )
        self.assertEqual(status, 200)
        assert isinstance(body, dict)
        return body["result"]

    def tool(self, name: str, arguments: object) -> tuple[str, bool]:
        """Call a tool; return its text and whether it failed."""
        result: object = self.result(
            "tools/call", {"name": name, "arguments": arguments}
        )
        assert isinstance(result, dict)
        return result["content"][0]["text"], result["isError"]

    def test_initialize(self) -> None:
        """The client's version is echoed; tools are offered."""
        result: object = self.result(
            "initialize", {"protocolVersion": "2025-03-26"}
        )
        assert isinstance(result, dict)
        self.assertEqual(result["protocolVersion"], "2025-03-26")
        self.assertEqual(result["capabilities"], {"tools": {}})
        self.assertEqual(self.result("ping"), {})

    def test_notification(self) -> None:
        """A notification gets 202 and no body."""
        self.assertEqual(
            self.post(
                {"jsonrpc": "2.0", "method": "notifications/initialized"}
            ),
            (202, None),
        )

    def test_tools(self) -> None:
        """The three tools are listed and work."""
        result: object = self.result("tools/list")
        assert isinstance(result, dict)
        self.assertEqual(
            [tool["name"] for tool in result["tools"]],
            ["find", "describe", "call"],
        )
        self.assertIn(
            "samples.add (reads): Add {a} and {b}.",
            self.tool("find", {"text": "add"})[0],
        )
        self.assertIn(
            "add(a: float, b: float) -> float",
            self.tool("describe", {"name": "add"})[0],
        )
        self.assertEqual(
            self.tool("call", {"name": "add", "arguments": {"a": 1, "b": 2}}),
            ("3", False),
        )
        self.assertEqual(
            self.tool("call", {"name": "corners", "arguments": {"count": 2}}),
            ("[[0.0, 0.0], [1.0, 0.0]]", False),
        )
        self.assertNotIn("MainThread", self.ran_in)
        self.assertTrue(self.ran_in)

    def test_errors(self) -> None:
        """Bad tools, arguments and methods are reported, not fatal."""
        text: str
        failed: bool
        text, failed = self.tool(
            "call", {"name": "add", "arguments": {"a": "1", "b": 2}}
        )
        self.assertTrue(failed)
        self.assertIn("`a` = '1'", text)
        self.assertTrue(self.tool("nonsense", {})[1])
        self.assertTrue(
            self.tool(
                "call",
                {"name": "corners", "arguments": {"count": 1, "size": None}},
            )[1]
        )
        body: object
        _status, body = self.post({"jsonrpc": "2.0", "id": 2, "method": "x"})
        assert isinstance(body, dict)
        self.assertEqual(body["error"]["code"], server.METHOD_NOT_FOUND)
        with (
            self.assertRaises(urllib.error.HTTPError),
            urllib.request.urlopen(self.url),
        ):
            pass


if __name__ == "__main__":
    unittest.main()
