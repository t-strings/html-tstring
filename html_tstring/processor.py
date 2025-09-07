import random
import string
import typing as t
from collections.abc import Iterable
from functools import lru_cache
from string.templatelib import Interpolation, Template

from markupsafe import Markup

from .classnames import classnames
from .nodes import Element, Fragment, HasHTMLDunder, Node, Text
from .parser import parse_html_iter
from .utils import format_interpolation as base_format_interpolation

# --------------------------------------------------------------------------
# Value formatting
# --------------------------------------------------------------------------


def _format_safe(value: object, format_spec: str) -> str:
    assert format_spec == "safe"
    return Markup(value)


CUSTOM_FORMATTERS = (("safe", _format_safe),)


def format_interpolation(interpolation: Interpolation) -> object:
    return base_format_interpolation(
        interpolation,
        formatters=CUSTOM_FORMATTERS,
    )


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


def _instrument(strings: tuple[str, ...]) -> t.Iterable[str]:
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

    for i, s in enumerate(strings):
        yield s
        # There are always count-1 placeholders between count strings.
        if i < count - 1:
            yield _placeholder(i)


@lru_cache()
def _instrument_and_parse(strings: tuple[str, ...]) -> Node:
    """
    Instrument the strings and parse the resulting HTML.

    The result is cached to avoid re-parsing the same template multiple times.
    """
    instrumented = _instrument(strings)
    return parse_html_iter(instrumented)


# --------------------------------------------------------------------------
# Placeholder Substitution
# --------------------------------------------------------------------------


def _force_dict(value: t.Any, *, kind: str) -> dict:
    """Try to convert a value to a dict, raising TypeError if not possible."""
    try:
        return dict(value)
    except (TypeError, ValueError):
        raise TypeError(
            f"Cannot use {type(value).__name__} as value for {kind} attributes"
        ) from None


def _substitute_aria_attrs(value: object) -> t.Iterable[tuple[str, str | None]]:
    """Produce aria-* attributes based on the interpolated value for "aria"."""
    d = _force_dict(value, kind="aria")
    for sub_k, sub_v in d.items():
        if sub_v is True:
            yield f"aria-{sub_k}", "true"
        elif sub_v is False:
            yield f"aria-{sub_k}", "false"
        elif sub_v is None:
            pass
        else:
            yield f"aria-{sub_k}", str(sub_v)


def _substitute_data_attrs(value: object) -> t.Iterable[tuple[str, str | None]]:
    """Produce data-* attributes based on the interpolated value for "data"."""
    d = _force_dict(value, kind="data")
    for sub_k, sub_v in d.items():
        if sub_v is True:
            yield f"data-{sub_k}", None
        elif sub_v not in (False, None):
            yield f"data-{sub_k}", str(sub_v)


def _substitute_class_attr(value: object) -> t.Iterable[tuple[str, str | None]]:
    """Substitute a class attribute based on the interpolated value."""
    yield ("class", classnames(value))


def _substitute_style_attr(value: object) -> t.Iterable[tuple[str, str | None]]:
    """Substitute a style attribute based on the interpolated value."""
    try:
        d = _force_dict(value, kind="style")
        style_str = "; ".join(f"{k}: {v}" for k, v in d.items())
        yield ("style", style_str)
    except TypeError:
        yield ("style", str(value))


def _substitute_spread_attrs(value: object) -> t.Iterable[tuple[str, str | None]]:
    """
    Substitute a spread attribute based on the interpolated value.

    A spread attribute is one where the key is a placeholder, indicating that
    the entire attribute set should be replaced by the interpolated value.
    The value must be a dict or iterable of key-value pairs.
    """
    d = _force_dict(value, kind="spread")
    for sub_k, sub_v in d.items():
        yield from _substitute_attr(sub_k, sub_v)


# A collection of custom handlers for certain attribute names that have
# special semantics. This is in addition to the special-casing in
# _substitute_attr() itself.
CUSTOM_ATTR_HANDLERS = {
    "class": _substitute_class_attr,
    "data": _substitute_data_attrs,
    "style": _substitute_style_attr,
    "aria": _substitute_aria_attrs,
}


