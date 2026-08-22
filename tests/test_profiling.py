import sys
import types
from unittest.mock import patch

from tests.conftest import MockHistoryPort
from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.components._generator import define_component
from webcompy.elements import html
from webcompy.router import Router, RouterView
from webcompy.router._lazy import lazy
from webcompy_server import configure_server_context


@define_component("profile-test-root")
def ProfileTestRoot(context):
    return html.DIV({}, "hello")


@define_component("profile-router-root")
def ProfileRouterRoot(context):
    return html.DIV({}, RouterView())


@define_component("profile-lazy-page")
def ProfileLazyPage(context):
    return html.DIV({}, "lazy")


def _make_app(**kwargs):
    return WebComPyApp(root_component=ProfileTestRoot, **kwargs)


def _make_ctx(app, **kwargs):
    configure_server_context(app)
    return app.create_render_context(**kwargs)


class TestProfileDataProperty:
    def test_profile_data_none_when_disabled(self):
        config = WebComPyAppConfig(profile=False)
        app = _make_app(config=config)
        assert app.profile_data is None

    def test_profile_data_empty_dict_when_enabled(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        data = app.profile_data
        assert isinstance(data, dict)
        assert data == {}
        assert app._profile_data is data

    def test_app_owns_profile_data_without_context(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        assert isinstance(app._profile_data, dict)

    def test_context_creation_records_init_phases(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        ctx = _make_ctx(app)
        try:
            assert "init_start" in app._profile_data
            assert "imports_done" in app._profile_data
            assert "init_done" in app._profile_data
            assert app.profile_data is app._profile_data
        finally:
            ctx.dispose()

    def test_context_does_not_own_profile_state(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        ctx = _make_ctx(app)
        try:
            assert not hasattr(ctx, "_profile_data")
            assert not hasattr(ctx, "profile_data")
        finally:
            ctx.dispose()


class TestRecordPhase:
    def test_record_phase_populates_data(self):
        with (
            patch("webcompy.app._app.time.perf_counter", return_value=1.0),
        ):
            config = WebComPyAppConfig(profile=True)
            app = _make_app(config=config)
        with patch("webcompy.app._app.time.perf_counter", return_value=2.0):
            app._record_phase("custom_phase")
        assert "custom_phase" in app._profile_data
        assert app._profile_data["custom_phase"] == 2.0

    def test_record_phase_noop_when_disabled(self):
        config = WebComPyAppConfig(profile=False)
        app = _make_app(config=config)
        app._record_phase("should_not_exist")
        assert "should_not_exist" not in app._profile_data

    def test_record_phase_first_occurrence_wins(self):
        counter = iter([5.0, 9.0])

        def mock_counter():
            return next(counter)

        with patch(
            "webcompy.app._app.time.perf_counter",
            side_effect=mock_counter,
        ):
            config = WebComPyAppConfig(profile=True)
            app = _make_app(config=config)
            app._record_phase("once_phase")
            app._record_phase("once_phase")
        assert app._profile_data["once_phase"] == 5.0

    def test_record_phase_values_monotonically_increasing(self):
        counter = iter([1.0, 1.5, 2.0])

        def mock_counter():
            return next(counter)

        with patch(
            "webcompy.app._app.time.perf_counter",
            side_effect=mock_counter,
        ):
            config = WebComPyAppConfig(profile=True)
            app = _make_app(config=config)
            ctx = _make_ctx(app)
        try:
            assert app._profile_data["init_start"] < app._profile_data["init_done"]
        finally:
            ctx.dispose()


class TestEmitProfileSummary:
    def test_emit_profile_summary_format(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        app._profile_data.update(
            {
                "pyscript_ready": 0.0,
                "imports_done": 0.1,
                "init_done": 0.2,
                "custom_elements_defined": 0.25,
                "run_done": 0.4,
                "loading_removed": 0.501,
                "lazy_preloaded": 0.6,
            }
        )
        with patch("builtins.print") as mock_print:
            app._emit_profile_summary()
        output = mock_print.call_args[0][0]
        assert "[WebComPy Profile]" in output
        assert "pyscript_ready → imports_done" in output
        assert "imports_done   → init_done" in output
        assert "init_done      → custom_elements_defined" in output
        assert "custom_elements_defined → run_done" in output
        assert "run_done       → loading_removed" in output
        assert "run_done       → lazy_preloaded" in output
        assert "Total:" in output

    def test_emit_profile_summary_skips_negative_pairs(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        app._profile_data.update({"run_done": 0.5, "lazy_preloaded": 0.4})
        with patch("builtins.print") as mock_print:
            app._emit_profile_summary()
        output = mock_print.call_args[0][0]
        assert "[WebComPy Profile]" in output
        assert "lazy_preloaded" not in output

    def test_emit_profile_summary_noop_when_disabled(self):
        config = WebComPyAppConfig(profile=False)
        app = _make_app(config=config)
        with patch("builtins.print") as mock_print:
            app._emit_profile_summary()
        mock_print.assert_not_called()


class TestBootstrapCompatibility:
    def test_bootstrap_assignment_before_context_does_not_raise(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        app._profile_data["pyscript_ready"] = 123.0
        assert app._profile_data["pyscript_ready"] == 123.0
        with patch("builtins.print"):
            app._emit_profile_summary()

    def test_emit_summary_without_phases_prints_header_only(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        with patch("builtins.print") as mock_print:
            app._emit_profile_summary()
        output = mock_print.call_args[0][0]
        assert "[WebComPy Profile]" in output


class TestLazyPreloadPhaseRecordedOnServer:
    def test_lazy_preloaded_recorded_during_context_creation(self):
        fake_module = types.ModuleType("profile_lazy_module")
        fake_module.ProfileLazyPage = ProfileLazyPage
        sys.modules["profile_lazy_module"] = fake_module
        try:
            lazy_gen = lazy("profile_lazy_module:ProfileLazyPage", __file__)
            router = Router(
                {"path": "/docs", "component": lazy_gen},
                history=MockHistoryPort(mode="hash"),
                preload=True,
            )
            app = WebComPyApp(
                root_component=ProfileRouterRoot,
                router=router,
                config=WebComPyAppConfig(profile=True),
            )
            assert "lazy_preloaded" not in app._profile_data
            configure_server_context(app)
            ctx = app.create_render_context("/docs")
            try:
                assert lazy_gen._resolved is ProfileLazyPage
                assert "lazy_preloaded" in app._profile_data
                assert app._profile_data["init_start"] < app._profile_data["lazy_preloaded"]
            finally:
                ctx.dispose()
        finally:
            sys.modules.pop("profile_lazy_module", None)

    def test_lazy_preloaded_recorded_at_most_once_across_requests(self):
        fake_module = types.ModuleType("profile_lazy_module_once")
        fake_module.ProfileLazyPage = ProfileLazyPage
        sys.modules["profile_lazy_module_once"] = fake_module
        try:
            lazy_gen = lazy("profile_lazy_module_once:ProfileLazyPage", __file__)
            router = Router(
                {"path": "/docs", "component": lazy_gen},
                history=MockHistoryPort(mode="hash"),
                preload=True,
            )
            app = WebComPyApp(
                root_component=ProfileRouterRoot,
                router=router,
                config=WebComPyAppConfig(profile=True),
            )
            configure_server_context(app)
            ctx1 = app.create_render_context("/docs")
            try:
                assert "lazy_preloaded" in app._profile_data
                first_value = app._profile_data["lazy_preloaded"]
            finally:
                ctx1.dispose()
            ctx2 = app.create_render_context("/docs")
            try:
                assert app._profile_data["lazy_preloaded"] is first_value
            finally:
                ctx2.dispose()
        finally:
            sys.modules.pop("profile_lazy_module_once", None)


class TestAppConfigProfile:
    def test_profile_default_false(self):
        config = WebComPyAppConfig()
        assert config.profile is False

    def test_profile_can_be_set(self):
        config = WebComPyAppConfig(profile=True)
        assert config.profile is True

    def test_profile_false_explicit(self):
        config = WebComPyAppConfig(profile=False)
        assert config.profile is False


class TestAppInitRecordsPhases:
    def test_init_phases_present(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        ctx = _make_ctx(app)
        try:
            data = app.profile_data
            assert data is not None
            assert "init_start" in data
            assert "init_done" in data
        finally:
            ctx.dispose()

    def test_config_profile_synced(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        assert app.config.profile is True

    def test_profile_enabled_via_config(self):
        config = WebComPyAppConfig(profile=True)
        app = _make_app(config=config)
        assert app._profile is True
        ctx = _make_ctx(app)
        try:
            assert app.profile_data is not None
        finally:
            ctx.dispose()
