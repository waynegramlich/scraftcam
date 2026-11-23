"""Tests for `scraftcam.exposed.handles` (#507), without Qt."""

import gc
import unittest

from scraftcam.exposed.exposed import ExposedError
from scraftcam.exposed.handles import Handles


class View:  # pylint: disable=too-few-public-methods
    """A stand-in for a live object."""


class Window:  # pylint: disable=too-few-public-methods
    """Another kind of live object."""


class TestHandles(unittest.TestCase):
    """Handles are counted per class, held weakly, and reset."""

    def test_counted_per_class(self) -> None:
        """Each class counts from 1; an object keeps its handle."""
        handles: Handles = Handles()
        first: View = View()
        second: View = View()
        window: Window = Window()
        self.assertEqual(handles.handle(first), "View 1")
        self.assertEqual(handles.handle(window), "Window 1")
        self.assertEqual(handles.handle(second), "View 2")
        self.assertEqual(handles.handle(first), "View 1")
        self.assertIs(handles.find("View 2"), second)

    def test_gone_and_unknown(self) -> None:
        """A dropped object's handle has gone; others never were."""
        handles: Handles = Handles()
        view: View | None = View()
        handles.handle(view)
        view = None
        gc.collect()
        with self.assertRaisesRegex(ExposedError, "`View 1` has gone"):
            handles.find("View 1")
        name: str
        for name in ("View 2", "Window 1", "View", "nonsense"):
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(ExposedError, "is not a handle"),
            ):
                handles.find(name)

    def test_reset(self) -> None:
        """After a reset, counting starts again from 1."""
        handles: Handles = Handles()
        kept: View = View()
        handles.handle(kept)
        handles.handle(View())
        handles.reset()
        self.assertEqual(handles.handle(kept), "View 1")
        self.assertEqual(handles.handle(View()), "View 2")


if __name__ == "__main__":
    unittest.main()
