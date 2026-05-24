from __future__ import annotations

from webcompy.components._generator import define_component
from webcompy.testing import create_test_app


@define_component
def _IsolationRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "hello")


class TestRenderContextIsolation:
    def test_independent_contexts_from_same_app(self):
        app = create_test_app(root_component=_IsolationRoot)

        ctx1 = app.create_render_context()
        ctx1.set_title("Title 1")
        ctx1.set_html_attr("lang", "ja")
        ctx1.append_script({"src": "/a.js"})
        ctx1.append_link({"rel": "icon", "href": "/favicon1.ico"})

        ctx2 = app.create_render_context()
        ctx2.set_title("Title 2")
        ctx2.set_html_attr("lang", "en")
        ctx2.append_script({"src": "/b.js"})
        ctx2.append_link({"rel": "icon", "href": "/favicon2.ico"})

        assert ctx1.head["title"].value == "Title 1"
        assert ctx2.head["title"].value == "Title 2"
        assert ctx1.html_attrs["lang"] == "ja"
        assert ctx2.html_attrs["lang"] == "en"

        scripts1 = ctx1.scripts
        scripts2 = ctx2.scripts
        assert any(s[0].get("src") == "/a.js" for s in scripts1)
        assert any(s[0].get("src") == "/b.js" for s in scripts2)
        assert not any(s[0].get("src") == "/b.js" for s in scripts1)
        assert not any(s[0].get("src") == "/a.js" for s in scripts2)

        ctx1.dispose()
        ctx2.dispose()

    def test_styles_isolated(self):
        app = create_test_app(root_component=_IsolationRoot)
        ctx = app.create_render_context()
        style = ctx.style
        assert isinstance(style, str)
        ctx.dispose()
