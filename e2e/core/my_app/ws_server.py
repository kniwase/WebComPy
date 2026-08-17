import itertools
import json

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

    async def typed_echo(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                message = await websocket.receive_text()
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue
                op = payload.get("op")
                if op == "roundtrip":
                    await websocket.send_text(
                        json.dumps(
                            {
                                "user": "ada",
                                "text": "hello",
                                "at": "2025-01-02T03:04:05",
                                "__webcompy_transfer_meta__": {"/at": "datetime"},
                            }
                        )
                    )
                elif op == "bad":
                    await websocket.send_text("this is not json")
                elif op == "extra":
                    await websocket.send_text(json.dumps({"user": "ada", "text": "hello", "admin": True}))
        except WebSocketDisconnect:
            pass

    return Starlette(
        routes=[
            WebSocketRoute("/echo", echo),
            WebSocketRoute("/typed", typed_echo),
        ]
    )
