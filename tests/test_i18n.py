from __future__ import annotations

import warnings

import pytest

from webcompy.components import ComponentContext, define_component
from webcompy.di import DIScope
from webcompy.i18n import I18nController, I18nManager, use_i18n
from webcompy.i18n._catalog import translate_message
from webcompy.i18n._plural import get_plural_category
from webcompy.i18n._server import read_locale_from_cookie, resolve_locale
from webcompy.i18n._types import I18N_COOKIE_NAME, I18N_KEY
from webcompy.ports._keys import COOKIE_PORT_KEY
from webcompy.template import render_template
from webcompy_testing import TestRenderer

_EN_JA = {
    "en": {
        "nav": {"home": "Home"},
        "greeting": "Hello, {name}!",
        "items": {"one": "{count} item", "other": "{count} items"},
    },
    "ja": {
        "nav": {"home": "ホーム"},
        "greeting": "こんにちは、{name} さん！",  # noqa: RUF001
        "items": {"other": "{count} 個のアイテム"},
    },
}


def _manager(**kwargs):
    kwargs.setdefault("default_locale", "en")
    kwargs.setdefault("supported_locales", {"en", "ja"})
    return I18nManager(_EN_JA, **kwargs)


class _FakeCookiePort:
    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._store = dict(initial or {})
        self.calls: list[tuple[str, ...]] = []

    def get(self, name: str) -> str | None:
        return self._store.get(name)

    def set(self, name: str, value: str, **kwargs: object) -> None:
        self.calls.append(("set", name, value, str(kwargs)))
        self._store[name] = value

    def delete(self, name: str, **kwargs: object) -> None:
        self.calls.append(("delete", name, str(kwargs)))
        self._store.pop(name, None)

    def get_all(self) -> dict[str, str]:
        return dict(self._store)


class TestManagerAndComposable:
    def test_use_i18n_returns_locale_t_controller(self) -> None:
        manager = _manager()
        scope = DIScope()
        scope.provide(I18N_KEY, manager)
        with scope:
            locale, t, controller = use_i18n()
            assert locale is manager.locale
            assert locale.value == "en"
            assert callable(t)
            assert isinstance(controller, I18nController)
            controller.set("ja")
            assert locale.value == "ja"
            assert t("nav.home") == "ホーム"

    def test_use_i18n_raises_without_manager(self) -> None:
        scope = DIScope()
        with scope, pytest.raises(LookupError, match="I18nManager"):
            use_i18n()

    def test_use_i18n_raises_type_error_for_wrong_value(self) -> None:
        scope = DIScope()
        scope.provide(I18N_KEY, object())
        with scope, pytest.raises(TypeError, match="I18nManager"):
            use_i18n()


class TestCatalogResolution:
    def test_dot_path_nesting(self) -> None:
        assert _manager().t("nav.home") == "Home"

    def test_interpolation(self) -> None:
        assert _manager().t("greeting", name="Alice") == "Hello, Alice!"

    def test_missing_param_renders_literal(self) -> None:
        assert _manager().t("greeting") == "Hello, {name}!"

    def test_region_falls_back_to_language(self) -> None:
        catalogs = {
            "de": {"nav": {"home": "Startseite"}},
            "en": {"nav": {"home": "Home"}},
        }
        manager = I18nManager(catalogs, default_locale="en", supported_locales={"de-AT", "en"})
        manager.set_locale("de-AT")
        assert manager.t("nav.home") == "Startseite"

    def test_falls_back_to_fallback_locale(self) -> None:
        catalogs = {"en": {"nav": {"home": "Home"}}}
        manager = I18nManager(catalogs, default_locale="en", supported_locales={"de-AT"})
        manager.set_locale("de-AT")
        assert manager.t("nav.home") == "Home"

    def test_missing_key_returns_key(self) -> None:
        assert _manager().t("nope.deep") == "nope.deep"


class TestPluralization:
    def test_english_one_other_dict(self) -> None:
        manager = _manager()
        assert manager.t("items", count=1) == "1 item"
        assert manager.t("items", count=3) == "3 items"

    def test_pipe_shorthand(self) -> None:
        manager = I18nManager({"en": {"items": "{count} item|{count} items"}}, default_locale="en")
        assert manager.t("items", count=1) == "1 item"
        assert manager.t("items", count=3) == "3 items"

    def test_other_only_locale_uses_other(self) -> None:
        manager = I18nManager(
            {"ja": {"items": {"other": "{count} 個"}}},
            default_locale="ja",
            supported_locales={"ja"},
        )
        assert manager.t("items", count=1) == "1 個"

    def test_russian_few_many_boundaries(self) -> None:
        expected = {
            1: "one",
            2: "few",
            4: "few",
            5: "many",
            11: "many",
            12: "many",
            14: "many",
            21: "one",
            22: "few",
            25: "many",
            101: "one",
        }
        for count, category in expected.items():
            assert get_plural_category("ru", count) == category, count

    def test_arabic_categories(self) -> None:
        expected = {0: "zero", 1: "one", 2: "two", 3: "few", 10: "few", 11: "many", 99: "many", 100: "other"}
        for count, category in expected.items():
            assert get_plural_category("ar", count) == category, count

    def test_unknown_locale_falls_back_with_warning(self) -> None:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            category = get_plural_category("zz-fake", 1)
        assert category == "one"
        assert any("zz-fake" in str(w.message) for w in captured)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            result = translate_message({"en": _EN_JA["en"]}, ("zz-fake", "en"), "items", count=2)
        assert result == "2 items"
        assert any("zz-fake" in str(w.message) for w in captured)


