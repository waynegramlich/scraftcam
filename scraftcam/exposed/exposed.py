"""The registry of exposed functions, and the three ways in.

A function is exposed by marking it `@exposed.reads` (it only looks)
or `@exposed.changes` (it changes something: a file, the drawing, the
selection).  Its type hints and docstring are its manual: `find()`
searches the names and first docstring lines, `describe()` gives the
signature and the whole docstring, and `call()` checks the arguments
against the hints and runs it.

The first docstring line is also the step's narration
(`narration()`): any `{name}` in it is filled in with that argument,
as in "Drag corner {index} to {x}, {y}." (`T.mi~7` #494).
"""

from __future__ import annotations

import inspect
import string
import types
import typing
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, TypeVar

# The two kinds of exposed function (#489).
Kind = Literal["reads", "changes"]

# Any function, kept as it is by the decorators.
Function = TypeVar("Function", bound=Callable[..., object])


class ExposedError(Exception):
    """A bad name or bad arguments: the message says which and why."""


@dataclass(frozen=True, slots=True)
class Exposed:
    """One exposed function.

    Attributes:
    * `name` (`str`):
        Its full name, `MODULE.QUALNAME` (e.g.
        `scraftcam.gui.outline_editor.drag`).
    * `function` (`Callable[..., object]`):
        The function itself.
    * `kind` (`Kind`):
        `"reads"` or `"changes"`.
    * `docstring` (`str`):
        Its cleaned docstring (`inspect.getdoc()`).
    * `narration` (`str`):
        The docstring's first line, the step's narration template.

    Constructor:
    * `Exposed(name, function, kind, docstring, narration)`
    """

    # Constructor arguments:
    name: str = field(init=True)
    function: Callable[..., object] = field(init=True, repr=False)
    kind: Kind = field(init=True)
    docstring: str = field(init=True)
    narration: str = field(init=True)


# Every exposed function, by its full name.
REGISTRY: dict[str, Exposed] = {}


def _register(function: Function, kind: Kind) -> Function:
    """Add `function` to `REGISTRY` and give it back unchanged.

    Arguments:
    * `function` (`Function`):
        The function being exposed.
    * `kind` (`Kind`):
        `"reads"` or `"changes"`.

    Returns:
    * (`Function`): `function` itself.

    Raises:
    * `ExposedError`: when it has no docstring, or its name is taken.
    """
    # The docstring is the manual: refuse a function without one.
    docstring: str = inspect.getdoc(function) or ""
    name: str = f"{function.__module__}.{function.__qualname__}"
    if not docstring:
        raise ExposedError(f"`{name}` has no docstring to expose")

    # A second function under one name is a mistake, not a reload.
    old: Exposed | None = REGISTRY.get(name)
    if old is not None and old.function is not function:
        raise ExposedError(f"`{name}` is exposed twice")
    first_line: str = docstring.splitlines()[0]
    REGISTRY[name] = Exposed(name, function, kind, docstring, first_line)
    return function


def reads(function: Function) -> Function:
    """Expose `function` as one that only looks.

    Arguments:
    * `function` (`Function`):
        The function being exposed.

    Returns:
    * (`Function`): `function` itself.
    """
    return _register(function, "reads")


def changes(function: Function) -> Function:
    """Expose `function` as one that changes something.

    Arguments:
    * `function` (`Function`):
        The function being exposed.

    Returns:
    * (`Function`): `function` itself.
    """
    return _register(function, "changes")


def find(text: str = "") -> list[str]:
    """Find the exposed functions whose name or narration has `text`.

    Arguments:
    * `text` (`str`):
        What to look for, in any case; empty finds everything.

    Returns:
    * (`list[str]`): one `NAME (KIND): NARRATION` line each, sorted.
    """
    # Match the name and narration, ignoring case.
    wanted: str = text.lower()
    lines: list[str] = []
    exposed: Exposed
    for exposed in REGISTRY.values():
        if wanted in exposed.name.lower() or (
            wanted in exposed.narration.lower()
        ):
            lines.append(
                f"{exposed.name} ({exposed.kind}): {exposed.narration}"
            )
    return sorted(lines)


def lookup(name: str) -> Exposed:
    """Return the exposed function named `name`.

    Arguments:
    * `name` (`str`):
        Its full name, or any unique ending of it after a `.` (e.g.
        `outline_editor.drag` or `drag`).

    Returns:
    * (`Exposed`): the one it names.

    Raises:
    * `ExposedError`: when it names none, or more than one.
    """
    # An exact name wins; otherwise a unique dotted ending.
    exact: Exposed | None = REGISTRY.get(name)
    if exact is not None:
        return exact
    matches: list[str] = sorted(
        full for full in REGISTRY if full.endswith(f".{name}")
    )
    if not matches:
        raise ExposedError(f"nothing exposed is named `{name}`")
    if len(matches) > 1:
        raise ExposedError(f"`{name}` could be any of: {', '.join(matches)}")
    return REGISTRY[matches[0]]


def describe(name: str) -> str:
    """Describe an exposed function: signature, kind and docstring.

    Arguments:
    * `name` (`str`):
        Its name, as `lookup()` takes it.

    Returns:
    * (`str`): its signature line, its kind, and its docstring.
    """
    exposed: Exposed = lookup(name)
    signature: inspect.Signature = inspect.signature(
        exposed.function, eval_str=True
    )
    return f"{exposed.name}{signature} ({exposed.kind})\n\n{exposed.docstring}"


