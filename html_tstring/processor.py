import random
import string
import typing as t
from functools import lru_cache
from string.templatelib import Interpolation, Template

from .nodes import (
    Element,
    Fragment,
    Node,
    Text,
)
from .parser import parse_html
from .utils import format_interpolation

# --------------------------------------------------------------------------
# Instrumentation, Parsing, and Caching
# --------------------------------------------------------------------------

_PLACEHOLDER_PREFIX = f"t🐍-{''.join(random.choices(string.ascii_lowercase, k=4))}-"
_PP_LEN = len(_PLACEHOLDER_PREFIX)


def _placeholder(i: int) -> str:
    """Generate a placeholder for the i-th interpolation."""
    return f"{_PLACEHOLDER_PREFIX}{i}"


def _placholder_index(s: str) -> int:
    """Extract the index from a placeholder string."""
    return int(s[_PP_LEN:])


def _instrument(strings: t.Sequence[str]) -> str:
    """
    Join the strings with placeholders in between where interpolations go.

    This is used to prepare the template string for parsing, so that we can
    later substitute the actual interpolated values into the parse tree.

    The placeholders are chosen to be unlikely to collide with typical HTML
    content.
    """
    count = len(strings)

    # TODO: special case callables() so that we use the same placeholder
    # to open *and* close tags.

    def _placeholder_or_final(i: int, s: str) -> str:
        """Return the string with a placeholder if not the last one."""
        # There are always count-1 placeholders between count strings.
        return f"{s}{_placeholder(i)}" if i < count - 1 else s

    return "".join(_placeholder_or_final(i, s) for i, s in enumerate(strings))


@lru_cache()
def _instrument_and_parse(strings: tuple[str, ...]) -> Node:
    """
    Instrument the strings and parse the resulting HTML.

    The result is cached to avoid re-parsing the same template multiple times.
    """
    instrumented = _instrument(strings)
    return parse_html(instrumented)


# --------------------------------------------------------------------------
# Placeholder Substitution
# --------------------------------------------------------------------------


def _substitute_attrs(
    attrs: dict[str, str | None], interpolations: tuple[Interpolation, ...]
) -> dict[str, str | None]:
    new_attrs: dict[str, str | None] = {}
    for key, value in attrs.items():
        if key.startswith(_PLACEHOLDER_PREFIX):
            index = _placholder_index(key)
            interpolation = interpolations[index]
            value = format_interpolation(interpolation)
            if not isinstance(value, str):
                raise ValueError(
                    f"Attribute interpolation must be a string, got: {value!r}"
                )
            new_attrs[key] = value
        else:
            new_attrs[key] = value
    return new_attrs


def _substitute_node(p_node: Node, interpolations: tuple[Interpolation, ...]) -> Node:
    match p_node:
        case Text(text) if str(text).startswith(_PLACEHOLDER_PREFIX):
            index = _placholder_index(str(text))
            interpolation = interpolations[index]
            value = format_interpolation(interpolation)
            match value:
                case str():
                    return Text(value)
                case Node():
                    return value
                case Template():
                    return html(value)
                case _:
                    raise ValueError(f"Invalid interpolation value: {value!r}")
        case Element(tag=tag, attrs=attrs, children=children):
            new_attrs = _substitute_attrs(attrs, interpolations)
            new_children = [_substitute_node(c, interpolations) for c in children]
            return Element(tag=tag, attrs=new_attrs, children=new_children)
        case Fragment(children=children):
            new_children = [_substitute_node(c, interpolations) for c in children]
            return Fragment(children=new_children)
        case _:
            return p_node


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def html(template: Template) -> Node:
    """Create an HTML element from a string."""
    # Parse the HTML, returning a tree of nodes with placeholders
    # where interpolations go.
    p_node = _instrument_and_parse(template.strings)
    return _substitute_node(p_node, template.interpolations)
