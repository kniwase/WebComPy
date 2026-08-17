import itertools

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

_conn_counter = itertools.count(1)


def create_ws_app() -> Starlette:
    async def echo(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text(f"conn:{next(_conn_counter)}")
        try:
            while True:
                message = await websocket.receive_text()
                if message == "kill":
                    await websocket.close(code=1011)
                    return
                await websocket.send_text(f"echo:{message}")
        except WebSocketDisconnect:
            pass

    return Starlette(routes=[WebSocketRoute("/echo", echo)])
