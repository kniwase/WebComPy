import asyncio
import uuid

from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route


def create_sse_app() -> Starlette:
    async def events(request):
        session_id = uuid.uuid4().hex

        async def generate():
            yield f"event: session\ndata: {session_id}\n\n"
            for i in range(1, 4):
                yield f"id: {i}\nevent: message\ndata: ping-{i}\n\n"
            while True:
                await asyncio.sleep(3600)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    return Starlette(routes=[Route("/events", events)])


def create_sse_post_app() -> Starlette:
    async def post_query(request):
        body_text = (await request.body()).decode("utf-8")
        last_event_id = request.headers.get("last-event-id")

        if last_event_id is None:

            async def generate():
                yield f"id: 0\nevent: message\ndata: echo:{body_text}\n\n"
                for i in range(1, 4):
                    yield f"id: {i}\nevent: message\ndata: ping-{i}\n\n"

        else:

            async def generate():
                for i in range(4, 7):
                    yield f"id: {i}\nevent: message\ndata: ping-{i}\n\n"
                await asyncio.sleep(3600)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    return Starlette(routes=[Route("/post-query", post_query, methods=["POST"])])
