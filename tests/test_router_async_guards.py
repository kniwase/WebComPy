from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from tests.conftest import FakeDOMEvent, MockHistoryPort
from webcompy.components import ComponentGenerator
from webcompy.router._pages import RouterPage, WebComPyRouterException
from webcompy.router._router import Router


def _make_router(mode="hash", base_url="") -> tuple[Router, MockHistoryPort]:
    page = RouterPage(path="/", component=MagicMock(spec=ComponentGenerator))
    hist = MockHistoryPort(mode=mode)
    return Router(page, history=hist, base_url=base_url), hist


class TestSyncFastPath:
    def test_allow_commits_synchronously(self):
        router, hist = _make_router()
        navigated: list[str] = []
        router.after_route_change.append(navigated.append)
        router.__set_path__("/about", {"k": "v"})
        assert hist.value == "/about/"
        assert hist.pushed_urls == [("/about/", {"k": "v"})]
        assert navigated == ["/about/"]

    def test_cancel_leaves_everything_untouched(self):
        router, hist = _make_router()
        navigated: list[str] = []

        def guard(from_path, to_path):
            return False if to_path == "/admin/" else None

        router.before_route_change.append(guard)
        router.after_route_change.append(navigated.append)
        router.__set_path__("/admin", None)
        assert hist.value == "/"
        assert hist.pushed_urls == []
        assert hist.replaced_urls == []
        assert navigated == []

    def test_short_circuit(self):
        router, _hist = _make_router()
        second_called = False

        def guard_a(from_path, to_path):
            return False

        def guard_b(from_path, to_path):
            nonlocal second_called
            second_called = True
            return None

        router.before_route_change.extend([guard_a, guard_b])
        router.__set_path__("/blocked", None)
        assert not second_called

    def test_same_path_no_duplicate_push(self):
        router, hist = _make_router()
        router.__set_path__("/about", None)
        router.__set_path__("/about", None)
        assert hist.pushed_urls == [("/about/", None)]

    def test_path_with_query_pushed_and_normalized(self):
        router, hist = _make_router()
        router.__set_path__("/search/?q=1", None)
        assert hist.pushed_urls == [("/search/?q=1", None)]
        assert hist.value == "/search/?q=1"

    def test_query_path_without_slash_normalized(self):
        router, hist = _make_router()
        router.__set_path__("/search?q=1", None)
        assert hist.pushed_urls == [("/search/?q=1", None)]
        assert hist.value == "/search/?q=1"

    def test_path_variants_deduplicated(self):
        router, hist = _make_router()
        router.__set_path__("/about", None)
        router.__set_path__("/about/", None)
        assert hist.pushed_urls == [("/about/", None)]


class TestAsyncGuards:
    @pytest.mark.asyncio
    async def test_async_guard_allow(self):
        router, hist = _make_router()
        done = asyncio.Event()
        router.after_route_change.append(lambda p: done.set())

        async def guard(from_path, to_path):
            await asyncio.sleep(0.01)
            return None

        router.before_route_change.append(guard)
        router.__set_path__("/about", None)
        assert hist.value == "/"
        assert not done.is_set()
        await asyncio.wait_for(done.wait(), timeout=1)
        assert hist.value == "/about/"
        assert hist.pushed_urls == [("/about/", None)]

    @pytest.mark.asyncio
    async def test_async_guard_cancel(self):
        router, hist = _make_router()
        navigated: list[str] = []
        reached = asyncio.Event()
        router.after_route_change.append(navigated.append)

        async def guard(from_path, to_path):
            reached.set()
            await asyncio.sleep(0.01)
            return False

        router.before_route_change.append(guard)
        router.__set_path__("/admin", None)
        await asyncio.wait_for(reached.wait(), timeout=1)
        await asyncio.sleep(0.05)
        assert hist.value == "/"
        assert hist.pushed_urls == []
        assert navigated == []

    @pytest.mark.asyncio
    async def test_async_guard_redirect(self):
        router, hist = _make_router()
        done = asyncio.Event()
        navigated: list[str] = []
        router.after_route_change.append(lambda p: (navigated.append(p), done.set()))

        async def guard(from_path, to_path):
            await asyncio.sleep(0.01)
            return "/login" if to_path == "/admin/" else None

        router.before_route_change.append(guard)
        router.__set_path__("/admin", None)
        await asyncio.wait_for(done.wait(), timeout=1)
        assert hist.value == "/login/"
        assert hist.replaced_urls == [("/login/", None)]
        assert hist.pushed_urls == []
        assert navigated == ["/login/"]

    @pytest.mark.asyncio
    async def test_async_guard_then_remaining_sync_guards_run(self):
        router, _hist = _make_router()
        calls: list[tuple[str, str]] = []
        done = asyncio.Event()
        router.after_route_change.append(lambda p: done.set())

        async def async_guard(from_path, to_path):
            await asyncio.sleep(0.01)
            return None

        def sync_guard(from_path, to_path):
            calls.append(("sync", to_path))
            return None

        router.before_route_change.extend([async_guard, sync_guard])
        router.__set_path__("/about", None)
        await asyncio.wait_for(done.wait(), timeout=1)
        assert calls == [("sync", "/about/")]


