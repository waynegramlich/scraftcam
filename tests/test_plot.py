"""Tests for `plot.py`: run `python3 -m unittest -v`."""

import itertools
import json
import math
import re
import unittest
from typing import Any, cast

from scraftcam.gcode import CNC
from scraftcam.geometry import ArcSegment
from scraftcam.plot import (
    MAX_POINTS,
    PathMove,
    SpacePoint,
    command_moves,
    path_moves,
    path_steps,
    plot_html,
    read_gcode,
    sketch_path,
    sketch_steps,
)
from tests.test_gcode import milling
from tests.test_geometry import square


# Class `TestPlot`:
class TestPlot(unittest.TestCase):
    """The moves a plot draws, and the page that draws them."""

    # Method `TestPlot.test_moves()`:
    def test_moves(self) -> None:
        """Lines go straight, and arcs and helices are broken up."""
        cnc: CNC = milling()
        cnc.rapid(x=1.0, y=0.0)
        cnc.linear(z=-0.1)
        cnc.arc(
            ArcSegment((1.0, 0.0), (0.0, 1.0), (0.0, 0.0), 1.0, math.pi / 2),
            z=-0.2,
        )
        moves = path_moves(cnc)

        # The rapids start where X and Y are not known yet.
        self.assertEqual([move["g"] for move in moves], [1, 3])
        self.assertEqual(moves[0]["pts"], [[1.0, 0.0, 2.0], [1.0, 0.0, -0.1]])
        self.assertEqual((moves[0]["f"], moves[0]["tool"]), (12.0, 1))
        arc = moves[1]["pts"]
        self.assertEqual(len(arc), 19)
        for point in arc:
            self.assertAlmostEqual(math.hypot(point[0], point[1]), 1.0)
        self.assertAlmostEqual(arc[9][2], -0.15)
        self.assertEqual(arc[-1], [0.0, 1.0, -0.2])

    # Method `TestPlot.test_drilling()`:
    def test_cycle_with_no_axes(self) -> None:
        """A cycle with no X or Y drills where the tool is."""
        moves = command_moves(
            [
                {"G": 0, "Z": 1.0},
                {"G": 0, "X": 2.0, "Y": 3.0},
                {"G": 98},
                {"G": 83, "Z": -0.5, "R": 0.05, "Q": 0.1, "F": 4.0},
                {"G": 80},
                {"G": 0, "X": 4.0},
            ]
        )
        self.assertEqual(
            [move["pts"][-1] for move in moves],
            [
                [2.0, 3.0, 1.0],
                [2.0, 3.0, 0.05],
                [2.0, 3.0, -0.5],
                [2.0, 3.0, 1.0],
                [4.0, 3.0, 1.0],
            ],
        )

    def test_drilling(self) -> None:
        """A canned cycle is drawn as over, down, through and up."""
        cnc: CNC = milling()
        cnc.change_tool(2)
        cnc.rapid(x=0.0, y=0.0)
        cnc.drill([(1.0, 1.0), (2.0, 1.0)], -0.2)
        moves = path_moves(cnc)
        holes = [move for move in moves if move["g"] == 1]
        self.assertEqual(len(holes), 2)
        self.assertEqual(holes[1]["pts"], [[2.0, 1.0, 0.05], [2.0, 1.0, -0.2]])
        self.assertEqual((holes[1]["f"], holes[1]["tool"]), (4.0, 2))
        self.assertEqual(moves[-1]["pts"][-1], [2.0, 1.0, 1.0])

    # Method `TestPlot.test_read_gcode()`:
    def test_read_gcode(self) -> None:
        """A program's G-code reads back into the same moves."""
        cnc: CNC = milling()
        cnc.change_tool(2)
        cnc.rapid(x=0.0, y=0.0)
        cnc.drill([(1.0, 1.0), (2.0, 1.0)], -0.2)
        cnc.change_tool(1)
        cnc.rapid(x=1.0, y=0.0)
        cnc.linear(z=-0.1)
        cnc.arc(
            ArcSegment((1.0, 0.0), (0.0, 1.0), (0.0, 0.0), 1.0, math.pi / 2),
            z=-0.2,
        )
        commands = read_gcode(cnc.gcode())
        self.assertEqual(len(commands), len(cnc.commands))
        self.assertEqual(commands[0], {"comment": cnc.name})
        expected = path_moves(cnc)
        moves = command_moves(commands)
        self.assertEqual(len(moves), len(expected))
        for move, want in zip(moves, expected, strict=True):
            self.assertEqual(
                (move["g"], move["line"], move["tool"]),
                (want["g"], want["line"], want["tool"]),
            )
            self.assertAlmostEqual(move["f"], want["f"])
            self.assertEqual(len(move["pts"]), len(want["pts"]))
            for point, want_point in zip(
                move["pts"], want["pts"], strict=True
            ):
                for value, want_value in zip(point, want_point, strict=True):
                    self.assertAlmostEqual(value, want_value, places=3)

    # Method `TestPlot.test_page()`:
    def test_page(self) -> None:
        """The page carries the program, its moves and the outlines."""
        cnc: CNC = milling()
        cnc.pocket(square(1.0, 0.125), -0.2, 0.1)
        cnc.finish()
        page: str = plot_html(cnc, [(square(1.0, 0.125), 0.0)], "A </b> test")
        self.assertIn("<title>A &lt;/b&gt; test</title>", page)
        found = re.search(r'id="path-data">(.*?)</script>', page, re.DOTALL)
        assert found is not None
        data = json.loads(found.group(1))
        self.assertEqual(data["lines"], cnc.gcode().splitlines())
        self.assertEqual(len(data["outlines"]), 1)
        self.assertEqual(len(data["outlines"][0]["pts"]), 8 * 8)
        self.assertGreater(len(data["moves"]), 10)

    # Method `TestPlot.test_sketch()`:
    def test_sketch(self) -> None:
        """The path goes into one 3D sketch per operation and kind."""
        cnc: CNC = milling()
        cnc.profile(square(1.0, 0.25), -0.1, 0.1)
        cnc.finish()
        fake: FakeSolidCraft = FakeSolidCraft()
        names: list[str] = sketch_path(cast(Any, fake), cnc, 25.4)
        self.assertEqual(
            names,
            [
                "Profile Square outside to Z-0.1 cuts",
                "Profile Square outside to Z-0.1 rapids",
            ],
        )
        self.assertEqual(len(fake.transport.batches), 2)
        steps: list[dict[str, Any]] = fake.transport.batches[0]
        commands: list[str] = [step["command"] for step in steps]
        self.assertEqual(commands[:2], ["sketch.create", "sketch.options"])
        self.assertEqual(commands[-1], "sketch.finish")
        self.assertTrue(steps[1]["params"]["sketch_3d"])
        self.assertEqual(
            set(commands[2:-1]), {"sketch.line3d"}, "only 3D lines"
        )

        # The cuts, in millimeters: down from above the part to the
        # depth, then around (the corners as points along them).
        first: list[list[float]] = steps[2]["params"]["points"]
        self.assertAlmostEqual(first[0][2], 1.0 * 25.4)
        self.assertAlmostEqual(first[1][2], 0.05 * 25.4)
        self.assertAlmostEqual(first[2][2], -0.1 * 25.4)
        self.assertGreater(len(first), 20)

    def test_jumps_split_polylines(self) -> None:
        """A jump starts a new `sketch.line3d`; joined moves share one."""
        moves: list[PathMove] = [
            _move([[0, 0, 0], [1, 0, 0]]),
            _move([[1, 0, 0], [1, 1, 0]]),
            _move([[5, 5, 0], [6, 5, 0]]),
            _move([[6, 5, 0], [6, 5, 0]]),
        ]
        steps: list[dict[str, Any]] = path_steps(moves, 2.0)
        self.assertEqual(
            [step["params"] for step in steps],
            [
                {"points": [[0, 0, 0], [2, 0, 0], [2, 2, 0]]},
                {"points": [[10, 10, 0], [12, 10, 0]]},
            ],
        )

    def test_long_polylines_split(self) -> None:
        """A polyline longer than `MAX_POINTS` shares its split points."""
        count: int = 2 * MAX_POINTS + 10
        points: list[SpacePoint] = [[i, 0.0, 0.0] for i in range(count)]
        steps: list[dict[str, Any]] = path_steps([_move(points)], 1.0)
        pieces: list[list[SpacePoint]] = [
            step["params"]["points"] for step in steps
        ]
        self.assertEqual(len(pieces), 3)
        piece: list[SpacePoint]
        for piece in pieces:
            self.assertLessEqual(len(piece), MAX_POINTS)
        first: list[SpacePoint]
        second: list[SpacePoint]
        for first, second in itertools.pairwise(pieces):
            self.assertEqual(first[-1], second[0])
        self.assertEqual(sum(len(p) - 1 for p in pieces), count - 1)

    def test_sketch_steps(self) -> None:
        """A batch is create, options, drawing, finish, and maybe hide."""
        steps: list[dict[str, Any]] = sketch_steps("T01 cuts", [], hide=True)
        self.assertEqual(
            [step["command"] for step in steps],
            [
                "sketch.create",
                "sketch.options",
                "sketch.finish",
                "browser.visibility",
            ],
        )
        self.assertEqual(len(sketch_steps("T01 cuts", [])), 3)


