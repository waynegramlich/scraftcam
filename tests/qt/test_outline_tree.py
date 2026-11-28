"""Tests of flat outlines as trees (`T.sa~6.11` #S5): polygons'
parents and heights, circles, cut lines and their sections."""

import unittest
from pathlib import Path
from typing import cast

from scraftcam.appearance import STANDARD_HATCHES
from scraftcam.diagram import TEXT, Stroke, Weight
from scraftcam.gui.outline_diagram import outline_sheet
from scraftcam.gui.outline_editor import (
    Drawing,
    OutlineEditor,
    drawing_from_text,
)
from scraftcam.gui.outline_file import (
    Outline,
    OutlineError,
    outline_from_text,
    outline_text,
)
from scraftcam.gui.outline_polygon import outline_cacheable, outline_extruded
from scraftcam.gui.outline_section import (
    Shape,
    material,
    section_strokes,
    spans,
)
from scraftcam.gui.values import evaluate, formula_names, real_corners
from scraftcam.shops import EXAMPLE_SHOP
from scraftcam.solid import Solid, SolidAssembly, SolidRoundedPolygon
from tests import qt_app

# The shipped vise block: a block, a slot, two counterbored holes and
# a cut line through them.
VISE_BLOCK: Path = (
    EXAMPLE_SHOP / "tooling" / "vises" / "vise_block.outline.toml"
)

# A square from 0 to 10, as drawn.
SQUARE: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (10.0, 0.0),
    (10.0, 10.0),
    (0.0, 10.0),
)


# Function `vise_block()`:
def vise_block() -> Outline:
    """Return the shipped vise block's outline."""
    return outline_from_text(VISE_BLOCK.read_text(), str(VISE_BLOCK))


# Class `FileTest`:
class FileTest(unittest.TestCase):
    """Parents, heights, circles and cut lines in outline files."""

    def test_round_trip(self) -> None:
        """The vise block is written back exactly as it is read."""
        text: str = VISE_BLOCK.read_text()
        outline: Outline = outline_from_text(text, "vise")
        self.assertEqual(outline_text(outline), text)
        self.assertEqual(
            [(each.name, each.parent) for each in outline.polygons],
            [("block", ""), ("slot", "block")],
        )
        self.assertEqual(
            [(each.name, each.parent) for each in outline.circles],
            [
                ("bore1", "block"),
                ("hole1", "bore1"),
                ("bore2", "block"),
                ("hole2", "bore2"),
            ],
        )
        self.assertEqual(outline.cuts[0].vertices, ["V11", "V12", "V13"])
        self.assertTrue(outline.nested("hole1", "block"))
        self.assertFalse(outline.nested("hole1", "bore2"))

    def test_refused(self) -> None:
        """A circle about no vertex, a parent that is no polygon, a
        loop of parents and a cut line in a revolved outline are each
        named."""
        text: str = VISE_BLOCK.read_text()
        bad: dict[str, str] = {
            'center = "V9"': "is not a vertex",
            'parent = "bore1"': "is not a polygon",
            'parent = "block"\nz = "H - SD"': "go round in a loop",
            "revolve = false": "its own section",
        }
        broken: dict[str, str] = {
            'center = "V9"': 'center = "V99"',
            'parent = "bore1"': 'parent = "nothing"',
            'parent = "block"\nz = "H - SD"': 'parent = "slot"\nz = "H - SD"',
            "revolve = false": "revolve = true",
        }
        old: str
        for old, said in bad.items():
            with self.subTest(old=old):
                self.assertIn(old, text)
                with self.assertRaisesRegex(OutlineError, said):
                    outline_from_text(
                        text.replace(old, broken[old], 1), "vise"
                    )


# Class `SolidTest`:
class SolidTest(unittest.TestCase):
    """Flat outlines made into extruded trees."""

    def test_vise_block(self) -> None:
        """The block goes up 1-1/2 in; the slot and counterbores cut
        down to 1 in, the clearance holes through to 0."""
        solid: Solid = outline_extruded(vise_block(), "vise_block")
        assert isinstance(solid, SolidRoundedPolygon)
        self.assertAlmostEqual(solid.root.z.mm(), 38.1)
        self.assertEqual(
            [
                (child.polygon.name, round(child.z.mm(), 6))
                for child in solid.root.children
            ],
            [
                ("vise_block_slot", 25.4),
                ("vise_block_bore1", 25.4),
                ("vise_block_bore2", 25.4),
            ],
        )
        self.assertEqual(solid.root.children[1].children[0].z.mm(), 0.0)
        shape: dict[str, object] = cast(
            dict[str, object], outline_cacheable(vise_block(), "vise").shape
        )
        self.assertEqual(shape["kind"], "outline_extruded")

    def test_roots_and_missing_z(self) -> None:
        """Two roots make an assembly; a shape with no `z` is named."""
        outline: Outline = vise_block()
        outline.circles[0].parent = ""
        outline.circles[0].z = "1 in"
        self.assertIsInstance(
            outline_extruded(outline, "vise_block"), SolidAssembly
        )
        outline.polygons[1].z = ""
        with self.assertRaisesRegex(ValueError, "slot: has no z"):
            outline_extruded(outline, "vise_block")

    def test_cut_needs_no_dimensions(self) -> None:
        """A cut line's corners are given as drawn; the rest placed."""
        outline: Outline = vise_block()
        self.assertIsNone(
            real_corners(outline.points, outline.letters, outline.dimensions)
        )
        corners: list[tuple[float, float]] | None = real_corners(
            outline.points,
            outline.letters,
            outline.dimensions,
            needed=outline.solid_corners(),
        )
        assert corners is not None
        self.assertAlmostEqual(corners[1][0], 6 * 25.4)
        self.assertEqual(corners[10], outline.points[10])


