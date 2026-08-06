from unittest.mock import MagicMock

import pytest

from tests.conftest import MockHistoryPort
from webcompy.di._keys import _ROUTER_KEY
from webcompy.di._scope import DIScope
from webcompy.router._link import TypedRouterLink
from webcompy.router._pages import RouterPage
from webcompy.router._router import Router
from webcompy.signal import Signal


def _make_router(initial_path="/", mode="history", base_url=""):
    pages = [
        RouterPage(path="/", component=MagicMock(spec=object)),
        RouterPage(path="/docs", component=MagicMock(spec=object)),
        RouterPage(path="/docs/getting-started", component=MagicMock(spec=object)),
        RouterPage(path="/docsx", component=MagicMock(spec=object)),
        RouterPage(path="/search", component=MagicMock(spec=object)),
        RouterPage(path="/about", component=MagicMock(spec=object)),
        RouterPage(path="/a", component=MagicMock(spec=object)),
        RouterPage(path="/b", component=MagicMock(spec=object)),
        RouterPage(path="/users/{id}", component=MagicMock(spec=object)),
    ]
    hist = MockHistoryPort(mode=mode, initial_path=initial_path)
    return Router(*pages, history=hist, base_url=base_url)


def _processed(link):
    return {k: link._proc_attr(v) for k, v in link._generate_attrs().items()}


class TestRouterLinkActive:
    @pytest.fixture(autouse=True)
    def _setup_di(self):
        self.router = _make_router()
        self.scope = DIScope({_ROUTER_KEY: self.router})
        with self.scope:
            yield
        self.scope.dispose()

    def test_prefix_match_activates(self):
        self.router = _make_router(initial_path="/docs/getting-started")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active")
            attrs = _processed(link)
            assert attrs["class"] == "active"
            assert attrs["aria-current"] == "page"

    def test_segment_boundary_prevents_false_positive(self):
        self.router = _make_router(initial_path="/docsx")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active")
            attrs = _processed(link)
            assert attrs.get("class") is None
            assert attrs.get("aria-current") is None

    def test_trailing_slash_normalization(self):
        self.router = _make_router(initial_path="/docs/")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active")
            attrs = _processed(link)
            assert attrs["class"] == "active"
            assert attrs["aria-current"] == "page"

    def test_root_matches_exactly(self):
        self.router = _make_router(initial_path="/about")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/", text=["Home"], active_class="active")
            attrs = _processed(link)
            assert attrs.get("class") is None
            assert attrs.get("aria-current") is None

    def test_root_active_on_root(self):
        self.router = _make_router(initial_path="/")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/", text=["Home"], active_class="active")
            attrs = _processed(link)
            assert attrs["class"] == "active"
            assert attrs["aria-current"] == "page"

    def test_exact_matching(self):
        self.router = _make_router(initial_path="/docs/getting-started")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active", exact=True)
            attrs = _processed(link)
            assert attrs.get("class") is None
            assert attrs.get("aria-current") is None

    def test_exact_matching_on_self(self):
        self.router = _make_router(initial_path="/docs")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active", exact=True)
            attrs = _processed(link)
            assert attrs["class"] == "active"
            assert attrs["aria-current"] == "page"

    def test_query_string_ignored(self):
        self.router = _make_router(initial_path="/search?q=python")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/search", text=["Search"], active_class="active")
            attrs = _processed(link)
            assert attrs["class"] == "active"
            assert attrs["aria-current"] == "page"

    def test_no_match_never_active(self):
        self.router = _make_router(initial_path="/nowhere")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active")
            attrs = _processed(link)
            assert attrs.get("class") is None
            assert attrs.get("aria-current") is None

    def test_reactive_toggle_on_navigation(self):
        self.router = _make_router(initial_path="/a")
        with DIScope({_ROUTER_KEY: self.router}):
            link_a = TypedRouterLink(to="/a", text=["A"], active_class="active")
            link_b = TypedRouterLink(to="/b", text=["B"], active_class="active")
            assert _processed(link_a)["class"] == "active"
            assert _processed(link_a)["aria-current"] == "page"
            assert _processed(link_b).get("class") is None
            self.router.__set_path__("/b", None)
            assert _processed(link_a).get("class") is None
            assert _processed(link_a).get("aria-current") is None
            assert _processed(link_b)["class"] == "active"
            assert _processed(link_b)["aria-current"] == "page"

    def test_active_class_signal_updates_at_runtime(self):
        self.router = _make_router(initial_path="/docs")
        with DIScope({_ROUTER_KEY: self.router}):
            active_class = Signal("active")
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class=active_class)
            assert _processed(link)["class"] == "active"
            active_class.value = "current"
            assert _processed(link)["class"] == "current"

    def test_ssr_initial_render(self):
        self.router = _make_router(initial_path="/about")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/about", text=["About"], active_class="active")
            attrs = _processed(link)
            assert "active" in attrs["class"]
            assert attrs["aria-current"] == "page"


