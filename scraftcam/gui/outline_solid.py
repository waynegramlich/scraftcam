"""An outline in SolidCraft (`T.prg~5.1.9.2` #108), no Qt.

A revolved outline file (`outline_file.py`) is built in SolidCraft:
each letter becomes a SolidCraft parameter with its default, and each
corner is sketched as its formula in the letters (`dimensions.solve()`),
so a changed parameter rebuilds the solid in milliseconds.

A tip on the axis (a corner at X = 0 between an edge on the axis and a
slanted one) revolves into an ill-defined point (#106), so it is cut
flat when built: the corner becomes two, `TIP_FLAT` of the way along
the slanted edge and on the axis at that height, leaving a small flat
circle, as `tooling/cutter_models.py`'s `COUNTERSINK_TIP_FLAT` does.
The file keeps the true, sharp outline.

Run alone: `python3 -m scraftcam.gui.outline_solid FILE (PORT |
headless)`.
"""

import sys
from pathlib import Path

from ..model import Length
from ..pybind.scraftpybind import JSON, PyBind, connect
from .dimensions import Formula, Solution, solve
from .letters import ANGLE_UNITS, Letter
from .outline_file import Outline, outline_from_text

# The share of a tip's slanted edge cut off (#106, #111).
TIP_FLAT: float = 0.05

# A coordinate on the axis, as sent.
ZERO: str = "0 mm"


# Function `corner_expressions()`:
def corner_expressions(outline: Outline) -> list[tuple[str, str]]:
    """Return each corner as SolidCraft expressions in the letters.

    Arguments:
    * `outline` (`Outline`): The outline.

    Returns:
    * (`list[tuple[str, str]]`): Each corner's X and Y.

    Raises:
    * `ValueError`: When a corner is not dimensioned yet.
    """
    solution: Solution = solve(outline.points, outline.dimensions)
    missing: list[tuple[int, str]] = solution.missing(len(outline.points))
    if missing:
        floating: str = ", ".join(
            f"corner {corner} {axis}" for corner, axis in missing
        )
        raise ValueError(f"Not dimensioned yet: {floating}.")
    return [
        (_expression(solution.x[corner]), _expression(solution.y[corner]))
        for corner in range(len(outline.points))
    ]


# Function `flatten_tips()`:
def flatten_tips(corners: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Cut each tip on the axis flat (#106).

    A corner at X = 0 between an edge on the axis and a slanted one
    becomes two: `TIP_FLAT` along the slanted edge, and on the axis at
    the same height.  A corner beside a level edge is no tip.

    Arguments:
    * `corners` (`list[tuple[str, str]]`): Each corner's X and Y.

    Returns:
    * (`list[tuple[str, str]]`): The corners, tips cut.
    """
    flat: list[tuple[str, str]] = []
    index: int
    x: str
    y: str
    for index, (x, y) in enumerate(corners):
        before: tuple[str, str] = corners[index - 1]
        after: tuple[str, str] = corners[(index + 1) % len(corners)]
        other: tuple[str, str] = after if before[0] == ZERO else before
        if (
            x != ZERO
            or (before[0] == ZERO) == (after[0] == ZERO)
            or other[1] == y
        ):
            flat.append((x, y))
            continue
        height: str = f"({y} + {TIP_FLAT} * (({other[1]}) - ({y})))"
        pair: list[tuple[str, str]] = [
            (ZERO, height),
            (f"({TIP_FLAT} * ({other[0]}))", height),
        ]
        flat += pair if before[0] == ZERO else pair[::-1]
    return flat


# Function `letter_value()`:
def letter_value(text: str) -> str:
    """Return a letter's default as SolidCraft takes it.

    Arguments:
    * `text` (`str`): The default (`1/8 in`, `59 deg`).

    Returns:
    * (`str`): An expression (`(1/8) in`), lengths by
      `Length.solidcraft()` so mixed numbers are read right.
    """
    if text.split()[-1] in ANGLE_UNITS:
        return text
    return Length.parse(text).solidcraft()


# Function `build()`:
def build(solidcraft: PyBind, outline: Outline, name: str) -> str:
    """Build a revolved outline: its letters as parameters, its
    corners as their formulas, its profile on the XZ plane revolved
    about Z (the drawing's Y).

    Arguments:
    * `solidcraft` (`PyBind`): The SolidCraft session.
    * `outline` (`Outline`): A revolved outline.
    * `name` (`str`): The body's name.

    Returns:
    * (`str`): The body's name, as SolidCraft gave it.

    Raises:
    * `ValueError`: When the outline is not revolved, or not fully
      dimensioned.
    """
    if not outline.revolve:
        raise ValueError("Only revolved outlines are built so far.")
    corners: list[tuple[str, str]] = flatten_tips(corner_expressions(outline))
    letter: Letter
    for letter in outline.letters:
        solidcraft.parameters.add(
            name=letter.letter, expression=letter_value(letter.default)
        )
    solidcraft.sketch.create(
        plane={
            "origin": [0.0, 0.0, 0.0],
            "x_dir": [1.0, 0.0, 0.0],
            "y_dir": [0.0, 0.0, 1.0],
        },
        name=f"{name} profile",
    )
    drawn: JSON = solidcraft.sketch.line(
        points=[[x, y] for x, y in corners], closed=True
    )
    solidcraft.sketch.finish()
    assert isinstance(drawn, dict)
    made: JSON = solidcraft.solid.revolve(
        axis={"origin": [0.0, 0.0, 0.0], "dir": [0.0, 0.0, 1.0]},
        profiles=[{"curves": drawn["curves"]}],
        body_name=name,
    )
    assert isinstance(made, dict)
    bodies: JSON = made["created_bodies"]
    assert isinstance(bodies, list) and isinstance(bodies[0], str)
    return bodies[0]


# Function `_expression()`:
def _expression(formula: Formula) -> str:
    """Return a coordinate's formula as an expression (`0` as `ZERO`,
    since a bare number in a sum of lengths is ambiguous).

    Arguments:
    * `formula` (`Formula`): The formula.

    Returns:
    * (`str`): The expression.
    """
    text: str = str(formula)
    return ZERO if text == "0" else f"({text})"


# Function `main()`:
def main() -> None:
    """Build the outline file named on the command line in a
    SolidCraft (a control port, or `headless`)."""
    path: Path = Path(sys.argv[1])
    outline: Outline = outline_from_text(
        path.read_text(encoding="utf-8"), str(path)
    )
    with connect(sys.argv[2]) as transport:
        solidcraft: PyBind = PyBind(transport)
        solidcraft.file.new()
        print(build(solidcraft, outline, path.name.split(".")[0]))


if __name__ == "__main__":
    main()
