"""Keep `SolidModel`s built in one SolidCraft up to date (`T.cmt~5.3`).

Changes go one way, from our models to SolidCraft (#15, #22):

* `SolidCraftLink.add()` names a model `BASE_NNN` (#59), builds it in
  a component of its own and places it.
* After an edit, `send()` settles the model, then sends every value
  that changed (`SolidModel.solidcraft_values()`) as plain values, at
  most `outline.CHANGE_LIMIT` to a call; a change to a field marked
  `shape` (`meta(..., shape=True)`), or to the names of the values
  (a `Profile` with more segments), deletes the model's component and
  parameters and builds it again (#19).
* `place()` moves a model.  SolidCraft's `occurrence.move` is
  relative, so the link remembers where each model is and sends the
  delta (a quaternion delta, made a matrix only for the call, #45).
  The transform SolidCraft returns is compared with ours, and a
  correction is sent when they differ by more than `DRIFT` (#48).
"""

import re
from dataclasses import Field, dataclass, field, fields
from typing import Any

from .model import Length, Placement, SolidModel
from .outline import send_changes
from .pybind.scraftpybind import JSON, PyBind

# A 3x4 rigid matrix as plain rows (rotation, then translation in mm).
Rows = list[list[float]]

# How far (mm, or matrix entry) SolidCraft's placement may drift from
# ours before a correction is sent (#48: 1e-7 might show, 1e-9 not).
DRIFT: float = 1e-8

# A model's base name: letters, digits and `_`, not at either end, so
# that `BASE_NNN__PATH` is a SolidCraft parameter name (#17, #26).
BASE_NAME: re.Pattern[str] = re.compile(r"[A-Za-z](?:\w*[A-Za-z0-9])?")


# Class `LinkedModel`:
@dataclass(slots=True)
class LinkedModel:
    """A model built in SolidCraft, and what was last sent for it.

    Attributes:
    * `model` (`SolidModel`): The model.
    * `name` (`str`): Its name in SolidCraft (`jaw_plate_001`).
    * `placement` (`Placement`): Where SolidCraft has it.
    * `parameters` (`dict[str, object]`):
      Each parameter (by dotted path) as last built or sent.
    * `values` (`dict[str, str]`):
      Each SolidCraft parameter's expression as last sent.

    Constructor:
    * `LinkedModel(model, name)`
    """

    # Constructor arguments:
    model: SolidModel = field()
    name: str = field()

    # Remaining attributes (alphabetized):
    parameters: dict[str, object] = field(init=False, default_factory=dict)
    placement: Placement = field(init=False, default_factory=Placement)
    values: dict[str, str] = field(init=False, default_factory=dict)

    # Method `LinkedModel.remember()`:
    def remember(self) -> None:
        """Note the model's parameters and SolidCraft values as sent."""
        self.parameters = dict(self.model.parameters())
        self.values = self.model.solidcraft_values(self.name)


