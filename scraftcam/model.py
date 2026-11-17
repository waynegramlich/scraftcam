"""The values that parametric models are built from (`T.cmt~5.3`).

* `Length`: a length kept exactly as written (a `Fraction`) in its
  own unit (`in`, `ft`, `mm`, `m`), so `3-7/8 in` never reads
  `3.1999999`.  Inches and millimeters convert exactly (25.4 =
  127/5).
* `Angle`: an angle in degrees, also a `Fraction`.  Radians are taken
  too, converted to degrees with `RADIAN_DIGITS` decimals.
* `Rotation`: a unit quaternion inside, given as an axis and an
  angle, or as "point this axis that way".  Rotations are composed as
  quaternions; a matrix is made from one only at the very end, as
  multiplying many matrices lets errors pile up.
* `Placement`: a rotation then a translation, composed down a tree of
  models, made into the 3x4 matrix that SolidCraft's
  `occurrence.move(matrix=...)` takes.

* `SolidModel`: the base class of parametric models.  Parameters
  are `init=True` fields, described by `meta()`; results are
  `init=False` fields, computed by `update()`.  `settle()` repeats
  `update()` until no result moves, within a wall clock limit.

The SolidCraft link (`SolidCraftLink`) comes later.
"""

import math
import re
import time
from collections.abc import Iterator
from dataclasses import Field, dataclass, field, fields
from fractions import Fraction
from typing import Any, ClassVar

# A point or direction: `(x, y, z)`, in millimeters for points.
Vector = tuple[float, float, float]

# A 3x4 matrix, row by row: a rotation with the translation on the
# right, as SolidCraft's `occurrence.move(matrix=...)` takes it.
Matrix = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]

# Millimeters per unit, exact.
MM_PER: dict[str, Fraction] = {
    "in": Fraction(127, 5),
    "ft": Fraction(1524, 5),
    "mm": Fraction(1),
    "m": Fraction(1000),
}

# The decimals kept when radians are converted to degrees (at least 6,
# the user's choice, 2026-11-16), and when a computed length is made
# exact again.
RADIAN_DIGITS: int = 9
LENGTH_DIGITS: int = 9

# A number as people write it: `3`, `-3.875`, `7/8`, `3-7/8`, `.5`.
NUMBER: re.Pattern[str] = re.compile(
    r"(?P<sign>[-+]?)\s*"
    r"(?:(?P<whole>\d+)(?:\s*-\s*|\s+)(?=\d+\s*/))?"
    r"(?P<number>\d*\.?\d+(?:\s*/\s*\d+)?)"
)

# The largest power of two denominator shown as a fraction (`1/64`).
FRACTION_DENOMINATOR: int = 64


# Function `parse_number()`:
def parse_number(text: str) -> Fraction:
    """Read a number as people write it, exactly.

    Arguments:
    * `text` (`str`):
      A whole number, a decimal, a fraction or a whole number and a
      fraction (`3`, `-3.875`, `7/8`, `3-7/8`, `3 7/8`).

    Returns:
    * (`Fraction`): Its exact value.

    Raises:
    * `ValueError`: If `text` is not such a number.
    """
    # The whole text must be one number.
    match: re.Match[str] | None = NUMBER.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"{text!r} is not a number")

    # Add the whole part and the fraction, then the sign.
    value: Fraction = Fraction(match["number"].replace(" ", ""))
    if match["whole"]:
        value += int(match["whole"])
    return -value if match["sign"] == "-" else value


# Function `number_text()`:
def number_text(number: Fraction | int, *, fractions: bool) -> str:
    """Write a number the way people would.

    Arguments:
    * `number` (`Fraction | int`): The number.
    * `fractions` (`bool`):
      Whether a power of two denominator up to `FRACTION_DENOMINATOR`
      is written as a fraction (`3-7/8`), as inches usually are.

    Returns:
    * (`str`): A whole number, a fraction, or a decimal (exact when it
      ends, otherwise rounded to `LENGTH_DIGITS` decimals).
    """
    # Whole numbers, and (for inches) fractions such as 3-7/8.
    value: Fraction = Fraction(number)
    denominator: int = value.denominator
    if denominator == 1:
        return str(value.numerator)
    sign: str = "-" if value < 0 else ""
    size: Fraction = abs(value)
    power_of_two: bool = denominator & (denominator - 1) == 0
    if fractions and power_of_two and denominator <= FRACTION_DENOMINATOR:
        whole: int = size.numerator // denominator
        part: Fraction = size - whole
        return f"{sign}{whole}-{part}" if whole else f"{sign}{part}"

    # A decimal: exact when only 2s and 5s divide the denominator.
    rest: int = denominator
    twos: int = 0
    fives: int = 0
    while rest % 2 == 0:
        rest //= 2
        twos += 1
    while rest % 5 == 0:
        rest //= 5
        fives += 1
    digits: int = max(twos, fives) if rest == 1 else LENGTH_DIGITS
    text: str = f"{float(size):.{digits}f}".rstrip("0").rstrip(".")
    return f"{sign}{text}"


