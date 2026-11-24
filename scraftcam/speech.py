"""Speech for recordings: the microphone and Whisper (`T.mi~7` #521).

While a recording is made, `Microphone` captures the default
PipeWire source with `pw-record` (16 kHz mono, as Whisper wants;
Linux only, #533).  Afterwards `transcribe()` gives the words with
their times, read by a local Whisper model (nothing leaves the
computer), and `split()` hands each step the words spoken since the
gesture before it: people say what they are about to do, then do it.
The person then edits the text (#520).
"""

from __future__ import annotations

import re
import shutil
import signal
import subprocess
import textwrap
import wave
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# The model, and where models are kept (#531).
MODEL: str = "base.en"
MODELS: Path = Path.home() / ".scraftcam" / "models"

# The sound Whisper takes.
RATE: int = 16000


@dataclass(frozen=True, slots=True)
class Word:
    """One spoken word.

    Constructor:
    * `Word(start, text)`

    Attributes:
    * `start` (`float`):
        When it was said, in seconds from the start of recording.
    * `text` (`str`):
        The word, with its punctuation.
    """

    # Constructor arguments:
    start: float = field(init=True)
    text: str = field(init=True)


def split(words: Sequence[Word], times: Sequence[float]) -> list[str]:
    """Hand each step the words spoken since the step before it.

    Arguments:
    * `words` (`Sequence[Word]`):
        The words, in order.
    * `times` (`Sequence[float]`):
        When each step's gesture began, in order; a step with no
        time (-1, one only to read) takes nothing.

    Returns:
    * (`list[str]`): each step's words, wrapped to 68 columns (as
      its bullet's lines); words after the last step go to it.
    """
    # Each word goes to the first step whose time is after it.
    found: list[list[str]] = [[] for _ in times]
    timed: list[int] = [index for index, when in enumerate(times) if when >= 0]
    word: Word
    for word in words:
        index: int
        chosen: int = timed[-1] if timed else -1
        for index in timed:
            if word.start < times[index]:
                chosen = index
                break
        if chosen >= 0:
            found[chosen].append(word.text.strip())
    texts: list[str] = []
    pieces: list[str]
    for pieces in found:
        text: str = re.sub(r"\s+", " ", " ".join(pieces)).strip()
        texts.append("\n".join(textwrap.wrap(text, 68)))
    return texts


def gain_problems() -> list[str]:
    """Name each sound card whose automatic gain control is off.

    The user's USB boom microphone gives speech buried in hiss
    without it (#536), and the setting may not survive a replug or
    a reboot (#537).

    Returns:
    * (`list[str]`): one warning per card with the control off, with
      the command that turns it on; empty when all is well, or when
      `amixer` is missing.
    """
    # Every card that has the control.
    if shutil.which("amixer") is None:
        return []
    cards: Path = Path("/proc/asound/cards")
    numbers: list[str] = (
        re.findall(
            r"^\s*(\d+)\s", cards.read_text(encoding="utf-8"), re.MULTILINE
        )
        if cards.exists()
        else []
    )
    found: list[str] = []
    number: str
    for number in numbers:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            ["amixer", "-c", number, "get", "Auto Gain Control"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and "[off]" in completed.stdout:
            found.append(
                f"card {number}: automatic gain control is off; turn it "
                f"on with: amixer -c {number} set 'Auto Gain Control' on"
            )
    return found


class Microphone:  # pylint: disable=too-few-public-methods
    """The default PipeWire source, recorded to a `.wav`.

    Attributes:
    * `path` (`Path`):
        The `.wav` written.
    * `process` (`subprocess.Popen[bytes] | None`):
        `pw-record`, while it runs.
    """

    def __init__(self, path: Path) -> None:
        """Start recording into `path`.

        Arguments:
        * `path` (`Path`):
            The `.wav` to write.

        Raises:
        * `OSError`: when `pw-record` is missing or cannot start.
        """
        # 16 kHz, mono, 16 bits: what Whisper takes.
        program: str | None = shutil.which("pw-record")
        if program is None:
            raise OSError("`pw-record` (PipeWire) is not installed")
        self.path: Path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        # It runs until `stop()`, so no `with`.
        self.process: subprocess.Popen[bytes] | None = subprocess.Popen(  # pylint: disable=consider-using-with
            [
                program,
                "--rate",
                str(RATE),
                "--channels",
                "1",
                "--format",
                "s16",
                str(path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        """Stop recording, leaving a finished `.wav`."""
        # An interrupt lets `pw-record` finish the file's header.
        if self.process is not None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None


def transcribe(path: Path) -> list[Word]:
    """Read the words spoken in a `.wav`, with their times.

    Arguments:
    * `path` (`Path`):
        A 16 kHz mono 16 bit `.wav` (as `Microphone` writes).

    Returns:
    * (`list[Word]`): the words, in order.
    """
    # Fetched the first time (#531): the package, then the model.
    from scraftcam.packages import require  # pylint: disable=import-outside-toplevel

    require("faster_whisper")
    # pylint: disable=import-outside-toplevel,import-error
    # They live in `~/.scraftcam/packages/`, out of `mypy`'s sight.
    import numpy  # type: ignore[import-not-found]
    from faster_whisper import (  # type: ignore[import-not-found]
        WhisperModel,
    )

    # The samples read here: its own reader (PyAV) fails (#538).
    with wave.open(str(path)) as sound:
        frames: bytes = sound.readframes(sound.getnframes())
    audio: numpy.ndarray = (
        numpy.frombuffer(frames, dtype=numpy.int16).astype(numpy.float32)
        / 32768
    )
    model: WhisperModel = WhisperModel(
        MODEL, device="cpu", compute_type="int8", download_root=str(MODELS)
    )
    # Not conditioned on its own earlier text, which can loop on
    # repetitive talk ("testing, one, two, ..."), retrying at random.
    segments, _info = model.transcribe(
        audio,
        word_timestamps=True,
        language="en",
        condition_on_previous_text=False,
    )
    return [
        Word(float(word.start), str(word.word))
        for segment in segments
        for word in (segment.words or [])
    ]
