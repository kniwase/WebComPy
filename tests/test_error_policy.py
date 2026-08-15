from __future__ import annotations

import pytest

from webcompy.components import define_component
from webcompy.di._keys import ERROR_POLICY_KEY
from webcompy.elements import ErrorBoundary, html
from webcompy_testing import create_test_app, render_app_html


@define_component("crashing-child")
def CrashingChild(context):
    raise RuntimeError("policy crash")


@define_component("contained-root")
def ContainedRoot(context):
    return html.DIV(
        {"data-testid": "policy-root"},
        ErrorBoundary(
            children=lambda: CrashingChild(None),
            fallback=lambda e, r: html.DIV({"data-testid": "policy-fallback"}, str(e)),
        ),
        html.SPAN({"data-testid": "policy-sibling"}, "alive"),
    )


@define_component("uncontained-root")
def UncontainedRoot(context):
    return html.DIV({}, CrashingChild(None))


def _render(app):
    return render_app_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
    )


class TestSsrTolerant:
    def test_ssr_renders_fallback_and_rest_of_page(self):
        app = create_test_app(root_component=ContainedRoot)
        html_out = _render(app)
        assert "policy-fallback" in html_out
        assert "policy crash" in html_out
        assert "policy-sibling" in html_out
        assert "alive" in html_out

    def test_ssr_uncontained_error_still_fails(self):
        app = create_test_app(root_component=UncontainedRoot)
        with pytest.raises(RuntimeError, match="policy crash"):
            _render(app)


class TestSsgFailFast:
    def test_ssg_policy_fails_build_on_contained_error(self):
        app = create_test_app(root_component=ContainedRoot)
        app.provide(ERROR_POLICY_KEY, "ssg")
        with pytest.raises(RuntimeError, match="policy crash"):
            _render(app)

    def test_ssg_policy_succeeds_without_errors(self):
        @define_component("healthy-root")
        def HealthyRoot(context):
            return html.DIV({"data-testid": "healthy"}, "ok")

        app = create_test_app(root_component=HealthyRoot)
        app.provide(ERROR_POLICY_KEY, "ssg")
        html_out = _render(app)
        assert "healthy" in html_out
