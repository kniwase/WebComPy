from __future__ import annotations

from webcompy.components._generator import define_component
from webcompy.signal import ReactiveList, Signal
from webcompy_testing import create_test_app, render_app_html


@define_component
def _AttrTestRoot(context):
    from webcompy.elements import html

    return html.DIV({"class": "container", "id": "main", "data-value": "42"}, "hello")


@define_component
def _EventTestRoot(context):
    from webcompy.elements import html

    return html.BUTTON({"@click": lambda e: None}, "click me")


@define_component
def _ConditionalTestRoot(context):
    from webcompy.elements import html

    show = Signal(True)
    return html.DIV(
        {},
        html.DIV({"data-branch": "true"}) if show.value else html.DIV({"data-branch": "false"}),
    )


@define_component
def _ListTestRoot(context):
    from webcompy.elements import html

    items = ReactiveList(["a", "b", "c"])
    return html.UL(
        {},
        *(html.LI({}, item) for item in items),
    )


@define_component
def _NestedTestRoot(context):
    from webcompy.elements import html

    return html.SECTION(
        {},
        html.H1({}, "title"),
        html.DIV(
            {"class": "content"},
            html.P({}, "paragraph 1"),
            html.P({}, "paragraph 2"),
        ),
    )


def _generate(root, **kwargs):
    app = create_test_app(root_component=root)
    return render_app_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        app_version="0.0.0",
        wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        **kwargs,
    )


class TestServerRenderingAttributes:
    def test_multiple_attributes_rendered(self):
        html_str = _generate(_AttrTestRoot)
        assert 'class="container"' in html_str
        assert 'id="main"' in html_str
        assert 'data-value="42"' in html_str

    def test_text_content_rendered(self):
        html_str = _generate(_AttrTestRoot)
        assert "hello" in html_str


class TestServerRenderingEventHandlers:
    def test_button_with_event_handler(self):
        html_str = _generate(_EventTestRoot)
        assert "<button" in html_str
        assert "click me" in html_str


class TestServerRenderingConditional:
    def test_conditional_true_branch(self):
        html_str = _generate(_ConditionalTestRoot)
        assert 'data-branch="true"' in html_str


class TestServerRenderingList:
    def test_list_items_rendered(self):
        html_str = _generate(_ListTestRoot)
        assert "<ul" in html_str
        assert "<li" in html_str
        assert ">a<" in html_str
        assert ">b<" in html_str
        assert ">c<" in html_str


class TestServerRenderingNested:
    def test_nested_structure(self):
        html_str = _generate(_NestedTestRoot)
        assert "<section" in html_str
        assert "<h1" in html_str
        assert ">title<" in html_str
        assert 'class="content"' in html_str
        assert ">paragraph 1<" in html_str
        assert ">paragraph 2<" in html_str
