"""Checks of SolidCraft's replies, shared by the tests."""

import unittest

from scraftcam.pybind.scraftpybind import JSON, PyBind


# Function `totals()`:
def totals(properties: JSON) -> tuple[float, list[float], list[float]]:
    """Return a design's volume and its bounding box's corners.

    Arguments:
    * `properties` (`JSON`): What `component.properties()` returned.

    Returns:
    * (`tuple[float, list[float], list[float]]`): The volume (mm^3),
      and the box's lowest and highest corners (mm, X Y Z).
    """
    # Each level is checked as it is read, so that a change in the
    # reply fails here rather than deep in a test.
    assert isinstance(properties, dict)
    total: JSON = properties["total"]
    assert isinstance(total, dict)
    volume: JSON = total["volume_mm3"]
    box: JSON = total["bbox"]
    assert isinstance(volume, float) and isinstance(box, dict)
    low: JSON = box["min"]
    high: JSON = box["max"]
    assert isinstance(low, list) and isinstance(high, list)
    return (
        volume,
        [float(str(each)) for each in low],
        [float(str(each)) for each in high],
    )


# Function `assert_apart()`:
def assert_apart(
    case: unittest.TestCase, solidcraft: PyBind, names: list[str]
) -> None:
    """Check that no two of the bodies overlap, and all were checked.

    Arguments:
    * `case` (`unittest.TestCase`): The test that checks.
    * `solidcraft` (`PyBind`): The SolidCraft session.
    * `names` (`list[str]`): The bodies' names.
    """
    result: JSON = solidcraft.inspect.interference(bodies=names)
    assert isinstance(result, dict)
    case.assertEqual(result["checked"], len(names))
    case.assertEqual(result["interferences"], [])
    case.assertEqual(result["unchecked"], [])