def _substitute_attr(
    key: str,
    value: object,
) -> t.Iterable[tuple[str, str | None]]:
    """
    Substitute a single attribute based on its key and the interpolated value.

    A single parsed attribute with a placeholder may result in multiple
    attributes in the final output, for instance if the value is a dict or
    iterable of key-value pairs. Likewise, a value of False will result in
    the attribute being omitted entirely; nothing is yielded in that case.
    """
    # Special handling for certain attribute names that have special semantics
    if custom_handler := CUSTOM_ATTR_HANDLERS.get(key):
        yield from custom_handler(value)
        return

    # General handling for all other attributes:
    match value:
        case str():
            yield (key, str(value))
        case True:
            yield (key, None)
        case False | None:
            pass
        case dict() as d:
            for sub_k, sub_v in d.items():
                if sub_v is True:
                    yield sub_k, None
                elif sub_v not in (False, None):
                    yield sub_k, str(sub_v)
        case Iterable() as it:
            for item in it:
                match item:
                    case tuple() if len(item) == 2:
                        sub_k, sub_v = item
                        if sub_v is True:
                            yield sub_k, None
                        elif sub_v not in (False, None):
                            yield sub_k, str(sub_v)
                    case str() | Markup():
                        yield str(item), None
                    case _:
                        raise TypeError(
                            f"Cannot use {type(item).__name__} as attribute "
                            f"key-value pair in iterable for attribute '{key}'"
                        )
        case _:
            raise TypeError(
                f"Cannot use {type(value).__name__} as attribute value for "
                f"attribute '{key}'"
            )


def _substitute_attrs(
    attrs: dict[str, str | None], interpolations: tuple[Interpolation, ...]
) -> dict[str, str | None]:
    """Substitute placeholders in attributes based on the corresponding interpolations."""
    new_attrs: dict[str, str | None] = {}
    for key, value in attrs.items():
        if value and value.startswith(_PLACEHOLDER_PREFIX):
            index = _placholder_index(value)
            interpolation = interpolations[index]
            value = format_interpolation(interpolation)
            for sub_k, sub_v in _substitute_attr(key, value):
                new_attrs[sub_k] = sub_v
        elif key.startswith(_PLACEHOLDER_PREFIX):
            index = _placholder_index(key)
            interpolation = interpolations[index]
            value = format_interpolation(interpolation)
            for sub_k, sub_v in _substitute_spread_attrs(value):
                new_attrs[sub_k] = sub_v
        else:
            new_attrs[key] = value
    return new_attrs


def _substitute_and_flatten_children(
    children: t.Iterable[Node], interpolations: tuple[Interpolation, ...]
) -> list[Node]:
    """Substitute placeholders in a list of children and flatten any fragments."""
    new_children: list[Node] = []
    for child in children:
        substituted = _substitute_node(child, interpolations)
        if isinstance(substituted, Fragment):
            # This can happen if an interpolation results in a Fragment, for
            # instance if it is iterable.
            new_children.extend(substituted.children)
        else:
            new_children.append(substituted)
    return new_children


def _node_from_value(value: object) -> Node:
    """
    Convert an arbitrary value to a Node.

    This is the primary substitution performed when replacing interpolations
    in child content positions.
    """
    match value:
        case str():
            return Text(value)
        case Node():
            return value
        case Template():
            return html(value)
        case HasHTMLDunder():
            return Text(value)
        case False:
            return Text("")
        case Iterable():
            children = [_node_from_value(v) for v in value]
            return Fragment(children=children)
        case _:
            return Text(str(value))


def _substitute_node(p_node: Node, interpolations: tuple[Interpolation, ...]) -> Node:
    """Substitute placeholders in a node based on the corresponding interpolations."""
    match p_node:
        case Text(text) if str(text).startswith(_PLACEHOLDER_PREFIX):
            index = _placholder_index(str(text))
            interpolation = interpolations[index]
            value = format_interpolation(interpolation)
            return _node_from_value(value)
        case Element(tag=tag, attrs=attrs, children=children):
            new_attrs = _substitute_attrs(attrs, interpolations)
            new_children = _substitute_and_flatten_children(children, interpolations)
            return Element(tag=tag, attrs=new_attrs, children=new_children)
        case Fragment(children=children):
            new_children = _substitute_and_flatten_children(children, interpolations)
            return Fragment(children=new_children)
        case _:
            return p_node


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def html(template: Template) -> Node:
    """Parse a t-string and return a tree of Nodes."""
    # Parse the HTML, returning a tree of nodes with placeholders
    # where interpolations go.
    p_node = _instrument_and_parse(template.strings)
    return _substitute_node(p_node, template.interpolations)
