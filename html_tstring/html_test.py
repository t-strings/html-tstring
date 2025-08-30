from .element import Element
from .html import html

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
# t-string substitution tests
# --------------------------------------------------------------------------


def test_interpolated_string():
    name = "Alice"
    element = html(t"<p>Hello, {name}!</p>")
    assert element.tag == "p"
    assert len(element.attrs) == 0
    assert element.children == ("Hello, ", "Alice", "!")
    assert element.render() == "<p>Hello, Alice!</p>"


def test_escaping_in_text():
    name = "<Alice & Bob>"
    element = html(t"<p>Hello, {name}!</p>")
    assert element.tag == "p"
    assert len(element.attrs) == 0
    assert element.children == ("Hello, ", "<Alice & Bob>", "!")
    assert element.render() == "<p>Hello, &lt;Alice &amp; Bob&gt;!</p>"


def test_interpolated_attribute():
    url = "https://example.com/"
    element = html(t'<a href="{url}">Link</a>')
    assert element.tag == "a"
    assert len(element.attrs) == 1
    assert element.attrs["href"] == "https://example.com/"
    assert len(element.children) == 1
    assert element.children[0] == "Link"
    assert element.render() == '<a href="https://example.com/">Link</a>'


def test_escaping_in_attribute():
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


def test_interpolated_attribute_unquoted():
    id = "roquefort"
    element = html(t"<div id={id}>Cheese</div>")
    assert element.tag == "div"
    assert len(element.attrs) == 1
    assert element.attrs["id"] == "roquefort"
    assert len(element.children) == 1
    assert element.children[0] == "Cheese"
    assert element.render() == '<div id="roquefort">Cheese</div>'
