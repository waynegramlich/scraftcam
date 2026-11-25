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
from scraftcam.gui.hides import Hide
from scraftcam.gui.letters import Letter
from scraftcam.gui.outline_file import (
    COUNTERBORED,
    PLAIN,
    Hole,
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
        Letter("R", "Corner radius", "1/32 in", "", fillet=True),
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
    note_radius="D",
    hides=[Hide(1, 1, 2, 1.8, 2.0)],
)


class OutlineFileTest(unittest.TestCase):
    """Writing and reading outline files."""

    def test_round_trip(self) -> None:
        """What is written reads back the same, and writes the same."""
        text: str = outline_text(HALF_DRILL)
        self.assertTrue(
            text.startswith('kind = "outline"\nversion = 5\nrevolve = true')
        )
        self.assertIn('to = "y_axis"', text)
        self.assertIn('from = "origin"', text)
        self.assertIn("rays = [1, -1]", text)
        self.assertEqual(text.count("fillet = true"), 1)
        back: Outline = outline_from_text(text, "drill.outline.toml")
        self.assertEqual(back, HALF_DRILL)
        self.assertEqual(outline_text(back), text)

    def test_formula_letter(self) -> None:
        """A formula letter is written as `formula`, read back with its
        value worked out (#430)."""
        drill: Outline = Outline(
            list(HALF_DRILL.points),
            [
                Letter("PA", "Point angle", "118 deg", ""),
                Letter("HPA", "Half point angle", "", "", formula="PA / 2"),
            ],
        )
        text: str = outline_text(drill)
        self.assertIn('formula = "PA / 2"', text)
        self.assertEqual(text.count("default ="), 1)
        back: Outline = outline_from_text(text, "drill.outline.toml")
        self.assertEqual(back.letters[1].formula, "PA / 2")
        self.assertEqual(back.letters[1].default, "59 deg")
        self.assertEqual(outline_text(back), text)

    def test_old_version(self) -> None:
        """Only version 5 is read; older files were converted once
        (#773), and one without a version is refused too."""
        text: str = outline_text(HALF_DRILL)
        self.assertEqual(outline_from_text(text), HALF_DRILL)
        old: str
        for old in ("version = 4", "version = 7", ""):
            with self.assertRaises(OutlineError) as caught:
                outline_from_text(text.replace("version = 5", old))
            self.assertIn("version", str(caught.exception))

    def test_names(self) -> None:
        """Corners are written and read by name (#787): a dimension's
        ends and a strip's corners name them; a bad, doubled or end's
        word name is refused, and a new corner's name is never one
        used before."""
        text: str = outline_text(HALF_DRILL)
        self.assertIn('name = "V1"', text)
        self.assertNotIn("[[points]]", text)
        self.assertIn('below = "V2"', text)
        renamed: Outline = outline_from_text(text.replace('"V2"', '"Tip"'))
        self.assertEqual(renamed.names[1], "Tip")
        self.assertEqual(renamed.hides, HALF_DRILL.hides)
        bad: str
        for bad in ('"2x"', '"V1"', '"origin"'):
            with self.assertRaises(OutlineError) as caught:
                outline_from_text(text.replace('name = "V2"', f"name = {bad}"))
            self.assertIn("vertices[1]: name", str(caught.exception))
        self.assertEqual(
            Outline([(0.0, 0.0)] * 2, names=["V1", "V7"]).new_name(), "V8"
        )
        filled: Outline = Outline([(0.0, 0.0)] * 3, names=["Tip"])
        self.assertEqual(filled.names, ["Tip", "V1", "V2"])

    def test_text_sizes(self) -> None:
        """A text height and font steps are written only when set,
        and read back (`T.sfoe~6.4` #280)."""
        self.assertNotIn("text_height", outline_text(HALF_DRILL))
        self.assertNotIn("font_step", outline_text(HALF_DRILL))
        sized: Outline = outline_from_text(outline_text(HALF_DRILL))
        sized.text_height = 0.25
        sized.dimensions[0].font_step = -2
        text: str = outline_text(sized)
        self.assertIn("text_height = 0.25", text)
        self.assertIn("font_step = -2", text)
        self.assertEqual(outline_from_text(text), sized)
        bad: str
        for bad in ("text_height = -1", 'text_height = "big"'):
            with self.assertRaises(OutlineError):
                outline_from_text(text.replace("text_height = 0.25", bad))
        with self.assertRaises(OutlineError):
            outline_from_text(
                text.replace("font_step = -2", "font_step = 1.5")
            )

    def test_turned(self) -> None:
        """`turns` is written only when set, and read back (#300)."""
        self.assertNotIn("turns", outline_text(HALF_DRILL))
        turned: Outline = outline_from_text(outline_text(HALF_DRILL))
        turned.turns = 3
        text: str = outline_text(turned)
        self.assertIn("turns = 3", text)
        self.assertEqual(outline_from_text(text), turned)
        bad: str
        for bad in ("turns = 4", "turns = true", "turns = 1.5"):
            with self.assertRaises(OutlineError):
                outline_from_text(text.replace("turns = 3", bad))

    def test_moved(self) -> None:
        """A mark's `moved` is written only when set, and read back
        (#317)."""
        self.assertNotIn("moved", outline_text(HALF_DRILL))
        shifted: Outline = outline_from_text(outline_text(HALF_DRILL))
        shifted.dimensions[0].moved = (1.5, -2.0)
        text: str = outline_text(shifted)
        self.assertIn("moved = [1.5, -2.0]", text)
        self.assertEqual(outline_from_text(text), shifted)
        bad: str
        for bad in ("moved = [1.5]", 'moved = ["a", 2]', "moved = 3"):
            with self.assertRaises(OutlineError):
                outline_from_text(text.replace("moved = [1.5, -2.0]", bad))

    def test_holes(self) -> None:
        """Holes are written only when there are some, their sizes only
        when set, and read back (#290)."""
        self.assertNotIn("holes", outline_text(HALF_DRILL))
        holed: Outline = outline_from_text(outline_text(HALF_DRILL))
        holed.holes = [
            Hole(PLAIN, (0.5, 1.0), "D"),
            Hole(COUNTERBORED, (2.0, 1.0), "E", depth="0.53 in"),
        ]
        text: str = outline_text(holed)
        self.assertIn('kind = "counterbored"', text)
        self.assertIn('depth = "0.53 in"', text)
        self.assertNotIn("clearance", text)
        self.assertEqual(outline_from_text(text), holed)
        bad: str
        good: str
        for good, bad in (
            ('kind = "plain"', 'kind = "square"'),
            ("at = [0.5, 1.0]", "at = [0.5]"),
            ('letter = "D"', 'letter = ""'),
            ('depth = "0.53 in"', "depth = 0.53"),
            ('letter = "D"', 'letter = "D"\ndepth = "1 in"'),
        ):
            # Only the holes' tables, after the drill's own.
            head: str
            holes: str
            head, holes = text.split("[[holes]]", 1)
            with self.assertRaises(OutlineError, msg=bad):
                outline_from_text(
                    head + "[[holes]]" + holes.replace(good, bad, 1)
                )

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
            outline_from_text(
                'kind = "outline"\nversion = 5\n[[vertices]]\nat = [1]', "x"
            )
        lengthy: Outline = Outline(
            [(0.0, 0.0)], [], [Dimension("L", LENGTH, 0, 0)]
        )
        self.assertNotIn("rays", outline_text(lengthy))
        with self.assertRaises(OutlineError) as caught:
            outline_from_text(
                'kind = "outline"\n[letters.R]\nname = ""\n'
                'default = "1 in"\nhelp = ""\nfillet = 1',
                "x",
            )
        self.assertIn("letters.R.fillet", str(caught.exception))

    def test_checks(self) -> None:
        """Every problem is reported, naming the file and the entry
        (#93, #95)."""
        bad: str = (
            'kind = "outline"\n'
            "version = 5\n"
            "revolve = true\n"
            '[letters.A]\nname = "a"\ndefault = "1 in"\nhelp = ""\n'
            '[letters.B]\nname = "b"\n'
            '[[vertices]]\nname = "V1"\nat = [0.0, 0.0]\n'
            '[[vertices]]\nname = "V2"\nat = [-1.0, 2.0]\n'
            '[[vertices]]\nname = "V3"\nat = [1]\n'
            '[[dimensions]]\nletter = "A"\nkind = "horizontal"\n'
            'from = "V9"\nto = "y_axis"\noffset = 1.0\nalong = 0.5\n'
            '[[dimensions]]\nletter = "Q"\nkind = "diagonal"\n'
            'from = "V1"\nto = "V2"\noffset = true\nalong = 0.5\n'
            'rays = [1, 2]\nplaces = [["up", 1.0, 2.0]]\n'
        )
        bad += (
            '[[hides]]\naxis = "z"\n'
            '[[hides]]\naxis = "y"\nbelow = "V9"\nabove = "V2"\n'
            "low = 0\nhigh = 0\n"
        )
        with self.assertRaises(OutlineError) as caught:
            outline_from_text(bad, "drill.outline.toml")
        lines: list[str] = str(caught.exception).splitlines()
        self.assertTrue(
            all(line.startswith("drill.outline.toml: ") for line in lines)
        )
        text: str = str(caught.exception)
        for expected in (
            "letters.B: needs name, default (or formula) and help",
            "vertices[2]: needs at = [x, y]",
            "a revolved outline has a corner at X < 0",
            "dimensions[0]: from = 'V9': not a corner's name or origin",
            "dimensions[0]: to = 'y_axis'",
            "dimensions[1]: kind 'diagonal'",
            "dimensions[1]: letter 'Q'",
            "dimensions[1]: needs numbers for offset and along",
            "dimensions[1]: rays must be two of 1 and -1",
            "dimensions[1]: places:",
            'hides[0]: needs axis = "x" or "y"',
            "hides[1]: needs corners below, above and numbers",
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
