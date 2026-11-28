"""Tests of `scraftcam.gui.hides`: hide strips."""

import unittest

from scraftcam.gui.hides import (
    HIDE_X,
    HIDE_Y,
    Hide,
    inside_spans,
    lay,
    minus,
    strip,
)
from tests.qt.shapes import HOUSE

# Half a drill: tip at the origin, shoulder at 1.2, shank to 8.
DRILL: list[tuple[float, float]] = [
    (0.0, 0.0),
    (2.0, 1.2),
    (2.0, 8.0),
    (0.0, 8.0),
]


class HidesTest(unittest.TestCase):
    """Laying strips, and where they go when corners move."""

    def test_lay(self) -> None:
        """A strip over the shank, tied to the shoulder and the top."""
        hide = lay(DRILL, HIDE_Y, 3.0, 6.0)
        assert isinstance(hide, Hide)
        self.assertEqual((hide.below, hide.above), (1, 2))
        self.assertAlmostEqual(hide.low, 1.8)
        self.assertAlmostEqual(hide.high, 2.0)
        self.assertEqual(strip(DRILL, hide), (3.0, 6.0))
        self.assertEqual(lay(DRILL, HIDE_Y, 6.0, 3.0), hide)

        # The shank longer: the strip hides more (#160).
        longer: list[tuple[float, float]] = [*DRILL[:2], (2.0, 20), (0, 20)]
        self.assertEqual(strip(longer, hide), (3.0, 18.0))

    def test_refused(self) -> None:
        """Not over a corner, a fillet, or past the outline."""
        self.assertIn("corner", str(lay(DRILL, HIDE_Y, 0.5, 6.0)))
        self.assertIn("fillet", str(lay(DRILL, HIDE_Y, 3, 6, [(5.0, 7.0)])))
        self.assertIn("between", str(lay(DRILL, HIDE_Y, 8.5, 9.0)))
        self.assertIn("between", str(lay(DRILL, HIDE_X, -1.0, -0.5)))
        self.assertIn("Drag", str(lay(DRILL, HIDE_Y, 3.0, 3.0)))
        hide = lay(DRILL, HIDE_X, 0.5, 1.5)
        assert isinstance(hide, Hide)
        self.assertEqual(strip(DRILL, hide), (0.5, 1.5))

    def test_spans(self) -> None:
        """A line across is inside the outline edge to edge; a revolved
        one's mirror too; another hide's stretch taken out (#185)."""
        self.assertEqual(inside_spans(DRILL, HIDE_Y, 5.0), [(0.0, 2.0)])
        self.assertEqual(
            inside_spans(DRILL, HIDE_Y, 5.0, mirror=True), [(-2.0, 2.0)]
        )

        # Two polygons, a box and a roof on it (`T.sa~6.11` #765):
        # across the roof only its stretch, across both their union.
        house: list[tuple[float, float]] = list(HOUSE)
        loops: list[list[int]] = [[0, 1, 2, 3], [3, 2, 4]]
        self.assertEqual(
            inside_spans(house, HIDE_Y, 5.0, loops=loops), [(1.0, 3.0)]
        )
        self.assertEqual(
            inside_spans(house, HIDE_X, 1.0, loops=loops), [(0.0, 5.0)]
        )
        u_shape: list[tuple[float, float]] = [
            (0.0, 0.0),
            (6.0, 0.0),
            (6.0, 4.0),
            (4.0, 4.0),
            (4.0, 1.0),
            (2.0, 1.0),
            (2.0, 4.0),
            (0.0, 4.0),
        ]
        self.assertEqual(
            inside_spans(u_shape, HIDE_Y, 2.0), [(0.0, 2.0), (4.0, 6.0)]
        )
        self.assertEqual(inside_spans(u_shape, HIDE_X, 3.0), [(0.0, 1.0)])
        self.assertEqual(
            minus([(0.0, 6.0)], [(2.0, 3.0), (5.0, 9.0)]),
            [(0.0, 2.0), (3.0, 5.0)],
        )


if __name__ == "__main__":
    unittest.main()
