from string.templatelib import Template

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
    assert element == Element()
    assert element.render() == ""


def test_parse_text():
    element = html(t"Hello, world!")
    assert element == Element("", {}, ("Hello, world!",))
    assert element.render() == "Hello, world!"


def test_parse_void_element():
    element = html(t"<br>")
    assert element == Element("br")
    assert element.render() == "<br />"


def test_parse_void_element_self_closed():
    element = html(t"<br />")
    assert element == Element("br")
    assert element.render() == "<br />"


def test_parse_chain_of_void_elements():
    # Make sure our handling of CPython issue #69445 is reasonable.
    element = html(t"<br><hr><img src='image.png' /><br /><hr>")
    assert element == Element(
        "",
        {},
        (
            Element("br"),
            Element("hr"),
            Element("img", attrs={"src": "image.png"}),
            Element("br"),
            Element("hr"),
        ),
    )
    assert element.render() == '<br /><hr /><img src="image.png" /><br /><hr />'


def test_parse_element_with_text():
    element = html(t"<p>Hello, world!</p>")
    assert element == Element("p", children=("Hello, world!",))
    assert element.render() == "<p>Hello, world!</p>"


def test_parse_element_with_attributes():
    element = html(t'<a href="https://example.com" target="_blank">Link</a>')
    assert element == Element(
        "a",
        attrs={"href": "https://example.com", "target": "_blank"},
        children=("Link",),
    )
    assert element.render() == '<a href="https://example.com" target="_blank">Link</a>'


def test_parse_nested_elements():
    element = html(t"<div><p>Hello</p><p>World</p></div>")
    assert element == Element(
        "div",
        children=(
            Element("p", children=("Hello",)),
            Element("p", children=("World",)),
        ),
    )
    assert element.render() == "<div><p>Hello</p><p>World</p></div>"


# --------------------------------------------------------------------------
# Interpolated text content
# --------------------------------------------------------------------------


def text_interpolated_text_content():
    name = "Alice"
    element = html(t"<p>Hello, {name}!</p>")
    assert element == Element("p", children=("Hello, ", "Alice", "!"))
    assert element.render() == "<p>Hello, Alice!</p>"


def test_escaping_of_interpolated_text_content():
    name = "<Alice & Bob>"
    element = html(t"<p>Hello, {name}!</p>")
    assert element == Element("p", children=("Hello, ", "<Alice & Bob>", "!"))
    assert element.render() == "<p>Hello, &lt;Alice &amp; Bob&gt;!</p>"


# --------------------------------------------------------------------------
# Conditional rendering and control flow
# --------------------------------------------------------------------------


def test_conditional_rendering_with_if_else():
    is_logged_in = True
    user_profile = t"<span>Welcome, User!</span>"
    login_prompt = t"<a href='/login'>Please log in</a>"
    element = html(t"<div>{user_profile if is_logged_in else login_prompt}</div>")

    assert element == Element(
        "div", children=(Element("span", children=("Welcome, User!",)),)
    )
    assert element.render() == "<div><span>Welcome, User!</span></div>"

    is_logged_in = False
    element = html(t"<div>{user_profile if is_logged_in else login_prompt}</div>")
    assert element.render() == '<div><a href="/login">Please log in</a></div>'


def test_conditional_rendering_with_and():
    show_warning = True
    warning_message = t'<div class="warning">Warning!</div>'
    element = html(t"<main>{show_warning and warning_message}</main>")

    assert element == Element(
        "main",
        children=(Element("div", attrs={"class": "warning"}, children=("Warning!",)),),
    )
    assert element.render() == '<main><div class="warning">Warning!</div></main>'

    show_warning = False
    element = html(t"<main>{show_warning and warning_message}</main>")
    # Assuming False renders nothing
    assert element.render() == "<main></main>"


# --------------------------------------------------------------------------
# Interpolated nesting of templates and elements
# --------------------------------------------------------------------------


def test_interpolated_template_content():
    child = t"<span>Child</span>"
    element = html(t"<div>{child}</div>")
    assert element == Element("div", children=(html(child),))
    assert element.render() == "<div><span>Child</span></div>"


def test_interpolated_element_content():
    child = html(t"<span>Child</span>")
    element = html(t"<div>{child}</div>")
    assert element == Element("div", children=(child,))
    assert element.render() == "<div><span>Child</span></div>"


