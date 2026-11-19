"""Tests of `scraftcam.gui.outline_file`: outlines as TOML."""

import unittest

from scraftcam.gui.dimensions import (
    ANGLE,
    HORIZONTAL,
    LENGTH,
    ORIGIN,
    Y_AXIS,
    Dimension,
)
from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_file import (
    Outline,
    OutlineError,
    outline_from_text,
    outline_text,
)

# Half a drill point, revolved: a tip angle from the Y axis and a
# radius from the origin, one dimension that has been a length too.
HALF_DRILL: Outline = Outline(
    [(0.0, 0.0), (2.0, 1.2), (2.0, 8.0), (0.0, 8.0)],
    [
        Letter("A", "Half point angle", "59 deg", 'The "half" angle.'),
        Letter("D", "Radius", "1/8 in", ""),
    ],
    [
        Dimension("A", ANGLE, 0, Y_AXIS, 0.6, 0.5, rays=(1, -1)),
        Dimension(
            "D",
            HORIZONTAL,
            ORIGIN,
            1,
            -0.4,
            0.25,
            (("length", 1e-5, 0.75),),
        ),
    ],
    revolve=True,
)


class OutlineFileTest(unittest.TestCase):
    """Writing and reading outline files."""

    def test_round_trip(self) -> None:
        """What is written reads back the same, and writes the same."""
        text: str = outline_text(HALF_DRILL)
        self.assertTrue(text.startswith('kind = "outline"\nrevolve = true'))
        self.assertIn('to = "y_axis"', text)
        self.assertIn('from = "origin"', text)
        self.assertIn("rays = [1, -1]", text)
        back: Outline = outline_from_text(text, "drill.outline.toml")
        self.assertEqual(back, HALF_DRILL)
        self.assertEqual(outline_text(back), text)

    def test_order_fixed(self) -> None:
        """One moved corner changes one line (#92)."""
        moved: Outline = outline_from_text(outline_text(HALF_DRILL))
        moved.points[1] = (2.5, 1.2)
        before: list[str] = outline_text(HALF_DRILL).splitlines()
        after: list[str] = outline_text(moved).splitlines()
        self.assertEqual(len(before), len(after))
        self.assertEqual(
            sum(
                1 for old, new in zip(before, after, strict=True) if old != new
            ),
            1,
        )

    def test_bad_text(self) -> None:
        """Text that is not an outline is refused, naming the file."""
        with self.assertRaises(OutlineError) as caught:
            outline_from_text("kind = [", "bad.toml")
        self.assertIn("bad.toml", str(caught.exception))
        with self.assertRaises(OutlineError):
            outline_from_text('kind = "tool"', "x")
        with self.assertRaises(OutlineError):
            outline_from_text('kind = "outline"\n[[points]]\nat = [1]', "x")
        lengthy: Outline = Outline(
            [(0.0, 0.0)], [], [Dimension("L", LENGTH, 0, 0)]
        )
        self.assertNotIn("rays", outline_text(lengthy))

    def test_checks(self) -> None:
        """Every problem is reported, naming the file and the entry
        (#93, #95)."""
        bad: str = (
            'kind = "outline"\n'
            "revolve = true\n"
            '[letters.A]\nname = "a"\ndefault = "1 in"\nhelp = ""\n'
            '[letters.B]\nname = "b"\n'
            "[[points]]\nat = [0.0, 0.0]\n"
            "[[points]]\nat = [-1.0, 2.0]\n"
            "[[points]]\nat = [1]\n"
            '[[dimensions]]\nletter = "A"\nkind = "horizontal"\n'
            'from = 7\nto = "y_axis"\noffset = 1.0\nalong = 0.5\n'
            '[[dimensions]]\nletter = "Q"\nkind = "diagonal"\n'
            "from = 0\nto = 1\noffset = true\nalong = 0.5\n"
            'rays = [1, 2]\nplaces = [["up", 1.0, 2.0]]\n'
        )
        with self.assertRaises(OutlineError) as caught:
            outline_from_text(bad, "drill.outline.toml")
        lines: list[str] = str(caught.exception).splitlines()
        self.assertTrue(
            all(line.startswith("drill.outline.toml: ") for line in lines)
        )
        text: str = str(caught.exception)
        for expected in (
            "letters.B: needs name, default and help",
            "points[2]: needs at = [x, y]",
            "a revolved outline has a corner at X < 0",
            "dimensions[0]: from = 7: not a corner 0-1 or origin",
            "dimensions[0]: to = 'y_axis'",
            "dimensions[1]: kind 'diagonal'",
            "dimensions[1]: letter 'Q'",
            "dimensions[1]: needs numbers for offset and along",
            "dimensions[1]: rays must be two of 1 and -1",
            "dimensions[1]: places:",
        ):
            self.assertIn(expected, text)
        for broken in (
            (
                'kind = "outline"\nrevolve = 3\npoints = 1\nletters = 2\n'
                "dimensions = 4"
            ),
            'kind = "outline"\ndimensions = [1]',
        ):
            with self.assertRaises(OutlineError):
                outline_from_text(broken, "x")


if __name__ == "__main__":
    unittest.main()