# Class `Length`:
@dataclass(frozen=True, slots=True)
class Length:
    """A length, kept exactly in the unit it was written in.

    Arithmetic between two lengths gives the left one's unit; a length
    times or over a number keeps its unit.  Lengths compare by size,
    whatever their units.

    Attributes:
    * `value` (`Fraction | int`): The number, in `unit` (always a
      `Fraction` once made).
    * `unit` (`str`): One of `MM_PER`'s keys.

    Constructor:
    * `Length(value, unit)`
    """

    # Constructor arguments:
    value: Fraction | int = field()
    unit: str = field()

    def __post_init__(self) -> None:
        """Check the unit, and make the value a `Fraction`.

        Raises:
        * `ValueError`: If `unit` is unknown.
        """
        if self.unit not in MM_PER:
            raise ValueError(f"{self.unit=} is not one of {list(MM_PER)}")
        object.__setattr__(self, "value", Fraction(self.value))

    # Method `Length.parse()`:
    @staticmethod
    def parse(text: str) -> "Length":
        """Read a length such as `3-7/8 in` or `20 mm`.

        Arguments:
        * `text` (`str`): A number (see `parse_number()`) and a unit.

        Returns:
        * (`Length`): The length.

        Raises:
        * `ValueError`: If the unit is missing or unknown, or the
          number is not one.
        """
        # The unit is the last word.
        words: list[str] = text.strip().rsplit(maxsplit=1)
        if len(words) != 2 or words[1] not in MM_PER:
            raise ValueError(
                f"{text!r} does not end in a unit ({', '.join(MM_PER)})"
            )
        return Length(parse_number(words[0]), words[1])

    # Method `Length.from_mm()`:
    @staticmethod
    def from_mm(mm: float, unit: str = "mm") -> "Length":
        """Make a computed length exact again.

        Arguments:
        * `mm` (`float`): The length, in millimeters.
        * `unit` (`str`): The unit to give it.

        Returns:
        * (`Length`): The length, rounded to `LENGTH_DIGITS` decimals
          of `unit`.
        """
        value: float = mm / float(MM_PER[unit])
        return Length(Fraction(f"{value:.{LENGTH_DIGITS}f}"), unit)

    # Method `Length.mm()`:
    def mm(self) -> float:
        """Return the length in millimeters, as a float.

        Returns:
        * (`float`): The length in millimeters.
        """
        return float(self.value * MM_PER[self.unit])

    # Method `Length.to()`:
    def to(self, unit: str) -> "Length":
        """Return the same length in another unit, exactly.

        Arguments:
        * `unit` (`str`): One of `MM_PER`'s keys.

        Returns:
        * (`Length`): The length in `unit`.
        """
        exact: Fraction = self.value * MM_PER[self.unit]
        return Length(exact / MM_PER[unit], unit)

    # Method `Length.solidcraft()`:
    def solidcraft(self) -> str:
        """Return the length as a SolidCraft expression.

        SolidCraft reads `3-7/8 in` as 3 mm less 7/8 in, so a mixed
        fraction is sent as `(3 + 7/8) in`.

        Returns:
        * (`str`): An expression such as `(3 + 7/8) in` or `20 mm`.
        """
        value: Fraction = Fraction(self.value)
        if value.denominator == 1:
            return f"{value.numerator} {self.unit}"
        whole: int = int(value)
        part: Fraction = abs(value - whole)
        if whole == 0:
            return f"({value}) {self.unit}"
        sign: str = "-" if value < 0 else ""
        return f"{sign}({abs(whole)} + {part}) {self.unit}"

    def __str__(self) -> str:
        """Return the length as people write it (`3-7/8 in`)."""
        fractions: bool = self.unit in ("in", "ft")
        return f"{number_text(self.value, fractions=fractions)} {self.unit}"

    def __add__(self, other: "Length") -> "Length":
        """Return the sum, in this length's unit."""
        return Length(self.value + other.to(self.unit).value, self.unit)

    def __sub__(self, other: "Length") -> "Length":
        """Return the difference, in this length's unit."""
        return Length(self.value - other.to(self.unit).value, self.unit)

    def __neg__(self) -> "Length":
        """Return the length with its sign changed."""
        return Length(-self.value, self.unit)

    def __mul__(self, factor: int | Fraction) -> "Length":
        """Return the length times an exact number."""
        return Length(self.value * factor, self.unit)

    __rmul__ = __mul__

    def __truediv__(self, divisor: int | Fraction) -> "Length":
        """Return the length over an exact number."""
        return Length(Fraction(self.value) / divisor, self.unit)

    def _exact_mm(self) -> Fraction:
        """Return the length in millimeters, exactly."""
        return self.value * MM_PER[self.unit]

    def __eq__(self, other: object) -> bool:
        """Return whether both are the same size, whatever the units."""
        if not isinstance(other, Length):
            return NotImplemented
        return self._exact_mm() == other._exact_mm()

    def __hash__(self) -> int:
        """Return a hash that equal lengths share."""
        return hash(self._exact_mm())

    def __lt__(self, other: "Length") -> bool:
        """Return whether this length is the shorter."""
        return self._exact_mm() < other._exact_mm()

    def __le__(self, other: "Length") -> bool:
        """Return whether this length is not the longer."""
        return self._exact_mm() <= other._exact_mm()

    def __gt__(self, other: "Length") -> bool:
        """Return whether this length is the longer."""
        return self._exact_mm() > other._exact_mm()

    def __ge__(self, other: "Length") -> bool:
        """Return whether this length is not the shorter."""
        return self._exact_mm() >= other._exact_mm()


