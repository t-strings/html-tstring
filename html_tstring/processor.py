import random
import string
import typing as t
from functools import lru_cache
from string.templatelib import Interpolation, Template

from .classnames import classnames
from .nodes import (
    Comment,
    DocumentType,
    Element,
    Fragment,
    Node,
    Text,
)
from .parser import parse_html


def _attrs(
    attrs: dict[str, str | None], bookkeep: dict[str, Interpolation]
) -> dict[str, str | None]:
    """Substitute any bookkeeping keys in attributes."""
    result: dict[str, str | None] = {}

    def _process_attr_key(key: str, value: object) -> dict[str, str | None]:
        # TODO XXX clarify the contract here. Mostly, we're mapping a single
        # key and value in the input template to zero or more key-value pairs
        # in the output element. But in the case of `data` (maybe others?),
        # we might want to map a single key in the input template to multiple
        # keys in the output element. So the return type here is a dict.
        if key == "class":
            return {key: classnames(value)}
        elif key == "data":
            if isinstance(value, dict):
                return {f"data-{k}": str(v) for k, v in value.items()}
            else:
                raise ValueError(
                    f"Invalid value for 'data' attribute: expected dict, got {type(value).__name__}"
                )
        elif key == "aria":
            if isinstance(value, dict):
                return {f"aria-{k}": str(v) for k, v in value.items()}
            else:
                raise ValueError(
                    f"Invalid value for 'aria' attribute: expected dict, got {type(value).__name__}"
                )
        elif key == "style":
            if isinstance(value, dict):
                return {key: "; ".join(f"{k}: {v}" for k, v in value.items())}
            elif isinstance(value, str):
                return {key: value}
            else:
                raise ValueError(
                    f"Invalid value for 'style' attribute: expected dict or str, got {type(value).__name__}"
                )
        elif isinstance(value, str):
            return {key: value}
        elif value is None or value is False:
            return {}
        elif value is True:
            return {key: None}
        else:
            # TODO: do we really want to allow this?
            return {key: str(value)}

    # TODO: clean this up when I understand the full logic. It's a mess.

    for key, value in attrs.items():
        if value is not None:
            if value in bookkeep:
                bk_value = _format_interpolation(bookkeep[value])
                result.update(_process_attr_key(key, bk_value))
            else:
                result[key] = value
        else:
            if key in bookkeep:
                bk_value = _format_interpolation(bookkeep[key])
                if isinstance(bk_value, str):
                    result[bk_value] = None
                elif isinstance(bk_value, dict):
                    for k, v in bk_value.items():
                        result.update(_process_attr_key(k, v))
                else:
                    raise ValueError(
                        f"Invalid attribute key substitution: {bk_value!r}"
                    )
            else:
                result[key] = None

    return result


def _children(
    children: list[NodeTuple], bookkeep: dict[str, Interpolation]
) -> tuple[Node, ...]:
    """Substitute any bookkeeping keys in children."""
    # TODO XXX: this satisfies the test cases but does not yet recurse.
    result: list[Node] = []
    for child in children:
        if isinstance(child, str):
            if child in bookkeep:
                bk_value = _format_interpolation(bookkeep[child])
                if isinstance(bk_value, (Element, Text)):
                    result.append(bk_value)
                elif isinstance(bk_value, Template):
                    result.append(html(bk_value))
                elif isinstance(bk_value, (list, tuple)):
                    # TODO XXX this should recurse
                    for item in bk_value:
                        if isinstance(item, (Element, Text)):
                            result.append(item)
                        elif isinstance(item, Template):
                            result.append(html(item))
                        elif item is False:
                            pass
                        else:
                            result.append(Text(str(item)))
                elif bk_value is False:
                    pass
                else:
                    # TODO: should I handle more types here?
                    result.append(Text(str(bk_value)))
            elif isinstance(child, Fragment):
                result.extend(child.children)
            elif isinstance(child, Element):
                result.append(child)
            else:
                result.append(Text(child))
        else:
            elements = list(_node_or_nodes_from_tuple(child, bookkeep))
            result.extend(elements)
    return tuple(result)


