"""A few exposed functions, for trying the MCP server alone.

`python3 -m scraftcam.exposed.server` serves these when no module is
named, so the protocol can be tried before any GUI is exposed
(`T.mi~7` #509).
"""

from scraftcam import __version__
from scraftcam.exposed import exposed


@exposed.reads
def version() -> str:
    """Give scraftcam's version."""
    return __version__


@exposed.reads
def add(a: float, b: float) -> float:
    """Add {a} and {b}."""
    return a + b


@exposed.reads
def corners(count: int, size: float = 1.0) -> list[tuple[float, float]]:
    """List the corners of a square of side {size}, {count} of them.

    Arguments:
    * `count` (`int`):
        How many corners, 0 to 4, counterclockwise from the origin.
    * `size` (`float`):
        The side.

    Returns:
    * (`list[tuple[float, float]]`): the corners.
    """
    square: list[tuple[float, float]] = [
        (0.0, 0.0),
        (size, 0.0),
        (size, size),
        (0.0, size),
    ]
    return square[:count]