# Function `_move()`:
def _move(points: list[SpacePoint]) -> PathMove:
    """Return a straight cut for a test.

    Arguments:
    * `points` (`list[SpacePoint]`): Its points.

    Returns:
    * (`PathMove`): The move.
    """
    return {"g": 1, "line": 0, "pts": points, "f": 1.0, "tool": 1}


# Class `FakeTransport`:
# A stand-in with only what the code under test uses.
class FakeTransport:  # pylint: disable=too-few-public-methods
    """Stands in for a GUI's transport, recording `engine.batch` steps.

    Attributes:
    * `batches` (`list[list[dict[str, Any]]]`): Each batch's steps.
    """

    # Method `FakeTransport.__init__()`:
    def __init__(self) -> None:
        """Start with no batches."""
        self.batches: list[list[dict[str, Any]]] = []

    # Method `FakeTransport.request()`:
    def request(self, method: str, params: dict[str, Any]) -> Any:
        """Record a batch, and answer that every step ran.

        Arguments:
        * `method` (`str`): The method (`engine.batch`).
        * `params` (`dict[str, Any]`): Its parameters.

        Returns:
        * (`Any`): The reply: every step completed.
        """
        assert method == "engine.batch"
        self.batches.append(params["commands"])
        return {"completed": len(params["commands"])}


