"""Tests for `scraftcam.exposed.exposed`; the samples below are
registered for each test only, in a registry of their own (#529)."""

import unittest

from scraftcam.exposed import exposed
from scraftcam.exposed.exposed import ExposedError


def corner_count(outline: str) -> int:
    """Count the corners of {outline}."""
    return len(outline)


def drag(index: int, x: float, y: float, snap: bool = True) -> str:
    """Drag corner {index} to {x}, {y}."""
    return f"{index} {x} {y} {snap}"


def place(points: list[tuple[float, float]], name: str | None = None) -> int:
    """Place {name} at the points."""
    return len(points) if name is None else -len(points)


class TestExposed(unittest.TestCase):
    """The registry, `find()`, `describe()`, `call()`, `narration()`."""

    def setUp(self) -> None:
        """Register the samples in a registry of their own (#529)."""
        self.enterContext(exposed.isolated())
        exposed.reads(corner_count)
        exposed.changes(drag)
        exposed.changes(place)

    def test_find(self) -> None:
        """Names and narrations are searched in any case."""
        found: list[str] = exposed.find("DRAG")
        self.assertEqual(
            found,
            [
                (
                    "tests.test_exposed.drag (changes): "
                    "Drag corner {index} to {x}, {y}."
                )
            ],
        )
        self.assertEqual(len(exposed.find("test_exposed")), 3)
        self.assertEqual(exposed.find("no such thing"), [])

    def test_lookup(self) -> None:
        """Full names and unique endings both work."""
        self.assertIs(exposed.lookup("drag").function, drag)
        self.assertIs(exposed.lookup("test_exposed.drag").function, drag)
        with self.assertRaisesRegex(ExposedError, "nothing exposed"):
            exposed.lookup("rag")

    def test_describe(self) -> None:
        """The signature, kind and docstring are given."""
        text: str = exposed.describe("drag")
        self.assertIn(
            "drag(index: int, x: float, y: float, snap: bool = True)"
            " -> str (changes)",
            text,
        )
        self.assertIn("Drag corner {index}", text)

    def test_call(self) -> None:
        """Arguments are bound by name and checked against hints."""
        self.assertEqual(
            exposed.call("drag", {"index": 3, "x": 1, "y": 2.5}),
            "3 1 2.5 True",
        )
        self.assertEqual(
            exposed.call("place", {"points": [[0, 0], [1, 2]]}), 2
        )
        self.assertEqual(
            exposed.call("place", {"points": [[0, 0]], "name": "A"}), -1
        )

    def test_call_refused(self) -> None:
        """Bad arguments are refused, saying which and why."""
        cases: tuple[tuple[dict[str, object], str], ...] = (
            (
                {"index": "3", "x": 1, "y": 2},
                "`index` = '3' is not of type `int`$",
            ),
            ({"index": True, "x": 1, "y": 2}, "`index` = True"),
            ({"index": 3, "x": 1}, "missing a required argument"),
            ({"index": 3, "x": 1, "y": 2, "z": 0}, "unexpected keyword"),
        )
        bad: dict[str, object]
        message: str
        for bad, message in cases:
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(ExposedError, message),
            ):
                exposed.call("drag", bad)
        with self.assertRaisesRegex(ExposedError, "needs 2 items"):
            exposed.call("place", {"points": [[0, 0, 0]]})
        with self.assertRaisesRegex(ExposedError, r"`points\[0\]\[1\]`"):
            exposed.call("place", {"points": [[0, "y"]]})
        with self.assertRaisesRegex(ExposedError, "`name`"):
            exposed.call("place", {"points": [], "name": 7})

    def test_narration(self) -> None:
        """`{name}`s are filled in; missing ones stay."""
        self.assertEqual(
            exposed.narration("drag", {"index": 3, "x": 1, "y": 2}),
            "Drag corner 3 to 1, 2.",
        )
        self.assertEqual(
            exposed.narration("place", {}), "Place {name} at the points."
        )

    def test_register_refused(self) -> None:
        """No docstring, or a name exposed twice, is refused."""

        def bare() -> None:
            pass

        with self.assertRaisesRegex(ExposedError, "no docstring"):
            exposed.reads(bare)

        def twin() -> None:
            """One."""

        def twin_again() -> None:
            """Two."""

        twin_again.__qualname__ = twin.__qualname__
        exposed.reads(twin)
        exposed.reads(twin)
        with self.assertRaisesRegex(ExposedError, "exposed twice"):
            exposed.reads(twin_again)


if __name__ == "__main__":
    unittest.main()
