from __future__ import annotations

from webcompy.components._generator import define_component
from webcompy_testing import create_test_app, render_app_html


@define_component
def _TestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test")


def _make_app(**config_kwargs):
    return create_test_app(root_component=_TestRoot, **config_kwargs)


def _generate_html(app, **kwargs):
    return render_app_html(app, **kwargs)


def test_framework_ui_css_link_present_default_base_url() -> None:
    app = _make_app(base_url="/")
    html_str = _generate_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0.0.0-py3-none-any.whl",
        runtime_serving="cdn",
    )
    assert 'href="/_webcompy-ui/index.css"' in html_str


def test_framework_ui_css_link_uses_base_url() -> None:
    app = _make_app(base_url="/myapp/")
    html_str = _generate_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0.0.0-py3-none-any.whl",
        runtime_serving="cdn",
    )
    assert 'href="/myapp/_webcompy-ui/index.css"' in html_str


def test_framework_ui_css_link_is_loaded_before_core_css() -> None:
    app = _make_app()
    html_str = _generate_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0.0.0-py3-none-any.whl",
        runtime_serving="cdn",
    )
    framework_idx = html_str.find("/_webcompy-ui/index.css")
    core_idx = html_str.find("core.css")
    assert framework_idx != -1
    assert core_idx != -1
    assert framework_idx < core_idx, "Framework UI CSS must be loaded before core.css"


def test_framework_ui_link_is_in_head() -> None:
    app = _make_app()
    html_str = _generate_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0.0.0-py3-none-any.whl",
        runtime_serving="cdn",
    )
    head_end = html_str.find("</head>")
    link_pos = html_str.find("/_webcompy-ui/index.css")
    assert link_pos < head_end, "Framework UI CSS link must be inside <head>"


def test_color_scheme_meta_tag_present() -> None:
    app = _make_app()
    html_str = _generate_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0.0.0-py3-none-any.whl",
        runtime_serving="cdn",
    )
    assert 'name="color-scheme"' in html_str
    assert 'content="light dark"' in html_str


def test_scoped_styles_appear_after_index_css_link() -> None:
    from webcompy.components import reactive_scoped_style
    from webcompy.elements import html as html_module

    @define_component
    def _StyledRoot(context):
        context.use_reactive_scoped_style(reactive_scoped_style(lambda: {".styled-box-rx": {"color": "blue"}}))
        return html_module.DIV({"class": "styled-box"}, "styled")

    _StyledRoot.scoped_style = {".styled-box": {"color": "red"}}

    app = create_test_app(root_component=_StyledRoot)
    html_str = _generate_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0.0.0-py3-none-any.whl",
        runtime_serving="cdn",
    )
    link_pos = html_str.find("/_webcompy-ui/index.css")
    cid_pos = html_str.find('data-webcompy-cid="')
    rx_pos = html_str.find('data-webcompy-cid-rx="')
    assert link_pos != -1, "Framework UI CSS link must be present"
    assert cid_pos != -1, "Scoped style element must be present"
    assert rx_pos != -1, "Reactive scoped style element must be present"
    assert link_pos < cid_pos, "Scoped styles must be emitted after the index.css layer-order declaration"
    assert link_pos < rx_pos, "Reactive scoped styles must be emitted after the index.css layer-order declaration"
    assert html_str.find('data-webcompy-cid="') < html_str.find("core.css"), (
        "Scoped styles must be emitted before core.css"
    )
    assert rx_pos < html_str.find("core.css"), "Reactive scoped styles must be emitted before core.css"