# Class `Angle`:
@dataclass(frozen=True, slots=True)
class Angle:
    """An angle, kept exactly in degrees.

    Attributes:
    * `degrees` (`Fraction | int`): The angle, in degrees (always a
      `Fraction` once made).

    Constructor:
    * `Angle(degrees)`
    """

    # Constructor arguments:
    degrees: Fraction | int = field()

    def __post_init__(self) -> None:
        """Make the value a `Fraction`."""
        object.__setattr__(self, "degrees", Fraction(self.degrees))

    # Method `Angle.parse()`:
    @staticmethod
    def parse(text: str) -> "Angle":
        """Read an angle such as `30`, `22.5 deg` or `0.5236 rad`.

        Arguments:
        * `text` (`str`):
          A number, then `deg` (the default when left out) or `rad`.

        Returns:
        * (`Angle`): The angle.

        Raises:
        * `ValueError`: If the unit is unknown or the number is not
          one.
        """
        # A bare number is in degrees.
        words: list[str] = text.strip().rsplit(maxsplit=1)
        if len(words) == 2 and words[1] in ("deg", "rad"):
            value: Fraction = parse_number(words[0])
            if words[1] == "rad":
                return Angle.from_radians(float(value))
            return Angle(value)
        return Angle(parse_number(text))

    # Method `Angle.from_radians()`:
    @staticmethod
    def from_radians(radians: float) -> "Angle":
        """Make an angle from radians.

        Arguments:
        * `radians` (`float`): The angle, in radians.

        Returns:
        * (`Angle`): The angle, in degrees rounded to `RADIAN_DIGITS`
          decimals.
        """
        degrees: float = math.degrees(radians)
        return Angle(Fraction(f"{degrees:.{RADIAN_DIGITS}f}"))

    # Method `Angle.radians()`:
    def radians(self) -> float:
        """Return the angle in radians.

        Returns:
        * (`float`): The angle, in radians.
        """
        return math.radians(float(self.degrees))

    def __str__(self) -> str:
        """Return the angle as people write it (`22.5 deg`)."""
        return f"{number_text(self.degrees, fractions=False)} deg"


# Function `_unit()`:
def _unit(vector: Vector) -> Vector:
    """Return a vector scaled to length 1.

    Arguments:
    * `vector` (`Vector`): A vector that is not zero.

    Returns:
    * (`Vector`): The same direction, of length 1.

    Raises:
    * `ValueError`: If `vector` is zero.
    """
    size: float = math.hypot(*vector)
    if size == 0.0:
        raise ValueError("a direction can not be (0, 0, 0)")
    return (vector[0] / size, vector[1] / size, vector[2] / size)


