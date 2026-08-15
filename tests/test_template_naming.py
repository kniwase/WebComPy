from __future__ import annotations

import pytest

from webcompy.components._generator import ComponentGenerator, ComponentStore
from webcompy.exception import WebComPyException
from webcompy.template._naming import (
    TagResolution,
    kebab_to_pascal,
    kebab_to_snake,
    resolve_tag,
)


class TestKebabToPascal:
    def test_single_hyphen(self):
        assert kebab_to_pascal("user-card") == "UserCard"

    def test_multiple_hyphens(self):
        assert kebab_to_pascal("my-fancy-widget") == "MyFancyWidget"

    def test_no_hyphen(self):
        assert kebab_to_pascal("widget") == "Widget"

    def test_empty_string(self):
        assert kebab_to_pascal("") == ""

    def test_mixed_case_input_capitalizes_segments(self):
        assert kebab_to_pascal("User-Card") == "UserCard"

    def test_single_segment(self):
        assert kebab_to_pascal("card") == "Card"


class TestKebabToSnake:
    def test_single_hyphen(self):
        assert kebab_to_snake("item-count") == "item_count"

    def test_multiple_hyphens(self):
        assert kebab_to_snake("data-foo-bar") == "data_foo_bar"

    def test_no_hyphen(self):
        assert kebab_to_snake("count") == "count"

    def test_empty_string(self):
        assert kebab_to_snake("") == ""

    def test_preserves_existing_underscores(self):
        assert kebab_to_snake("data_value") == "data_value"


class TestResolveTag:
    def _store_with(self, *names: str) -> ComponentStore:
        store = ComponentStore()
        for name in names:
            store.add_component(
                name, ComponentGenerator(name, lambda ctx: None, custom_element_name=f"x-{name.lower()}")
            )
        return store

    def test_br_maps_to_newline(self):
        resolution, name = resolve_tag("br", self._store_with("UserCard"))
        assert resolution is TagResolution.NEWLINE
        assert name is None

    def test_kebab_component_found(self):
        store = self._store_with("UserCard")
        resolution, name = resolve_tag("user-card", store)
        assert resolution is TagResolution.COMPONENT
        assert name == "UserCard"

    def test_kebab_component_missing_raises_with_available_list(self):
        store = self._store_with("Navbar", "Footer")
        with pytest.raises(WebComPyException) as exc_info:
            resolve_tag("user-card", store)
        message = str(exc_info.value)
        assert "UserCard" in message
        assert "<user-card>" in message
        assert "Navbar" in message
        assert "Footer" in message

    def test_kebab_component_missing_empty_store(self):
        with pytest.raises(WebComPyException, match="UserCard"):
            resolve_tag("user-card", self._store_with())

    def test_non_hyphen_unknown_falls_back_to_html(self):
        store = self._store_with("UserCard")
        resolution, name = resolve_tag("widget", store)
        assert resolution is TagResolution.HTML
        assert name is None

    def test_non_hyphen_known_lowercase_component(self):
        store = self._store_with("usercard")
        resolution, name = resolve_tag("usercard", store)
        assert resolution is TagResolution.COMPONENT
        assert name == "usercard"

    def test_non_hyphen_known_pascal_component_matches_pascalcase(self):
        """Component named exactly as the tag (PascalCase) resolves as-is.

        Note: due to Python's HTMLParser lowercasing, this is only reachable via
        binder unit tests where the parser layer is bypassed; resolve_tag accepts
        the tag verbatim.
        """
        store = self._store_with("UserCard")
        resolution, name = resolve_tag("UserCard", store)
        assert resolution is TagResolution.COMPONENT
        assert name == "UserCard"

    def test_multi_hyphen_kebab_component(self):
        store = self._store_with("MyFancyWidget")
        resolution, name = resolve_tag("my-fancy-widget", store)
        assert resolution is TagResolution.COMPONENT
        assert name == "MyFancyWidget"
