from __future__ import annotations

import asyncio

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.elements.generators import suspense


@define_component("async-greeting")
async def AsyncGreeting(context: ComponentContext[None]):
    await asyncio.sleep(0.01)
    return html.DIV({"data-testid": "suspense-data"}, html.H2({}, "Resolved!"))


@define_component("suspense-page")
def SuspensePage(context: ComponentContext[None]):
    context.set_title("Suspense - E2E")

    return html.DIV(
        {"data-testid": "suspense-page"},
        html.H2({}, "Suspense Test"),
        suspense(
            fallback=lambda: html.P({"data-testid": "fallback"}, "Loading..."),
            children=lambda: AsyncGreeting(None),
        ),
    )
