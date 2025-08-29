import typing as t
from dataclasses import dataclass, field
from string.templatelib import Template

# See https://developer.mozilla.org/en-US/docs/Glossary/Void_element
VOID_ELEMENTS = [
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


@dataclass(frozen=True)
class Element:
    tag: str
    children: t.Sequence[Element | str] = field(default_factory=tuple)
    attrs: t.Mapping[str, str | bool | None] = field(default_factory=dict)

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

    def render(self, *, indent: int = 0, level: int = 0) -> str:
        """Render the element as a string with optional indentation."""
        single_indent = " " * indent
        indent_str = single_indent * level if indent else ""
        attrs_str = "".join(
            f" {key}"
            if value is True
            else f' {key}="{value}"'
            if value is not None
            else ""
            for key, value in self.attrs.items()
        )

        if self.is_fragment:
            return "\n".join(
                child.render(indent=indent, level=level)
                if isinstance(child, Element)
                else f"{indent_str}{child}"
                for child in self.children
            )

        if self.is_void:
            return f"{indent_str}<{self.tag}{attrs_str} />"

        if not self.has_children:
            return f"{indent_str}<{self.tag}{attrs_str}></{self.tag}>"

        children_str = "\n".join(
            child.render(indent=indent, level=level + 1)
            if isinstance(child, Element)
            else f"{indent_str}  {child}"
            for child in self.children
        )
        return f"{indent_str}<{self.tag}{attrs_str}>\n{children_str}\n{indent_str}</{self.tag}>"

    def __html__(self) -> str:
        """
        Return the HTML representation of the element.

        Useful for integration with templating engines that recognize the
        __html__ dunder, like Django and Jinja2.
        """
        return self.render()

    def __str__(self) -> str:
        """Pretty-print the element with an indent of 2 spaces."""
        return self.render(indent=2)


def html(template: Template) -> Element:
    """Create an HTML element from a template.

    Args:
        template (Template): The template to create the HTML element from.

    Returns:
        Element: The created HTML element.
    """
    raise NotImplementedError()
