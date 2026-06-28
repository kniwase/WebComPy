from __future__ import annotations

import importlib
import sys


def test_use_theme_importable_from_theme_package() -> None:
    from webcompy.ui.theme import use_theme

    assert callable(use_theme)


def test_use_theme_importable_from_composables_package() -> None:
    from webcompy.ui.composables import use_theme

    assert callable(use_theme)


def test_use_theme_from_theme_and_composables_is_same_callable() -> None:
    from webcompy.ui.composables import use_theme as from_composables
    from webcompy.ui.theme import use_theme as from_theme

    assert from_theme is from_composables


def test_use_theme_reexported_via_composables_dunder_all() -> None:
    mod = importlib.import_module("webcompy.ui.composables")
    assert "use_theme" in mod.__all__


def test_use_theme_reexported_via_theme_dunder_all() -> None:
    mod = importlib.import_module("webcompy.ui.theme")
    assert "use_theme" in mod.__all__


def test_legacy_underscore_composables_path_removed() -> None:
    sys.modules.pop("webcompy.ui._composables", None)
    try:
        importlib.import_module("webcompy.ui._composables")
    except ImportError:
        return
    raise AssertionError(
        "webcompy.ui._composables must not be importable; it was a private "
        "module that has been replaced by the public webcompy.ui.composables"
    )
