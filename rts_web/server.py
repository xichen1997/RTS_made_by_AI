"""FastAPI application exposing the RTS game over websockets."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .game.constants import TICK_SECONDS
from .game.models import Action
from .game.state import GameState

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"
INDEX_FILE = STATIC_DIR / "index.html"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="ChronoFront", description="Web-based RTS prototype")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.state.game_state = GameState()
    app.state.lock = asyncio.Lock()
    app.state.connections: Dict[str, WebSocket] = {}
    app.state.loop_task: Optional[asyncio.Task] = None
    return app


app = create_app()


@app.on_event("startup")
async def _start_game_loop() -> None:
    async def game_loop() -> None:
        while True:
            async with app.state.lock:
                events = app.state.game_state.tick_once()
                snapshot = app.state.game_state.snapshot()
            message = {"type": "state", "payload": snapshot.__dict__, "events": events}
            await _broadcast(message)
            await asyncio.sleep(TICK_SECONDS)

    app.state.loop_task = asyncio.create_task(game_loop())


@app.on_event("shutdown")
async def _stop_game_loop() -> None:
    if app.state.loop_task:
        app.state.loop_task.cancel()
        try:
            await app.state.loop_task
        except asyncio.CancelledError:
            pass


@app.get("/")
async def serve_index() -> FileResponse:
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=500, detail="Missing web assets")
    return FileResponse(INDEX_FILE)


async def _broadcast(message: dict) -> None:
    disconnects = []
    for player_id, websocket in list(app.state.connections.items()):
        try:
            await websocket.send_json(message)
        except (RuntimeError, WebSocketDisconnect):
            disconnects.append(player_id)
    for player_id in disconnects:
        await _disconnect(player_id)


async def _disconnect(player_id: str) -> None:
    websocket = app.state.connections.pop(player_id, None)
    if websocket:
        await websocket.close()
    async with app.state.lock:
        app.state.game_state.remove_player(player_id)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, name: str = "Commander") -> None:
    await websocket.accept()
    async with app.state.lock:
        player = app.state.game_state.add_player(name)
        if not player:
            await websocket.send_json({"type": "error", "message": "Server is full."})
            await websocket.close()
            return
        app.state.connections[player.id] = websocket
        snapshot = app.state.game_state.snapshot()
    await websocket.send_json({"type": "init", "payload": snapshot.__dict__, "player_id": player.id})

    try:
        while True:
            data = await websocket.receive_json()
            action_type = str(data.get("type", "")).lower()
            payload = data.get("payload", {})
            action = Action(player_id=player.id, type=action_type, payload=payload)
            async with app.state.lock:
                app.state.game_state.queue_action(action)
    except WebSocketDisconnect:
        await _disconnect(player.id)


__all__ = ["app", "create_app"]
