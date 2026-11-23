"""Real sizes of an outline (`T.oe~6.2` #127), no Qt.

The drawing is in unitless steps; its real sizes come from the letters'
defaults.  Here the corners' formulas (`dimensions.solve()`) are worked
out with those values, in millimeters and radians, so that checks can
be made on the real outline, such as fillets too big for their edges:
SolidCraft takes those silently, leaving the solid as first built
(`T.sdfm~2.5.2.1`'s experiments).

Expressions are read by `ast`, allowing only numbers, the letters,
`+ - * / ^`, `deg`, `mm` and SolidCraft's functions used in formulas.
"""

import ast
import math
import re
from collections.abc import Callable

from ..model import MM_PER, Angle, Length
from .dimensions import ANGLE, RADIUS, Dimension, Solution, solve
from .letters import ANGLE_UNITS, Letter, use_problem, value_problem

# The functions a formula may use, and the units it may name.
FUNCTIONS: dict[str, Callable[..., float]] = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "abs": abs,
}
UNITS: dict[str, float] = {"deg": math.pi / 180.0, "mm": 1.0}

# A number written before a unit (`90 deg`) is a product.
NUMBER_UNIT: re.Pattern[str] = re.compile(r"(\d)\s+(deg|mm)\b")

# Fillets may use up an edge, within this much (mm, #114).
FIT_SLACK: float = 1e-9


# Function `letter_values()`:
def letter_values(letters: list[Letter]) -> dict[str, float]:
    """Return each good letter's value: millimeters, or radians.

    Arguments:
    * `letters` (`list[Letter]`): The letters.

    Returns:
    * (`dict[str, float]`): By letter; bad values left out.
    """
    # The letters given values first, as the formulas use only those.
    values: dict[str, float] = {}
    letter: Letter
    for letter in letters:
        if letter.formula or value_problem(letter.default):
            continue
        if letter.default.split()[-1] in ANGLE_UNITS:
            values[letter.letter] = math.radians(
                float(Angle.parse(letter.default).degrees)
            )
        else:
            values[letter.letter] = Length.parse(letter.default).mm()

    # Then the formula letters, worked out exactly (not from the text
    # of their `default`, which is rounded).
    given: dict[str, float] = dict(values)
    for letter in letters:
        if letter.formula and not _formula_problem(letter, letters):
            values[letter.letter] = evaluate(letter.formula, given)
    return values


# Function `formula_names()`:
def formula_names(formula: str) -> list[str]:
    """Return the letters a formula names, in order, each once.

    Arguments:
    * `formula` (`str`): The formula (`PA / 2`).

    Returns:
    * (`list[str]`): The names that are not functions or units; empty
      when the formula cannot be read.
    """
    text: str = NUMBER_UNIT.sub(r"\1 * \2", formula).replace("^", "**")
    try:
        tree: ast.Expression = ast.parse(text, mode="eval")
    except SyntaxError:
        return []
    names: list[str] = []
    node: ast.AST
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id not in FUNCTIONS
            and node.id not in UNITS
            and node.id not in names
        ):
            names.append(node.id)
    return names


# Function `formula_problem()`:
def formula_problem(letters: list[Letter], index: int) -> str:
    """Return what is wrong with one letter's formula ("" if nothing,
    or if it has none).

    Arguments:
    * `letters` (`list[Letter]`): All of the outline's letters.
    * `index` (`int`): The one to check.

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    return _formula_problem(letters[index], letters)


# Function `_formula_problem()`:
def _formula_problem(letter: Letter, letters: list[Letter]) -> str:
    """Return what is wrong with a letter's formula ("" if nothing).

    A formula may name only letters given values, never another formula
    letter, so that there are no loops and the order does not matter.

    Arguments:
    * `letter` (`Letter`): The letter.
    * `letters` (`list[Letter]`): All of the outline's letters.

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    # No formula: nothing to check.
    if not letter.formula:
        return ""

    # Each name must be a letter given a good value.
    named: str = _names_problem(letter, letters)
    if named:
        return named

    # And it must work out.
    given: dict[str, float] = letter_values(
        [each for each in letters if not each.formula]
    )
    try:
        evaluate(letter.formula, given)
    except ValueError as error:
        return f"{letter.letter} = {letter.formula}: {error}"
    return ""


