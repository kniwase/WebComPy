from __future__ import annotations

from webcompy.components import define_component
from webcompy.ui import Spinner as TopLevelSpinner
from webcompy.ui._styles import get_styles_file
from webcompy.ui.components import Spinner as ThemedSpinner
from webcompy.ui.headless import Spinner as HeadlessSpinner
from webcompy_testing import TestRenderer


def test_headless_spinner_renders_status_role_and_data_state() -> None:
    """The headless Spinner root MUST carry role="status" and
    data-state="loading", with the label rendered as text content."""

    @define_component()
    def SpinnerHeadlessPage(context):
        return HeadlessSpinner({"label": "Loading data"})

    with TestRenderer.render(SpinnerHeadlessPage) as result:
        root = result.query_selector("div")
        assert root is not None
        assert root.getAttribute("role") == "status"
        assert root.getAttribute("data-state") == "loading"
        assert result.find_by_text("Loading data") is not None


def test_headless_spinner_uses_aria_label_when_label_is_absent() -> None:
    """Without a label prop, the aria_label fallback MUST become the
    aria-label attribute and no text node is rendered."""

    @define_component()
    def SpinnerAriaPage(context):
        return HeadlessSpinner({"aria_label": "Loading"})

    with TestRenderer.render(SpinnerAriaPage) as result:
        root = result.query_selector("div")
        assert root is not None
        assert root.getAttribute("aria-label") == "Loading"
        assert result.find_by_text("Loading") is None


def test_headless_spinner_label_takes_precedence_over_aria_label() -> None:
    """With both props supplied, the visually hidden label text wins and
    no aria-label attribute is emitted (no double announcement)."""

    @define_component()
    def SpinnerBothLabelsPage(context):
        return HeadlessSpinner({"label": "Loading data", "aria_label": "Loading"})

    with TestRenderer.render(SpinnerBothLabelsPage) as result:
        root = result.query_selector("div")
        assert root is not None
        assert root.getAttribute("aria-label") is None
        assert result.find_by_text("Loading data") is not None


def test_headless_spinner_emits_no_visual_styling() -> None:
    """The headless Spinner MUST NOT emit visual styles: no inline style
    attribute, and its scoped CSS contains only structural properties."""

    @define_component()
    def SpinnerNoStylePage(context):
        return HeadlessSpinner({"label": "Loading data"})

    with TestRenderer.render(SpinnerNoStylePage) as result:
        root = result.query_selector("div")
        assert root is not None
        assert root.getAttribute("style") is None
        css = HeadlessSpinner.scoped_style
        for forbidden in ("color", "background", "animation", "font", "shadow"):
            assert forbidden not in css


def test_headless_spinner_appends_user_class_last() -> None:
    """User classes MUST come after the framework class on the headless
    root element."""

    @define_component()
    def SpinnerUserClassPage(context):
        return HeadlessSpinner({"class_name": "my-custom"})

    with TestRenderer.render(SpinnerUserClassPage) as result:
        root = result.query_selector("div")
        assert root is not None
        assert root.getAttribute("class").split() == ["webcompy-headless-spinner", "my-custom"]


def test_themed_spinner_appends_user_class_after_defaults() -> None:
    """User classes MUST come after the themed defaults on the themed
    root element."""

    @define_component()
    def SpinnerThemedClassPage(context):
        return ThemedSpinner({"class_name": "my-custom"})

    with TestRenderer.render(SpinnerThemedClassPage) as result:
        root = result.query_selector("div")
        assert root is not None
        assert root.getAttribute("class").split() == [
            "webcompy-headless-spinner",
            "webcompy-spinner",
            "my-custom",
        ]


def test_themed_spinner_composes_headless_behavior_with_size() -> None:
    """The themed Spinner MUST inherit the headless behavior (role,
    data-state, hidden label) and apply the size variant classes."""

    @define_component()
    def SpinnerThemedSizePage(context):
        return ThemedSpinner({"label": "Loading data", "size": "lg"})

    with TestRenderer.render(SpinnerThemedSizePage) as result:
        root = result.query_selector("div")
        assert root is not None
        assert root.getAttribute("role") == "status"
        assert root.getAttribute("data-state") == "loading"
        classes = root.getAttribute("class").split()
        assert "webcompy-spinner" in classes
        assert "webcompy-spinner--lg" in classes
        assert result.find_by_text("Loading data") is not None


def test_themed_spinner_defaults_to_medium_size() -> None:
    """Without a size prop the themed Spinner MUST render the medium
    variant (no size modifier class)."""

    @define_component()
    def SpinnerThemedDefaultPage(context):
        return ThemedSpinner({"label": "Loading data"})

    with TestRenderer.render(SpinnerThemedDefaultPage) as result:
        root = result.query_selector("div")
        assert root is not None
        classes = root.getAttribute("class").split()
        assert classes == ["webcompy-headless-spinner", "webcompy-spinner"]


def test_themed_spinner_falls_back_to_medium_on_unknown_size() -> None:
    """An unknown size value MUST fall back to the medium variant."""

    @define_component()
    def SpinnerThemedUnknownSizePage(context):
        return ThemedSpinner({"size": "xl"})

    with TestRenderer.render(SpinnerThemedUnknownSizePage) as result:
        root = result.query_selector("div")
        assert root is not None
        classes = root.getAttribute("class").split()
        assert classes == ["webcompy-headless-spinner", "webcompy-spinner"]


def test_spinner_import_paths_resolve_per_contract() -> None:
    """The three import paths MUST resolve per the two-layer layout: the
    headless import yields the behavior core, the components import and
    the top-level import yield the same themed component."""

    assert HeadlessSpinner is not ThemedSpinner
    assert TopLevelSpinner is ThemedSpinner


def test_primitives_stylesheet_is_imported_in_component_layer_order() -> None:
    """index.css MUST import primitives.css between components.css and
    code-block.css so the primitives stay inside the components layer."""

    index = get_styles_file("index.css")
    assert index is not None
    text = index.decode()
    assert '@import url("./primitives.css");' in text
    assert text.index("components.css") < text.index("primitives.css") < text.index("code-block.css")


def test_primitives_stylesheet_consumes_tokens_and_honors_reduced_motion() -> None:
    """primitives.css MUST style through design tokens and MUST suppress
    the spin animation under prefers-reduced-motion."""

    css = get_styles_file("primitives.css")
    assert css is not None
    text = css.decode()
    assert "@layer components" in text
    assert "var(--color-accent)" in text
    assert "var(--color-border-muted)" in text
    assert "var(--space-" in text
    assert "@media (prefers-reduced-motion: reduce)" in text
    assert "animation: none" in text


# browser-dualrun: skip
