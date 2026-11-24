"""Tests for `scraftcam.exposed.client`, against a real server."""

import unittest
from http.server import ThreadingHTTPServer

from scraftcam.exposed import client, samples, server

# `samples` is imported for what it exposes.
del samples


class TestClient(unittest.TestCase):
    """Arguments from words, and tools over HTTP (#568)."""

    http: ThreadingHTTPServer
    port: int

    @classmethod
    def setUpClass(cls) -> None:
        """Serve the samples on a free port."""
        cls.http, _ = server.serve(0)
        cls.port = cls.http.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        """Stop serving."""
        cls.http.shutdown()
        cls.http.server_close()

    def test_arguments(self) -> None:
        """Values are JSON when they read as JSON, else text."""
        self.assertEqual(
            client.arguments_of(
                ["a=3", "b=-1.5", "c=[1, 2]", 'd="x y"', "e=Undo"]
            ),
            {"a": 3, "b": -1.5, "c": [1, 2], "d": "x y", "e": "Undo"},
        )
        with self.assertRaises(client.ClientError):
            client.arguments_of(["no_equals"])

    def test_tools(self) -> None:
        """A call answers; a bad one raises with the server's text."""
        self.assertEqual(
            client.tool(
                self.port,
                "call",
                {"name": "add", "arguments": {"a": 2, "b": 3}},
            ),
            "5",
        )
        self.assertIn("add", client.tool(self.port, "find", {"text": "add"}))
        with self.assertRaises(client.ClientError):
            client.tool(self.port, "call", {"name": "nothing_such"})

    def test_no_server(self) -> None:
        """Nothing listening is a `ClientError`, not a traceback."""
        free: ThreadingHTTPServer
        free, _ = server.serve(0)
        port: int = free.server_address[1]
        free.shutdown()
        free.server_close()
        with self.assertRaises(client.ClientError):
            client.request(port, "ping", {})


if __name__ == "__main__":
    unittest.main()
