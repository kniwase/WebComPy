from webcompy.components._generator import define_component
from webcompy_testing import create_test_app, render_app_html


@define_component("loading-root")
def LoadingRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test")


def _make_app(**config_kwargs):
    return create_test_app(root_component=LoadingRoot, **config_kwargs)


def _generate_html(app, **kwargs):
    return render_app_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=False,
        wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        **kwargs,
    )


class TestLoadingScreenMarkup:
    def test_loading_element_present_with_role(self):
        html_str = _generate_html(_make_app())
        assert 'id="webcompy-loading"' in html_str
        assert 'role="status"' in html_str

    def test_default_fade_attr(self):
        html_str = _generate_html(_make_app())
        assert 'data-wc-fade="250"' in html_str

    def test_fade_attr_serialized_from_config(self):
        app = _make_app(loading={"fade_out_ms": 400})
        html_str = _generate_html(app)
        assert 'data-wc-fade="400"' in html_str

    def test_style_vars_emitted(self):
        app = _make_app(loading={"reveal_delay_ms": 500, "fade_out_ms": 300})
        html_str = _generate_html(app)
        assert "--wc-delay:500ms" in html_str
        assert "--wc-fade:300ms" in html_str

    def test_compact_spinner_markup(self):
        html_str = _generate_html(_make_app())
        assert 'class="wc-loader"' in html_str
        assert "width:40px" in html_str
        assert "height:40px" in html_str
        assert "0.8s linear infinite" in html_str

    def test_grace_period_reveal_css(self):
        html_str = _generate_html(_make_app())
        assert "@keyframes wc-reveal" in html_str
        assert "var(--wc-delay, 350ms) forwards" in html_str

    def test_fading_transition_css(self):
        html_str = _generate_html(_make_app())
        assert "wc-fading" in html_str
        assert "transition:opacity var(--wc-fade, 250ms) ease" in html_str

    def test_theme_aware_styles(self):
        html_str = _generate_html(_make_app())
        assert "light-dark" in html_str
        assert "data-theme" in html_str

    def test_hidden_utility_rule(self):
        html_str = _generate_html(_make_app())
        assert "#webcompy-loading[hidden]{display:none" in html_str

    def test_reduced_motion_rules(self):
        html_str = _generate_html(_make_app())
        assert "prefers-reduced-motion" in html_str
        assert "wc-spin" in html_str


class _FakeNode:
    def __init__(self, attrs):
        self._attrs = attrs

    def getAttribute(self, name):
        return self._attrs.get(name)


class TestLoadingFadeResolution:
    def _app_with_loading(self, fade_out_ms):
        return _make_app(loading={"fade_out_ms": fade_out_ms})

    def test_attribute_wins_over_config(self):
        from webcompy.app._root_component import _loading_fade_ms

        node = _FakeNode({"data-wc-fade": "500"})
        app = self._app_with_loading(250)
        assert _loading_fade_ms(node, app) == 500

    def test_config_fallback_when_attr_missing(self):
        from webcompy.app._root_component import _loading_fade_ms

        node = _FakeNode({})
        app = self._app_with_loading(400)
        assert _loading_fade_ms(node, app) == 400

    def test_default_when_no_config(self):
        from webcompy.app._root_component import _loading_fade_ms

        node = _FakeNode({})
        app = _make_app()
        assert _loading_fade_ms(node, app) == 250

    def test_default_when_no_app(self):
        from webcompy.app._root_component import _loading_fade_ms

        node = _FakeNode({})
        assert _loading_fade_ms(node, None) == 250

    def test_invalid_attr_falls_back(self):
        from webcompy.app._root_component import _loading_fade_ms

        node = _FakeNode({"data-wc-fade": "abc"})
        app = self._app_with_loading(300)
        assert _loading_fade_ms(node, app) == 300