# Class `SolidCraftLink`:
@dataclass(slots=True)
class SolidCraftLink:
    """The models built in one SolidCraft session.

    Attributes:
    * `solidcraft` (`PyBind`): The SolidCraft session.
    * `counts` (`dict[str, int]`): The last number given to each base.
    * `drift` (`float`):
      The largest drift seen from SolidCraft's placements, for tests.
    * `linked` (`dict[str, LinkedModel]`): The models, by name.

    Constructor:
    * `SolidCraftLink(solidcraft)`
    """

    # Constructor arguments:
    solidcraft: PyBind = field()

    # Remaining attributes (alphabetized):
    counts: dict[str, int] = field(init=False, default_factory=dict)
    drift: float = field(init=False, default=0.0)
    linked: dict[str, LinkedModel] = field(init=False, default_factory=dict)

    # Method `SolidCraftLink.add()`:
    def add(
        self,
        model: SolidModel,
        base: str,
        placement: Placement | None = None,
    ) -> str:
        """Build a model under the next `BASE_NNN` name, and place it.

        Arguments:
        * `model` (`SolidModel`): The model, settled.
        * `base` (`str`): Its base name (e.g. `jaw_plate`).
        * `placement` (`Placement | None`):
          Where it goes (default: where it was built).

        Returns:
        * (`str`): Its name (e.g. `jaw_plate_001`).

        Raises:
        * `ValueError`: If `base` can not start a parameter name.
        """
        if not BASE_NAME.fullmatch(base):
            raise ValueError(f"{base=} is not a usable model name")
        number: int = self.counts.get(base, 0) + 1
        self.counts[base] = number
        name: str = f"{base}_{number:03d}"
        linked: LinkedModel = LinkedModel(model, name)
        self.linked[name] = linked
        self._build(linked)
        if placement is not None:
            self.place(name, placement)
        return name

    # Method `SolidCraftLink.send()`:
    def send(self, name: str) -> str:
        """Settle an edited model and bring SolidCraft up to date.

        Arguments:
        * `name` (`str`): The model's name.

        Returns:
        * (`str`): `unchanged`, `changed` (parameters sent) or
          `rebuilt` (a `shape` field changed, or the values' names).

        Raises:
        * `ValueError`: From the model's checks; nothing is sent.
        """
        # Settled first, so that a refused edit leaves SolidCraft as
        # it was (SolidCraft checks names, not values).
        linked: LinkedModel = self.linked[name]
        linked.model.settle()
        now: dict[str, object] = dict(linked.model.parameters())
        values: dict[str, str] = linked.model.solidcraft_values(name)
        if values.keys() != linked.values.keys() or any(
            now.get(path) != linked.parameters.get(path)
            for path in shape_paths(linked.model)
        ):
            self._delete(name)
            placement: Placement = linked.placement
            linked.placement = Placement()
            self._build(linked)
            self.place(name, placement)
            return "rebuilt"

        # Only what changed goes out.
        changed: bool = values != linked.values
        if changed:
            send_changes(self.solidcraft, linked.values, values)
        linked.remember()
        return "changed" if changed else "unchanged"

    # Method `SolidCraftLink.place()`:
    def place(self, name: str, placement: Placement) -> None:
        """Move a model to `placement`, in the design's coordinates.

        Arguments:
        * `name` (`str`): The model's name.
        * `placement` (`Placement`): Where it goes.
        """
        linked: LinkedModel = self.linked[name]
        if placement == linked.placement:
            return
        delta: Placement = placement.delta(linked.placement)
        moved: JSON = self.solidcraft.occurrence.move(
            occurrence=f"{name}:1", matrix=_rows(delta.matrix())
        )
        linked.placement = placement

        # SolidCraft multiplies matrices; it is put back where we say
        # once it drifts.
        ours: Rows = _rows(placement.matrix())
        theirs: Rows = _transform(moved)
        off: float = _off(ours, theirs)
        self.drift = max(self.drift, off)
        if off > DRIFT:
            self.solidcraft.occurrence.move(
                occurrence=f"{name}:1",
                matrix=_compose(ours, _inverse(theirs)),
            )

    # Method `SolidCraftLink.remove()`:
    def remove(self, name: str) -> None:
        """Delete a model from SolidCraft and from the link.

        Arguments:
        * `name` (`str`): The model's name.
        """
        self._delete(name)
        del self.linked[name]

    # Method `SolidCraftLink._build()`:
    def _build(self, linked: LinkedModel) -> None:
        """Build a model in a new component, free to move, at the origin.

        Arguments:
        * `linked` (`LinkedModel`): The model and its name.
        """
        created: JSON = self.solidcraft.component.create(name=linked.name)
        linked.model.build(self.solidcraft, linked.name)
        self.solidcraft.component.activate(component="root")

        # A design's first occurrence is grounded, and refuses to move.
        assert isinstance(created, dict)
        if created.get("grounded"):
            self.solidcraft.occurrence.ground(
                occurrence=f"{linked.name}:1", grounded=False
            )
        linked.remember()

    # Method `SolidCraftLink._delete()`:
    def _delete(self, name: str) -> None:
        """Delete a model's component (its features) and its parameters.

        Arguments:
        * `name` (`str`): The model's name.
        """
        self.solidcraft.component.delete(component=name)
        listed: JSON = self.solidcraft.parameters.list()
        assert isinstance(listed, dict)
        parameters: JSON = listed["parameters"]
        assert isinstance(parameters, list)
        each: JSON
        for each in parameters:
            assert isinstance(each, dict)
            parameter: JSON = each["name"]
            assert isinstance(parameter, str)
            if parameter.startswith(f"{name}__"):
                self.solidcraft.parameters.delete(name=parameter)