class TestRedirect:
    def test_redirect_reruns_full_chain_and_replaces(self):
        router, hist = _make_router()
        calls: list[tuple[str, str]] = []

        def guard(from_path, to_path):
            calls.append((from_path, to_path))
            return "/login" if to_path == "/admin/" else None

        router.before_route_change.append(guard)
        router.__set_path__("/admin", None)
        assert calls == [("/", "/admin/"), ("/", "/login/")]
        assert hist.value == "/login/"
        assert hist.replaced_urls == [("/login/", None)]
        assert hist.pushed_urls == []

    def test_redirect_loop_raises(self):
        router, hist = _make_router()

        def guard(from_path, to_path):
            return "/b/" if to_path == "/a/" else "/a/" if to_path == "/b/" else None

        router.before_route_change.append(guard)
        with pytest.raises(WebComPyRouterException):
            router.__set_path__("/a", None)
        assert hist.value == "/"

    def test_redirect_loop_suppressed_by_handler(self):
        router, hist = _make_router()
        received: list[Exception] = []

        def guard(from_path, to_path):
            return "/b/" if to_path == "/a/" else "/a/" if to_path == "/b/" else None

        def handler(exc):
            received.append(exc)
            return True

        router.before_route_change.append(guard)
        router.on_route_error.append(handler)
        router.__set_path__("/a", None)
        assert len(received) == 1
        assert isinstance(received[0], WebComPyRouterException)
        assert hist.value == "/"


class TestLatestWins:
    @pytest.mark.asyncio
    async def test_pending_navigation_superseded(self):
        router, hist = _make_router()
        loop = asyncio.get_running_loop()
        gate = loop.create_future()
        after: list[str] = []
        router.after_route_change.append(after.append)

        async def slow_guard(from_path, to_path):
            await gate
            return None

        router.before_route_change.append(slow_guard)
        router.__set_path__("/slow", None)
        router.before_route_change.clear()
        router.__set_path__("/fast", None)
        assert hist.value == "/fast/"
        gate.set_result(None)
        await asyncio.sleep(0.05)
        assert hist.value == "/fast/"
        assert after == ["/fast/"]
        assert hist.pushed_urls == [("/fast/", None)]

    @pytest.mark.asyncio
    async def test_superseded_chain_cannot_redirect(self):
        router, hist = _make_router()
        loop = asyncio.get_running_loop()
        gate = loop.create_future()
        after: list[str] = []
        router.after_route_change.append(after.append)

        async def slow_guard(from_path, to_path):
            await gate
            return "/login"

        router.before_route_change.append(slow_guard)
        router.__set_path__("/slow", None)
        router.before_route_change.clear()
        router.__set_path__("/fast", None)
        gate.set_result(None)
        await asyncio.sleep(0.05)
        assert hist.value == "/fast/"
        assert hist.pushed_urls == [("/fast/", None)]
        assert hist.replaced_urls == []
        assert after == ["/fast/"]

    @pytest.mark.asyncio
    async def test_popstate_supersedes_pending_chain(self):
        router, hist = _make_router()
        loop = asyncio.get_running_loop()
        gate = loop.create_future()
        after: list[str] = []
        router.after_route_change.append(after.append)

        async def slow_guard(from_path, to_path):
            await gate
            return None

        router.before_route_change.append(slow_guard)
        router.__set_path__("/slow", None)
        router._on_browser_navigation("/", None)
        assert hist.value == "/"
        assert after == ["/"]
        gate.set_result(None)
        await asyncio.sleep(0.05)
        assert hist.value == "/"
        assert after == ["/"]


