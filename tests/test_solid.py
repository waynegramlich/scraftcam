"""Tests for `scraftcam/solid.py`: solids and planar polygons."""

import math
import shutil
import tempfile
import unittest
from collections.abc import Sequence
from fractions import Fraction
from pathlib import Path
from typing import cast

from scraftcam.geometry import ArcSegment, Corner, LineSegment
from scraftcam.model import Angle, Length, Placement, Rotation
from scraftcam.pybind.scraftpybind import JSON, PyBind, connect
from scraftcam.solid import (
    Appearance,
    Layer,
    Leaf,
    Placed,
    RoundedPolygon,
    Solid,
    SolidAssembly,
    SolidRoundedPolygon,
    SolidStep,
    check_name,
)
from scraftcam.tooling.jaw_plate import JawPlate
from scraftcam.tooling.kurt_vise import jaw_plate_solid
from tests.solidcraft_checks import totals

# Whether a headless SolidCraft can be run.
HAVE_SOLIDCRAFT: bool = shutil.which("solidcraft-cli") is not None


# Function `square()`:
def square(side: float = 10.0, radius: float = 0.0) -> RoundedPolygon:
    """Return a counter-clockwise square with its low corner at 0, 0."""
    return RoundedPolygon(
        (
            Corner(0.0, 0.0, radius),
            Corner(side, 0.0, radius),
            Corner(side, side, radius),
            Corner(0.0, side, radius),
        ),
        "square",
    )


# Function `points()`:
def points(polygon: RoundedPolygon) -> list[tuple[float, float]]:
    """Return the corners as rounded points, for comparing."""
    return [(round(c.x, 9), round(c.y, 9)) for c in polygon.corners]


# Class `FakeCalls`:
# A stand-in for SolidCraft needs no more methods.
# pylint: disable-next=too-few-public-methods
class FakeCalls:
    """Records the calls made to one of SolidCraft's tool groups."""

    def __init__(self, reply: object) -> None:
        """Answer every call with `reply`."""
        self.reply: object = reply
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __getattr__(self, name: str) -> object:
        """Return a function that records a call to `name`."""

        # Function `call()`:
        def call(**arguments: object) -> object:
            """Record the call and answer it."""
            self.calls.append((name, arguments))
            return self.reply

        return call


# Class `FakeSolidCraft`:
# A stand-in for SolidCraft needs no more methods.
# pylint: disable-next=too-few-public-methods
class FakeSolidCraft:
    """Just enough of `PyBind` for these tests."""

    def __init__(self) -> None:
        """Make the tool groups."""
        self.file: FakeCalls = FakeCalls({"created_bodies": ["body1"]})
        self.sketch: FakeCalls = FakeCalls({"curves": ["c"]})
        self.solid: FakeCalls = FakeCalls({})


# Class `TestNames`:
class TestNames(unittest.TestCase):
    """Names must be ones SolidCraft takes."""

    def test_names(self) -> None:
        """Good names pass; bad ones are refused."""
        good: str
        for good in ("jaw", "jaw_plate_001", "A", "x" * 64):
            check_name(good)
        bad: str
        for bad in ("", "_jaw", "jaw_", "1jaw", "jaw plate", "x" * 65):
            with self.assertRaises(ValueError, msg=bad):
                check_name(bad)


# Class `TestAppearance`:
class TestAppearance(unittest.TestCase):
    """Colors are checked and given as hex."""

    def test_hex(self) -> None:
        """Each part goes to two hex digits."""
        self.assertEqual(Appearance(1.0, 0.5, 0.0).hex(), "#ff8000")

    def test_range(self) -> None:
        """A part outside 0 to 1 is refused."""
        with self.assertRaises(ValueError):
            Appearance(0.0, 0.0, 0.0, 1.5)
        with self.assertRaises(ValueError):
            Appearance(-0.1, 0.0, 0.0)