# Function `_cross()`:
def _cross(a: Vector, b: Vector) -> Vector:
    """Return the cross product `a x b`.

    Arguments:
    * `a` (`Vector`): The first vector.
    * `b` (`Vector`): The second vector.

    Returns:
    * (`Vector`): Their cross product.
    """
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


# Class `Rotation`:
@dataclass(frozen=True, slots=True)
class Rotation:
    """A rotation, kept as a unit quaternion `w + xi + yj + zk`.

    End users never see the quaternion: rotations are made with
    `about()` or `pointing()`.  `a * b` is `b` then `a`, as with
    matrices.  Every result is normalized again, so that a long chain
    of compositions stays a rotation.

    Attributes:
    * `w` (`float`): The scalar part.
    * `x` (`float`): The `i` part.
    * `y` (`float`): The `j` part.
    * `z` (`float`): The `k` part.

    Constructor:
    * `Rotation(w, x, y, z)`
    """

    # Constructor arguments:
    w: float = field(default=1.0)
    x: float = field(default=0.0)
    y: float = field(default=0.0)
    z: float = field(default=0.0)

    def __post_init__(self) -> None:
        """Normalize the quaternion.

        Raises:
        * `ValueError`: If it is zero.
        """
        size: float = math.sqrt(
            self.w * self.w
            + self.x * self.x
            + self.y * self.y
            + self.z * self.z
        )
        if size == 0.0:
            raise ValueError("a rotation can not be the zero quaternion")
        object.__setattr__(self, "w", self.w / size)
        object.__setattr__(self, "x", self.x / size)
        object.__setattr__(self, "y", self.y / size)
        object.__setattr__(self, "z", self.z / size)

    # Method `Rotation.about()`:
    @staticmethod
    def about(axis: Vector, angle: Angle) -> "Rotation":
        """Make a rotation by an angle about an axis (right hand rule).

        Arguments:
        * `axis` (`Vector`): The axis's direction (any length but 0).
        * `angle` (`Angle`): How far to turn.

        Returns:
        * (`Rotation`): The rotation.
        """
        # Half the angle, about the unit axis.
        direction: Vector = _unit(axis)
        half: float = angle.radians() / 2.0
        sine: float = math.sin(half)
        return Rotation(
            math.cos(half),
            direction[0] * sine,
            direction[1] * sine,
            direction[2] * sine,
        )

    # Method `Rotation.pointing()`:
    @staticmethod
    def pointing(axis: Vector, toward: Vector) -> "Rotation":
        """Make the shortest rotation that points `axis` along `toward`.

        Arguments:
        * `axis` (`Vector`): The model's own direction (e.g. `(0, 0, 1)`).
        * `toward` (`Vector`): Where it should point.

        Returns:
        * (`Rotation`): The rotation.
        """
        # The half way vector gives the quaternion directly; opposite
        # directions turn half way round any perpendicular axis.
        a: Vector = _unit(axis)
        b: Vector = _unit(toward)
        dot: float = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
        if dot < -1.0 + 1e-12:
            other: Vector = (1.0, 0.0, 0.0)
            if abs(a[0]) > 0.9:
                other = (0.0, 1.0, 0.0)
            perpendicular: Vector = _unit(_cross(a, other))
            return Rotation(0.0, *perpendicular)
        cross: Vector = _cross(a, b)
        return Rotation(1.0 + dot, *cross)

    # Method `Rotation.inverse()`:
    def inverse(self) -> "Rotation":
        """Return the rotation that undoes this one.

        Returns:
        * (`Rotation`): The inverse rotation.
        """
        return Rotation(self.w, -self.x, -self.y, -self.z)

    # Method `Rotation.apply()`:
    def apply(self, vector: Vector) -> Vector:
        """Rotate a vector.

        Arguments:
        * `vector` (`Vector`): The vector.

        Returns:
        * (`Vector`): The vector, rotated.
        """
        # v' = v + 2w (q x v) + 2 q x (q x v), with q the vector part.
        q: Vector = (self.x, self.y, self.z)
        t: Vector = _cross(q, vector)
        t = (2.0 * t[0], 2.0 * t[1], 2.0 * t[2])
        u: Vector = _cross(q, t)
        return (
            vector[0] + self.w * t[0] + u[0],
            vector[1] + self.w * t[1] + u[1],
            vector[2] + self.w * t[2] + u[2],
        )

    # Method `Rotation.rows()`:
    def rows(self) -> tuple[Vector, Vector, Vector]:
        """Return the 3x3 rotation matrix, row by row.

        Returns:
        * (`tuple[Vector, Vector, Vector]`): The rows.
        """
        w, x, y, z = self.w, self.x, self.y, self.z
        return (
            (
                1 - 2 * (y * y + z * z),
                2 * (x * y - w * z),
                2 * (x * z + w * y),
            ),
            (
                2 * (x * y + w * z),
                1 - 2 * (x * x + z * z),
                2 * (y * z - w * x),
            ),
            (
                2 * (x * z - w * y),
                2 * (y * z + w * x),
                1 - 2 * (x * x + y * y),
            ),
        )

    def __mul__(self, other: "Rotation") -> "Rotation":
        """Return `other` then this rotation (the Hamilton product)."""
        a: Rotation = self
        b: Rotation = other
        return Rotation(
            a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
            a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
            a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
            a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
        )


