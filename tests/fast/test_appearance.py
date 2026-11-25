"""Tests of `scraftcam.appearance`: colours and hatches."""

import unittest

from scraftcam.appearance import STANDARD_HATCHES, Color, Hatch, Look, looks


# Class `ColorTest`:
class ColorTest(unittest.TestCase):
    """Colours as percentages."""

    def test_parse(self) -> None:
        """Spaces and the transparency are optional."""
        self.assertEqual(
            Color.parse("R13%G32%B78%"), Color(13.0, 32.0, 78.0, 0.0)
        )
        self.assertEqual(
            Color.parse(" r13% g32% b78% t40% "), Color(13.0, 32.0, 78.0, 40.0)
        )

    def test_refused(self) -> None:
        """A bad text or a part over 100% is refused."""
        text: str
        for text in ("#2050c0", "R13% G32%", "R101% G0% B0%"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                Color.parse(text)

    def test_round_trip(self) -> None:
        """Text and Qt's 0 to 255 parts go both ways."""
        color: Color = Color.parse("R20% G40% B60% T20%")
        self.assertEqual(color.text(), "R20% G40% B60% T20%")
        self.assertEqual(color.rgba(), (51, 102, 153, 204))
        self.assertEqual(Color.from_rgba(*color.rgba()), color)
        self.assertEqual(Color(1.0, 2.0, 3.0).text(), "R1% G2% B3%")


# Class `HatchTest`:
class HatchTest(unittest.TestCase):
    """Hatches as angle, spacing and thickness."""

    def test_parse(self) -> None:
        """A crosshatch is two sets; lengths are kept in inches."""
        hatch: Hatch = Hatch.parse("A45 S2mm T0.25mm+a135s0.1inT0.01 in")
        self.assertEqual(len(hatch.lines), 2)
        self.assertAlmostEqual(hatch.lines[0].spacing, 2.0 / 25.4)
        self.assertAlmostEqual(hatch.lines[1].angle, 135.0)
        self.assertAlmostEqual(hatch.lines[1].thickness, 0.01)
        self.assertAlmostEqual(
            Hatch.parse("A0 S1pt T2pt").lines[0].thickness, 2.0 / 72
        )
        self.assertEqual(
            hatch.written, "A45 S2mm T0.25mm + a135s0.1inT0.01 in"
        )

    def test_refused(self) -> None:
        """A missing unit, a bad text or a zero spacing is refused."""
        text: str
        for text in ("A45 S2 T0.25mm", "45 2mm 0.25mm", "A45 S0mm T1mm"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                Hatch.parse(text)

    def test_standard(self) -> None:
        """The standard hatches are all different."""
        self.assertEqual(
            len({hatch.lines for hatch in STANDARD_HATCHES}),
            len(STANDARD_HATCHES),
        )


# Class `LooksTest`:
class LooksTest(unittest.TestCase):
    """A drawing's polygons' colours and hatches."""

    def test_looks(self) -> None:
        """Own colour wins; materials never share a hatch (#781)."""
        materials: dict[str, tuple[str, str]] = {
            "hss": ("R65% G67% B70%", ""),
            "steel": ("R50% G50% B50%", "A45 S2mm T0.25mm"),
        }
        found: list[Look] = looks(
            [("hss", ""), ("steel", "R1% G2% B3%"), ("", ""), ("HSS", "")],
            materials,
        )
        self.assertEqual(found[0].color, Color(65.0, 67.0, 70.0))
        self.assertEqual(found[1].color, Color(1.0, 2.0, 3.0))
        self.assertEqual(found[2], Look(None, None))
        assert found[0].hatch is not None and found[1].hatch is not None
        self.assertEqual(found[0].hatch, STANDARD_HATCHES[1])
        self.assertEqual(found[1].hatch.written, "A45 S2mm T0.25mm")
        self.assertEqual(found[3].hatch, found[0].hatch)


if __name__ == "__main__":
    unittest.main()
