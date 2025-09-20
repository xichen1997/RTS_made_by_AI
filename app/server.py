"""FastAPI application that exposes the RTS game over WebSockets."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .rooms import RoomManager

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="Red Horizon Online")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


async def get_manager() -> RoomManager:
    return app.state.room_manager


@app.on_event("startup")
async def startup() -> None:
    app.state.room_manager = RoomManager()


@app.get("/")
async def index() -> FileResponse:
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Client not built")
    return FileResponse(index_path)


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, room_id: str, manager: RoomManager = Depends(get_manager)
) -> None:
    await websocket.accept()
    join_payload: Dict[str, Any] = await websocket.receive_json()
    if join_payload.get("type") != "join":
        await websocket.close(code=4001)
        return
    player_name = join_payload.get("player_name") or "Commander"
    room = await manager.get_room(room_id)
    player_id = await room.join(websocket, player_name)

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")
            if msg_type == "command":
                await room.dispatch_command(player_id, message.get("command", {}))
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await room.leave(player_id)
        await manager.remove_room_if_empty(room_id)


__all__ = ["app"]