# Class `TestSolidStep`:
class TestSolidStep(unittest.TestCase):
    """A `SolidStep` is one STEP file."""

    def test_base_does_not_build(self) -> None:
        """`Solid` itself can not be built."""
        with self.assertRaises(NotImplementedError):
            # A fake stands in for `PyBind`.
            Solid("thing").build(FakeSolidCraft())  # type: ignore[arg-type]

    def test_suffix(self) -> None:
        """Only `.step` and `.stp` files are taken."""
        SolidStep("vise", Path("vise.STEP"))
        with self.assertRaises(ValueError):
            SolidStep("vise", Path("vise.stl"))

    def test_build(self) -> None:
        """The file is inserted; a missing one is refused."""
        fake: FakeSolidCraft = FakeSolidCraft()
        with tempfile.TemporaryDirectory() as directory:
            path: Path = Path(directory) / "vise.step"
            solid: SolidStep = SolidStep(
                "vise", path, appearance=Appearance(0.5, 0.5, 0.5)
            )
            with self.assertRaises(FileNotFoundError):
                # A fake stands in for `PyBind`.
                solid.build(fake)  # type: ignore[arg-type]
            path.write_text("ISO-10303-21;\n")
            # A fake stands in for `PyBind`.
            bodies: list[str] = solid.build(fake)  # type: ignore[arg-type]
        self.assertEqual(bodies, ["body1"])
        self.assertEqual(
            fake.file.calls,
            [("insert_step", {"path": str(path), "name": "vise"})],
        )