class TestRouterLinkActiveRegression:
    @pytest.fixture(autouse=True)
    def _setup_di(self):
        self.router = _make_router()
        self.scope = DIScope({_ROUTER_KEY: self.router})
        with self.scope:
            yield
        self.scope.dispose()

    def test_no_active_class_renders_identical_attrs(self):
        self.router = _make_router(initial_path="/docs")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], attrs={"class": "nav-link", "id": "d"})
            attrs = link._generate_attrs()
            assert attrs["class"] == "nav-link"
            assert attrs["id"] == "d"
            assert "aria-current" not in attrs
            assert link._class_attr is None
            assert link._aria_current_attr is None

    def test_no_active_class_plain_to_has_no_subscriptions(self):
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"])
            assert link._callback_nodes == []

    def test_no_active_class_signal_to_has_only_to_subscription(self):
        to = Signal("/docs")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to=to, text=["Docs"])
            assert len(link._callback_nodes) == 1


class TestRouterLinkActiveClassMerging:
    @pytest.fixture(autouse=True)
    def _setup_di(self):
        self.router = _make_router(initial_path="/docs")
        self.scope = DIScope({_ROUTER_KEY: self.router})
        with self.scope:
            yield
        self.scope.dispose()

    def test_user_class_str_merges(self):
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active", attrs={"class": "nav-link"})
            assert _processed(link)["class"] == "nav-link active"
            assert _processed(link)["aria-current"] == "page"

    def test_user_class_str_when_inactive(self):
        self.router = _make_router(initial_path="/about")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active", attrs={"class": "nav-link"})
            attrs = _processed(link)
            assert attrs["class"] == "nav-link"
            assert attrs.get("aria-current") is None

    def test_user_class_signal_merges_and_stays_reactive(self):
        user_class = Signal("nav-link")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active", attrs={"class": user_class})
            assert _processed(link)["class"] == "nav-link active"
            user_class.value = "nav-link-custom"
            assert _processed(link)["class"] == "nav-link-custom active"

    def test_user_class_signal_reacts_to_navigation(self):
        user_class = Signal("nav-link")
        self.router = _make_router(initial_path="/about")
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active", attrs={"class": user_class})
            assert _processed(link)["class"] == "nav-link"
            self.router.__set_path__("/docs", None)
            assert _processed(link)["class"] == "nav-link active"

    def test_active_class_empty_string_toggles_aria_current(self):
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="", attrs={"class": "nav-link"})
            attrs = _processed(link)
            assert attrs["class"] == "nav-link"
            assert attrs["aria-current"] == "page"

    def test_active_class_empty_string_without_user_class(self):
        with DIScope({_ROUTER_KEY: self.router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="")
            attrs = _processed(link)
            assert attrs.get("class") is None
            assert attrs["aria-current"] == "page"


class TestRouterLinkActiveModes:
    def test_hash_mode_matching(self):
        router = _make_router(initial_path="/docs/getting-started", mode="hash")
        with DIScope({_ROUTER_KEY: router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active")
            attrs = _processed(link)
            assert attrs["class"] == "active"

    def test_history_mode_base_url_stripped(self):
        router = _make_router(initial_path="/app/docs", mode="history", base_url="app")
        with DIScope({_ROUTER_KEY: router}):
            link = TypedRouterLink(to="/docs", text=["Docs"], active_class="active")
            attrs = _processed(link)
            assert attrs["class"] == "active"

    def test_path_params_target(self):
        router = _make_router(initial_path="/users/42")
        path_params = Signal({"id": "42"})
        with DIScope({_ROUTER_KEY: router}):
            link = TypedRouterLink(to="/users/{id}", text=["User"], path_params=path_params, active_class="active")
            attrs = _processed(link)
            assert attrs["class"] == "active"