class TestPopstateNormalization:
    def test_on_browser_navigation_normalizes_path(self):
        router, hist = _make_router()
        navigated: list[str] = []
        router.after_route_change.append(navigated.append)
        router._on_browser_navigation("/about", None)
        assert hist.value == "/about/"
        assert navigated == ["/about/"]

    def test_on_browser_navigation_strips_base_url(self):
        router, hist = _make_router(mode="history", base_url="/myapp/")
        navigated: list[str] = []
        router.after_route_change.append(navigated.append)
        router._on_browser_navigation("/myapp/about/", None)
        assert hist.value == "/about/"
        assert navigated == ["/about/"]

    def test_no_duplicate_push_after_popstate(self):
        router, hist = _make_router(mode="history", base_url="/myapp/")
        hist._value = "/myapp/about/"
        router._on_browser_navigation("/myapp/about/", None)
        assert hist.value == "/about/"
        router.__set_path__("/about/", None)
        assert hist.pushed_urls == []
        assert hist.value == "/about/"

    def test_no_duplicate_push_after_popstate_without_trailing_slash(self):
        router, hist = _make_router()
        router._on_browser_navigation("/about", None)
        assert hist.value == "/about/"
        router.__set_path__("/about/", None)
        assert hist.pushed_urls == []
        assert hist.value == "/about/"


class TestURLOwnership:
    def test_cancelled_link_navigation_leaves_url_untouched(self):
        router, hist = _make_router()

        def guard(from_path, to_path):
            return False if to_path == "/admin/" else None

        router.before_route_change.append(guard)
        router.__set_path__("/admin", None)
        assert hist.pushed_urls == []
        assert hist.replaced_urls == []

    def test_programmatic_set_path_pushes_url(self):
        router, hist = _make_router()
        router.__set_path__("/about", None)
        assert hist.pushed_urls == [("/about/", None)]

    def test_routerlink_click_pushes_normalized_href(self):
        from webcompy.di._keys import _ROUTER_KEY
        from webcompy.di._scope import DIScope
        from webcompy.router._link import TypedRouterLink

        page = RouterPage(path="/home", component=MagicMock(spec=object))
        hist = MockHistoryPort(mode="hash")
        router = Router(page, history=hist)
        with DIScope({_ROUTER_KEY: router}):
            link = TypedRouterLink(to="/home", text=["Home"])
            link._on_click(FakeDOMEvent(href="#/home/"))
        assert hist.pushed_urls == [("/home/", None)]
        assert hist.value == "/home/"

    def test_history_mode_guard_receives_clean_path(self):
        router, hist = _make_router(mode="history")
        calls: list[tuple[str, str]] = []
        navigated: list[str] = []
        router.after_route_change.append(navigated.append)

        def guard(from_path, to_path):
            calls.append((from_path, to_path))
            return None

        router.before_route_change.append(guard)
        router.__set_path__("/about", None)
        assert calls == [("/", "/about/")]
        assert navigated == ["/about/"]
        assert hist.value == "/about/"


class TestPerRequestIsolation:
    def test_clone_has_independent_token_counter(self):
        from webcompy.di._scope import DIScope
        from webcompy.ports._keys import HISTORY_PORT_KEY

        router, _hist = _make_router()
        clone = router._clone_for_request()
        assert clone._nav_token_counter is not router._nav_token_counter
        assert clone._latest_token == 0
        clone_hist = MockHistoryPort(mode="hash")
        with DIScope({HISTORY_PORT_KEY: clone_hist}):
            clone.__set_path__("/b", None)
            assert clone._latest_token == 1
            clone.__set_path__("/c", None)
            assert clone._latest_token == 2
        router.__set_path__("/a", None)
        assert router._latest_token == 1
        assert clone._latest_token == 2


class TestGuardExceptions:
    def test_sync_guard_raise_propagates_unsuppressed(self):
        router, hist = _make_router()

        def guard(from_path, to_path):
            raise RuntimeError("boom")

        router.before_route_change.append(guard)
        with pytest.raises(RuntimeError):
            router.__set_path__("/admin", None)
        assert hist.value == "/"

    def test_sync_guard_raise_suppressed(self):
        router, hist = _make_router()
        received: list[Exception] = []

        def guard(from_path, to_path):
            raise RuntimeError("boom")

        def handler(exc):
            received.append(exc)
            return True

        router.before_route_change.append(guard)
        router.on_route_error.append(handler)
        router.__set_path__("/admin", None)
        assert len(received) == 1
        assert isinstance(received[0], RuntimeError)
        assert hist.value == "/"

    @pytest.mark.asyncio
    async def test_async_guard_raise_routed_to_on_route_error(self):
        router, hist = _make_router()
        received: list[Exception] = []
        reached = asyncio.Event()

        async def guard(from_path, to_path):
            reached.set()
            await asyncio.sleep(0.01)
            raise RuntimeError("boom")

        def handler(exc):
            received.append(exc)
            return True

        router.before_route_change.append(guard)
        router.on_route_error.append(handler)
        router.__set_path__("/admin", None)
        await asyncio.wait_for(reached.wait(), timeout=1)
        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert isinstance(received[0], RuntimeError)
        assert hist.value == "/"
        assert hist.pushed_urls == []
