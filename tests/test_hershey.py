"""Tests for `scraftcam.hershey`: text drawn as strokes."""

import unittest

from scraftcam import hershey
from scraftcam.geometry import Point


def box(lines: list[list[Point]]) -> tuple[float, float, float, float]:
    """Return the low X, low Y, high X, high Y around some strokes."""
    xs: list[float] = [point[0] for line in lines for point in line]
    ys: list[float] = [point[1] for line in lines for point in line]
    return min(xs), min(ys), max(xs), max(ys)


class TestHershey(unittest.TestCase):
    """Strokes, widths and glyphs."""

    def test_capital_height(self) -> None:
        """An `H` stands on the base line, as tall as the height."""
        low_y: float
        high_y: float
        _, low_y, _, high_y = box(hershey.strokes("H", (0.0, 0.0), 6.0))
        self.assertAlmostEqual(low_y, 0.0)
        self.assertAlmostEqual(high_y, 6.0)

    def test_a(self) -> None:
        """An `A`'s apex is centered, its feet on the base line."""
        lines: list[list[Point]] = hershey.strokes("A", (0.0, 0.0), 21.0)
        self.assertEqual(lines[0], [(9.0, 21.0), (1.0, 0.0)])
        self.assertEqual(len(lines), 3)

    def test_width(self) -> None:
        """Widths add, scale with the height, and match the advance."""
        self.assertAlmostEqual(hershey.width("A", 21.0), 18.0)
        self.assertAlmostEqual(
            hershey.width("AB", 10.5),
            hershey.width("A", 10.5) + hershey.width("B", 10.5),
        )
        second: list[list[Point]] = hershey.strokes("AA", (0.0, 0.0), 21.0)
        self.assertAlmostEqual(second[3][0][0], 18.0 + 9.0)

    def test_origin(self) -> None:
        """The origin moves every point."""
        here: list[list[Point]] = hershey.strokes("A", (0.0, 0.0), 21.0)
        there: list[list[Point]] = hershey.strokes("A", (5.0, 7.0), 21.0)
        self.assertEqual(there[0][0], (here[0][0][0] + 5, here[0][0][1] + 7))

    def test_angle(self) -> None:
        """At 90 degrees the base line runs up the Y axis."""
        lines: list[list[Point]] = hershey.strokes("-", (0.0, 0.0), 21.0, 90)
        start: Point = lines[0][0]
        end: Point = lines[0][1]
        self.assertAlmostEqual(start[0], end[0])
        self.assertGreater(end[1], start[1])

    def test_unknown(self) -> None:
        """A character not in the font is drawn as `?`."""
        self.assertEqual(
            hershey.strokes("€", (0.0, 0.0), 1.0),
            hershey.strokes("?", (0.0, 0.0), 1.0),
        )

    def test_space(self) -> None:
        """A space has width but no strokes."""
        self.assertEqual(hershey.strokes(" ", (0.0, 0.0), 1.0), [])
        self.assertGreater(hershey.width(" ", 1.0), 0.0)

    def test_extras(self) -> None:
        """The degree, diameter and plus or minus signs are drawn."""
        degree: list[list[Point]] = hershey.strokes("°", (0.0, 0.0), 21.0)
        self.assertGreater(box(degree)[1], 14.0)
        self.assertEqual(len(hershey.strokes("⌀", (0, 0), 1.0)), 2)
        self.assertEqual(len(hershey.strokes("±", (0, 0), 1.0)), 3)

    def test_every_glyph(self) -> None:
        """Every glyph decodes, right edge past its left."""
        character: str
        for character in hershey.GLYPHS:
            left: int
            right: int
            # The decoder is private, but every glyph must pass it.
            # pylint: disable-next=protected-access
            left, right, _ = hershey._glyph(character)
            self.assertLess(left, right, character)
        self.assertEqual(len(hershey.GLYPHS), 98)


if __name__ == "__main__":
    unittest.main()