# Function `_names_problem()`:
def _names_problem(letter: Letter, letters: list[Letter]) -> str:
    """Return what is wrong with the letters a formula names ("" if
    nothing): each must be a letter given a good value.

    Arguments:
    * `letter` (`Letter`): The formula letter.
    * `letters` (`list[Letter]`): All of the outline's letters.

    Returns:
    * (`str`): The problem, as the user should read it.
    """
    by_name: dict[str, Letter] = {each.letter: each for each in letters}
    names: list[str] = formula_names(letter.formula)
    head: str = f"{letter.letter} = {letter.formula}"
    if not names:
        return f"{head}: names no letter."
    name: str
    for name in names:
        other: Letter | None = by_name.get(name)
        if other is None:
            return f"{head}: no letter {name}."
        if other.formula:
            return (
                f"{head}: {name} is a formula letter too; name only "
                "letters given values."
            )
        if value_problem(other.default):
            return f"{head}: {name} is bad."
    return ""


# Function `refresh_formulas()`:
def refresh_formulas(letters: list[Letter]) -> None:
    """Set each formula letter's `default` to its worked out value.

    An angle when every letter it names is an angle (in `deg`), else a
    length in the unit of the first length letter it names; "" when
    the formula has a problem (`formula_problem()`).

    Arguments:
    * `letters` (`list[Letter]`): The outline's letters, changed in
      place.
    """
    values: dict[str, float] = letter_values(letters)
    by_name: dict[str, Letter] = {each.letter: each for each in letters}
    letter: Letter
    for letter in letters:
        if not letter.formula:
            continue
        if letter.letter not in values or _formula_problem(letter, letters):
            letter.default = ""
            continue
        units: list[str] = [
            by_name[name].default.split()[-1]
            for name in formula_names(letter.formula)
        ]
        lengths: list[str] = [
            unit for unit in units if unit not in ANGLE_UNITS
        ]
        value: float = values[letter.letter]
        letter.default = (
            f"{value / float(MM_PER[lengths[0]]):.6g} {lengths[0]}"
            if lengths
            else f"{math.degrees(value):.6g} deg"
        )


# Function `evaluate()`:
def evaluate(expression: str, values: dict[str, float]) -> float:
    """Work out a formula.

    Arguments:
    * `expression` (`str`): A formula (`0 + (R) * tan(90 deg - A)`).
    * `values` (`dict[str, float]`): The letters' values.

    Returns:
    * (`float`): Its value, in millimeters or radians.

    Raises:
    * `ValueError`: When it names something unknown, or cannot be
      worked out.
    """
    text: str = NUMBER_UNIT.sub(r"\1 * \2", expression).replace("^", "**")
    try:
        tree: ast.Expression = ast.parse(text, mode="eval")
        return float(_value(tree.body, values))
    except (SyntaxError, ZeroDivisionError, OverflowError) as error:
        raise ValueError(f"{expression!r}: {error}") from error


