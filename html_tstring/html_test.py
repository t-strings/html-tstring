import pytest

from .element import Element
from .html import clsx, html

# --------------------------------------------------------------------------
# clsx tests
# --------------------------------------------------------------------------


def test_clsx_empty():
    assert clsx() == ""


def test_clsx_strings():
    assert clsx("btn", "btn-primary") == "btn btn-primary"


def test_clsx_strings_strip():
    assert clsx("  btn  ", " btn-primary ") == "btn btn-primary"


def test_cslx_empty_strings():
    assert clsx("", "btn", "", "btn-primary", "") == "btn btn-primary"


def test_clsx_lists_and_tuples():
    assert (
        clsx(["btn", "btn-primary"], ("active", "disabled"))
        == "btn btn-primary active disabled"
    )


def test_clsx_dicts():
    assert (
        clsx(
            "btn",
            {"btn-primary": True, "disabled": False, "active": True, "shown": "yes"},
        )
        == "btn btn-primary active shown"
    )


def test_clsx_mixed_inputs():
    assert (
        clsx(
            "btn",
            ["btn-primary", "active"],
            {"disabled": True, "hidden": False},
            ("extra",),
        )
        == "btn btn-primary active disabled extra"
    )


def test_clsx_ignores_none_and_false():
    assert (
        clsx("btn", None, False, "active", {"hidden": None, "visible": True})
        == "btn active visible"
    )


def test_clsx_raises_type_error_on_invalid_input():
    with pytest.raises(ValueError):
        clsx(123)

    with pytest.raises(ValueError):
        clsx(["btn", 456])


def test_clsx_kitchen_sink():
    assert (
        clsx(
            "foo",
            [1 and "bar", {"baz": False, "bat": None}, ["hello", ["world"]]],
            "cya",
        )
        == "foo bar hello world cya"
    )


# --------------------------------------------------------------------------
# Basic HTML parsing tests
# --------------------------------------------------------------------------


def test_parse_empty():
    element = html(t"")
    assert element.tag == ""
    assert len(element.attrs) == 0
    assert len(element.children) == 0
    assert element.render() == ""


def test_parse_text():
    element = html(t"Hello, world!")
    assert element.tag == ""
    assert len(element.attrs) == 0
    assert len(element.children) == 1
    assert element.children[0] == "Hello, world!"
    assert element.render() == "Hello, world!"


def test_parse_void_element():
    element = html(t"<br>")
    assert element.tag == "br"
    assert len(element.attrs) == 0
    assert len(element.children) == 0
    assert element.render() == "<br />"


def test_parse_void_element_self_closed():
    element = html(t"<br />")
    assert element.tag == "br"
    assert len(element.attrs) == 0
    assert len(element.children) == 0
    assert element.render() == "<br />"


def test_parse_chain_of_void_elements():
    # Make sure our handling of CPython issue #69445 is reasonable.
    element = html(t"<br><hr><img src='image.png' /><br /><hr>")
    assert element.tag == ""
    assert len(element.attrs) == 0
    assert len(element.children) == 5

    assert isinstance(element.children[0], Element)
    assert element.children[0].tag == "br"
    assert isinstance(element.children[1], Element)
    assert element.children[1].tag == "hr"
    assert isinstance(element.children[2], Element)
    assert element.children[2].tag == "img"
    assert isinstance(element.children[3], Element)
    assert element.children[3].tag == "br"
    assert isinstance(element.children[4], Element)
    assert element.children[4].tag == "hr"

    assert element.render() == '<br /><hr /><img src="image.png" /><br /><hr />'


def test_parse_element_with_text():
    element = html(t"<p>Hello, world!</p>")
    assert element.tag == "p"
    assert len(element.attrs) == 0
    assert len(element.children) == 1
    assert element.children[0] == "Hello, world!"
    assert element.render() == "<p>Hello, world!</p>"


def test_parse_element_with_attributes():
    element = html(t'<a href="https://example.com" target="_blank">Link</a>')
    assert element.tag == "a"
    assert len(element.attrs) == 2
    assert element.attrs["href"] == "https://example.com"
    assert element.attrs["target"] == "_blank"
    assert len(element.children) == 1
    assert element.children[0] == "Link"
    assert element.render() == '<a href="https://example.com" target="_blank">Link</a>'


def test_parse_nested_elements():
    element = html(t"<div><p>Hello</p><p>World</p></div>")
    assert element.tag == "div"
    assert len(element.attrs) == 0
    assert len(element.children) == 2

    assert isinstance(element.children[0], Element)
    assert element.children[0].tag == "p"
    assert len(element.children[0].children) == 1
    assert element.children[0].children[0] == "Hello"

    assert isinstance(element.children[1], Element)
    assert element.children[1].tag == "p"
    assert len(element.children[1].children) == 1
    assert element.children[1].children[0] == "World"

    assert element.render() == "<div><p>Hello</p><p>World</p></div>"


