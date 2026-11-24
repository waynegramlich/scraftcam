"""Tests for `scraftcam.screws` (`T.sfoe~6.4` #328)."""

import unittest
from fractions import Fraction

from scraftcam.model import Length
from scraftcam.screws import SCREWS, Screw, screw


# Class `TestScrews`:
class TestScrews(unittest.TestCase):
    """The screw table and its lookup."""

    def test_half_inch(self) -> None:
        """A 1/2 in screw, as on Shars 202-1664's jaws."""
        found: Screw = screw(Length.parse("1/2 in"))
        self.assertEqual(found.name, "1/2")
        self.assertEqual(found.clearance, Length(Fraction(17, 32), "in"))
        self.assertEqual(found.counterbore, Length(Fraction(13, 16), "in"))
        self.assertEqual(found.depth, Length(Fraction(1, 2), "in"))

    def test_metric_and_number_sizes(self) -> None:
        """A size in mm, and a numbered size, find their screws."""
        self.assertEqual(screw(Length.parse("12.7 mm")).name, "1/2")
        self.assertEqual(screw(Length.parse("0.19 in")).name, "#10")

    def test_unknown(self) -> None:
        """A size not in the table is refused, the sizes named."""
        with self.assertRaisesRegex(KeyError, "#4, #5"):
            screw(Length.parse("3/4 in"))

    def test_table_sane(self) -> None:
        """Each hole is over its screw, each counterbore over its hole."""
        each: Screw
        for each in SCREWS:
            self.assertGreater(each.clearance, each.diameter, each.name)
            self.assertGreater(each.counterbore, each.clearance, each.name)


if __name__ == "__main__":
    unittest.main()
