from unittest.mock import patch

from webcompy.app._app import WebComPyApp
from webcompy.app._config import AppConfig
from webcompy.components._generator import define_component


@define_component
def ProfileTestRoot(context):
    from webcompy.elements import html

    return html.DIV({}, "hello")


def _make_app(**kwargs):
    return WebComPyApp(root_component=ProfileTestRoot, **kwargs)


class TestProfileDataProperty:
    def test_profile_data_none_when_disabled(self):
        app = _make_app(profile=False)
        assert app.profile_data is None

    def test_profile_data_empty_dict_when_enabled(self):
        app = _make_app(profile=True)
        result = app.profile_data
        assert isinstance(result, dict)
        assert "init_start" in result
        assert "imports_done" in result
        assert "init_done" in result


class TestRecordPhase:
    def test_record_phase_populates_data(self):
        with patch("webcompy.app._app.time.perf_counter", return_value=1.0):
            app = _make_app(profile=True)
        with patch("webcompy.app._app.time.perf_counter", return_value=2.0):
            app._record_phase("custom_phase")
        assert "custom_phase" in app._profile_data
        assert app._profile_data["custom_phase"] == 2.0

    def test_record_phase_noop_when_disabled(self):
        app = _make_app(profile=False)
        app._record_phase("should_not_exist")
        assert "should_not_exist" not in app._profile_data

    def test_record_phase_values_monotonically_increasing(self):
        counter = iter([1.0, 2.0, 3.0])

        def mock_counter():
            return next(counter)

        with patch("webcompy.app._app.time.perf_counter", side_effect=mock_counter):
            app = _make_app(profile=True)
        assert app._profile_data["init_start"] < app._profile_data["imports_done"]
        assert app._profile_data["imports_done"] < app._profile_data["init_done"]


class TestEmitProfileSummary:
    def test_emit_profile_summary_format(self):
        counter_values = iter([0.0, 0.1, 0.3, 0.31, 0.4, 0.5, 0.501])

        def mock_counter():
            return next(counter_values)

        with (
            patch("webcompy.app._app.time.perf_counter", side_effect=mock_counter),
            patch("builtins.print") as mock_print,
        ):
            app = _make_app(profile=True)
            app._profile_data["pyscript_ready"] = 0.0
            app._profile_data["loading_removed"] = 0.501
            app._emit_profile_summary()
        output = mock_print.call_args[0][0]
        assert "[WebComPy Profile]" in output
        assert "Total:" in output

    def test_emit_profile_summary_noop_when_disabled(self):
        app = _make_app(profile=False)
        with patch("builtins.print") as mock_print:
            app._emit_profile_summary()
        mock_print.assert_not_called()


class TestAppConfigProfile:
    def test_profile_default_false(self):
        config = AppConfig()
        assert config.profile is False

    def test_profile_can_be_set(self):
        config = AppConfig(profile=True)
        assert config.profile is True

    def test_profile_false_explicit(self):
        config = AppConfig(profile=False)
        assert config.profile is False


class TestAppInitRecordsPhases:
    def test_init_phases_present(self):
        app = _make_app(profile=True)
        data = app.profile_data
        assert data is not None
        assert "init_start" in data
        assert "imports_done" in data
        assert "init_done" in data

    def test_config_profile_synced(self):
        app = _make_app(profile=True)
        assert app.config.profile is True
