from dataclasses import dataclass
from typing import Any

from webcompy.aio import AsyncWrapper
from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, repeat
from webcompy.rpc import Procedure, RpcContext, RpcHttpClient, RpcMiddleware, add_rpc_middleware, batch
from webcompy.signal import ReactiveList, use_computed, use_reactive_list, use_state

UNIT_PRICES = {
    "Keyboard": 120,
    "Monitor": 340,
    "Dock": 180,
}


@dataclass
class QuoteParams:
    item: str
    quantity: int


@dataclass
class QuoteResult:
    item: str
    quantity: int
    unit_price: int
    total: int


@dataclass
class SummaryParams:
    currency: str


@dataclass
class SummaryResult:
    currency: str
    catalog_size: int


quote_order = Procedure("orders.quote", QuoteParams, QuoteResult)
catalog_summary = Procedure("catalog.summary", SummaryParams, SummaryResult)


def _synthesize_result(method: str, params: Any) -> dict[str, Any]:
    if method == "orders.quote":
        unit_price = UNIT_PRICES.get(params.item, 100)
        return {
            "item": params.item,
            "quantity": params.quantity,
            "unit_price": unit_price,
            "total": unit_price * params.quantity,
        }
    if method == "catalog.summary":
        return {
            "currency": params.currency,
            "catalog_size": len(UNIT_PRICES),
        }
    return {}


def create_rpc_mock(call_log: ReactiveList[str]) -> RpcMiddleware:
    async def rpc_mock(ctx: RpcContext, next: Any) -> Any:
        ctx.headers["X-Demo-Rpc-Mock"] = "active"
        if ctx.is_batch:
            entries = ctx.batch_entries or []
            names = ", ".join(entry.method for entry in entries)
            call_log.append(f"batch([{names}]) -> synthesized {len(entries)} responses")
            fragments = [{"result": _synthesize_result(entry.method, entry.params)} for entry in entries]
            return await next(ctx, response=fragments)
        if ctx.method in {"orders.quote", "catalog.summary"}:
            call_log.append(f"{ctx.method}({ctx.params}) -> synthesized result")
            return await next(ctx, response={"result": _synthesize_result(ctx.method, ctx.params)})
        return await next(ctx)

    return rpc_mock


@define_component()
def RpcMiddlewareDemo(_: ComponentContext[None]):
    call_log: ReactiveList[str] = use_reactive_list(lambda: [])
    selected_item = use_state(lambda: "Keyboard")
    quantity = use_state(lambda: 2)
    quote_output = use_state(lambda: "Click Request Quote to invoke orders.quote")
    batch_output = use_state(lambda: "")

    add_rpc_middleware(create_rpc_mock(call_log))
    client = RpcHttpClient()

    def _select_item(name: str):
        def _on_click(_ev: Any) -> None:
            selected_item.value = name

        return _on_click

    def _adjust_qty(delta: int):
        def _on_click(_ev: Any) -> None:
            quantity.value = max(1, quantity.value + delta)

        return _on_click

    @AsyncWrapper()
    async def _request_quote(_ev: Any) -> None:
        result = await quote_order(client, QuoteParams(item=selected_item.value, quantity=quantity.value))
        quote_output.value = f"{result.quantity}x {result.item} @ ${result.unit_price} -> Total: ${result.total}"

    @AsyncWrapper()
    async def _run_batch(_ev: Any) -> None:
        quote, summary = await batch(
            quote_order(client, QuoteParams(item=selected_item.value, quantity=quantity.value)),
            catalog_summary(client, SummaryParams(currency="USD")),
        )
        quote_output.value = f"{quote.quantity}x {quote.item} @ ${quote.unit_price} -> Total: ${quote.total}"
        batch_output.value = f"Catalog size: {summary.catalog_size} items ({summary.currency})"

    return html.DIV(
        {"class": "rpc-mw-demo"},
        html.H1({}, "RPC Middleware Mock"),
        html.DIV(
            {"class": "item-picker"},
            *tuple(
                html.BUTTON(
                    {
                        "type": "button",
                        "class": use_computed(lambda name=name: "active" if selected_item.value == name else ""),
                        "@click": _select_item(name),
                    },
                    name,
                )
                for name in UNIT_PRICES
            ),
        ),
        html.DIV(
            {"class": "qty-row"},
            html.SPAN({}, "Quantity:"),
            html.BUTTON({"type": "button", "@click": _adjust_qty(-1)}, "-"),
            html.SPAN({"class": "qty-value"}, use_computed(lambda: str(quantity.value))),
            html.BUTTON({"type": "button", "@click": _adjust_qty(1)}, "+"),
        ),
        html.DIV(
            {"class": "action-row"},
            html.BUTTON({"type": "button", "class": "primary-btn", "@click": _request_quote}, "Request Quote"),
            html.BUTTON({"type": "button", "@click": _run_batch}, "Run Batch"),
        ),
        html.P({"class": "quote-result"}, quote_output),
        html.P({"class": "batch-result"}, batch_output),
        html.H2({}, "Middleware Call Log"),
        html.UL(
            {"class": "log-list"},
            repeat(call_log, lambda entry: html.LI({}, entry)),
        ),
    )


RpcMiddlewareDemo.scoped_style = {
    ".rpc-mw-demo": {
        "font-family": "var(--font-sans, sans-serif)",
        "padding": "var(--space-3)",
        "color": "var(--color-fg)",
        "max-width": "38rem",
    },
    ".rpc-mw-demo h1": {
        "margin": "0 0 var(--space-3) 0",
        "font-size": "var(--font-size-xl, 1.25rem)",
    },
    ".rpc-mw-demo h2": {
        "margin": "var(--space-3) 0 var(--space-2) 0",
        "font-size": "var(--font-size-base, 1rem)",
    },
    ".item-picker, .qty-row, .action-row": {
        "display": "flex",
        "align-items": "center",
        "gap": "var(--space-2)",
        "margin-bottom": "var(--space-2)",
        "flex-wrap": "wrap",
    },
    ".qty-value": {
        "min-width": "2rem",
        "text-align": "center",
        "font-weight": "600",
    },
    ".quote-result, .batch-result": {
        "font-weight": "600",
        "margin": "var(--space-2) 0",
    },
    ".log-list": {
        "list-style": "none",
        "padding": "0",
        "margin": "0",
    },
    ".log-list li": {
        "font-family": "var(--font-mono, monospace)",
        "font-size": "0.85rem",
        "padding": "0.25rem 0.5rem",
        "border-bottom": "1px solid var(--color-border)",
    },
    ".rpc-mw-demo button": {
        "padding": "0.35rem 0.75rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
    ".rpc-mw-demo button.active": {
        "border-color": "var(--color-accent)",
        "color": "var(--color-accent)",
        "font-weight": "600",
    },
    ".rpc-mw-demo button.primary-btn": {
        "border-color": "var(--color-accent)",
        "background": "var(--color-accent)",
        "color": "#ffffff",
    },
}

app = WebComPyApp(root_component=RpcMiddlewareDemo)
app.run()
