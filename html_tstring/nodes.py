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


# TODO: add a pretty-printer for nodes for debugging
# TODO: consider how significant whitespace is handled from t-string to nodes


@t.runtime_checkable
class HasHTMLDunder(t.Protocol):
    def __html__(self) -> str: ...


type HTMLDunder = t.Callable[[], str]


@dataclass(frozen=True)
class Node(HasHTMLDunder):
    def __html__(self) -> str:
        """Return the HTML representation of the node."""
        # By default, just return the string representation
        return str(self)


@dataclass(frozen=True)
class Text(Node):
    # Django's `SafeString` and Markupsafe/Jinja2's `Markup` both inherit
    # from `str`, but that is not a requirement for the `__html__` dunder.
    text: str | HasHTMLDunder

    @cached_property
    def _cached_str(self) -> str:
        if isinstance(self.text, HasHTMLDunder):
            return self.text.__html__()
        return escape(self.text, quote=False)

    def __str__(self) -> str:
        return self._cached_str


@dataclass(frozen=True)
class Fragment(Node):
    children: t.Sequence[Node] = field(default_factory=tuple)

    def __str__(self) -> str:
        return "".join(str(child) for child in self.children)


@dataclass(frozen=True)
class Comment(Node):
    text: str

    def __str__(self) -> str:
        return f"<!--{self.text}-->"


@dataclass(frozen=True)
class DocumentType(Node):
    text: str = "html"

    def __str__(self) -> str:
        return f"<!DOCTYPE {self.text}>"


@dataclass(frozen=True)
class Element(Node):
    tag: str
    attrs: t.Mapping[str, str | None] = field(default_factory=dict)
    children: t.Sequence[Node] = field(default_factory=tuple)

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
        children_str = "".join(str(child) for child in self.children)
        return f"<{self.tag}{attrs_str}>{children_str}</{self.tag}>"
