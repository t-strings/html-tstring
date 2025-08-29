import typing as t
from dataclasses import dataclass, field
from html import escape

# See https://developer.mozilla.org/en-US/docs/Glossary/Void_element
VOID_ELEMENTS = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)


@dataclass(frozen=True)
class Element:
    """Represents an HTML element or fragment."""

    tag: str
    children: t.Sequence[Element | str] = field(default_factory=tuple)
    attrs: t.Mapping[str, str | bool] = field(default_factory=dict)

    @property
    def is_void(self) -> bool:
        """Return True if the element is a void element."""
        return self.tag in VOID_ELEMENTS

    @property
    def is_fragment(self) -> bool:
        """Return True if the element is a fragment (i.e., has no tag)."""
        return self.tag == ""

    @property
    def has_children(self) -> bool:
        """Return True if the element has children."""
        return bool(self.children)

    def __post_init__(self):
        """Ensure all preconditions are met."""
        # Void elements cannot have children
        if self.is_void and self.has_children:
            raise ValueError(f"Void element <{self.tag}> cannot have children.")

        # Fragments cannot have attributes
        if self.is_fragment and self.attrs:
            raise ValueError("Fragment elements cannot have attributes.")

    def _render(self, *, indent: str, level: int) -> str:
        """Internal method to render the element with indentation."""
        newline = "\n" if indent else ""
        indent_str = indent * level

        attrs_str = "".join(
            f" {key}" if value is True else f' {key}="{escape(str(value), quote=True)}"'
            for key, value in self.attrs.items()
        )

        if self.is_fragment:
            return newline.join(
                child._render(indent=indent, level=level)
                if isinstance(child, Element)
                else f"{indent_str}{escape(child, quote=False)}"
                for child in self.children
            )

        if self.is_void:
            return f"{indent_str}<{self.tag}{attrs_str} />"

        if not self.has_children:
            return f"{indent_str}<{self.tag}{attrs_str}></{self.tag}>"

        children_str = newline.join(
            child._render(indent=indent, level=level + 1)
            if isinstance(child, Element)
            else f"{indent_str}{indent}{escape(child, quote=False)}"
            for child in self.children
        )
        return f"{indent_str}<{self.tag}{attrs_str}>{newline}{children_str}{newline}{indent_str}</{self.tag}>"

    def render(self, *, indent: int = 0, level: int = 0) -> str:
        """Render the element as a string with optional indentation."""
        return self._render(indent=" " * indent, level=level)

    def __html__(self) -> str:
        """
        Return the HTML representation of the element.

        Useful for integration with templating engines that recognize the
        __html__ dunder, like Django and Jinja2.
        """
        return self.render()

    def __str__(self) -> str:
        """Return a pretty-printed string representation for the element."""
        return self.render(indent=2)