# The three zero lengths of a placement at the origin.
ORIGIN: tuple[Length, Length, Length] = (
    Length(Fraction(0), "mm"),
    Length(Fraction(0), "mm"),
    Length(Fraction(0), "mm"),
)


# Class `Placement`:
@dataclass(frozen=True, slots=True)
class Placement:
    """Where a model sits in its parent: a rotation, then a translation.

    A point `p` of the model is `rotation.apply(p) + translation` in
    the parent.  Composed placements compute their translations in
    millimeters, rounded to `LENGTH_DIGITS` decimals (until preferred
    units are settled, `T.cmt~5.3` #53).

    Attributes:
    * `translation` (`tuple[Length, Length, Length]`): X, Y and Z.
    * `rotation` (`Rotation`): The rotation, about the model's origin.

    Constructor:
    * `Placement(translation, rotation)`
    """

    # Constructor arguments:
    translation: tuple[Length, Length, Length] = field(default=ORIGIN)
    rotation: Rotation = field(default_factory=Rotation)

    # Method `Placement.mm()`:
    def mm(self) -> Vector:
        """Return the translation in millimeters.

        Returns:
        * (`Vector`): The translation, in millimeters.
        """
        x, y, z = self.translation
        return (x.mm(), y.mm(), z.mm())

    # Method `Placement.compose()`:
    def compose(self, child: "Placement") -> "Placement":
        """Return `child` placed in this placement's parent.

        Arguments:
        * `child` (`Placement`): A placement within this one.

        Returns:
        * (`Placement`): `child` then this placement.
        """
        moved: Vector = self.rotation.apply(child.mm())
        here: Vector = self.mm()
        return Placement(
            (
                Length.from_mm(moved[0] + here[0]),
                Length.from_mm(moved[1] + here[1]),
                Length.from_mm(moved[2] + here[2]),
            ),
            self.rotation * child.rotation,
        )

    # Method `Placement.inverse()`:
    def inverse(self) -> "Placement":
        """Return the placement that undoes this one.

        Returns:
        * (`Placement`): The inverse placement.
        """
        rotation: Rotation = self.rotation.inverse()
        back: Vector = rotation.apply(self.mm())
        return Placement(
            (
                Length.from_mm(-back[0]),
                Length.from_mm(-back[1]),
                Length.from_mm(-back[2]),
            ),
            rotation,
        )

    # Method `Placement.delta()`:
    def delta(self, old: "Placement") -> "Placement":
        """Return the move that takes `old` to this placement.

        SolidCraft's `occurrence.move` is relative to where the
        occurrence is, so what is sent is this delta.

        Arguments:
        * `old` (`Placement`): Where it is now.

        Returns:
        * (`Placement`): `d`, such that `d.compose(old)` is this one.
        """
        return self.compose(old.inverse())

    # Method `Placement.matrix()`:
    def matrix(self) -> Matrix:
        """Return the 3x4 matrix for `occurrence.move(matrix=...)`.

        Returns:
        * (`Matrix`): The rotation's rows, each with its translation
          (in millimeters) on the right.
        """
        rows: tuple[Vector, Vector, Vector] = self.rotation.rows()
        t: Vector = self.mm()
        return (
            (*rows[0], t[0]),
            (*rows[1], t[1]),
            (*rows[2], t[2]),
        )