def _resolve_tag(
    tag: str,
    bookkeep: dict[str, Interpolation],
    attrs: dict[str, str | None],
    children: tuple[Node, ...],
) -> str | Node:
    if tag in bookkeep:
        bk_value = _format_interpolation(bookkeep[tag])
        if isinstance(bk_value, str):
            return bk_value
        elif callable(bk_value):
            result = bk_value(*children, **attrs)
            if isinstance(result, (Element, str)):
                return result
            elif isinstance(result, Template):
                return html(result)
            elif isinstance(result, str):
                return result
            else:
                raise ValueError(f"Invalid tag callable result: {result!r}")
        else:
            raise ValueError(f"Invalid tag substitution: {bk_value!r}")
    return tag


def _node_or_nodes_from_tuple(
    node: NodeTuple, bookkeep: dict[str, Interpolation]
) -> t.Iterable[Node]:
    if node[NODE_KIND] == KIND_TEXT:
        text = node[NODE_TEXT]
        assert text is not None
        if text in bookkeep:
            as_interpolation = bookkeep[text]
            print("HERE IS THE INTERPOLATION: ", as_interpolation)
            bk_value = _format_interpolation(bookkeep[str(text)].value)
            print("VALUE OF bk_value: ", bk_value)
            yield Text(str(bk_value))
        else:
            yield Text(text)
        return
    elif node[NODE_KIND] == KIND_COMMENT:
        text = node[NODE_TEXT]
        # TODO: XXX handle __html__ here?
        assert isinstance(text, str)
        yield Comment(text)
        return
    elif node[NODE_KIND] == KIND_DOCTYPE:
        text = node[NODE_TEXT]
        # TODO: XXX handle __html__ here?
        assert isinstance(text, str) or text is None
        yield DocumentType(text or "html")
        return
    elif node[NODE_KIND] not in (KIND_ELEMENT, KIND_FRAGMENT):
        raise ValueError(f"Invalid node kind: {node[NODE_KIND]!r}")
    attrs = _attrs(node[NODE_ATTRS], bookkeep)
    children = _children(node[NODE_CHILDREN], bookkeep)
    tag_or_node = _resolve_tag(node[NODE_TAG], bookkeep, attrs, children)
    if isinstance(tag_or_node, str):
        if tag_or_node == "":
            # Fragment
            yield Fragment(children=children)
        else:
            yield Element(tag=tag_or_node, attrs=attrs, children=children)
    elif isinstance(tag_or_node, Fragment):
        yield from tag_or_node.children
    else:
        yield tag_or_node


def _node_from_tuple(node: NodeTuple, bookkeep: dict[str, Interpolation]) -> Node:
    nodes = list(_node_or_nodes_from_tuple(node, bookkeep))
    print("HERE ARE THE NODES: ", nodes)
    if len(nodes) == 1:
        return nodes[0]
    else:
        return Fragment(children=tuple(nodes))


# --------------------------------------------------------------------------
# Safe HTML support
# --------------------------------------------------------------------------


class SafeHTML:
    """A wrapper to mark a string as safe for direct inclusion in HTML."""

    def __init__(self, content: str):
        self.content = content

    def __html__(self) -> str:
        return self.content

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return f"raw({self.content!r})"


# TODO: so much to do here, to handle different types of interpolations
# and their contexts. Also, to cache parsed templates.


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

    def _placeholder_or_final(i: int, s: str) -> str:
        """Return the string with a placeholder if not the last one."""
        # There are always count-1 placeholders between count strings.
        return f"{s}{_placeholder(i)}" if i < count - 1 else s

    return "".join(_placeholder_or_final(i, s) for i, s in enumerate(strings))


@lru_cache()
def _instrument_and_parse(strings: tuple[str, ...]) -> Node:
    instrumented = _instrument(strings)
    return parse_html(instrumented)


def html(template: Template) -> Node:
    """Create an HTML element from a string."""
    # Parse the HTML, returning a tree of nodes with placeholders
    # where interpolations go.
    placeholder_node = _instrument_and_parse(template.strings)
    return _substitute_interpolations(placeholder_node, template.interpolations)