# Class `TestRoundedPolygon`:
class TestRoundedPolygon(unittest.TestCase):
    """Planar polygons are checked, flipped and turned."""

    def test_outline(self) -> None:
        """A rounded square has four lines and four arcs."""
        polygon: RoundedPolygon = square(10.0, 1.0)
        self.assertTrue(polygon.is_ccw())
        self.assertEqual(len(polygon.segments), 8)
        got: float
        want: float
        for got, want in zip(polygon.box, (0.0, 10.0, 0.0, 10.0), strict=True):
            self.assertAlmostEqual(got, want, 12)

    def test_circle(self) -> None:
        """A square of side 2r with radius r is a circle: arcs only."""
        polygon: RoundedPolygon = square(2.0, 1.0)
        self.assertTrue(
            all(isinstance(s, ArcSegment) for s in polygon.segments)
        )

    def test_bad(self) -> None:
        """Bad names, units and outlines are refused."""
        with self.assertRaises(ValueError):
            RoundedPolygon(square().corners, "_bad")
        with self.assertRaises(ValueError):
            RoundedPolygon(square().corners, "bad", "furlong")
        with self.assertRaises(ValueError):
            square(2.0, 1.5)

    def test_messages_in_unit(self) -> None:
        """Lengths in messages are in the polygon's own unit."""
        inch: float = 25.4
        with self.assertRaisesRegex(
            ValueError, r"edge 1 long \(lengths in in\)"
        ):
            RoundedPolygon(
                (
                    Corner(0.0, 0.0, 0.75 * inch),
                    Corner(inch, 0.0, 0.75 * inch),
                    Corner(inch, inch, 0.0),
                    Corner(0.0, inch, 0.0),
                ),
                "tight",
                "in",
            )
        with self.assertRaisesRegex(
            ValueError, r"cross at \(0\.5, 0\.5\) \(lengths in in\)"
        ):
            RoundedPolygon(
                (
                    Corner(0.0, 0.0),
                    Corner(inch, inch),
                    Corner(inch, 0.0),
                    Corner(0.0, inch),
                ),
                "bow",
                "in",
            )
        small: RoundedPolygon = RoundedPolygon(square(2.0).corners, unit="in")
        with self.assertRaisesRegex(
            ValueError, r"both 1\.0 \(lengths in in\)"
        ):
            SolidRoundedPolygon(
                "flat",
                Layer(
                    RoundedPolygon(square(20.0).corners, unit="in"),
                    inches("0"),
                    inches("0"),
                    inches("1"),
                    (Layer(small, inches("0"), inches("0"), inches("1")),),
                ),
            )

    def test_mirrored(self) -> None:
        """A right half makes the whole, edge middles left out."""
        # A 10 wide, 20 tall rectangle, with a notch in its top middle.
        half: tuple[Corner, ...] = (
            Corner(0.0, -10.0),
            Corner(5.0, -10.0, 1.0),
            Corner(5.0, 10.0, 1.0),
            Corner(3.0, 10.0),
            Corner(3.0, 8.0),
            Corner(0.0, 8.0),
        )
        whole: RoundedPolygon = RoundedPolygon.mirrored(half, "vise")
        self.assertEqual(len(whole.corners), 8)
        self.assertTrue(whole.is_ccw())
        self.assertAlmostEqual(whole.signed_area, 200.0 - 6.0 * 2.0)
        self.assertIn(Corner(-3.0, 8.0), whole.corners)
        bad: tuple[Corner, ...]
        for bad in (
            half[:1],
            half[1:],
            (Corner(0.0, 0.0), Corner(-1.0, 1.0), Corner(0.0, 1.0)),
        ):
            with self.assertRaises(ValueError):
                RoundedPolygon.mirrored(bad)

    def test_immutable(self) -> None:
        """A polygon can not be changed once made."""
        with self.assertRaises(AttributeError):
            # Changing a frozen field is what is tested.
            square().name = "other"  # type: ignore[misc]

    def test_flip(self) -> None:
        """Flipping across X = 20 mirrors it, keeping its direction."""
        flipped: RoundedPolygon = square().flip((20.0, 0.0), (20.0, 1.0))
        self.assertTrue(flipped.is_ccw())
        self.assertEqual(
            points(flipped),
            [(40.0, 0.0), (40.0, 10.0), (30.0, 10.0), (30.0, 0.0)],
        )
        self.assertEqual(flipped.name, "square")
        with self.assertRaises(ValueError):
            square().flip((1.0, 1.0), (1.0, 1.0))

    def test_rotate(self) -> None:
        """A quarter turn about the origin takes X to Y."""
        turned: RoundedPolygon = square().rotate(
            (0.0, 0.0), Angle(Fraction(90)), "turned"
        )
        self.assertEqual(turned.name, "turned")
        self.assertEqual(
            points(turned),
            [(0.0, 0.0), (0.0, 10.0), (-10.0, 10.0), (-10.0, 0.0)],
        )
        self.assertAlmostEqual(turned.signed_area, 100.0)

    def test_renamed(self) -> None:
        """`renamed()` keeps the corners."""
        self.assertEqual(square().renamed("other").corners, square().corners)

    def test_draw(self) -> None:
        """Lines and arcs are sent moved, clockwise arcs reversed."""
        fake: FakeSolidCraft = FakeSolidCraft()
        polygon: RoundedPolygon = square(10.0, 1.0)
        curves: list[str] = polygon.draw(
            # A fake stands in for `PyBind`.
            fake,  # type: ignore[arg-type]
            5.0,
            0.0,
        )
        self.assertEqual(len(curves), 8)
        name: str
        arguments: dict[str, object]
        name, arguments = fake.sketch.calls[0]
        first: LineSegment | ArcSegment = polygon.segments[0]
        assert isinstance(first, LineSegment)
        self.assertEqual(name, "line")
        self.assertEqual(
            arguments["points"],
            [
                (first.start[0] + 5.0, first.start[1]),
                (first.end[0] + 5.0, first.end[1]),
            ],
        )

        # Going clockwise, each arc is sent from its end.
        clockwise: RoundedPolygon = RoundedPolygon(
            square(10.0, 1.0).corners[::-1], "clockwise"
        )
        self.assertFalse(clockwise.is_ccw())
        fake = FakeSolidCraft()
        # A fake stands in for `PyBind`.
        clockwise.draw(fake, 0.0, 0.0)  # type: ignore[arg-type]
        arc: LineSegment | ArcSegment = clockwise.segments[1]
        assert isinstance(arc, ArcSegment) and arc.sweep < 0.0
        self.assertEqual(
            fake.sketch.calls[1],
            (
                "arc_center_point",
                {"center": arc.center, "start": arc.end, "end": arc.start},
            ),
        )


# Function `close()`:
def close(a: Sequence[float], b: Sequence[float]) -> bool:
    """Return whether two boxes agree within 1e-9."""
    return all(abs(p - q) <= 1e-9 for p, q in zip(a, b, strict=True))


# Function `inches()`:
def inches(text: str) -> Length:
    """Return a length in inches, from text such as `13/16`."""
    return Length.parse(f"{text} in")


