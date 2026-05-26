"""
Minimal reproduction test for SPA navigation bug where nested .card elements
lose the last sibling after SwitchElement _refresh().
"""

from __future__ import annotations

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, switch
from webcompy.signal import Signal
from webcompy.testing import TestRenderer


@define_component
def PageA(ctx: ComponentContext):
    """Page with nested .card structure — 3 cards total (outer + 2 inner)"""
    return html.DIV(
        {"class": "container"},
        html.DIV(
            {"class": "card"},  # outer card
            html.DIV(
                {"class": "card-body"},
                html.H5({"class": "card-title"}, "PageA"),
                html.DIV(
                    {"class": "card"},  # inner card 1
                    html.DIV({"class": "card-body"}, "Content A1"),
                ),
                html.BR(),
                html.DIV(
                    {"class": "card"},  # inner card 2 — disappears in SPA nav
                    html.DIV({"class": "card-header"}, "Code"),
                    html.DIV({"class": "card-body"}, "Source A"),
                ),
            ),
        ),
    )


@define_component
def PageB(ctx: ComponentContext):
    """Same structure as PageA but different content"""
    return html.DIV(
        {"class": "container"},
        html.DIV(
            {"class": "card"},  # outer card
            html.DIV(
                {"class": "card-body"},
                html.H5({"class": "card-title"}, "PageB"),
                html.DIV(
                    {"class": "card"},  # inner card 1
                    html.DIV({"class": "card-body"}, "Content B1"),
                ),
                html.BR(),
                html.DIV(
                    {"class": "card"},  # inner card 2 — disappears in SPA nav
                    html.DIV({"class": "card-header"}, "Code"),
                    html.DIV({"class": "card-body"}, "Source B"),
                ),
            ),
        ),
    )


def _count_cards(result) -> int:
    """Count elements with class='card' in rendered VDOM"""
    nodes = result.query_selector_all("div")
    count = 0
    for node in nodes:
        cls = node.getAttribute("class")
        if cls and "card" in cls.split():
            count += 1
    return count


def test_nested_card_survives_switch():
    """
    WHEN two pages with identical nested .card structures are switched
    via a Signal-driven switch element inside a wrapper DIV,
    THEN all 3 cards (outer + 2 inner) should be present in both renders.

    This reproduces the SPA navigation bug where the last inner .card
    (Code card) disappears after client-side route change.

    NOTE: This test currently passes with TestRenderer but the bug only
    reproduces in a real browser environment due to timing differences
    in SwitchElement._refresh() and _position_element_nodes().
    """
    is_page_a = Signal(True)

    @define_component
    def App(ctx: ComponentContext):
        return html.DIV(
            {"class": "wrapper"},
            switch(
                {"case": is_page_a, "generator": lambda: PageA(None)},
                default=lambda: PageB(None),
            ),
        )

    with TestRenderer.render(App) as result:
        # Initial render: PageA
        count_a = _count_cards(result)
        assert count_a == 3, f"PageA: expected 3 cards, got {count_a}"

        # Switch to PageB
        is_page_a.value = False

        # After switch: PageB
        count_b = _count_cards(result)
        assert count_b == 3, f"PageB: expected 3 cards, got {count_b}"


def test_nested_card_with_br_sibling():
    """
    BR element between two .card siblings should not affect count.
    Regression test for the exact DemoDisplay structure.
    """
    current = Signal(True)

    @define_component
    def App(ctx: ComponentContext):
        return html.DIV(
            {"class": "wrapper"},
            switch(
                {"case": current, "generator": lambda: None},
                default=lambda: html.DIV(
                    html.DIV(
                        {"class": "card"},
                        html.DIV(
                            html.DIV({"class": "card"}, "Content 1"),
                            html.BR(),
                            html.DIV(
                                {"class": "card"},
                                html.DIV({"class": "card-header"}, "Code"),
                                html.DIV({"class": "card-body"}, "Source"),
                            ),
                        ),
                    ),
                ),
            ),
        )

    with TestRenderer.render(App) as result:
        assert _count_cards(result) == 3  # outer + 2 inner
        current.value = False
        assert _count_cards(result) == 3  # outer + 2 inner


def test_flat_card_structure_works():
    """
    Flat .card structure (no nesting) should work correctly.
    This is the workaround that was confirmed to work.
    """
    current = Signal(True)

    @define_component
    def App(ctx: ComponentContext):
        return html.DIV(
            {"class": "wrapper"},
            switch(
                {"case": current, "generator": lambda: None},
                default=lambda: html.DIV(
                    html.H5("Title"),
                    html.DIV({"class": "card"}, "Content 1"),
                    html.DIV({"class": "card"}, "Content 2"),
                ),
            ),
        )

    with TestRenderer.render(App) as result:
        assert _count_cards(result) == 2
        current.value = False
        assert _count_cards(result) == 2


if __name__ == "__main__":
    test_nested_card_survives_switch()
    test_nested_card_with_br_sibling()
    test_flat_card_structure_works()
    print("All tests passed!")
