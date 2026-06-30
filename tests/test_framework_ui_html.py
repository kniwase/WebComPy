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
        app_version="0.0.0",
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
        app_version="0.0.0",
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
        app_version="0.0.0",
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
        app_version="0.0.0",
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
        app_version="0.0.0",
        wheel_filename="test_pkg-0.0.0-py3-none-any.whl",
        runtime_serving="cdn",
    )
    assert 'name="color-scheme"' in html_str
    assert 'content="light dark"' in html_str