class TestReactivity:
    def test_locale_switch_updates_rendered_translation(self) -> None:
        manager = _manager()
        scope = DIScope()
        scope.provide(I18N_KEY, manager)

        @define_component()
        def I18nPage(_: ComponentContext[None]):
            _locale, t, _controller = use_i18n()
            return render_template('<span data-testid="t">{{ t("nav.home") }}</span>', {"t": t})

        with TestRenderer.render(I18nPage, parent_scope=scope) as result:
            el = result.find_by_attribute("data-testid", "t")
            assert el is not None
            assert el.textContent == "Home"
            manager.set_locale("ja")
            assert el.textContent == "ホーム"

    def test_t_reads_locale_signal_at_call_time(self) -> None:
        manager = _manager()
        assert manager.t("nav.home") == "Home"
        manager.locale.value = "ja"
        assert manager.t("nav.home") == "ホーム"


class TestResolutionAndPersistence:
    def test_initial_locale_reads_cookie_in_browser(self) -> None:
        scope = DIScope()
        scope.provide(COOKIE_PORT_KEY, _FakeCookiePort({I18N_COOKIE_NAME: "ja"}))
        with scope:
            manager = _manager()
        assert manager.value == "ja"

    def test_set_locale_writes_cookie(self) -> None:
        port = _FakeCookiePort()
        scope = DIScope()
        scope.provide(I18N_KEY, _manager())
        scope.provide(COOKIE_PORT_KEY, port)
        with scope:
            manager = _manager()
            manager.set_locale("ja")
        assert port._store.get(I18N_COOKIE_NAME) == "ja"

    def test_set_locale_skips_cookie_when_persist_disabled(self) -> None:
        port = _FakeCookiePort()
        manager = I18nManager(_EN_JA, default_locale="en", supported_locales={"en", "ja"}, persist=False)
        scope = DIScope()
        scope.provide(COOKIE_PORT_KEY, port)
        with scope:
            manager.set_locale("ja")
        assert I18N_COOKIE_NAME not in port._store

    def test_read_locale_from_cookie_not_found(self) -> None:
        assert read_locale_from_cookie(None) is None
        assert read_locale_from_cookie({}) is None
        assert read_locale_from_cookie({"cookie": "other=value"}) is None

    def test_read_locale_from_cookie_parses(self) -> None:
        headers = {"cookie": f"other=1; {I18N_COOKIE_NAME}=ja; x=y"}
        assert read_locale_from_cookie(headers) == "ja"

    def test_read_locale_from_cookie_handles_list_headers(self) -> None:
        headers = [("Cookie", f"{I18N_COOKIE_NAME}=ja")]
        assert read_locale_from_cookie(headers) == "ja"

    def test_cookie_wins_over_accept_language(self) -> None:
        headers = {"cookie": f"{I18N_COOKIE_NAME}=ja", "accept-language": "en-US,en;q=0.9"}
        assert resolve_locale(headers, ["en", "ja"], "en") == "ja"

    def test_first_visit_uses_accept_language(self) -> None:
        headers = {"accept-language": "de-DE,de;q=0.9,en;q=0.8"}
        assert resolve_locale(headers, ["en", "de"], "en") == "de"

    def test_accept_language_q_value_sorting(self) -> None:
        headers = {"accept-language": "fr;q=0.5,en;q=0.9,de;q=0.8"}
        assert resolve_locale(headers, ["de", "en"], "en") == "en"

    def test_accept_language_matches_language_part(self) -> None:
        headers = {"accept-language": "en-US;q=0.9"}
        assert resolve_locale(headers, ["en", "ja"], "ja") == "en"

    def test_malformed_accept_language_falls_back_to_default(self) -> None:
        assert resolve_locale({"accept-language": ";;;~!"}, ["en", "ja"], "en") == "en"

    def test_default_fallback(self) -> None:
        assert resolve_locale({}, ["en", "ja"], "en") == "en"
        assert resolve_locale({"accept-language": "de"}, ["en", "ja"], "en") == "en"