def test_interpolated_nonstring_content():
    number = 42
    element = html(t"<p>The answer is {number}.</p>")
    assert element == Element("p", children=("The answer is ", "42", "."))
    assert element.render() == "<p>The answer is 42.</p>"


def test_list_items():
    items = ["Apple", "Banana", "Cherry"]
    element = html(t"<ul>{[t'<li>{item}</li>' for item in items]}</ul>")
    assert element.tag == "ul"
    assert len(element.attrs) == 0
    assert element.children == (
        Element("li", children=("Apple",)),
        Element("li", children=("Banana",)),
        Element("li", children=("Cherry",)),
    )
    assert element.render() == "<ul><li>Apple</li><li>Banana</li><li>Cherry</li></ul>"


def test_nested_list_items():
    # TODO XXX this is a pretty abusrd test case; clean it up when refactoring
    outer = ["fruit", "more fruit"]
    inner = ["apple", "banana", "cherry"]
    inner_items = [t"<li>{item}</li>" for item in inner]
    outer_items = [t"<li>{category}<ul>{inner_items}</ul></li>" for category in outer]
    element = html(t"<ul>{outer_items}</ul>")
    assert element == Element(
        "ul",
        children=(
            Element(
                "li",
                children=(
                    "fruit",
                    Element(
                        "ul",
                        children=(
                            Element("li", children=("apple",)),
                            Element("li", children=("banana",)),
                            Element("li", children=("cherry",)),
                        ),
                    ),
                ),
            ),
            Element(
                "li",
                children=(
                    "more fruit",
                    Element(
                        "ul",
                        children=(
                            Element("li", children=("apple",)),
                            Element("li", children=("banana",)),
                            Element("li", children=("cherry",)),
                        ),
                    ),
                ),
            ),
        ),
    )
    assert (
        element.render()
        == "<ul><li>fruit<ul><li>apple</li><li>banana</li><li>cherry</li></ul></li><li>more fruit<ul><li>apple</li><li>banana</li><li>cherry</li></ul></li></ul>"
    )


# --------------------------------------------------------------------------
# Interpolated attribute content
# --------------------------------------------------------------------------


def test_interpolated_attribute_value():
    url = "https://example.com/"
    element = html(t'<a href="{url}">Link</a>')
    assert element == Element(
        "a", attrs={"href": "https://example.com/"}, children=("Link",)
    )
    assert element.render() == '<a href="https://example.com/">Link</a>'


def test_escaping_of_interpolated_attribute_value():
    url = 'https://example.com/?q="test"&lang=en'
    element = html(t'<a href="{url}">Link</a>')
    assert element == Element(
        "a",
        attrs={"href": 'https://example.com/?q="test"&lang=en'},
        children=("Link",),
    )
    assert (
        element.render()
        == '<a href="https://example.com/?q=&quot;test&quot;&amp;lang=en">Link</a>'
    )


def test_interpolated_unquoted_attribute_value():
    id = "roquefort"
    element = html(t"<div id={id}>Cheese</div>")
    assert element == Element("div", attrs={"id": "roquefort"}, children=("Cheese",))
    assert element.render() == '<div id="roquefort">Cheese</div>'


def test_interpolated_attribute_value_true():
    disabled = True
    element = html(t"<button disabled={disabled}>Click me</button>")
    assert element == Element(
        "button", attrs={"disabled": None}, children=("Click me",)
    )
    assert element.render() == "<button disabled>Click me</button>"


def test_interpolated_attribute_value_falsy():
    disabled = False
    crumpled = None
    element = html(t"<button disabled={disabled} crumpled={crumpled}>Click me</button>")
    assert element == Element("button", attrs={}, children=("Click me",))
    assert element.render() == "<button>Click me</button>"


def test_interpolated_attribute_spread_dict():
    attrs = {"href": "https://example.com/", "target": "_blank"}
    element = html(t"<a {attrs}>Link</a>")
    assert element == Element(
        "a",
        attrs={"href": "https://example.com/", "target": "_blank"},
        children=("Link",),
    )
    assert element.render() == '<a href="https://example.com/" target="_blank">Link</a>'


def test_interpolated_mixed_attribute_values_and_spread_dict():
    attrs = {"href": "https://example.com/", "id": "link1"}
    target = "_blank"
    element = html(t'<a {attrs} target="{target}">Link</a>')
    assert element == Element(
        "a",
        attrs={"href": "https://example.com/", "id": "link1", "target": "_blank"},
        children=("Link",),
    )
    assert (
        element.render()
        == '<a href="https://example.com/" id="link1" target="_blank">Link</a>'
    )


