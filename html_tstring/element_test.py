import pytest

from .html import Element


def test_empty_fragment():
    fragment = Element("")
    assert fragment.is_fragment
    assert fragment.render() == ""
    assert str(fragment) == ""


def test_fragment_with_attributes():
    with pytest.raises(ValueError):
        _ = Element("", attrs={"id": "test"})


def test_fragment_with_text():
    fragment = Element("", children=["test"])
    assert fragment.render() == "test"
    assert str(fragment) == "test"


def test_fragment_with_children():
    fragment = Element("", children=[Element("div"), "text", Element("span")])
    assert fragment.render() == "<div></div>text<span></span>"
    assert str(fragment) == "<div></div>\ntext\n<span></span>"


def test_element_with_fragment_with_children():
    div = Element(
        "div",
        children=[
            Element("", children=[Element("div", children=["wow"]), "inside fragment"])
        ],
    )
    assert div.render() == "<div><div>wow</div>inside fragment</div>"
    assert str(div) == "<div>\n  <div>\n    wow\n  </div>\n  inside fragment\n</div>"


def test_void_element():
    br = Element("br")
    assert br.is_void
    assert not br.is_fragment
    assert not br.has_children
    assert br.render() == "<br />"
    assert str(br) == "<br />"


def test_void_element_with_attributes():
    br = Element("br", attrs={"class": "line-break", "hidden": None})
    assert br.render() == '<br class="line-break" hidden />'
    assert str(br) == '<br class="line-break" hidden />'


def test_void_element_with_children():
    with pytest.raises(ValueError):
        _ = Element("br", children=["should not be here"])


def test_standard_element():
    div = Element("div")
    assert not div.is_void
    assert not div.is_fragment
    assert not div.has_children
    assert div.render() == "<div></div>"
    assert str(div) == "<div></div>"


def test_standard_element_with_attributes():
    div = Element(
        "div",
        attrs={"id": "main", "data-role": "container", "hidden": None},
    )
    assert div.render() == '<div id="main" data-role="container" hidden></div>'
    assert str(div) == '<div id="main" data-role="container" hidden></div>'


def test_standard_element_with_text_child():
    div = Element("div", children=["Hello, world!"])
    assert div.has_children
    assert div.render() == "<div>Hello, world!</div>"
    assert str(div) == "<div>\n  Hello, world!\n</div>"


def test_standard_element_with_element_children():
    div = Element(
        "div",
        children=[
            Element("h1", children=["Title"]),
            Element("p", children=["This is a paragraph."]),
        ],
    )
    assert div.has_children
    assert div.render() == "<div><h1>Title</h1><p>This is a paragraph.</p></div>"
    assert (
        str(div) == "<div>\n"
        "  <h1>\n"
        "    Title\n"
        "  </h1>\n"
        "  <p>\n"
        "    This is a paragraph.\n"
        "  </p>\n"
        "</div>"
    )


def test_standard_element_with_mixed_children():
    div = Element(
        "div",
        children=[
            "Intro text.",
            Element("h1", children=["Title"]),
            "Some more text.",
            Element("hr"),
            Element("p", children=["This is a paragraph."]),
        ],
    )
    assert div.has_children
    assert div.render() == (
        "<div>Intro text.<h1>Title</h1>Some more text.<hr /><p>This is a paragraph.</p></div>"
    )
    assert (
        str(div) == "<div>\n"
        "  Intro text.\n"
        "  <h1>\n"
        "    Title\n"
        "  </h1>\n"
        "  Some more text.\n"
        "  <hr />\n"
        "  <p>\n"
        "    This is a paragraph.\n"
        "  </p>\n"
        "</div>"
    )


def test_complex_tree():
    html = Element(
        "html",
        children=[
            Element(
                "head",
                children=[
                    Element("title", children=["Test Page"]),
                    Element("meta", attrs={"charset": "UTF-8"}),
                ],
            ),
            Element(
                "body",
                attrs={"class": "main-body"},
                children=[
                    Element("h1", children=["Welcome to the Test Page"]),
                    Element(
                        "p",
                        children=[
                            "This is a sample paragraph with ",
                            Element("strong", children=["bold text"]),
                            " and ",
                            Element("em", children=["italic text"]),
                            ".",
                        ],
                    ),
                    Element("br"),
                    Element(
                        "ul",
                        children=[
                            Element("li", children=["Item 1"]),
                            Element("li", children=["Item 2"]),
                            Element("li", children=["Item 3"]),
                        ],
                    ),
                ],
            ),
        ],
    )
    assert html.render() == (
        '<html><head><title>Test Page</title><meta charset="UTF-8" /></head>'
        '<body class="main-body"><h1>Welcome to the Test Page</h1>'
        "<p>This is a sample paragraph with <strong>bold text</strong> and "
        "<em>italic text</em>.</p><br /><ul><li>Item 1</li><li>Item 2</li>"
        "<li>Item 3</li></ul></body></html>"
    )
    assert (
        str(html) == "<html>\n"
        "  <head>\n"
        "    <title>\n"
        "      Test Page\n"
        "    </title>\n"
        '    <meta charset="UTF-8" />\n'
        "  </head>\n"
        '  <body class="main-body">\n'
        "    <h1>\n"
        "      Welcome to the Test Page\n"
        "    </h1>\n"
        "    <p>\n"
        "      This is a sample paragraph with \n"
        "      <strong>\n"
        "        bold text\n"
        "      </strong>\n"
        "       and \n"
        "      <em>\n"
        "        italic text\n"
        "      </em>\n"
        "      .\n"
        "    </p>\n"
        "    <br />\n"
        "    <ul>\n"
        "      <li>\n"
        "        Item 1\n"
        "      </li>\n"
        "      <li>\n"
        "        Item 2\n"
        "      </li>\n"
        "      <li>\n"
        "        Item 3\n"
        "      </li>\n"
        "    </ul>\n"
        "  </body>\n"
        "</html>"
    )


def test_dunder_html_method():
    div = Element("div", children=["Hello"])
    assert div.__html__() == div.render()


def test_escaping_of_text_content():
    div = Element("div", children=["<script>alert('XSS')</script>"])
    assert div.render() == "<div>&lt;script&gt;alert('XSS')&lt;/script&gt;</div>"


def test_escaping_of_attribute_values():
    div = Element("div", attrs={"class": '">XSS<'})
    assert div.render() == '<div class="&quot;&gt;XSS&lt;"></div>'
