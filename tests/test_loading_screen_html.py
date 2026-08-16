import pytest

from webcompy.components._generator import define_component
from webcompy_testing import create_test_app, render_app_html


@define_component("loading-root")
def LoadingRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "test")


def _make_app(**config_kwargs):
    return create_test_app(root_component=LoadingRoot, **config_kwargs)


def _generate_html(app, prerender=False, **kwargs):
    return render_app_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=prerender,
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
        assert "#webcompy-loading [hidden]{display:none" in html_str

    def test_reduced_motion_rules(self):
        html_str = _generate_html(_make_app())
        assert "prefers-reduced-motion" in html_str
        assert "wc-spin" in html_str

    def test_controller_script_present_as_classic_script(self):
        html_str = _generate_html(_make_app())
        assert "<script>(function" in html_str
        assert 'window.addEventListener("py:progress"' in html_str
        assert 'window.addEventListener("py:ready"' in html_str

    def test_controller_stage_mapping_emitted(self):
        html_str = _generate_html(_make_app())
        assert '"Loading interpreter"' in html_str
        assert '"runtime_download"' in html_str
        assert '"Loaded Pyodide"' in html_str
        assert '"runtime_ready"' in html_str

    def test_controller_ceiling_values_emitted(self):
        html_str = _generate_html(_make_app())
        assert '"runtime_download": 60' in html_str
        assert '"app_start": 97' in html_str

    def test_controller_syncs_fade_var_from_attribute(self):
        html_str = _generate_html(_make_app())
        assert 'setProperty("--wc-fade", root.getAttribute("data-wc-fade") + "ms")' in html_str

    def test_controller_reduced_motion_gate_emitted(self):
        html_str = _generate_html(_make_app())
        assert 'matchMedia("(prefers-reduced-motion: reduce)")' in html_str

    def test_controller_watchdog_completion_guard_emitted(self):
        html_str = _generate_html(_make_app())
        assert 'hasAttribute("data-wc-complete")' in html_str

    def test_controller_timeout_hidden_on_init_emitted(self):
        html_str = _generate_html(_make_app())
        assert "if (timeoutEl) timeoutEl.hidden = true;" in html_str

    def test_controller_substatus_packages_window_emitted(self):
        html_str = _generate_html(_make_app())
        assert 'showSub = key === "packages"' in html_str
        assert "if (showSub) setSub(detail);" in html_str

    def test_status_and_timeout_hooks_present(self):
        html_str = _generate_html(_make_app())
        assert "data-wc-status" in html_str
        assert "data-wc-substatus" in html_str
        assert "data-wc-timeout" in html_str
        assert "data-wc-reload" in html_str
        assert "aria-hidden" in html_str

    def test_custom_messages_merged_into_controller(self):
        app = _make_app(loading={"messages": {"runtime_download": "ランタイムを取得中…"}})
        html_str = _generate_html(app)
        assert '"runtime_download": "ランタイムを取得中…"' in html_str
        assert '"runtime_prepare": "Preparing Python runtime…"' in html_str

    def test_stages_false_omits_status_markup(self):
        app = _make_app(loading={"stages": False})
        html_str = _generate_html(app)
        assert 'class="wc-status"' not in html_str
        assert 'class="wc-substatus"' not in html_str
        assert "data-wc-timeout" in html_str

    def test_stages_false_controller_still_emitted(self):
        app = _make_app(loading={"stages": False})
        html_str = _generate_html(app)
        assert "<script>(function" in html_str
        assert '"stages": false' in html_str

    def test_default_prerendered_page_uses_content_mode(self):
        html_str = _generate_html(_make_app(), prerender=True)
        assert 'data-wc-mode="content"' in html_str
        assert 'class="wc-booting"' in html_str
        assert "data-wc-bar" in html_str
        assert 'class="wc-loader"' not in html_str

    def test_non_prerendered_page_uses_overlay_mode(self):
        html_str = _generate_html(_make_app(), prerender=False)
        assert 'data-wc-mode="overlay"' in html_str
        assert 'class="wc-booting"' not in html_str
        assert 'class="wc-loader"' in html_str
        assert 'class="wc-bar"' not in html_str

    def test_explicit_mode_overrides_auto(self):
        app = _make_app(loading={"mode": "overlay"})
        html_str = _generate_html(app, prerender=True)
        assert 'data-wc-mode="overlay"' in html_str
        assert 'class="wc-loader"' in html_str

    def test_content_inert_attrs_emitted(self):
        app = _make_app(loading={"mode": "content", "interaction": "inert"})
        html_str = _generate_html(app, prerender=True)
        assert 'data-wc-interaction="inert"' in html_str
        assert "data-wc-selector" not in html_str

    def test_content_block_attrs_emitted(self):
        app = _make_app(loading={"mode": "content"})
        html_str = _generate_html(app, prerender=True)
        assert 'data-wc-interaction="block"' in html_str
        assert "data-wc-selector" not in html_str

    def test_dormant_false_omits_body_class(self):
        app = _make_app(loading={"mode": "content", "dormant": False})
        html_str = _generate_html(app, prerender=True)
        assert 'class="wc-booting"' not in html_str

    def test_content_mode_css_rules(self):
        html_str = _generate_html(_make_app(), prerender=True)
        assert "data-wc-mode='content'" in html_str
        assert "passthrough" in html_str
        assert "@keyframes wc-dormant-in" in html_str
        assert "wc-waking" in html_str
        assert "[data-wc-complete] .wc-bar-fill" in html_str

    def test_controller_aria_busy_and_inert_application(self):
        app = _make_app(loading={"mode": "content", "interaction": "inert"})
        html_str = _generate_html(app, prerender=True)
        assert '"interaction": "inert"' in html_str
        assert 'setAttribute("aria-busy", "true")' in html_str
        assert 'setAttribute("inert", "")' in html_str

    def test_controller_selector_in_config(self):
        app = _make_app(selector="#my-widget", loading={"mode": "content"})
        html_str = _generate_html(app, prerender=True)
        assert '"selector": "#my-widget"' in html_str

    def test_splash_preset_structure(self):
        app = _make_app(loading={"template": "splash"})
        html_str = _generate_html(app)
        assert 'class="wc-splash"' in html_str
        assert 'class="wc-splash-logo"' in html_str
        assert 'class="wc-loader"' not in html_str

    def test_bar_preset_structure(self):
        app = _make_app(loading={"template": "bar"})
        html_str = _generate_html(app)
        assert 'class="wc-bar"' in html_str
        assert 'class="wc-loader"' not in html_str

    def test_overlay_preset_structure(self):
        app = _make_app(loading={"template": "overlay"})
        html_str = _generate_html(app)
        assert 'class="wc-loader"' in html_str
        assert 'class="wc-bar"' not in html_str

    def test_custom_template_injected(self):
        template = (
            '<div id="webcompy-loading" data-wc-fade="300">'
            "<span data-wc-status></span>"
            "<span data-wc-timeout hidden></span>"
            "</div>"
        )
        app = _make_app(loading={"template": template})
        html_str = _generate_html(app)
        assert 'data-wc-fade="300"' in html_str
        assert "data-wc-status" in html_str
        assert "data-wc-template-marker" not in html_str

    def test_custom_template_missing_id_fails(self):
        app = _make_app(loading={"template": "<div>no contract</div>"})
        with pytest.raises(Exception, match="webcompy-loading"):
            _generate_html(app)

    def test_custom_template_file_resolution(self, tmp_path):
        template_path = tmp_path / "splash.html"
        template_path.write_text(
            '<div id="webcompy-loading"><span data-wc-status></span></div>',
            encoding="utf-8",
        )
        app = _make_app(loading={"template": "splash.html"})
        html_str = _generate_html(app, app_package_path=tmp_path)
        assert "data-wc-status" in html_str

    def test_custom_template_missing_file_fails(self, tmp_path):
        app = _make_app(loading={"template": "missing.html"})
        with pytest.raises(Exception, match=r"missing\.html"):
            _generate_html(app, app_package_path=tmp_path)

    def test_custom_template_without_hooks_warns(self):
        template = '<div id="webcompy-loading"><p>static splash</p></div>'
        app = _make_app(loading={"template": template})
        _generate_html(app)


class TestLoadingConfigResolution:
    def test_resolve_loading_config_copies_messages(self):
        from webcompy.app._config import _LOADING_DEFAULTS
        from webcompy_server._html import _resolve_loading_config

        resolved = _resolve_loading_config(None)
        assert resolved["messages"] is not _LOADING_DEFAULTS["messages"]
        resolved["messages"]["runtime_download"] = "Mutated"
        assert _LOADING_DEFAULTS["messages"] == {}

    def test_resolve_loading_config_merges_config(self):
        from webcompy_server._html import _resolve_loading_config

        resolved = _resolve_loading_config({"mode": "content", "fade_out_ms": 400})
        assert resolved["mode"] == "content"
        assert resolved["fade_out_ms"] == 400
        assert resolved["reveal_delay_ms"] == 350
        assert resolved["messages"] == {}


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