# The kinds of value a parameter can hold (`meta()`'s `unit`).
UNIT_KINDS: tuple[str, ...] = ("length", "angle", "count", "text", "flag")

# How far a result may still move when a model is settled: 1e-9 mm
# for lengths, 1e-9 degrees for angles, 1e-9 for plain numbers.
SETTLED: float = 1e-9

# The default wall clock limit for `SolidModel.settle()`, in seconds.
SETTLE_SECONDS: float = 5.0


# Function `meta()`:
def meta(
    unit: str, label: str, help_text: str, *, shape: bool = False
) -> dict[str, Any]:
    """Return a parameter's metadata, for `field(metadata=...)`.

    Arguments:
    * `unit` (`str`): Its kind of value, one of `UNIT_KINDS`.
    * `label` (`str`): Its short name, as people see it.
    * `help_text` (`str`): One line saying what it is.
    * `shape` (`bool`):
      Whether a change to it changes the model's shape (e.g. a hole
      count), so that the model is built again, instead of having
      its SolidCraft parameters changed.

    Returns:
    * (`dict[str, Any]`): The metadata.

    Raises:
    * `ValueError`: If `unit` is unknown.
    """
    if unit not in UNIT_KINDS:
        raise ValueError(f"{unit=} is not one of {UNIT_KINDS}")
    return {"unit": unit, "label": label, "help": help_text, "shape": shape}


# Class `NotSettledError`:
class NotSettledError(RuntimeError):
    """A model whose results were still moving at the wall clock limit.

    Attributes:
    * `moving` (`dict[str, float]`):
      Each result still moving (by its dotted path), and how far it
      moved in the last pass.
    * `passes` (`int`): The passes done.

    Constructor:
    * `NotSettledError(moving, passes, seconds)`
    """

    def __init__(
        self, moving: dict[str, float], passes: int, seconds: float
    ) -> None:
        """Make the error and its message.

        Arguments:
        * `moving` (`dict[str, float]`): The results still moving.
        * `passes` (`int`): The passes done.
        * `seconds` (`float`): The wall clock limit.
        """
        self.moving: dict[str, float] = moving
        self.passes: int = passes
        listed: str = ", ".join(
            f"{path} by {by:.3g}" for path, by in sorted(moving.items())
        )
        super().__init__(
            f"not settled after {passes} passes ({seconds} s): {listed}"
        )


# Function `_numbers()`:
def _numbers(value: object) -> tuple[float, ...] | None:
    """Return a result as numbers to compare passes by, if it has them.

    Arguments:
    * `value` (`object`): A result.

    Returns:
    * (`tuple[float, ...] | None`): Millimeters for a `Length`,
      degrees for an `Angle`, the value for a number, the translation
      (mm) and quaternion for a `Placement`; `None` for anything else,
      which is compared for equality.
    """
    numbers: tuple[float, ...] | None = None
    if isinstance(value, Length):
        numbers = (value.mm(),)
    elif isinstance(value, Angle):
        numbers = (float(value.degrees),)
    elif isinstance(value, Placement):
        rotation: Rotation = value.rotation
        numbers = (
            *value.mm(),
            rotation.w,
            rotation.x,
            rotation.y,
            rotation.z,
        )
    elif isinstance(value, (int, float, Fraction)) and not isinstance(
        value, bool
    ):
        numbers = (float(value),)
    return numbers