# Function `solidcraft_lengths()`:
def solidcraft_lengths(model: SolidModel, name: str) -> dict[str, Length]:
    """Return a model's lengths by their SolidCraft parameter names.

    Arguments:
    * `model` (`SolidModel`): The model.
    * `name` (`str`): Its name in SolidCraft.

    Returns:
    * (`dict[str, Length]`): `NAME__PATH` to each length parameter and
      result, as `SolidModel.build()` names them.
    """
    lengths: dict[str, Length] = {}
    path: str
    value: object
    for path, value in (*model.parameters(), *model.results()):
        if isinstance(value, Length):
            lengths[f"{name}__{path.replace('.', '__')}"] = value
    return lengths


# Function `shape_paths()`:
def shape_paths(model: SolidModel, prefix: str = "") -> list[str]:
    """Return the dotted paths of the parameters that change the shape.

    Arguments:
    * `model` (`SolidModel`): The model.
    * `prefix` (`str`): The model's path in its parent.

    Returns:
    * (`list[str]`): Every parameter marked `shape`, children's too.
    """
    paths: list[str] = []
    each: Field[Any]
    for each in fields(model):
        value: object = getattr(model, each.name)
        if isinstance(value, SolidModel):
            paths += shape_paths(value, f"{prefix}{each.name}.")
        elif each.init and each.metadata.get("shape"):
            paths.append(f"{prefix}{each.name}")
    return paths


# Function `_rows()`:
def _rows(matrix: tuple[tuple[float, ...], ...]) -> Rows:
    """Return a 3x4 matrix as lists, as SolidCraft takes it.

    Arguments:
    * `matrix` (`tuple[tuple[float, ...], ...]`): The matrix.

    Returns:
    * (`Rows`): The same rows, as lists.
    """
    return [list(row) for row in matrix]


# Function `_transform()`:
def _transform(moved: JSON) -> Rows:
    """Return the placement `occurrence.move` reports, as 3x4 rows.

    Arguments:
    * `moved` (`JSON`): The move's result; its `transform` is 4x4 with
      row vectors (the translation in the bottom row).

    Returns:
    * (`Rows`): The same placement with column vectors, as we send it.
    """
    assert isinstance(moved, dict)
    transform: JSON = moved["transform"]
    assert isinstance(transform, list)
    numbers: list[list[float]] = []
    row: JSON
    for row in transform:
        assert isinstance(row, list)
        numbers.append([float(n) for n in row if isinstance(n, int | float)])
    return [[numbers[j][i] for j in range(4)] for i in range(3)]


# Function `_off()`:
def _off(a: Rows, b: Rows) -> float:
    """Return how far apart two 3x4 matrices are (largest entry).

    Arguments:
    * `a` (`Rows`): One matrix.
    * `b` (`Rows`): The other.

    Returns:
    * (`float`): The largest difference of two entries.
    """
    return max(
        abs(x - y)
        for row_a, row_b in zip(a, b, strict=True)
        for x, y in zip(row_a, row_b, strict=True)
    )


# Function `_compose()`:
def _compose(a: Rows, b: Rows) -> Rows:
    """Return the rigid move `b` then `a`, as 3x4 rows.

    Arguments:
    * `a` (`Rows`): The second move.
    * `b` (`Rows`): The first move.

    Returns:
    * (`Rows`): `a b`.
    """
    return [
        [sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
        + [sum(a[i][k] * b[k][3] for k in range(3)) + a[i][3]]
        for i in range(3)
    ]


# Function `_inverse()`:
def _inverse(a: Rows) -> Rows:
    """Return the inverse of a rigid move: `R^T`, `-R^T t`.

    Arguments:
    * `a` (`Rows`): The move.

    Returns:
    * (`Rows`): Its inverse.
    """
    return [
        [a[k][i] for k in range(3)]
        + [-sum(a[k][i] * a[k][3] for k in range(3))]
        for i in range(3)
    ]