# Class `FormulaTest`:
class FormulaTest(unittest.TestCase):
    """Inches in formulas (#862)."""

    def test_inches(self) -> None:
        """`in` is a unit, not Python's word."""
        self.assertAlmostEqual(evaluate("1/2 in + D", {"D": 1.0}), 13.7)
        self.assertEqual(evaluate("0 in", {}), 0.0)
        self.assertEqual(formula_names("H - 1/2 in"), ["H"])


# Class `SectionTest`:
class SectionTest(unittest.TestCase):
    """Sections along cut lines."""

    def test_spans(self) -> None:
        """A line across a square is inside it once, clipped."""
        self.assertEqual(
            spans(SQUARE, (-5.0, 5.0), (15.0, 5.0)), [(5.0, 15.0)]
        )
        self.assertEqual(spans(SQUARE, (2.0, 5.0), (8.0, 5.0)), [(0.0, 6.0)])
        self.assertEqual(spans(SQUARE, (-5.0, 20.0), (15.0, 20.0)), [])

    def test_material(self) -> None:
        """A child going up adds, one going down cuts, a grandchild
        going down from a cut cuts on."""
        shapes: list[Shape] = [
            Shape("block", "", 20.0, SQUARE),
            Shape("boss", "block", 25.0, SQUARE),
            Shape("bore", "block", 15.0, SQUARE),
            Shape("hole", "bore", 0.0, SQUARE),
        ]
        everywhere: dict[str, bool] = {shape.name: True for shape in shapes}
        self.assertEqual(
            material(shapes, everywhere | {"hole": False, "bore": False}),
            [(0.0, 25.0)],
        )
        self.assertEqual(
            material(shapes, everywhere | {"boss": False, "hole": False}),
            [(0.0, 15.0)],
        )
        self.assertEqual(material(shapes, everywhere | {"boss": False}), [])

    def test_section_strokes(self) -> None:
        """A section is hatched, outlined thick and titled."""
        strokes: list[Stroke] = section_strokes(
            "A",
            ((-5.0, 5.0), (15.0, 5.0), (5.0, 0.0)),
            [Shape("block", "", 2.0, SQUARE)],
            scale=1.0,
            corner=(0.0, 0.0),
            height=1.0,
            hatch=STANDARD_HATCHES[0],
        )
        self.assertEqual(
            sum(1 for stroke in strokes if stroke.hatch is not None), 1
        )
        self.assertEqual(
            sum(1 for stroke in strokes if stroke.weight == Weight.THICK), 4
        )
        self.assertTrue(any(stroke.role == TEXT for stroke in strokes))

    def test_vise_block_sheet(self) -> None:
        """The vise block's diagram holds its section."""
        strokes: tuple[Stroke, ...] = outline_sheet(vise_block()).strokes
        self.assertTrue(any(stroke.hatch is not None for stroke in strokes))


# Class `EditorTest`:
class EditorTest(unittest.TestCase):
    """[New Circle], [Cut Line] and deleting what they stand on."""

    def test_new_circle_and_cut(self) -> None:
        """A circle stands on the chosen corner's polygon; a cut line
        crosses it; deleting a center takes its circle, its child
        standing on its parent instead."""
        drawing: Drawing = drawing_from_text(VISE_BLOCK.read_text(), "vise")
        self.assertEqual(drawing.new_circle(0), "C2")
        self.assertEqual(drawing.circles[-1].parent, "block")
        self.assertEqual(drawing.new_cut(0), "B")
        self.assertEqual(len(drawing.cuts[-1].vertices), 3)
        drawing.remove(drawing.names.index("V9"))
        self.assertEqual(
            [circle.name for circle in drawing.circles],
            ["bore2", "hole2", "C2"],
        )
        drawing.remove(drawing.names.index("V11"))
        self.assertEqual([cut.name for cut in drawing.cuts], ["B"])

    def test_nested_do_not_overlap(self) -> None:
        """A slot inside its block is not called an overlap."""
        editor: OutlineEditor = OutlineEditor(
            drawing_from_text(VISE_BLOCK.read_text(), "vise")
        )
        self.assertEqual(editor.overlap_problem(), "")
        editor.deleteLater()
        qt_app.process_events()


if __name__ == "__main__":
    unittest.main()