# Class `SolidModel`:
@dataclass(slots=True)
class SolidModel:
    """The base class of parametric models.

    A model is an editable dataclass.  Its `init=True` fields are its
    parameters, each with `meta()` metadata; its `init=False` fields
    are results, computed by `update()`.  A field may hold another
    model (a child): the parent sets the child's parameters, calls its
    `update()` and reads its results, and a child never reads its
    parent.  `settle()` repeats `update()` until no result moves.

    Each model builds in its own coordinates, in its own `UNIT` (the
    unit its designer chose, `T.cmt~5.3` #53).  Built or edited, there
    is one path: `__post_init__()` settles it, and after an edit the
    caller settles it again.

    Attributes:
    * `UNIT` (`ClassVar[str]`): The model's preferred length unit.

    Constructor:
    * `SolidModel()`
    """

    # Remaining attributes (alphabetized):
    UNIT: ClassVar[str] = "mm"

    def __post_init__(self) -> None:
        """Settle the model as soon as it is made."""
        self.settle()

    # Method `SolidModel.update()`:
    def update(self) -> None:
        """Compute the results from the parameters, once.

        Subclasses set their children's parameters, call their
        `update()`, read their results and check their own parameters
        together (raising `ValueError`); this one does nothing.
        """

    # Method `SolidModel.settle()`:
    def settle(self, seconds: float = SETTLE_SECONDS) -> int:
        """Repeat `update()` until no result moves.

        Arguments:
        * `seconds` (`float`): The wall clock limit.

        Returns:
        * (`int`): The passes it took (2 or more: the last one shows
          that nothing moved).

        Raises:
        * `NotSettledError`: If results still moved at the limit.
        """
        # Each pass is compared with the one before it.
        deadline: float = time.monotonic() + seconds
        before: dict[str, object] = dict(self.results())
        passes: int = 0
        while True:
            self.update()
            passes += 1
            after: dict[str, object] = dict(self.results())
            moving: dict[str, float] = _moved(before, after)
            if not moving:
                return passes
            if time.monotonic() > deadline:
                raise NotSettledError(moving, passes, seconds)
            before = after

    # Method `SolidModel.results()`:
    def results(self, prefix: str = "") -> Iterator[tuple[str, object]]:
        """Yield every result, children's included, by dotted path.

        Arguments:
        * `prefix` (`str`): The path of this model in its parent.

        Yields:
        * (`tuple[str, object]`): A result's path and value.
        """
        yield from self._walk(prefix, parameters=False)

    # Method `SolidModel.parameters()`:
    def parameters(self, prefix: str = "") -> Iterator[tuple[str, object]]:
        """Yield every parameter, children's included, by dotted path.

        A child model is a parameter of its parent, but what is
        yielded are its own parameters (`jaw.width`), not the child.

        Arguments:
        * `prefix` (`str`): The path of this model in its parent.

        Yields:
        * (`tuple[str, object]`): A parameter's path and value.
        """
        yield from self._walk(prefix, parameters=True)

    # Method `SolidModel.parameter_fields()`:
    def parameter_fields(self) -> Iterator["Field[Any]"]:
        """Yield this model's own parameter fields (not its children's).

        Yields:
        * (`Field[Any]`): A field with `init=True`.
        """
        each: Field[Any]
        for each in fields(self):
            if each.init:
                yield each

    def _walk(
        self, prefix: str, *, parameters: bool
    ) -> Iterator[tuple[str, object]]:
        """Yield the parameters or the results, children's included.

        Arguments:
        * `prefix` (`str`): The path of this model in its parent.
        * `parameters` (`bool`): Parameters if true, else results.

        Yields:
        * (`tuple[str, object]`): A path and its value.
        """
        each: Field[Any]
        for each in fields(self):
            value: object = getattr(self, each.name)
            path: str = f"{prefix}{each.name}"
            if isinstance(value, SolidModel):
                yield from value._walk(  # pylint: disable=protected-access
                    f"{path}.", parameters=parameters
                )
            elif each.init == parameters:
                yield path, value


# Function `_moved()`:
def _moved(
    before: dict[str, object], after: dict[str, object]
) -> dict[str, float]:
    """Return the results that moved between two passes.

    Arguments:
    * `before` (`dict[str, object]`): The results of one pass.
    * `after` (`dict[str, object]`): The results of the next.

    Returns:
    * (`dict[str, float]`): Each result that moved more than
      `SETTLED`, and by how much (`inf` for a change that is not a
      number, or a result that came or went).
    """
    moving: dict[str, float] = {}
    path: str
    for path in before.keys() | after.keys():
        old: object = before.get(path)
        new: object = after.get(path)
        old_numbers: tuple[float, ...] | None = _numbers(old)
        new_numbers: tuple[float, ...] | None = _numbers(new)
        if (
            old_numbers is not None
            and new_numbers is not None
            and len(old_numbers) == len(new_numbers)
        ):
            by: float = max(
                abs(n - o)
                for o, n in zip(old_numbers, new_numbers, strict=True)
            )
            if not by <= SETTLED:  # A `nan` (from `inf`) moves too.
                moving[path] = by
        elif path not in before or path not in after or old != new:
            moving[path] = math.inf
    return moving
