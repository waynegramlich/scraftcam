"""Tests for `scraftcam.gui.outline_cuts`: hide strips cut out."""

import math
import unittest

from scraftcam.diagram import LINE, Stroke, Weight, polyline
from scraftcam.geometry import ArcSegment, Point
from scraftcam.gui.hides import HIDE_X, HIDE_Y, Hide
from scraftcam.gui.outline_cuts import (
    GAP,
    cut_strokes,
    pieces,
    shift_at,
)
from scraftcam.gui.outline_file import Outline

# A tall counter-clockwise 2 x 10 rectangle, its middle hidden.
TALL: list[tuple[float, float]] = [
    (0.0, 0.0),
    (2.0, 0.0),
    (2.0, 10.0),
    (0.0, 10.0),
]


def tall(axis: int = HIDE_Y) -> Outline:
    """Return the rectangle with Y 3 to 7 (or X 0.5 to 1.5) hidden."""
    hide: Hide = (
        Hide(HIDE_Y, 1, 2, 3.0, 3.0)
        if axis == HIDE_Y
        else Hide(HIDE_X, 0, 1, 0.5, 0.5)
    )
    return Outline(points=list(TALL), hides=[hide])


def ys(strokes: list[Stroke]) -> list[float]:
    """Return every Y the strokes' segments start or end at."""
    return [
        point[1]
        for stroke in strokes
        for segment in stroke.segments
        for point in (segment.start, segment.end)
    ]


class TestPieces(unittest.TestCase):
    """The pieces a cut makes, and their shifts."""

    def test_pieces(self) -> None:
        """Above the cut moves down by what it hides, less the gap."""
        found = pieces(tall(), HIDE_Y, 1.0)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0][1:], (3.0, 0.0))
        self.assertEqual(found[1][0], 7.0)
        self.assertEqual(found[1][2], -3.0)
        self.assertEqual(shift_at(found, 8.0), -3.0)
        self.assertEqual(shift_at(found, 1.0), 0.0)
        self.assertEqual(pieces(tall(), HIDE_X, 1.0)[0][2], 0.0)


