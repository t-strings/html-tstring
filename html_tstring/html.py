import typing as t

# from string.templatelib import Template
from html.parser import HTMLParser

from .element import VOID_ELEMENTS, Element


class ElementParser(HTMLParser):
    stack: list[Element]

    def __init__(self):
        super().__init__()
        self.stack = [Element(tag="")]

    def handle_starttag(
        self, tag: str, attrs: t.Sequence[tuple[str, str | None]]
    ) -> None:
        new_element = Element(tag=tag, attrs=dict(attrs))
        self.stack.append(new_element)

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
            # Special case to handle void elements that are not self-closed.
            if tag in VOID_ELEMENTS:
                if (
                    self.stack[0].children
                    and isinstance(self.stack[0].children[-1], Element)
                    and self.stack[0].children[-1].tag == tag
                ):
                    # The last child is the void element we just added.
                    return
            raise ValueError(
                f"Unexpected closing tag </{tag}> with no matching opening tag."
            )

        element = self.stack.pop()
        if element.tag != tag:
            raise ValueError(f"Mismatched closing tag </{tag}> for <{element.tag}>.")

        self.stack[-1] = self.stack[-1].append_child(element)

    def handle_data(self, data: str) -> None:
        self.stack[-1] = self.stack[-1].append_child(data)

    def get_element(self) -> Element:
        if len(self.stack) != 1:
            raise ValueError("Invalid HTML structure: unclosed tags remain.")

        root = self.stack[0]
        assert root.is_fragment

        if len(root.children) == 1 and isinstance(root.children[0], Element):
            return root.children[0]
        return root


def html(template: str) -> Element:
    """Create an HTML element from a string."""
    parser = ElementParser()
    parser.feed(template)
    return parser.get_element()