# Class `FakeSolidCraft`:
# Its commands come from `__getattr__()`, so `pylint` sees no public
# methods.
class FakeSolidCraft:  # pylint: disable=too-few-public-methods
    """Stands in for `PyBind`, recording the sketch commands.

    Attributes:
    * `calls` (`list[tuple[str, dict[str, Any]]]`): Each command's name
      and arguments.
    * `sketch` (`FakeSolidCraft`):
      Itself, for `solidcraft.sketch.X()`.
    * `transport` (`FakeTransport`): Where batches go.
    """

    # Method `FakeSolidCraft.__init__()`:
    def __init__(self) -> None:
        """Start with no calls."""
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.sketch: FakeSolidCraft = self
        self.transport: FakeTransport = FakeTransport()

    # Method `FakeSolidCraft.__getattr__()`:
    def __getattr__(self, name: str) -> Any:
        """Return a function that records a call of a command.

        Arguments:
        * `name` (`str`): The command's name.

        Returns:
        * (`Any`): The recording function.
        """

        # Function `record()`:
        def record(**arguments: Any) -> dict[str, Any]:
            """Record a call.

            Arguments:
            * `arguments` (`Any`): The command's arguments.

            Returns:
            * (`dict[str, Any]`): An empty result.
            """
            self.calls.append((name, arguments))
            return {}

        return record


if __name__ == "__main__":
    unittest.main()