# Function `jaw()`:
def jaw() -> SolidRoundedPolygon:
    """Return the 202-1664 jaw: a plate with two counterbored holes."""
    plate: RoundedPolygon = RoundedPolygon(
        (
            Corner(0.0, 0.0),
            Corner(6 * 25.4, 0.0),
            Corner(6 * 25.4, 2 * 25.4),
            Corner(0.0, 2 * 25.4),
        ),
        unit="in",
    )
    counterbore: RoundedPolygon = RoundedPolygon.circle(inches("13/16"))
    clearance: RoundedPolygon = RoundedPolygon.circle(inches("17/32"))
    zero: Length = inches("0")
    hole: Layer = Layer(clearance, zero, zero, zero)
    layers: list[Layer] = [
        Layer(counterbore, inches(x), inches("0.937"), inches("0.47"), [hole])
        for x in ("1.0625", "4.9375")
    ]
    return SolidRoundedPolygon(
        "jaw", Layer(plate, zero, zero, inches("1"), layers)
    )


# Function `measured()`:
def measured(solidcraft: PyBind) -> tuple[float, list[float]]:
    """Return the design's volume (mm^3) and its box's sorted sides."""
    volume: float
    low: list[float]
    high: list[float]
    volume, low, high = totals(
        solidcraft.component.properties(component="root")
    )
    sides: list[float] = sorted(b - a for a, b in zip(low, high, strict=True))
    return volume, sides


# Function `parents_of()`:
def parents_of(listed: JSON) -> dict[str, str]:
    """Return each component's parent's name, from `component.list`."""
    assert isinstance(listed, dict)
    components: JSON = listed["components"]
    assert isinstance(components, list)
    parents: dict[str, str] = {}
    by_id: dict[object, str] = {}
    each: JSON
    for each in components:
        assert isinstance(each, dict)
        by_id[each["id"]] = str(each["name"])
    for each in components:
        assert isinstance(each, dict)
        parents[str(each["name"])] = by_id.get(each["parent"], "")
    return parents


