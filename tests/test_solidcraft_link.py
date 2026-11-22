"""Tests for `scraftcam.solidcraft_link`.

The SolidCraft tests run a headless `solidcraft-cli`, and are skipped
when it is not on the `PATH`.
"""

import shutil
import unittest
from dataclasses import dataclass, field
from typing import cast

from scraftcam.model import (
    Angle,
    Length,
    Placement,
    Rotation,
    SolidModel,
    meta,
)
from scraftcam.pybind.scraftpybind import JSON, PyBind, connect
from scraftcam.solidcraft_link import (
    SolidCraftLink,
    _compose,
    _inverse,
    _off,
    _rows,
    send_changes,
    shape_paths,
    solidcraft_lengths,
)
from scraftcam.tooling.jaw_plate import JawPlate
from tests.test_jaw_plate import body_facts

HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None


# Class `Block`:
@dataclass(slots=True)
class Block(SolidModel):
    """A square block, with a `shape` field to make a rebuild.

    Attributes:
    * `width` (`Length`): Its size across, X and Y.
    * `pieces` (`int`): A shape field (only counted, never built).

    Constructor:
    * `Block(width, pieces)`
    """

    # Constructor arguments:
    width: Length = field(
        default=Length(20, "mm"),
        metadata=meta("length", "Width", "Its size across."),
    )
    pieces: int = field(
        default=1,
        metadata=meta("count", "Pieces", "A shape field.", shape=True),
    )

    def update(self) -> None:
        """Refuse a block with no size."""
        if self.width <= Length(0, "mm"):
            raise ValueError(f"{self.width}: no size")

    def build(self, solidcraft: PyBind, name: str) -> str:
        """Build a 10 mm high block, its width a parameter."""
        solidcraft.parameters.add(
            name=f"{name}__width", expression=self.width.solidcraft()
        )
        solidcraft.sketch.create(plane="XY", name=name)
        half: float = self.width.mm() / 2.0
        outline: JSON = solidcraft.sketch.rectangle_center(
            center=(0.0, 0.0), corner=(half, half)
        )
        assert isinstance(outline, dict)
        sides: JSON = outline["sides"]
        assert isinstance(sides, dict)
        for side in ("bottom", "left"):
            solidcraft.sketch.dimension(
                entities=[sides[side]], type="length", value=f"{name}__width"
            )
        solidcraft.sketch.finish()
        extruded: JSON = solidcraft.solid.extrude(distance=10.0)
        assert isinstance(extruded, dict)
        bodies: JSON = extruded["bodies"]
        assert isinstance(bodies, list) and isinstance(bodies[0], str)
        return bodies[0]


# Class `TestHelpers`:
class TestHelpers(unittest.TestCase):
    """Names, shape fields and the matrix helpers, with no SolidCraft."""

    def test_names(self) -> None:
        """Lengths are named `NAME__PATH`; shape fields are found."""
        lengths: dict[str, Length] = solidcraft_lengths(Block(), "b_001")
        self.assertEqual(lengths, {"b_001__width": Length(20, "mm")})
        self.assertEqual(shape_paths(Block()), ["pieces"])
        self.assertEqual(shape_paths(JawPlate()), [])

    def test_matrices(self) -> None:
        """A move composed with its inverse is no move."""
        turned: Placement = Placement(
            (Length(1, "in"), Length(2, "mm"), Length(0, "mm")),
            Rotation.about((0.0, 0.0, 1.0), Angle(30)),
        )
        move = _rows(turned.matrix())
        none = _rows(Placement().matrix())
        self.assertLess(_off(_compose(move, _inverse(move)), none), 1e-12)
        self.assertGreater(_off(move, none), 1.0)

    def test_bad_base(self) -> None:
        """A base name that can not start a parameter name is refused."""
        link: SolidCraftLink = SolidCraftLink(PyBind(connect("headless")))
        with self.assertRaises(ValueError):
            link.add(Block(), "_hidden")


