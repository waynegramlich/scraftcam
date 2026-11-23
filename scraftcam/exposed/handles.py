"""Handles for live objects reached over MCP (#488, #507).

A live object (an `OutlineView`, a window) is named by its class and
a count in the order made, as `"OutlineView 1"`: the same on every
replay of a recording (#502), unlike `id()`.  Handles are held
weakly, so a closed window's handle simply goes; a Qt object whose
C++ side has been deleted is refused too.
"""

from __future__ import annotations

import sys
import weakref
from dataclasses import dataclass, field

from scraftcam.exposed.exposed import ExposedError


@dataclass(slots=True)
class Handles:
    """The handles of one session (reset when a replay starts).

    Constructor:
    * `Handles()`

    Attributes (alphabetized):
    * `counts` (`dict[str, int]`):
        The last count given, by class name.
    * `names` (`weakref.WeakKeyDictionary[object, str]`):
        Each object's handle.
    * `objects` (`weakref.WeakValueDictionary[str, object]`):
        Each handle's object.
    """

    # Remaining attributes (alphabetized):
    counts: dict[str, int] = field(init=False, default_factory=dict)
    names: weakref.WeakKeyDictionary[object, str] = field(
        init=False, default_factory=weakref.WeakKeyDictionary
    )
    objects: weakref.WeakValueDictionary[str, object] = field(
        init=False, default_factory=weakref.WeakValueDictionary
    )

    def handle(self, thing: object) -> str:
        """Give `thing`'s handle, making it the first time.

        Arguments:
        * `thing` (`object`):
            The live object (one that takes weak references).

        Returns:
        * (`str`): its handle, as `"OutlineView 1"`.
        """
        # An object already named keeps its name.
        known: str | None = self.names.get(thing)
        if known is not None:
            return known

        # Otherwise the next count of its class.
        kind: str = type(thing).__name__
        count: int = self.counts.get(kind, 0) + 1
        self.counts[kind] = count
        name: str = f"{kind} {count}"
        self.names[thing] = name
        self.objects[name] = thing
        return name

    def find(self, name: str) -> object:
        """Give the live object named `name`.

        Arguments:
        * `name` (`str`):
            Its handle, as `"OutlineView 1"`.

        Returns:
        * (`object`): the object.

        Raises:
        * `ExposedError`: when there is no such handle, or its object
          has gone.
        """
        # Gone from Python, or never named.
        thing: object = self.objects.get(name)
        if thing is None:
            kind: str
            number: str
            kind, _, number = name.rpartition(" ")
            last: int = self.counts.get(kind, 0)
            made: bool = number.isdigit() and 1 <= int(number) <= last
            why: str = "has gone" if made else "is not a handle"
            raise ExposedError(f"`{name}` {why}")

        # A Qt object whose C++ side was deleted (only checked when
        # Qt is loaded, so this module needs no Qt).
        shiboken: object = sys.modules.get("shiboken6")
        is_valid: object = getattr(shiboken, "isValid", None)
        if callable(is_valid) and not is_valid(thing):
            raise ExposedError(f"`{name}` has gone (deleted by Qt)")
        return thing

    def reset(self) -> None:
        """Forget every handle and count, as a replay starts."""
        self.counts.clear()
        self.names.clear()
        self.objects.clear()
