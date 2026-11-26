import json
from dataclasses import dataclass
from typing import Any

from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html, repeat, switch
from webcompy.ports import FetchMiddleware, FetchNext, FetchRequest, FetchStream, Response, add_fetch_middleware
from webcompy.signal import ReactiveList, use_reactive_list, use_state


@dataclass
class Note:
    id: int
    title: str
    tag: str


def _json_response(payload: Any, status_code: int = 200, status_text: str = "OK") -> Response:
    return Response(
        text=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        status_code=status_code,
        status_text=status_text,
        ok=status_code < 400,
    )


def create_notes_mock() -> FetchMiddleware:
    store: list[dict[str, Any]] = [
        {"id": 1, "title": "Intercept GET /api/notes", "tag": "mock"},
        {"id": 2, "title": "Validate response with dataclass", "tag": "schema"},
    ]

    async def notes_mock(request: FetchRequest, next: FetchNext) -> Response | FetchStream:
        path = request.url.split("?", 1)[0]
        raw_body = request.body.decode("utf-8") if isinstance(request.body, bytes) else (request.body or "{}")
        if path == "/api/notes" and request.method == "GET":
            return _json_response(list(store))
        if path == "/api/notes" and request.method == "POST":
            payload = json.loads(raw_body)
            title = str(payload.get("title", "")).strip()
            if not title:
                return _json_response({"error": "title required"}, 400, "Bad Request")
            created = {
                "id": max((item["id"] for item in store), default=0) + 1,
                "title": title,
                "tag": str(payload.get("tag", "user")),
            }
            store.append(created)
            return _json_response(created, 201, "Created")
        if path.startswith("/api/notes/") and request.method == "DELETE":
            note_id = int(path.rsplit("/", 1)[-1])
            for idx, item in enumerate(store):
                if item["id"] == note_id:
                    store.pop(idx)
                    return _json_response({"deleted": note_id})
            return _json_response({"error": "not found"}, 404, "Not Found")
        return await next(request)

    return notes_mock


def create_trace_middleware(trace_log: ReactiveList[str]) -> FetchMiddleware:
    counter = 0

    async def trace_middleware(request: FetchRequest, next: FetchNext) -> Response | FetchStream:
        nonlocal counter
        counter += 1
        trace_id = f"trace-{counter}"
        request.headers = {**(request.headers or {}), "X-Demo-Trace": trace_id}
        response = await next(request)
        trace_log.append(f"{request.method} {request.url} -> {response.status_code} ({trace_id})")
        return response

    return trace_middleware


@define_component()
def FetchMiddlewareDemo(_: ComponentContext[None]):
    trace_log: ReactiveList[str] = use_reactive_list(lambda: [])
    notes: ReactiveList[Note] = use_reactive_list(lambda: [])
    title_input = use_state(lambda: "")
    status = use_state(lambda: "")

    add_fetch_middleware(create_trace_middleware(trace_log))
    add_fetch_middleware(create_notes_mock())

    async def _load_notes() -> list[Note]:
        loaded = await HttpClient.get("/api/notes", response_type=list[Note])
        notes.value = loaded
        return loaded

    notes_result = use_async_result(_load_notes)

    @AsyncWrapper()
    async def _add_note(_ev: Any) -> None:
        title = title_input.value.strip()
        if not title:
            status.value = "Enter a note title."
            return
        created = await HttpClient.post("/api/notes", json={"title": title, "tag": "custom"}, response_type=Note)
        notes.append(created)
        title_input.value = ""
        status.value = f"Saved note #{created.id}"

    def _delete_note(note_id: int):
        @AsyncWrapper()
        async def _on_click(_ev: Any) -> None:
            await HttpClient.delete(f"/api/notes/{note_id}")
            notes.value = [n for n in notes.value if n.id != note_id]
            status.value = f"Deleted note #{note_id}"

        return _on_click

    return html.DIV(
        {"class": "fetch-mw-demo"},
        html.H1({}, "Fetch Middleware Mock"),
        html.DIV(
            {"class": "note-form"},
            html.INPUT({"type": "text", "placeholder": "New note title...", ":bind": title_input}),
            html.BUTTON({"type": "button", "@click": _add_note}, "Add Note"),
        ),
        html.P({"class": "status-line"}, status),
        switch(
            {
                "case": notes_result.is_success,
                "generator": lambda: html.UL(
                    {"class": "notes-list"},
                    repeat(
                        notes,
                        lambda note, _key: html.LI(
                            {"class": "note-item"},
                            html.SPAN({"class": "note-title"}, f"{note.title} [{note.tag}]"),
                            html.BUTTON({"type": "button", "@click": _delete_note(note.id)}, "Delete"),
                        ),
                        key=lambda note: note.id,
                    ),
                ),
            },
            default=lambda: html.P({}, "Loading notes..."),
        ),
        html.H2({}, "Middleware Trace"),
        html.UL(
            {"class": "trace-list"},
            repeat(trace_log, lambda entry: html.LI({}, entry)),
        ),
    )


FetchMiddlewareDemo.scoped_style = {
    ".fetch-mw-demo": {
        "font-family": "var(--font-sans, sans-serif)",
        "padding": "var(--space-3)",
        "color": "var(--color-fg)",
        "max-width": "38rem",
    },
    ".fetch-mw-demo h1": {
        "margin": "0 0 var(--space-3) 0",
        "font-size": "var(--font-size-xl, 1.25rem)",
    },
    ".fetch-mw-demo h2": {
        "margin": "var(--space-3) 0 var(--space-2) 0",
        "font-size": "var(--font-size-base, 1rem)",
    },
    ".note-form": {
        "display": "flex",
        "gap": "var(--space-2)",
        "margin-bottom": "var(--space-2)",
    },
    ".note-form input": {
        "flex": "1",
        "padding": "0.35rem 0.5rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg)",
        "color": "var(--color-fg)",
    },
    ".status-line": {
        "font-size": "var(--font-size-sm, 0.875rem)",
        "color": "var(--color-link)",
        "min-height": "1.2rem",
    },
    ".notes-list, .trace-list": {
        "list-style": "none",
        "padding": "0",
        "margin": "0",
    },
    ".note-item": {
        "display": "flex",
        "justify-content": "space-between",
        "align-items": "center",
        "padding": "var(--space-2) var(--space-3)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "margin-bottom": "var(--space-2)",
        "background": "var(--color-bg-card)",
    },
    ".trace-list li": {
        "font-family": "var(--font-mono, monospace)",
        "font-size": "0.85rem",
        "padding": "0.25rem 0.5rem",
        "border-bottom": "1px solid var(--color-border)",
    },
    ".fetch-mw-demo button": {
        "padding": "0.35rem 0.75rem",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "background": "var(--color-bg-elevated)",
        "color": "var(--color-fg)",
        "cursor": "pointer",
    },
}

app = WebComPyApp(root_component=FetchMiddlewareDemo)
app.run()