# Class `TestSolidRoundedPolygon`:
class TestSolidRoundedPolygon(unittest.TestCase):
    """Trees of polygons are checked, then built as joins and cuts."""

    def test_names_and_positions(self) -> None:
        """Unnamed layers are numbered; positions add up."""
        shape: SolidRoundedPolygon = jaw()
        self.assertEqual(shape.shape.name, "jaw")
        names: list[str] = [child.name for child in shape.shape.children] + [
            grand.name
            for child in shape.shape.children
            for grand in child.children
        ]
        self.assertEqual(names, ["jaw_001", "jaw_003", "jaw_002", "jaw_004"])
        hole: tuple[float, float, float, float] = (
            shape.shape.children[1].children[0].box
        )
        self.assertAlmostEqual((hole[0] + hole[1]) / 2, 4.9375)
        self.assertAlmostEqual((hole[2] + hole[3]) / 2, 0.937)
        self.assertEqual(shape.shape.children[0].z_start, 1.0)

    def test_build(self) -> None:
        """The plate goes up; counterbores and holes are cut."""
        fake: FakeSolidCraft = FakeSolidCraft()
        # A fake stands in for `PyBind`.
        self.assertEqual(jaw().build(fake), ["jaw"])  # type: ignore[arg-type]
        extrudes: list[dict[str, object]] = [
            arguments
            for name, arguments in fake.solid.calls
            if name == "extrude"
        ]
        self.assertEqual(len(extrudes), 4)
        self.assertEqual(extrudes[1]["operation"], "cut")

        # The plate, then a counterbore and a hole, each cut down.
        distances: list[float] = [
            float(str(extrude["distance"])) for extrude in extrudes[:3]
        ]
        self.assertAlmostEqual(distances[0], 25.4)
        self.assertAlmostEqual(distances[1], (0.47 - 1) * 25.4)
        self.assertAlmostEqual(distances[2], -0.47 * 25.4)

    def test_turned_layers(self) -> None:
        """A layer turns about its center; its children turn along."""
        zero: Length = Length.parse("0 mm")
        small: RoundedPolygon = square(2.0)
        child: Layer = Layer(small, Length.parse("5 mm"), zero, zero)
        root: Layer = Layer(
            square(20.0),
            Length.parse("30 mm"),
            zero,
            inches("1"),
            (child,),
            angle=Angle(Fraction(90)),
            center=(Length.parse("10 mm"), Length.parse("10 mm")),
        )
        shape: SolidRoundedPolygon = SolidRoundedPolygon("turned", root)
        expected: tuple[tuple[float, ...], ...] = (
            (30.0, 50.0, 0.0, 20.0),
            (48.0, 50.0, 5.0, 7.0),
        )
        got: tuple[float, float, float, float]
        want: tuple[float, ...]
        for got, want in zip(
            (shape.shape.box, shape.shape.children[0].box),
            expected,
            strict=True,
        ):
            self.assertTrue(close(got, want), (got, want))

    def test_bad_trees(self) -> None:
        """Bad trees are refused when made."""
        zero: Length = inches("0")
        box: RoundedPolygon = square()
        small: RoundedPolygon = square(2.0)
        with self.assertRaises(ValueError):
            SolidRoundedPolygon("down", Layer(box, zero, zero, inches("-1")))
        with self.assertRaises(ValueError):
            SolidRoundedPolygon(
                "bad name", Layer(box, zero, zero, inches("1"))
            )
        cases: tuple[tuple[Layer, ...], ...] = (
            # Ends where its parent does.
            (Layer(small, zero, zero, inches("1")),),
            # Outside its parent.
            (Layer(small, Length.parse("20 mm"), zero, zero),),
            # Two children overlapping.
            (
                Layer(small, Length.parse("1 mm"), zero, zero),
                Layer(small, Length.parse("2 mm"), zero, zero),
            ),
        )
        children: tuple[Layer, ...]
        for children in cases:
            with self.assertRaises(ValueError, msg=repr(children)):
                SolidRoundedPolygon(
                    "bad", Layer(box, zero, zero, inches("1"), children)
                )
        SolidRoundedPolygon(
            "good",
            Layer(
                box,
                zero,
                zero,
                inches("1"),
                (
                    Layer(
                        small, Length.parse("1 mm"), Length.parse("1 mm"), zero
                    ),
                ),
            ),
            appearance=Appearance(0.5, 0.5, 0.5),
        )

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_matches_jaw_plate(self) -> None:
        """Layers make the same plate as `JawPlate` (`T.rps~6.6` #361)."""
        plate: JawPlate = JawPlate()
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            plate.build(solidcraft, "jaw")
            old: tuple[float, list[float]] = measured(solidcraft)
        with connect("headless") as transport:
            solidcraft = PyBind(transport)
            jaw_plate_solid(plate).build(solidcraft)
            new: tuple[float, list[float]] = measured(solidcraft)
        self.assertLess(abs(new[0] - old[0]) / old[0], 1e-3, (new, old))
        self.assertTrue(close(new[1], old[1]), (new, old))

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_build_live(self) -> None:
        """The jaw builds headless, with the volume and box it should."""
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            self.assertEqual(jaw().build(solidcraft), ["jaw"])
            properties: JSON = solidcraft.component.properties()
        volume: float
        top: list[float]
        volume, _, top = totals(properties)
        self.assertEqual(
            [round(v, 4) for v in top],
            [round(v * 25.4, 4) for v in (6.0, 2.0, 1.0)],
        )

        # Plate less two counterbores and two clearance holes (mm^3);
        # SolidCraft's volume is tessellated, so loosely.
        inch3: float = 25.4**3
        counterbore: float = math.pi * (13 / 32) ** 2 * (1 - 0.47)
        clearance: float = math.pi * (17 / 64) ** 2 * 0.47
        expected: float = (12 - 2 * (counterbore + clearance)) * inch3
        self.assertLess(abs(volume - expected) / expected, 1e-3)