# Function `_value()`:
def _value(node: ast.AST, values: dict[str, float]) -> float:
    """Work out one node of a formula.

    Arguments:
    * `node` (`ast.AST`): The node.
    * `values` (`dict[str, float]`): The letters' values.

    Returns:
    * (`float`): Its value.

    Raises:
    * `ValueError`: For anything not allowed.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.Name):
        return _name(node.id, values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_value(node.operand, values)
    if isinstance(node, ast.BinOp):
        left: float = _value(node.left, values)
        right: float = _value(node.right, values)
        operations: dict[type, Callable[[float, float], float]] = {
            ast.Add: float.__add__,
            ast.Sub: float.__sub__,
            ast.Mult: float.__mul__,
            ast.Div: float.__truediv__,
            ast.Pow: float.__pow__,
        }
        if type(node.op) in operations:
            return operations[type(node.op)](left, right)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FUNCTIONS
        and len(node.args) == 1
    ):
        return float(FUNCTIONS[node.func.id](_value(node.args[0], values)))
    raise ValueError(f"{ast.unparse(node)!r} is not allowed")


# Function `_name()`:
def _name(name: str, values: dict[str, float]) -> float:
    """Return a name's value: a letter, a unit or `pi`.

    Arguments:
    * `name` (`str`): The name.
    * `values` (`dict[str, float]`): The letters' values.

    Returns:
    * (`float`): Its value.

    Raises:
    * `ValueError`: For a name with no value.
    """
    known: dict[str, float] = {**UNITS, "pi": math.pi, **values}
    if name not in known:
        raise ValueError(f"{name} has no value")
    return known[name]


# Function `real_corners()`:
def real_corners(
    points: list[tuple[float, float]],
    letters: list[Letter],
    dimensions: list[Dimension],
) -> list[tuple[float, float]] | None:
    """Return the corners at their real places (mm), from the letters.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `letters` (`list[Letter]`): The letters.
    * `dimensions` (`list[Dimension]`): The dimensions.

    Returns:
    * (`list[tuple[float, float]] | None`): The corners; `None` while a
      corner is not dimensioned or a value is bad.
    """
    solution: Solution = solve(points, dimensions)
    if solution.missing(len(points)):
        return None
    values: dict[str, float] = letter_values(letters)
    try:
        return [
            (
                evaluate(str(solution.x[corner]), values),
                evaluate(str(solution.y[corner]), values),
            )
            for corner in range(len(points))
        ]
    except ValueError:
        return None


# Function `fillet_problems()`:
def fillet_problems(
    points: list[tuple[float, float]],
    letters: list[Letter],
    dimensions: list[Dimension],
) -> dict[int, str]:
    """Return each fillet too big for an edge, with what is wrong in
    the fillet letter's unit (#127).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `letters` (`list[Letter]`): The letters.
    * `dimensions` (`list[Dimension]`): The dimensions.

    Returns:
    * (`dict[int, str]`): By corner, the problem; empty while the real
      corners cannot be worked out.
    """
    real: list[tuple[float, float]] | None = real_corners(
        points, letters, dimensions
    )
    if real is None:
        return {}
    fillets: dict[int, str]
    reach: dict[int, float]
    fillets, reach = _fillets(real, letters, dimensions)
    units: dict[str, str] = {
        letter.letter: letter.default.split()[-1] for letter in letters
    }
    problems: dict[int, str] = {}
    corner: int
    here: tuple[float, float]
    for corner, here in enumerate(real):
        after: int = (corner + 1) % len(real)
        need: float = reach.get(corner, 0.0) + reach.get(after, 0.0)
        edge: float = math.dist(here, real[after])
        if need <= edge + FIT_SLACK:
            continue
        ends: list[int] = [end for end in (corner, after) if end in fillets]
        end: int
        for end in ends:
            problems.setdefault(
                end,
                _too_big([fillets[one] for one in ends], need, edge, units),
            )
    return problems


# Function `_fillets()`:
def _fillets(
    real: list[tuple[float, float]],
    letters: list[Letter],
    dimensions: list[Dimension],
) -> tuple[dict[int, str], dict[int, float]]:
    """Return each fillet's letter, and how far from its corner it
    meets its edges.

    Arguments:
    * `real` (`list[tuple[float, float]]`): The real corners (mm).
    * `letters` (`list[Letter]`): The letters.
    * `dimensions` (`list[Dimension]`): The dimensions.

    Returns:
    * (`tuple[dict[int, str], dict[int, float]]`): By corner, its
      letter, and its reach (mm); fillets with a bad value left out.
    """
    values: dict[str, float] = letter_values(letters)
    fillets: dict[int, str] = {
        dimension.start: dimension.letter
        for dimension in dimensions
        if dimension.kind == RADIUS and dimension.letter in values
    }
    return fillets, {
        corner: _reach(real, corner, values[letter])
        for corner, letter in fillets.items()
    }


# Function `_too_big()`:
def _too_big(
    names: list[str], need: float, edge: float, units: dict[str, str]
) -> str:
    """Return what is wrong, in the first fillet letter's unit.

    Arguments:
    * `names` (`list[str]`): The fillets' letters.
    * `need` (`float`): How much of the edge they need (mm).
    * `edge` (`float`): The edge's length (mm).
    * `units` (`dict[str, str]`): Each letter's unit.

    Returns:
    * (`str`): The message.
    """
    unit: str = units.get(names[0], "mm")
    return (
        f"{' and '.join(names)} need {Length.from_mm(need, unit)} "
        f"of a {Length.from_mm(edge, unit)} edge."
    )


# Function `_reach()`:
def _reach(
    real: list[tuple[float, float]], corner: int, radius: float
) -> float:
    """Return how far from its corner a fillet meets its edges.

    Arguments:
    * `real` (`list[tuple[float, float]]`): The real corners (mm).
    * `corner` (`int`): The rounded corner.
    * `radius` (`float`): Its radius (mm).

    Returns:
    * (`float`): The distance (mm); 0 for a straight corner.
    """
    here: tuple[float, float] = real[corner]
    back: tuple[float, float] = real[corner - 1]
    ahead: tuple[float, float] = real[(corner + 1) % len(real)]
    first: float = math.atan2(back[1] - here[1], back[0] - here[0])
    second: float = math.atan2(ahead[1] - here[1], ahead[0] - here[0])
    half: float = abs((second - first + math.pi) % (2 * math.pi) - math.pi) / 2
    if half <= 1e-12 or half >= math.pi / 2 - 1e-12:
        return 0.0
    return radius / math.tan(half)


# Function `real_coordinates()`:
def real_coordinates(
    points: list[tuple[float, float]],
    letters: list[Letter],
    dimensions: list[Dimension],
) -> tuple[dict[int, float], dict[int, float]] | None:
    """Return each coordinate the dimensions fix, at its real place
    (mm), corners not fully fixed included (#153).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `letters` (`list[Letter]`): The letters.
    * `dimensions` (`list[Dimension]`): The dimensions.

    Returns:
    * (`tuple[dict[int, float], dict[int, float]] | None`): X and Y
      by corner; `None` when a formula cannot be worked out (#154).
    """
    solution: Solution = solve(points, dimensions)
    values: dict[str, float] = letter_values(letters)
    try:
        return (
            {
                corner: evaluate(str(formula), values)
                for corner, formula in solution.x.items()
            },
            {
                corner: evaluate(str(formula), values)
                for corner, formula in solution.y.items()
            },
        )
    except (ValueError, ArithmeticError):
        return None


# Function `first_scale()`:
def first_scale(
    points: list[tuple[float, float]],
    real: tuple[dict[int, float], dict[int, float]],
) -> float:
    """Return drawing steps per millimeter, chosen once (#148): the
    middle of the drawn-to-real ratios of the fixed coordinates.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `real` (`tuple[dict[int, float], dict[int, float]]`): The fixed
      coordinates' real values (mm).

    Returns:
    * (`float`): The scale; 0 when nothing says.
    """
    # Each fixed coordinate's drawn over real value, when positive.
    ratios: list[float] = sorted(
        points[corner][axis] / value
        for axis in (0, 1)
        for corner, value in real[axis].items()
        if abs(value) > 1e-9 and points[corner][axis] / value > 0.0
    )
    return ratios[len(ratios) // 2] if ratios else 0.0


# Function `letters_bad()`:
def letters_bad(letters: list[Letter], dimensions: list[Dimension]) -> bool:
    """Return whether a letter a dimension uses has a bad value (red
    in the editor's table): the drawing then keeps its shape (#154).

    Arguments:
    * `letters` (`list[Letter]`): The letters.
    * `dimensions` (`list[Dimension]`): The dimensions.

    Returns:
    * (`bool`): Whether one has.
    """
    # A used letter whose value is bad, or the wrong kind for its use.
    letter: Letter
    for letter in letters:
        kinds: set[str] = {
            "angle" if dimension.kind == ANGLE else "length"
            for dimension in dimensions
            if dimension.letter == letter.letter
        }
        if kinds and (
            value_problem(letter.default)
            or use_problem(letter.letter, letter.default, kinds)
        ):
            return True
    return False


# Function `placed_corners()`:
def placed_corners(
    points: list[tuple[float, float]],
    letters: list[Letter],
    dimensions: list[Dimension],
    scale: float = 0.0,
) -> tuple[list[tuple[float, float]], float]:
    """Return the corners where the letters' values put them, to scale
    (#148, #153, #299): a coordinate the dimensions do not fix stays
    as drawn.  Values that cannot be drawn (a bad letter, a formula
    failing, edges crossing) leave the corners as they were (#154).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `letters` (`list[Letter]`): The letters.
    * `dimensions` (`list[Dimension]`): The dimensions.
    * `scale` (`float`):
      Drawing steps per mm; 0 picks one (`first_scale()`).

    Returns:
    * (`tuple[list[tuple[float, float]], float]`): The corners (a new
      list) and the scale used (0 when none could be picked).
    """
    # Nothing to place without good values and fixed coordinates.
    if not dimensions or letters_bad(letters, dimensions):
        return list(points), scale
    real: tuple[dict[int, float], dict[int, float]] | None = real_coordinates(
        points, letters, dimensions
    )
    if real is None:
        return list(points), scale
    if scale <= 0.0:
        scale = first_scale(points, real)
        if scale <= 0.0:
            return list(points), scale

    # Each fixed coordinate to scale, unless the edges would cross.
    placed: list[tuple[float, float]] = _to_scale(points, real, scale)
    if crosses(placed):
        return list(points), scale
    return placed, scale


# Function `values_cross()`:
def values_cross(
    points: list[tuple[float, float]],
    letters: list[Letter],
    dimensions: list[Dimension],
) -> list[tuple[int, int]]:
    """Return the edges that cross when the letters' values place the
    corners (#457): a template is drawn as drawn, so its defaults are
    checked here instead of by moving its corners.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `letters` (`list[Letter]`): The letters.
    * `dimensions` (`list[Dimension]`): The dimensions.

    Returns:
    * (`list[tuple[int, int]]`): Each pair of edges that cross (none
      when the values cannot place the corners at all).
    """
    # Nothing to check without good values and fixed coordinates.
    if not dimensions or letters_bad(letters, dimensions):
        return []
    real: tuple[dict[int, float], dict[int, float]] | None = real_coordinates(
        points, letters, dimensions
    )
    if real is None:
        return []
    scale: float = first_scale(points, real)
    if scale <= 0.0:
        return []
    return crossings(_to_scale(points, real, scale))


# Function `_to_scale()`:
def _to_scale(
    points: list[tuple[float, float]],
    real: tuple[dict[int, float], dict[int, float]],
    scale: float,
) -> list[tuple[float, float]]:
    """Return the corners with each fixed coordinate at its value.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners as drawn.
    * `real` (`tuple[dict[int, float], dict[int, float]]`):
      The fixed X and Y of each corner, in mm.
    * `scale` (`float`): Drawing steps per mm.

    Returns:
    * (`list[tuple[float, float]]`): The corners (a new list).
    """
    return [
        (
            real[0][corner] * scale if corner in real[0] else x,
            real[1][corner] * scale if corner in real[1] else y,
        )
        for corner, (x, y) in enumerate(points)
    ]


# Function `crosses()`:
def crosses(points: list[tuple[float, float]]) -> bool:
    """Return whether an outline's edges cross (not at shared corners).

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.

    Returns:
    * (`bool`): Whether two edges not side by side cross.
    """
    return bool(crossings(points))


# Function `crossings()`:
def crossings(points: list[tuple[float, float]]) -> list[tuple[int, int]]:
    """Return each pair of edges that cross (#242), not counting side
    by side ones meeting at their shared corner.

    Arguments:
    * `points` (`list[tuple[float, float]]`): The corners.

    Returns:
    * (`list[tuple[int, int]]`): The pairs, each edge by the corner it
      leaves, the lower first.
    """
    count: int = len(points)
    pairs: list[tuple[int, int]] = []
    first: int
    for first in range(count):
        second: int
        for second in range(first + 2, count):
            if first == 0 and second == count - 1:
                continue  # Side by side, around the end.
            if _segments_cross(
                points[first],
                points[(first + 1) % count],
                points[second],
                points[(second + 1) % count],
            ):
                pairs.append((first, second))
    return pairs


# Function `_segments_cross()`:
def _segments_cross(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    """Return whether segment AB properly crosses segment CD.

    Arguments:
    * `a` (`tuple[float, float]`): One end of the first.
    * `b` (`tuple[float, float]`): Its other end.
    * `c` (`tuple[float, float]`): One end of the second.
    * `d` (`tuple[float, float]`): Its other end.

    Returns:
    * (`bool`): Whether each straddles the other's line.
    """

    # Function `side()`:
    def side(
        p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]
    ) -> float:
        """Return which side of PQ the point R is (+ left)."""
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    return (
        side(a, b, c) * side(a, b, d) < 0 and side(c, d, a) * side(c, d, b) < 0
    )
