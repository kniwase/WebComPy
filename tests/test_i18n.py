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

    def test_babel_adapter_replaces_the_rule_source(self, monkeypatch) -> None:
        import sys
        import types

        from webcompy.i18n._adapters._babel import register_babel_plural_rules
        from webcompy.i18n._plural import _PLURAL_RULES

        categories = ("one", "few", "many", "other")

        def ru_form(count: int) -> int:
            if count == 1:
                return 0
            if 2 <= count <= 4:
                return 1
            if count == 5 or 11 <= count <= 14:
                return 2
            return 3

        class _Forms:
            order = categories

            def plural_form(self, count: int) -> int:
                return ru_form(count)

        class _Locale:
            plural_forms = _Forms()

            @classmethod
            def parse(cls, identifier: str) -> _Locale:
                assert identifier == "ru"
                return cls()

        babel_mod = types.ModuleType("babel")
        babel_mod.Locale = _Locale
        localedata_mod = types.ModuleType("babel.localedata")
        localedata_mod.locale_identifiers = lambda: ["ru"]
        monkeypatch.setitem(sys.modules, "babel", babel_mod)
        monkeypatch.setitem(sys.modules, "babel.localedata", localedata_mod)

        original = _PLURAL_RULES["ru"]
        try:
            register_babel_plural_rules(["ru"])
            assert _PLURAL_RULES["ru"] is not original
            assert get_plural_category("ru", 1) == "one"
            assert get_plural_category("ru", 3) == "few"
            assert get_plural_category("ru", 12) == "many"
        finally:
            from webcompy.i18n._plural import register_plural_rule

            register_plural_rule("ru", original, override=True)


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

    def test_cookie_resolves_when_supported(self) -> None:
        headers = {"cookie": f"other=1; {I18N_COOKIE_NAME}=ja; x=y"}
        assert resolve_locale(headers, ["en", "ja"], "en") == "ja"

    def test_cookie_language_part_matches_supported(self) -> None:
        headers = {"cookie": f"{I18N_COOKIE_NAME}=ja-JP"}
        assert resolve_locale(headers, ["en", "ja"], "en") == "ja"

    def test_unsupported_cookie_falls_back_to_default(self) -> None:
        headers = {"cookie": f"{I18N_COOKIE_NAME}=fr"}
        assert resolve_locale(headers, ["en", "ja"], "en") == "en"

    def test_accept_language_is_ignored(self) -> None:
        headers = {"accept-language": "de-DE,de;q=0.9,fr;q=0.8"}
        assert resolve_locale(headers, ["en", "de"], "en") == "en"

    def test_default_fallback(self) -> None:
        assert resolve_locale({}, ["en", "ja"], "en") == "en"
        assert resolve_locale(None, ["en", "ja"], "en") == "en"

    def test_ssr_sees_the_same_cookie_as_the_browser(self) -> None:
        from webcompy_server.ports._cookie import ServerCookiePort

        headers = {"cookie": f"{I18N_COOKIE_NAME}=ja"}
        port = ServerCookiePort(f"{I18N_COOKIE_NAME}=ja")
        scope = DIScope()
        scope.provide(COOKIE_PORT_KEY, port)
        with scope:
            manager = _manager()
        assert resolve_locale(headers, ["en", "ja"], "en") == manager.value == "ja"
