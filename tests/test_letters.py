"""Tests of `scraftcam.gui.letters`: the outline editor's letters."""

import unittest

from scraftcam.gui.letters import (
    Letter,
    letter_problem,
    next_letter,
    value_problem,
)


class LettersTest(unittest.TestCase):
    """Letter names, default values, new letters."""

    def test_value_problem(self) -> None:
        """Lengths and angles with units pass; others are explained."""
        text: str
        for text in ("6 in", "3-7/8 in", "20 mm", "59 deg", "1.5 rad"):
            self.assertEqual(value_problem(text), "", text)
        for text in ("6", "", "six in", "3 furlongs", "x deg"):
            self.assertIn("is not a value with a unit", value_problem(text))

    def test_letter_problem(self) -> None:
        """Bad shapes, kept names, repeats and case clashes."""
        letters: list[Letter] = [
            Letter(name)
            for name in ("W", "T1", "w", "W", "in", "1A", "ABCD", "OAL", "sin")
        ]
        self.assertEqual(letter_problem(letters, 0), "")
        self.assertEqual(letter_problem(letters, 1), "")
        self.assertIn("only in case", letter_problem(letters, 2))
        self.assertIn("used twice", letter_problem(letters, 3))
        self.assertIn("kept by SolidCraft", letter_problem(letters, 4))
        self.assertIn("a letter first", letter_problem(letters, 5))
        self.assertIn("a letter first", letter_problem(letters, 6))
        self.assertEqual(letter_problem(letters, 7), "")
        self.assertIn("a function", letter_problem(letters, 8))

    def test_next_letter(self) -> None:
        """The first free letter, in the last length's unit."""
        self.assertEqual(next_letter([]), Letter("A", default="1 in"))
        letters: list[Letter] = [
            Letter("A", default="20 mm"),
            Letter("b", default="59 deg"),
        ]
        self.assertEqual(next_letter(letters), Letter("C", default="1 mm"))
        letters = [Letter(chr(code)) for code in range(65, 91)]
        self.assertEqual(next_letter(letters).letter, "A1")


if __name__ == "__main__":
    unittest.main()