# Class `TestSolidCraftLink`:
@unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
class TestSolidCraftLink(unittest.TestCase):
    """Models added, edited, placed and rebuilt in a headless SolidCraft."""

    def test_link(self) -> None:
        """Each kind of change reaches SolidCraft the right way."""
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            link: SolidCraftLink = SolidCraftLink(solidcraft)

            # Numbered names, placed 100 mm along X.
            block: Block = Block()
            away: Placement = Placement(
                (Length(100, "mm"), Length(0, "mm"), Length(0, "mm"))
            )
            name: str = link.add(block, "block", away)
            self.assertEqual(name, "block_001")
            top: list[float] = body_facts(solidcraft)[1]
            self.assertAlmostEqual(top[0], 110.0, 6)

            # A length change is sent; sending again sends nothing.
            block.width = Length(30, "mm")
            self.assertEqual(link.send(name), "changed")
            self.assertEqual(link.send(name), "unchanged")
            volume: float
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume, 30.0 * 30.0 * 10.0, 3)
            self.assertAlmostEqual(top[0], 115.0, 6)

            # A refused edit sends nothing.
            block.width = Length(-1, "mm")
            with self.assertRaises(ValueError):
                link.send(name)
            block.width = Length(30, "mm")

            # A shape field rebuilds, in the same place.
            block.pieces = 2
            self.assertEqual(link.send(name), "rebuilt")
            volume, top = body_facts(solidcraft)
            self.assertAlmostEqual(volume, 30.0 * 30.0 * 10.0, 3)
            self.assertAlmostEqual(top[0], 115.0, 6)

            # Turned 90 degrees about Z, about its own origin.
            link.place(
                name,
                Placement(
                    away.translation,
                    Rotation.about((0.0, 0.0, 1.0), Angle(90)),
                ),
            )
            top = body_facts(solidcraft)[1]
            self.assertAlmostEqual(top[0], 115.0, 6)
            self.assertLess(link.drift, 1e-8)
            self.assertEqual(link.add(Block(), "block"), "block_002")


# Class `FakeParameters`:
# It stands in for the one method the code under test calls.
class FakeParameters:  # pylint: disable=too-few-public-methods
    """Records `parameters.change` calls in place of SolidCraft.

    Attributes:
    * `calls` (`list[dict[str, JSON]]`): The changes sent, in order.
    """

    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[dict[str, JSON]] = []

    def change(self, *, changes: dict[str, JSON]) -> JSON:
        """Record one change.

        Arguments:
        * `changes` (`dict[str, JSON]`): The values sent.

        Returns:
        * (`JSON`): No errors.
        """
        self.calls.append(changes)
        return {"errors": []}


# Class `FakeSolidCraft`:
# It stands in for `PyBind`'s one namespace the code under test uses.
class FakeSolidCraft:  # pylint: disable=too-few-public-methods
    """Stands in for `PyBind` with only its parameters.

    Attributes:
    * `parameters` (`FakeParameters`): The recorder.
    """

    def __init__(self) -> None:
        """Start a recorder."""
        self.parameters: FakeParameters = FakeParameters()


# Class `TestSendChanges`:
class TestSendChanges(unittest.TestCase):
    """Only what moved is sent, in chunks."""

    def test_chunks(self) -> None:
        """Seven changed values at most three a call: 3, 3, 1."""
        old: dict[str, str] = {f"v{index}": "1 mm" for index in range(9)}
        new: dict[str, str] = dict(old)
        index: int
        for index in range(7):
            new[f"v{index}"] = "2 mm"
        fake: FakeSolidCraft = FakeSolidCraft()
        errors: list[JSON] = send_changes(
            cast(PyBind, fake), old, new, limit=3
        )
        self.assertEqual(errors, [])
        self.assertEqual([len(c) for c in fake.parameters.calls], [3, 3, 1])
        self.assertNotIn("v8", fake.parameters.calls[-1])

    def test_unknown(self) -> None:
        """A name SolidCraft does not have is refused."""
        fake: FakeSolidCraft = FakeSolidCraft()
        with self.assertRaises(KeyError):
            send_changes(cast(PyBind, fake), {}, {"v0": "1 mm"})


if __name__ == "__main__":
    unittest.main()
