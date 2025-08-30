import typing as t
from html.parser import HTMLParser
from string.templatelib import Template

from .element import VOID_ELEMENTS, Element

# For performance, a mutable tuple is used while parsing.
type ElementTuple = tuple[str, dict[str, str | None], list["ElementTuple | str"]]


def _element_from_tuple(tpl: ElementTuple) -> Element:
    return Element(
        tag=tpl[0],
        attrs=tpl[1],
        children=tuple(
            _element_from_tuple(child) if isinstance(child, tuple) else child
            for child in tpl[2]
        ),
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
                children = self.stack[0][2]
                if isinstance(children[-1], tuple) and children[-1][0] == tag:
                    # The last child is the void element we just added.
                    return
            raise ValueError(
                f"Unexpected closing tag </{tag}> with no matching opening tag."
            )

        element = self.stack.pop()
        if element[0] != tag:
            raise ValueError(f"Mismatched closing tag </{tag}> for <{element[0]}>.")

        self._append_child(element)

    def handle_data(self, data: str) -> None:
        self._append_child(data)

    def _append_child(self, child: "ElementTuple | str") -> None:
        self.stack[-1][2].append(child)

    def get_element(self) -> Element:
        if len(self.stack) != 1:
            raise ValueError("Invalid HTML structure: unclosed tags remain.")

        root = self.stack[0]

        if len(root[2]) == 1 and isinstance(root[2][0], tuple):
            return _element_from_tuple(root[2][0])
        return _element_from_tuple(root)


def html(template: Template) -> Element:
    """Create an HTML element from a string."""
    parser = ElementParser()
    for part in template:
        if isinstance(part, str):
            parser.feed(part)
        else:
            raise NotImplementedError()
    return parser.get_element()
