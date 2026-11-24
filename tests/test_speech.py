"""Tests for `scraftcam.speech`: words handed to steps (no microphone
or model is needed)."""

import unittest

from scraftcam.speech import Word, split


def words(*pairs: tuple[float, str]) -> list[Word]:
    """Make words from (start, text) pairs."""
    return [Word(start, text) for start, text in pairs]


class TestSplit(unittest.TestCase):
    """Each step gets the words since the gesture before it."""

    def test_said_before_done(self) -> None:
        """Words before a gesture go to it; after the last, to it."""
        spoken: list[Word] = words(
            (0.2, " Now"),
            (0.5, " choose"),
            (0.9, " a corner."),
            (2.1, " Then"),
            (2.4, " drag"),
            (2.7, " it."),
            (5.0, " Done."),
        )
        self.assertEqual(
            split(spoken, [1.5, 3.0]),
            ["Now choose a corner.", "Then drag it. Done."],
        )

    def test_untimed_and_silent(self) -> None:
        """A step only to read takes nothing; a quiet one gets ""."""
        spoken: list[Word] = words((0.5, " one"), (4.0, " two"))
        self.assertEqual(
            split(spoken, [1.0, -1.0, 2.0, 3.0]), ["one", "", "", "two"]
        )
        self.assertEqual(split([], [1.0]), [""])
        self.assertEqual(split(spoken, []), [])

    def test_wrapped(self) -> None:
        """Long talk is wrapped to 68 columns."""
        spoken: list[Word] = [Word(0.1 * i, " word") for i in range(30)]
        text: str = split(spoken, [9.0])[0]
        self.assertTrue(all(len(line) <= 68 for line in text.splitlines()))
        self.assertEqual(text.split(), ["word"] * 30)


if __name__ == "__main__":
    unittest.main()
