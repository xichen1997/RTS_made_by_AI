"""ASGI application exposing the Nova Frontier RTS experience."""
from __future__ import annotations

import pathlib
from typing import Final

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState

from . import config
from .matchmaking import Match, Matchmaker, PlayerConnection

APP_DIR: Final = pathlib.Path(__file__).resolve().parent
FRONTEND_DIR: Final = APP_DIR.parent / "frontend"

app = FastAPI(title=config.GAME_NAME, version="0.1.0")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


async def get_matchmaker() -> Matchmaker:
    if not hasattr(app.state, "matchmaker"):
        app.state.matchmaker = Matchmaker()
    return app.state.matchmaker


@app.get("/health")
async def healthcheck() -> JSONResponse:
    """Simple readiness probe for container orchestration."""

    matchmaker = getattr(app.state, "matchmaker", None)
    active_matches = len(matchmaker._active_matches) if matchmaker else 0
    return JSONResponse({"status": "ok", "players_active": active_matches})


@app.get("/")
async def index() -> FileResponse:
    """Serve the compiled front-end."""

    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Front-end not built")
    return FileResponse(index_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, matchmaker: Matchmaker = Depends(get_matchmaker)) -> None:
    name = websocket.query_params.get("name", "Commander")
    await websocket.accept()
    connection: PlayerConnection | None = None
    match: Match | None = None
    try:
        connection, match = await matchmaker.register(name, websocket)
        await match.wait()
    except WebSocketDisconnect:
        pass
    finally:
        if connection is not None:
            await matchmaker.handle_disconnect(connection)
        if match is not None:
            await matchmaker.remove_match(match)
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()