# Class `TestSolidAssembly`:
class TestSolidAssembly(unittest.TestCase):
    """Assemblies nest, flatten, and pass colors down."""

    def test_vise_of_two_jaws(self) -> None:
        """One jaw placed twice, the pair placed again, turned."""
        red: Appearance = Appearance(1.0, 0.0, 0.0)
        grey: Appearance = Appearance(0.5, 0.5, 0.5)
        plate: SolidRoundedPolygon = jaw()
        zero: Length = inches("0")
        turned: Rotation = Rotation.about((0, 0, 1), Angle(Fraction(180)))
        pair: SolidAssembly = SolidAssembly(
            "pair",
            (
                Placed(plate),
                Placed(
                    plate,
                    Placement((inches("6"), inches("5"), zero), turned),
                    red,
                ),
            ),
            appearance=grey,
        )
        vise: SolidAssembly = SolidAssembly(
            "vise", (Placed(pair, Placement((zero, zero, inches("2")))),)
        )
        self.assertEqual(list(vise.solids()), ["vise", "pair", "jaw"])
        leaves: list[Leaf] = vise.leaves()
        self.assertEqual([leaf.appearance for leaf in leaves], [grey, red])
        self.assertEqual(leaves[1].path, ("vise", "pair", "jaw"))
        self.assertTrue(close(leaves[0].placement.mm(), (0.0, 0.0, 50.8)))
        self.assertTrue(close(leaves[1].placement.mm(), (152.4, 127.0, 50.8)))
        self.assertTrue(
            close(
                leaves[1].placement.rotation.apply((1.0, 0.0, 0.0)),
                (-1.0, 0.0, 0.0),
            )
        )

    def test_bad(self) -> None:
        """Empty assemblies and clashing names are refused."""
        with self.assertRaises(ValueError):
            SolidAssembly("empty", ())
        other: SolidStep = SolidStep("jaw", Path("jaw.step"))
        with self.assertRaises(ValueError):
            SolidAssembly("clash", (Placed(jaw()), Placed(other)))

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_build_live(self) -> None:
        """Nested components, one jaw built once and placed twice."""
        plate: SolidRoundedPolygon = jaw()
        zero: Length = inches("0")
        turned: Rotation = Rotation.about((0, 0, 1), Angle(Fraction(180)))
        pair: SolidAssembly = SolidAssembly(
            "pair",
            (
                Placed(plate, Placement((inches("1"), zero, zero))),
                Placed(
                    plate,
                    Placement((inches("7"), inches("5"), zero), turned),
                    Appearance(1.0, 0.0, 0.0, 0.25),
                ),
            ),
        )
        vise: SolidAssembly = SolidAssembly(
            "vise", (Placed(pair, Placement((zero, zero, inches("2")))),)
        )
        with connect("headless") as transport:
            solidcraft: PyBind = PyBind(transport)
            self.assertEqual(vise.build(solidcraft), ["jaw"])
            listed: JSON = solidcraft.component.list(compact=True)
            properties: JSON = solidcraft.component.properties(
                component="root"
            )
        parents: dict[str, str] = parents_of(listed)
        self.assertEqual(parents["jaw"], "pair")
        self.assertEqual(parents["pair"], "vise")
        low: list[float]
        high: list[float]
        _, low, high = totals(properties)
        self.assertEqual(
            [round(v / 25.4, 6) for v in (*low, *high)],
            [1.0, 0.0, 2.0, 7.0, 5.0, 3.0],
        )

    @unittest.skipUnless(HAVE_SOLIDCRAFT, "no `solidcraft-cli` on the PATH")
    def test_step_parts_live(self) -> None:
        """A STEP file placed twice is one component, no extra level."""
        # Headless SolidCraft writes only inside the project.
        with tempfile.TemporaryDirectory(dir="scratch") as directory:
            path: Path = (Path(directory) / "plate.step").resolve()
            with connect("headless") as transport:
                solidcraft: PyBind = PyBind(transport)
                made: list[str] = jaw_plate_solid(JawPlate()).build(solidcraft)
                solidcraft.file.export(
                    path=str(path), format="step", bodies=cast(JSON, made)
                )
            step: SolidStep = SolidStep("plate", path)
            pair: SolidAssembly = SolidAssembly(
                "pair",
                (
                    Placed(step),
                    Placed(
                        step,
                        Placement((inches("2"), inches("0"), inches("0"))),
                    ),
                ),
            )
            with connect("headless") as transport:
                solidcraft = PyBind(transport)
                self.assertEqual(len(pair.build(solidcraft)), 1)
                listed: JSON = solidcraft.component.list(compact=True)
        parents: dict[str, str] = parents_of(listed)
        self.assertEqual(
            parents, {"Untitled": "", "pair": "Untitled", "plate": "pair"}
        )


if __name__ == "__main__":
    unittest.main()