class TestCut(unittest.TestCase):
    """Strokes clipped and moved, break lines and S's."""

    def test_no_hides(self) -> None:
        """Nothing hidden: the same strokes."""
        strokes: list[Stroke] = [polyline([(0.0, 0.0), (1.0, 1.0)])]
        self.assertIs(cut_strokes(Outline(points=TALL), strokes, 1.0), strokes)

    def test_outline(self) -> None:
        """The sides are cut and closed up to the gap."""
        side: Stroke = polyline([(2.0, 0.0), (2.0, 10.0)])
        found: list[Stroke] = cut_strokes(tall(), [side], 0.5)
        kept: list[float] = sorted(ys(found[:2]))
        self.assertEqual(kept[:2], [0.0, 3.0])
        self.assertAlmostEqual(kept[2], 3.0 + GAP * 0.5)
        self.assertAlmostEqual(kept[3], 10.0 - 4.0 + GAP * 0.5)

    def test_breaks(self) -> None:
        """A zigzag break line on each side, across the part."""
        found: list[Stroke] = cut_strokes(tall(), [], 0.5)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0].segments[0].start, (0.0, 3.0))
        self.assertEqual(found[0].segments[-1].end, (2.0, 3.0))
        self.assertEqual(len(found[0].segments), 5)

    def test_breaks_across_x(self) -> None:
        """A strip top to bottom: break lines run up."""
        found: list[Stroke] = cut_strokes(tall(HIDE_X), [], 0.5)
        self.assertEqual(found[0].segments[0].start, (0.5, 0.0))
        self.assertEqual(found[0].segments[-1].end, (0.5, 10.0))

    def test_fill(self) -> None:
        """A filled stroke keeps its fill only when whole."""
        whole: Stroke = Stroke(
            polyline([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]).segments,
            Weight.THIN,
            filled=True,
        )
        cut: Stroke = Stroke(
            polyline([(0.0, 2.0), (1.0, 8.0)]).segments,
            Weight.THIN,
            filled=True,
        )
        found: list[Stroke] = cut_strokes(tall(), [whole, cut], 0.5)
        self.assertTrue(found[0].filled)
        self.assertFalse(found[1].filled)

    def test_arcs(self) -> None:
        """An arc inside a piece moves whole; one across a cut is
        clipped as lines."""
        inside: ArcSegment = ArcSegment(
            (9.0, 9.0), (9.0, 9.0), (8.5, 9.0), 0.5, 2 * math.pi
        )
        across: ArcSegment = ArcSegment(
            (1.0, 0.5), (1.0, 9.5), (1.0, 5.0), 4.5, math.pi
        )
        found: list[Stroke] = cut_strokes(
            tall(),
            [
                Stroke((inside,), Weight.THIN),
                Stroke((across,), Weight.THIN),
            ],
            0.5,
        )
        moved = found[0].segments[0]
        assert isinstance(moved, ArcSegment)
        self.assertAlmostEqual(moved.center[1], 9.0 - 3.0)
        self.assertEqual(len(found[1:-2]), 2)
        self.assertFalse(
            any(
                isinstance(segment, ArcSegment)
                for stroke in found[1:-2]
                for segment in stroke.segments
            )
        )

    def test_esses(self) -> None:
        """A dimension line across a cut ends in an S each side."""
        line: Stroke = Stroke(
            polyline([(4.0, 0.0), (4.0, 10.0)]).segments,
            Weight.THIN,
            role=LINE,
        )
        found: list[Stroke] = cut_strokes(tall(), [line], 0.5)
        esses: list[Stroke] = found[-2:]
        middle: Point = esses[0].segments[len(esses[0].segments) // 2].start
        self.assertAlmostEqual(middle[0], 4.0)
        self.assertAlmostEqual(middle[1], 3.0)
        self.assertAlmostEqual(
            esses[1].segments[len(esses[1].segments) // 2].start[1],
            3.0 + GAP * 0.5,
        )
        plain: Stroke = polyline([(4.0, 0.0), (4.0, 10.0)])
        self.assertEqual(len(cut_strokes(tall(), [plain], 0.5)), 4)


# A 12 x 12 square with three strips across each axis, each hiding 2:
# 1 to 3, 5 to 7 and 9 to 11 (as the grid plate will need).
SQUARE: list[tuple[float, float]] = [
    (0.0, 0.0),
    (12.0, 0.0),
    (12.0, 12.0),
    (0.0, 12.0),
]
STRIPS: tuple[tuple[float, float], ...] = ((1.0, 9.0), (5.0, 5.0), (9.0, 1.0))

# What is left of 0 to 12 on each axis, each gap closed to 1.
KEPT: list[tuple[float, float]] = [
    (0.0, 1.0),
    (2.0, 4.0),
    (5.0, 7.0),
    (8.0, 9.0),
]


def nine() -> Outline:
    """Return the square with its three strips across each axis."""
    hides: list[Hide] = [
        Hide(HIDE_Y, 1, 2, low, high) for low, high in STRIPS
    ] + [Hide(HIDE_X, 0, 1, low, high) for low, high in STRIPS]
    return Outline(points=list(SQUARE), hides=hides)


class TestThreeByThree(unittest.TestCase):
    """Three hide strips across each axis at once."""

    def test_sides(self) -> None:
        """Each side is cut in four, and moved in by the strips."""
        right: Stroke = polyline([(12.0, 0.0), (12.0, 12.0)])
        bottom: Stroke = polyline([(0.0, 0.0), (12.0, 0.0)])
        found: list[Stroke] = cut_strokes(nine(), [right, bottom], 0.5)
        spans: list[tuple[Point, Point]] = [
            (stroke.segments[0].start, stroke.segments[-1].end)
            for stroke in found[:8]
        ]
        self.assertEqual(
            spans[:4], [((9.0, low), (9.0, high)) for low, high in KEPT]
        )
        self.assertEqual(
            spans[4:], [((low, 0.0), (high, 0.0)) for low, high in KEPT]
        )

    def test_breaks(self) -> None:
        """Two break lines per strip, each cut in four by the others."""
        found: list[Stroke] = cut_strokes(nine(), [], 0.5)
        self.assertEqual(len(found), 6 * 2 * 4)
        self.assertTrue(all(len(stroke.segments) == 5 for stroke in found))
        across: set[float] = {
            stroke.segments[0].start[1]
            for stroke in found
            if stroke.segments[0].start[0] == 0.0
        }
        self.assertEqual(across, {1.0, 2.0, 4.0, 5.0, 7.0, 8.0})


if __name__ == "__main__":
    unittest.main()
