import typing as t
from dataclasses import dataclass, field
from functools import cached_property
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


CDATA_CONTENT_ELEMENTS = frozenset(["script", "style"])
RCDATA_CONTENT_ELEMENTS = frozenset(["textarea", "title"])
CONTENT_ELEMENTS = CDATA_CONTENT_ELEMENTS | RCDATA_CONTENT_ELEMENTS

# TODO: add a pretty-printer for nodes for debugging
# TODO: consider how significant whitespace is handled from t-string to nodes


class HasHTMLDunder(t.Protocol):
    def __html__(self) -> str: ...


type HTMLDunder = t.Callable[[], str]


@dataclass(slots=True)
class Node:
    def __html__(self) -> str:
        """Return the HTML representation of the node."""
        # By default, just return the string representation
        return str(self)


@dataclass(slots=False)
class Text(Node):
    # Django's `SafeString` and Markupsafe/Jinja2's `Markup` both inherit
    # from `str`, but that is not a requirement for the `__html__` dunder.
    text: str | HasHTMLDunder

    @cached_property
    def _cached_str(self) -> str:
        if hasattr(self.text, "__html__"):
            return t.cast(HasHTMLDunder, self.text).__html__()
        return escape(t.cast(str, self.text), quote=False)

    def _as_unescaped(self) -> str:
        """Return the text as-is, without escaping. For internal use only."""
        if hasattr(self.text, "__html__"):
            return t.cast(HasHTMLDunder, self.text).__html__()
        return t.cast(str, self.text)

    def __str__(self) -> str:
        return self._cached_str


@dataclass(slots=True)
class Fragment(Node):
    children: list[Node] = field(default_factory=list)

    def __str__(self) -> str:
        return "".join(str(child) for child in self.children)


@dataclass(slots=True)
class Comment(Node):
    text: str

    def __str__(self) -> str:
        return f"<!--{self.text}-->"


@dataclass(slots=True)
class DocumentType(Node):
    text: str = "html"

    def __str__(self) -> str:
        return f"<!DOCTYPE {self.text}>"


@dataclass(slots=True)
class Element(Node):
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)

    def __post_init__(self):
        """Ensure all preconditions are met."""
        if not self.tag:
            raise ValueError("Element tag cannot be empty.")

        # Void elements cannot have children
        if self.is_void and self.children:
            raise ValueError(f"Void element <{self.tag}> cannot have children.")

    @property
    def is_void(self) -> bool:
        return self.tag in VOID_ELEMENTS

    def __str__(self) -> str:
        # TODO: CONSIDER: should values in attrs support the __html__ dunder?
        attrs_str = "".join(
            f" {key}" if value is None else f' {key}="{escape(value, quote=True)}"'
            for key, value in self.attrs.items()
        )
        if self.is_void:
            return f"<{self.tag}{attrs_str} />"
        if not self.children:
            return f"<{self.tag}{attrs_str}></{self.tag}>"
        if self.tag in CONTENT_ELEMENTS:
            # Content elements should not escape their content
            children_str = "".join(
                child._as_unescaped() if isinstance(child, Text) else str(child)
                for child in self.children
            )
        else:
            children_str = "".join(str(child) for child in self.children)
        return f"<{self.tag}{attrs_str}>{children_str}</{self.tag}>"