# --------------------------------------------------------------------------
# Interpolated content tests
# --------------------------------------------------------------------------


def text_interpolated_text_content():
    name = "Alice"
    element = html(t"<p>Hello, {name}!</p>")
    assert element.tag == "p"
    assert len(element.attrs) == 0
    assert element.children == ("Hello, ", "Alice", "!")
    assert element.render() == "<p>Hello, Alice!</p>"


def test_escaping_of_interpolated_text_content():
    name = "<Alice & Bob>"
    element = html(t"<p>Hello, {name}!</p>")
    assert element.tag == "p"
    assert len(element.attrs) == 0
    assert element.children == ("Hello, ", "<Alice & Bob>", "!")
    assert element.render() == "<p>Hello, &lt;Alice &amp; Bob&gt;!</p>"


def test_interpolated_attribute_value():
    url = "https://example.com/"
    element = html(t'<a href="{url}">Link</a>')
    assert element.tag == "a"
    assert len(element.attrs) == 1
    assert element.attrs["href"] == "https://example.com/"
    assert len(element.children) == 1
    assert element.children[0] == "Link"
    assert element.render() == '<a href="https://example.com/">Link</a>'


def test_escaping_of_interpolated_attribute_value():
    url = 'https://example.com/?q="test"&lang=en'
    element = html(t'<a href="{url}">Link</a>')
    assert element.tag == "a"
    assert len(element.attrs) == 1
    assert element.attrs["href"] == 'https://example.com/?q="test"&lang=en'
    assert len(element.children) == 1
    assert element.children[0] == "Link"
    assert (
        element.render()
        == '<a href="https://example.com/?q=&quot;test&quot;&amp;lang=en">Link</a>'
    )


def test_interpolated_unquoted_attribute_value():
    id = "roquefort"
    element = html(t"<div id={id}>Cheese</div>")
    assert element.tag == "div"
    assert len(element.attrs) == 1
    assert element.attrs["id"] == "roquefort"
    assert len(element.children) == 1
    assert element.children[0] == "Cheese"
    assert element.render() == '<div id="roquefort">Cheese</div>'


def test_interpolated_attribute_spread_dict():
    attrs = {"href": "https://example.com/", "target": "_blank"}
    element = html(t"<a {attrs}>Link</a>")
    assert element.tag == "a"
    assert len(element.attrs) == 2
    assert element.attrs["href"] == "https://example.com/"
    assert element.attrs["target"] == "_blank"
    assert len(element.children) == 1
    assert element.children[0] == "Link"
    assert element.render() == '<a href="https://example.com/" target="_blank">Link</a>'


def test_interpolated_mixed_attribute_values_and_spread_dict():
    attrs = {"href": "https://example.com/", "id": "link1"}
    target = "_blank"
    element = html(t'<a {attrs} target="{target}">Link</a>')
    assert element.tag == "a"
    assert len(element.attrs) == 3
    assert element.attrs["href"] == "https://example.com/"
    assert element.attrs["id"] == "link1"
    assert element.attrs["target"] == "_blank"
    assert len(element.children) == 1
    assert element.children[0] == "Link"
    assert (
        element.render()
        == '<a href="https://example.com/" id="link1" target="_blank">Link</a>'
    )


def test_multiple_attribute_spread_dicts():
    attrs1 = {"href": "https://example.com/", "id": "overwrtten"}
    attrs2 = {"target": "_blank", "id": "link1"}
    element = html(t"<a {attrs1} {attrs2}>Link</a>")
    assert element.tag == "a"
    assert len(element.attrs) == 3
    assert element.attrs["href"] == "https://example.com/"
    assert element.attrs["target"] == "_blank"
    assert element.attrs["id"] == "link1"
    assert len(element.children) == 1
    assert element.children[0] == "Link"
    assert (
        element.render()
        == '<a href="https://example.com/" id="link1" target="_blank">Link</a>'
    )


def test_interpolated_class_attribute():
    classes = ["btn", "btn-primary", False and "disabled", None, {"active": True}]
    element = html(t'<button class="{classes}">Click me</button>')
    assert element.tag == "button"
    assert len(element.attrs) == 1
    assert element.attrs["class"] == "btn btn-primary active"
    assert len(element.children) == 1
    assert element.children[0] == "Click me"
    assert (
        element.render() == '<button class="btn btn-primary active">Click me</button>'
    )


def test_interpolated_attribute_spread_with_class_attribute():
    attrs = {"id": "button1", "class": ["btn", "btn-primary"]}
    element = html(t"<button {attrs}>Click me</button>")
    assert element.tag == "button"
    assert len(element.attrs) == 2
    assert element.attrs["id"] == "button1"
    assert element.attrs["class"] == "btn btn-primary"
    assert len(element.children) == 1
    assert element.children[0] == "Click me"
    assert (
        element.render()
        == '<button id="button1" class="btn btn-primary">Click me</button>'
    )