def test_multiple_attribute_spread_dicts():
    attrs1 = {"href": "https://example.com/", "id": "overwrtten"}
    attrs2 = {"target": "_blank", "id": "link1"}
    element = html(t"<a {attrs1} {attrs2}>Link</a>")
    assert element == Element(
        "a",
        attrs={"href": "https://example.com/", "id": "link1", "target": "_blank"},
        children=("Link",),
    )
    assert (
        element.render()
        == '<a href="https://example.com/" id="link1" target="_blank">Link</a>'
    )


def test_interpolated_class_attribute():
    classes = ["btn", "btn-primary", False and "disabled", None, {"active": True}]
    element = html(t'<button class="{classes}">Click me</button>')
    assert element == Element(
        "button", attrs={"class": "btn btn-primary active"}, children=("Click me",)
    )
    assert (
        element.render() == '<button class="btn btn-primary active">Click me</button>'
    )


def test_interpolated_attribute_spread_with_class_attribute():
    attrs = {"id": "button1", "class": ["btn", "btn-primary"]}
    element = html(t"<button {attrs}>Click me</button>")
    assert element == Element(
        "button",
        attrs={"id": "button1", "class": "btn btn-primary"},
        children=("Click me",),
    )
    assert (
        element.render()
        == '<button id="button1" class="btn btn-primary">Click me</button>'
    )


def test_interpolated_data_attributes():
    data = {"user-id": 123, "role": "admin"}
    element = html(t"<div data={data}>User Info</div>")
    assert element == Element(
        "div",
        attrs={"data-user-id": "123", "data-role": "admin"},
        children=("User Info",),
    )
    assert (
        element.render() == '<div data-user-id="123" data-role="admin">User Info</div>'
    )


def test_interpolated_aria_attributes():
    aria = {"label": "Close", "hidden": True}
    element = html(t"<button aria={aria}>X</button>")
    assert element == Element(
        "button", attrs={"aria-label": "Close", "aria-hidden": "True"}, children=("X",)
    )
    assert (
        element.render() == '<button aria-label="Close" aria-hidden="True">X</button>'
    )


def test_interpolated_style_attribute():
    styles = {"color": "red", "font-weight": "bold", "font-size": "16px"}
    element = html(t"<p style={styles}>Warning!</p>")
    assert element == Element(
        "p",
        attrs={"style": "color: red; font-weight: bold; font-size: 16px"},
        children=("Warning!",),
    )
    assert (
        element.render()
        == '<p style="color: red; font-weight: bold; font-size: 16px">Warning!</p>'
    )


# --------------------------------------------------------------------------
# Function component interpolation tests
# --------------------------------------------------------------------------


def TemplateComponent(
    *children: Element | str, first: int, second: int, third: str, **props: str
) -> Template:
    attrs = {
        "id": third,
        "data": {"first": first, "second": second},
        **props,
    }
    return t"<div {attrs}>Component: {children}</div>"


def test_interpolated_template_component():
    element = html(
        t'<{TemplateComponent} first=1 second={99} third="comp1" class="my-comp">Hello, Component!</{TemplateComponent}>'
    )
    assert element == Element(
        "div",
        attrs={
            "id": "comp1",
            "data-first": "1",
            "data-second": "99",
            "class": "my-comp",
        },
        children=("Component: ", "Hello, Component!"),
    )
    assert (
        element.render()
        == '<div id="comp1" data-first="1" data-second="99" class="my-comp">Component: Hello, Component!</div>'
    )


def test_invalid_component_invocation():
    with pytest.raises(TypeError):
        _ = html(t"<{TemplateComponent}>Missing props</{TemplateComponent}>")  # type: ignore


def Columns():
    return t"""<td>Column 1</td><td>Column 2</td>"""


def test_fragment_from_component():
    # This test assumes that if a component returns a template that parses
    # into multiple root elements, they are treated as a fragment.
    element = html(t"<table><tr><{Columns} /></tr></table>")
    assert element == Element(
        "table",
        children=(
            Element(
                "tr",
                children=(
                    Element("td", children=("Column 1",)),
                    Element("td", children=("Column 2",)),
                ),
            ),
        ),
    )
    assert (
        element.render() == "<table><tr><td>Column 1</td><td>Column 2</td></tr></table>"
    )
