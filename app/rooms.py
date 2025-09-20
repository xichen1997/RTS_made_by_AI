"""Room and connection management for the RTS web server."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict
from typing import Dict, Optional

from fastapi import WebSocket

from . import config
from .game import GameFullError, RTSGame


class RoomError(RuntimeError):
    """Base class for room related failures."""


class RoomNotFound(RoomError):
    """Raised when a user attempts to join a missing room."""


class GameRoom:
    """Holds the game simulation and active websocket connections."""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.game = RTSGame(room_id)
        self.connections: Dict[str, WebSocket] = {}
        self.player_names: Dict[str, str] = {}
        self.loop_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()
        self.tick_interval = 1.0 / config.TICK_RATE
        self.broadcast_interval = 1.0 / config.STATE_BROADCAST_RATE
        self._time_since_broadcast = 0.0

    async def join(self, websocket: WebSocket, player_name: str) -> str:
        """Insert a new player into the match using an accepted websocket."""
        player_id = uuid.uuid4().hex
        async with self.lock:
            try:
                self.game.add_player(player_id, player_name)
            except GameFullError as exc:  # pragma: no cover - simple guard
                await websocket.close(code=4000, reason=str(exc))
                raise
            self.connections[player_id] = websocket
            self.player_names[player_id] = player_name
            if not self.loop_task or self.loop_task.done():
                self.loop_task = asyncio.create_task(self._run_loop())
        await websocket.send_json(
            {
                "type": "welcome",
                "player_id": player_id,
                "room_id": self.room_id,
                "player_name": player_name,
            }
        )
        await self.broadcast(
            {
                "type": "event",
                "message": f"{player_name} joined the battle.",
            }
        )
        return player_id

    async def leave(self, player_id: str) -> None:
        async with self.lock:
            websocket = self.connections.pop(player_id, None)
            name = self.player_names.pop(player_id, None)
            self.game.remove_player(player_id)
        if websocket:
            try:
                await websocket.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
        if name:
            await self.broadcast(
                {"type": "event", "message": f"{name} has left the battle."}
            )

    async def _run_loop(self) -> None:
        try:
            while self.connections:
                await asyncio.sleep(self.tick_interval)
                self.game.update(self.tick_interval)
                self._time_since_broadcast += self.tick_interval
                if self._time_since_broadcast >= self.broadcast_interval:
                    snapshot = asdict(self.game.snapshot())
                    await self.broadcast({"type": "state", "state": snapshot})
                    self._time_since_broadcast = 0.0
        finally:
            self._time_since_broadcast = 0.0

    async def broadcast(self, message: Dict) -> None:
        """Send a JSON message to all connected players."""
        if not self.connections:
            return
        stale: list[str] = []
        for player_id, ws in list(self.connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(player_id)
        for player_id in stale:
            self.connections.pop(player_id, None)
            self.player_names.pop(player_id, None)
            self.game.remove_player(player_id)

    async def dispatch_command(self, player_id: str, command: Dict) -> None:
        """Queue a command if the issuing player is still connected."""
        if player_id not in self.connections:
            raise RoomError("player not connected")
        self.game.enqueue_command(player_id, command)


class RoomManager:
    """Registry that lazily instantiates rooms on demand."""

    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        self.lock = asyncio.Lock()

    async def get_room(self, room_id: str) -> GameRoom:
        async with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                room = GameRoom(room_id)
                self.rooms[room_id] = room
            return room

    async def remove_room_if_empty(self, room_id: str) -> None:
        async with self.lock:
            room = self.rooms.get(room_id)
            if room and not room.connections:
                self.rooms.pop(room_id, None)


__all__ = ["RoomManager", "GameRoom", "RoomError", "RoomNotFound"]
