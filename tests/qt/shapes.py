"""Shapes shared by the tests: a house, a box with a roof on it."""

# The house: a 4 x 4 box from the origin (corners 0-3) and the apex
# of its roof (corner 4), 2 above the box's top edge.
HOUSE: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (4.0, 0.0),
    (4.0, 4.0),
    (0.0, 4.0),
    (2.0, 6.0),
)