def _fits(value: object, hint: object) -> bool:
    """Tell whether `value` is of the plain JSON kind `hint`.

    Arguments:
    * `value` (`object`):
        The value as it came from JSON.
    * `hint` (`object`):
        A plain type hint; any hint not a JSON kind fits anything,
        until its text form is decided (#488).

    Returns:
    * (`bool`): whether it fits.
    """
    # `bool` is an `int` in Python, but not in JSON.
    is_number: bool = isinstance(value, (int, float)) and not isinstance(
        value, bool
    )
    fits: dict[object, bool] = {
        None: value is None,
        types.NoneType: value is None,
        bool: isinstance(value, bool),
        int: is_number and isinstance(value, int),
        float: is_number,
        str: isinstance(value, str),
        dict: isinstance(value, dict),
    }
    origin: object = typing.get_origin(hint) or hint
    return fits.get(origin, True)


def _check_items(name: str, value: object, hint: object) -> None:
    """Check a JSON list against a `list[...]` or `tuple[...]` hint.

    Arguments:
    * `name` (`str`):
        The argument's name, for the message.
    * `value` (`object`):
        The value as it came from JSON (JSON has no tuples, so a list
        stands in for one).
    * `hint` (`object`):
        The `list` or `tuple` hint.

    Raises:
    * `ExposedError`: when it, or any item, does not fit.
    """
    # A fixed tuple needs exactly its items; else all share one hint.
    if not isinstance(value, list):
        raise ExposedError(f"`{name}` = {value!r} is not a list")
    members: tuple[object, ...] = typing.get_args(hint)
    item_hints: tuple[object, ...]
    fixed: bool = typing.get_origin(hint) is tuple and (
        bool(members) and members[-1] is not Ellipsis
    )
    if fixed:
        if len(value) != len(members):
            raise ExposedError(
                f"`{name}` needs {len(members)} items, not {len(value)}"
            )
        item_hints = members
    else:
        item_hints = tuple(members[:1] or (object,)) * len(value)

    # Check each item against its own hint.
    index: int
    item: object
    item_hint: object
    for index, (item, item_hint) in enumerate(
        zip(value, item_hints, strict=True)
    ):
        _check(f"{name}[{index}]", item, item_hint)


def _misfit(name: str, value: object, hint: object) -> ExposedError:
    """Make the error for a `value` that does not fit its `hint`.

    Arguments:
    * `name` (`str`):
        The argument's name, for the message.
    * `value` (`object`):
        The value as it came from JSON.
    * `hint` (`object`):
        The type hint, named as written (`float`, not `<class
        'float'>`; #513).

    Returns:
    * (`ExposedError`): the error, for the caller to raise.
    """
    # `formatannotation()` gives a class's bare name, and drops
    # `typing.` from the rest.
    hint_text: str = inspect.formatannotation(hint)
    return ExposedError(f"`{name}` = {value!r} is not of type `{hint_text}`")


def _check(name: str, value: object, hint: object) -> None:
    """Check that the JSON `value` fits the type `hint`.

    Only JSON's own kinds are checked (`bool`, `int`, `float`, `str`,
    `None`, and `list`/`tuple`/`dict` of them, and unions); any other
    hint is passed through, until its text form is decided (#488).

    Arguments:
    * `name` (`str`):
        The argument's name, for the message.
    * `value` (`object`):
        The value as it came from JSON.
    * `hint` (`object`):
        The argument's type hint.

    Raises:
    * `ExposedError`: when it does not fit.
    """
    # A union fits when any one of its members does.
    origin: object = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        member: object
        for member in typing.get_args(hint):
            try:
                _check(name, value, member)
            except ExposedError:
                continue
            return
        raise _misfit(name, value, hint)

    # Lists and tuples item by item; the rest by their plain kind.
    if origin in (list, tuple):
        _check_items(name, value, hint)
    elif hint is not inspect.Parameter.empty and not _fits(value, hint):
        raise _misfit(name, value, hint)


def call(name: str, arguments: dict[str, object]) -> object:
    """Run an exposed function with `arguments` checked against it.

    Arguments:
    * `name` (`str`):
        Its name, as `lookup()` takes it.
    * `arguments` (`dict[str, object]`):
        The arguments by name, as they came from JSON.

    Returns:
    * (`object`): whatever the function returns.

    Raises:
    * `ExposedError`: when the name or arguments are bad.
    """
    # Bind the arguments by name, as JSON gives them.
    exposed: Exposed = lookup(name)
    signature: inspect.Signature = inspect.signature(
        exposed.function, eval_str=True
    )
    try:
        bound: inspect.BoundArguments = signature.bind(**arguments)
    except TypeError as error:
        raise ExposedError(f"`{exposed.name}`: {error}") from error

    # Check each one against its hint, then run it.
    argument: str
    value: object
    for argument, value in bound.arguments.items():
        _check(argument, value, signature.parameters[argument].annotation)
    return exposed.function(*bound.args, **bound.kwargs)


def narration(name: str, arguments: dict[str, object]) -> str:
    """Return a step's narration line, its `{name}`s filled in.

    Arguments:
    * `name` (`str`):
        Its name, as `lookup()` takes it.
    * `arguments` (`dict[str, object]`):
        The step's arguments by name; a missing one is left as
        `{name}`.

    Returns:
    * (`str`): the filled in narration.
    """
    # Fill in only the plain `{name}` fields the arguments have.
    template: str = lookup(name).narration
    parts: list[str] = []
    literal: str
    field_name: str | None
    for literal, field_name, _spec, _conversion in string.Formatter().parse(
        template
    ):
        parts.append(literal)
        if field_name is not None:
            parts.append(
                str(arguments[field_name])
                if field_name in arguments
                else f"{{{field_name}}}"
            )
    return "".join(parts)
