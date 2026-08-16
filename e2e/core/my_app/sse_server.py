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
