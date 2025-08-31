import typing as t
from html.parser import HTMLParser
from string.templatelib import Interpolation, Template

from .element import VOID_ELEMENTS, Element

# For performance, a mutable tuple is used while parsing.
type ElementTuple = tuple[str, dict[str, str | None], list["ElementTuple | str"]]
ELT_TAG = 0
ELT_ATTRS = 1
ELT_CHILDREN = 2


# TODO this is being put together super rapidly and so far it's a mess.
# Once I have a sense of how the features are settling out, I will clean
# this up, document it, and unit test it better. -Dave


def clsx(*args: object) -> str:
    """
    Construct a space-separated class string from various inputs.

    Accepts strings, lists/tuples of strings, and dicts mapping class names to
    boolean values. Ignores None and False values.

    Examples:
        clsx("btn", "btn-primary") -> "btn btn-primary"
        clsx("btn", {"btn-primary": True, "disabled": False}) -> "btn btn-primary"
        clsx(["btn", "btn-primary"], {"disabled": True}) -> "btn btn-primary disabled"
        clsx("btn", None, False, "active") -> "btn active"

    Args:
        *args: Variable length argument list containing strings, lists/tuples,
               or dicts.

    Returns:
        A single string with class names separated by spaces.
    """
    classes: list[str] = []

    for arg in args:
        if isinstance(arg, str):
            classes.append(arg)
        elif isinstance(arg, (list, tuple)):
            classes.append(clsx(*arg))
        elif isinstance(arg, dict):
            for key, value in arg.items():
                if bool(value):
                    classes.append(key)
        elif arg is None or isinstance(arg, bool):
            continue
        else:
            raise ValueError(f"Invalid class argument type: {type(arg).__name__}")

    return " ".join(stripped for c in classes if (stripped := c.strip()))


def _clsx_single(arg: object) -> str:
    """Helper to process a single argument to clsx()."""
    if isinstance(arg, str):
        return arg.strip()
    elif isinstance(arg, (list, tuple)):
        return clsx(*arg)
    elif isinstance(arg, dict):
        classes = [key for key, value in arg.items() if bool(value)]
        return " ".join(classes)
    elif arg is None or isinstance(arg, bool):
        return ""
    else:
        raise ValueError(f"Invalid class argument type: {type(arg).__name__}")


# TODO document, clean up, and individually unit test all helper functions here.


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
            return {key: _clsx_single(value)}
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
                bk_value = bookkeep[value].value
                result.update(_process_attr_key(key, bk_value))
            else:
                result[key] = value
        else:
            if key in bookkeep:
                bk_value = bookkeep[key].value
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
    children: list["ElementTuple | str"], bookkeep: dict[str, Interpolation]
) -> tuple[Element | str, ...]:
    """Substitute any bookkeeping keys in children."""
    result: list[Element | str] = []
    for child in children:
        if isinstance(child, str):
            if child in bookkeep:
                bk_value = bookkeep[child].value
                if isinstance(bk_value, (Element, str)):
                    result.append(bk_value)
                elif isinstance(bk_value, Template):
                    result.append(html(bk_value))
                elif isinstance(bk_value, (list, tuple)):
                    # TODO XXX this should recurse
                    for item in bk_value:
                        if isinstance(item, (Element, str)):
                            result.append(item)
                        elif isinstance(item, Template):
                            result.append(html(item))
                        else:
                            result.append(str(item))
                else:
                    # TODO: should I handle more types here?
                    result.append(str(bk_value))
            else:
                result.append(child)
        else:
            result.append(_element_from_tuple(child, bookkeep))
    return tuple(result)


def _resolve_tag(
    tag: str,
    bookkeep: dict[str, Interpolation],
    attrs: dict[str, str | None],
    children: tuple[Element | str, ...],
) -> str | Element:
    if tag in bookkeep:
        bk_value = bookkeep[tag].value
        if isinstance(bk_value, str):
            return bk_value
        elif callable(bk_value):
            result = bk_value(*children, **attrs)
            if isinstance(result, (Element, str)):
                return result
            elif isinstance(result, Template):
                return html(result)
            else:
                raise ValueError(f"Invalid tag callable result: {result!r}")
        else:
            raise ValueError(f"Invalid tag substitution: {bk_value!r}")
    return tag


