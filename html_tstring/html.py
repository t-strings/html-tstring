from string.templatelib import Template

from .element import Element


def html(template: Template) -> Element:
    """Create an HTML element from a template.

    Args:
        template (Template): The template to create the HTML element from.

    Returns:
        Element: The created HTML element.
    """
    raise NotImplementedError()
