# html-tstring

Tools to manipulate and render HTML using Python 3.14's t-strings.

Real documentation is forthcoming!

What can you do today?

1. Render HTML to an `Element` tree:

```python
from html_tstring import html

template = t"<div><h1>Hello, world!</h1></div>"
element = html(template)
print(str(element))
# <div><h1>Hello, world!</h1></div>
```

2. Get automatic escaping:

```python
from html_tstring import html

evil = "<script>alert('Hacked!');</script>"
template = t"<div>{evil}</div>"
element = html(template)
print(str(element))
# <div>&lt;script&gt;alert('Hacked!');&lt;/script&gt;</div>
```

3. Safely nest HTML elements:

```python
from html_tstring import html

header = html(t"<header><h1>Welcome</h1></header>")
template = t"<div>{header}<p>This is the main content.</p></div>"
element = html(template)
print(str(element))
# <div><header><h1>Welcome</h1></header><p>This is the main content.</p></div>
```

4. Or, safely nest HTML templates:

```python
from html_tstring import html

header_template = t"<header><h1>Welcome</h1></header>"
template = t"<div>{header_template}<p>This is the main content.</p></div>"
element = html(template)
print(str(element))
# <div><header><h1>Welcome</h1></header><p>This is the main content.</p></div>
```

TODO: write more examples, convert them into tests.
