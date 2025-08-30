from .element import Element
from .html import html


def test_t_strings():
    # Temporary. Ensure our GitHub CI action is running the 3.14 RC
    template = t"hello {42}"
    assert template.strings == ("hello ", "")
    assert template.values == (42,)


def test_parse_empty():
    element = html("")
    assert element.tag == ""
    assert len(element.attrs) == 0
    assert len(element.children) == 0
    assert element.render() == ""


def test_parse_text():
    element = html("Hello, world!")
    assert element.tag == ""
    assert len(element.attrs) == 0
    assert len(element.children) == 1
    assert element.children[0] == "Hello, world!"
    assert element.render() == "Hello, world!"


def test_parse_void_element():
    element = html("<br>")
    assert element.tag == "br"
    assert len(element.attrs) == 0
    assert len(element.children) == 0
    assert element.render() == "<br />"


def test_parse_void_element_self_closed():
    element = html("<br />")
    assert element.tag == "br"
    assert len(element.attrs) == 0
    assert len(element.children) == 0
    assert element.render() == "<br />"


def test_parse_chain_of_void_elements():
    # Make sure our handling of CPython issue #69445 is reasonable.
    element = html("<br><hr><img src='image.png' /><br /><hr>")
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
    element = html("<p>Hello, world!</p>")
    assert element.tag == "p"
    assert len(element.attrs) == 0
    assert len(element.children) == 1
    assert element.children[0] == "Hello, world!"
    assert element.render() == "<p>Hello, world!</p>"


def test_parse_element_with_attributes():
    element = html('<a href="https://example.com" target="_blank">Link</a>')
    assert element.tag == "a"
    assert len(element.attrs) == 2
    assert element.attrs["href"] == "https://example.com"
    assert element.attrs["target"] == "_blank"
    assert len(element.children) == 1
    assert element.children[0] == "Link"
    assert element.render() == '<a href="https://example.com" target="_blank">Link</a>'


def test_parse_nested_elements():
    element = html("<div><p>Hello</p><p>World</p></div>")
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