def _element_from_tuple(
    element: ElementTuple, bookkeep: dict[str, Interpolation]
) -> Element:
    attrs = _attrs(element[ELT_ATTRS], bookkeep)
    children = _children(element[ELT_CHILDREN], bookkeep)
    tag_or_elt = _resolve_tag(element[ELT_TAG], bookkeep, attrs, children)
    return (
        Element(tag=tag_or_elt, attrs=attrs, children=children)
        if isinstance(tag_or_elt, str)
        else tag_or_elt
    )


class ElementParser(HTMLParser):
    stack: list[ElementTuple]

    def __init__(self):
        super().__init__()
        self.stack = [("", {}, [])]

    def handle_starttag(
        self, tag: str, attrs: t.Sequence[tuple[str, str | None]]
    ) -> None:
        element = (tag, dict(attrs), [])
        self.stack.append(element)

        # Unfortunately, Python's built-in HTMLParser has inconsistent behavior
        # with void elements. In particular, it calls handle_endtag() for them
        # only if they explicitly self-close (e.g., <br />). But in the HTML
        # spec itself, *there is no distinction* between <br> and <br />.
        # So we need to handle this case ourselves.
        #
        # See https://github.com/python/cpython/issues/69445
        if tag in VOID_ELEMENTS:
            # Always call handle_endtag for void elements. If it happens
            # to be self-closed in the input, handle_endtag() will effectively
            # be called twice. We ignore the second call there.
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if len(self.stack) == 1:
            # Special case to handle void elements that are not self-closed aka
            # cpython #69445.
            if tag in VOID_ELEMENTS:
                children = self.stack[0][ELT_CHILDREN]
                if isinstance(children[-1], tuple) and children[-1][ELT_TAG] == tag:
                    # The last child is the void element we just added.
                    return
            raise ValueError(
                f"Unexpected closing tag </{tag}> with no matching opening tag."
            )

        element = self.stack.pop()
        if element[ELT_TAG] != tag:
            raise ValueError(
                f"Mismatched closing tag </{tag}> for <{element[ELT_TAG]}>."
            )

        self.append_child(element)

    def handle_data(self, data: str) -> None:
        self.append_child(data)

    def append_child(self, child: "ElementTuple | str") -> None:
        self.stack[-1][ELT_CHILDREN].append(child)

    def get_root(self) -> ElementTuple:
        if len(self.stack) != 1:
            raise ValueError("Invalid HTML structure: unclosed tags remain.")

        root = self.stack[0]

        if len(root[ELT_CHILDREN]) == 1 and isinstance(root[ELT_CHILDREN][0], tuple):
            return t.cast(ElementTuple, root[ELT_CHILDREN][0])

        return root


# TODO: so much to do here, to handle different types of interpolations
# and their contexts. Also, to cache parsed templates.


def html(template: Template) -> Element:
    """Create an HTML element from a string."""
    count: int = 0
    callables: dict[t.Callable, str] = {}
    bookkeep: dict[str, Interpolation] = {}

    parser = ElementParser()
    for part in template:
        if isinstance(part, str):
            parser.feed(part)
        else:
            # TODO: CONSIDER: how to choose a key that won't collide with
            # your typical t-string content?
            key = f"ts-bk-{count}"
            # TODO: CONSIDER: do we want to broaden this key reuse to
            # non-callables too? Or is it not worth the complexity?
            if callable(part.value):
                key = callables.get(part.value, key)
                callables[part.value] = key
            bookkeep[key] = part
            count += 1
            parser.feed(key)
    parser.close()
    root = parser.get_root()
    return _element_from_tuple(root, bookkeep)
