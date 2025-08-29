from .html import Element


def test_empty_fragment():
    fragment = Element("")
    assert str(fragment) == ""


def test_fragment_with_text():
    fragment = Element("", children=["test"])
    assert str(fragment) == "test"
