from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.ui.code_block import CodeBlock
from webcompy.utils import strip_multiline_text

from ...components.ui import InlineCode, Section


def _code(code: str) -> str:
    return strip_multiline_text(code).strip()


@define_component
def SignalStream(_: ComponentContext[None]):
    return html.DIV(
        {"class": "page-container"},
        Section(
            {"heading": "Signals and Streams"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "WebComPy state primitives are ",
                    html.STRONG({}, "cells"),
                    ": ",
                    InlineCode({"text": "Signal"}),
                    ", ",
                    InlineCode({"text": "Computed"}),
                    ", and ",
                    InlineCode({"text": "ReactiveList"}),
                    " hold ",
                    html.EM({}, "current state"),
                    " and propagate changes, with an equality contract that suppresses same-value writes.",
                    " Realtime data (WebSocket/SSE messages, progress ticks) has ",
                    html.STRONG({}, "occurrence"),
                    " semantics instead: every arrival matters, duplicates included.",
                    " The ",
                    InlineCode({"text": "webcompy.aio"}),
                    " stream utilities bridge these two worlds.",
                )
            },
        ),
        Section(
            {"heading": "to_signal: one-shot values"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "The ",
                    InlineCode({"text": "to_signal"}),
                    " utility pumps an ",
                    InlineCode({"text": "AsyncIterable"}),
                    " (or plain ",
                    InlineCode({"text": "Iterable"}),
                    ") into a ",
                    InlineCode({"text": "Signal"}),
                    ". The initial value is mandatory so the UI always has a renderable value before the first item arrives:",
                    CodeBlock(
                        {
                            "lang": "python",
                            "code": _code(
                                """
                                from webcompy.aio import to_signal

                                result = to_signal(progress_ticks(), 0)
                                # result.value: Signal[int]  — updated per item
                                # result.error: Signal[Exception | None]
                                # result.finished: Signal[bool]
                                """
                            ),
                        }
                    ),
                    "Because the bridge target is a ",
                    InlineCode({"text": "Signal"}),
                    ", the cell equality contract applies: an item equal to the current value does not notify consumers.",
                    " Use ",
                    InlineCode({"text": "to_reactive_list"}),
                    " or ",
                    InlineCode({"text": "to_async_iter"}),
                    " when every occurrence matters.",
                )
            },
        ),
        Section(
            {"heading": "to_reactive_list: accumulating feeds"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "Chat logs, notification feeds, and event histories accumulate ",
                    html.EM({}, "every"),
                    " item, duplicates included:",
                    CodeBlock(
                        {
                            "lang": "python",
                            "code": _code(
                                """
                                from webcompy.aio import to_reactive_list

                                feed = to_reactive_list(ws_messages, maxlen=100)
                                # feed.items: ReactiveList[str]  — newest 100 items
                                # feed.error: Signal[Exception | None]
                                # feed.finished: Signal[bool]
                                """
                            ),
                        }
                    ),
                    "Set ",
                    InlineCode({"text": "maxlen"}),
                    " to keep only the newest N items (drop-oldest). Without it the list grows unbounded, which is deliberate ",
                    "but SHALL be capped for long-lived streams.",
                )
            },
        ),
        Section(
            {"heading": "to_async_iter: consuming signal updates"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "The ",
                    InlineCode({"text": "to_async_iter"}),
                    " utility bridges a ",
                    InlineCode({"text": "Signal"}),
                    "'s updates into an async iterator. Each item corresponds to a signal ",
                    html.EM({}, "update"),
                    " (signal-level dedup applies upstream):",
                    CodeBlock(
                        {
                            "lang": "python",
                            "code": _code(
                                """
                                from webcompy.aio import to_async_iter

                                async for value in to_async_iter(count, emit_initial=True):
                                    await handle(value)
                                """
                            ),
                        }
                    ),
                    "Items produced before subscription are not replayed; pass ",
                    InlineCode({"text": "emit_initial=True"}),
                    " to enqueue the current value first. ",
                    InlineCode({"text": "maxlen"}),
                    " caps the internal buffer with drop-oldest semantics for slow consumers.",
                )
            },
        ),
        Section(
            {"heading": "Queue policy and lifecycle"},
            slots={
                "default": lambda: html.DIV(
                    {},
                    "Buffers are unbounded by default; a slow consumer lets the queue grow, so long-lived streams should set ",
                    InlineCode({"text": "maxlen"}),
                    ". Bridges created inside component setup are torn down automatically on component destroy; ",
                    "standalone usage requires an explicit ",
                    InlineCode({"text": "aclose()"}),
                    " call:",
                    CodeBlock(
                        {
                            "lang": "python",
                            "code": _code(
                                """
                                result = to_signal(infinite_source(), 0)
                                ...
                                await result.aclose()  # stop pumping
                                """
                            ),
                        }
                    ),
                    "Bridged values are derived client-side views and never participate in hydration transfer (same rule as ",
                    InlineCode({"text": "Computed"}),
                    ").",
                )
            },
        ),
    )


SignalStream.scoped_style = {
    ".page-container": {
        "max-width": "1200px",
        "margin": "0 auto",
        "padding": "var(--space-4)",
    },
}
