"""Matchmaking utilities and WebSocket session orchestration."""
from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from . import config
from .engine import GameEngine
from .models import Command, MatchView, Player, PlayerColor


@dataclass(slots=True)
class PlayerConnection:
    """State bound to an active websocket client."""

    websocket: WebSocket
    player: Player
    match_ready: asyncio.Future["Match"] = field(default_factory=asyncio.Future)


class Match:
    """Wrapper that binds ``GameEngine`` to a set of websocket clients."""

    def __init__(self, connections: List[PlayerConnection]) -> None:
        self.connections = connections
        players: Dict[str, Player] = {conn.player.id: conn.player for conn in connections}
        self.engine = GameEngine(seed=int(time.time()), players=players)
        self._runner: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        await self.engine.start()
        self._runner = asyncio.create_task(self._run())

    async def _run(self) -> None:
        subscriber_tasks = []
        listener_tasks = []
        try:
            for connection in self.connections:
                queue = self.engine.subscribe()
                subscriber_tasks.append(asyncio.create_task(self._dispatch_updates(connection, queue)))
                listener_tasks.append(asyncio.create_task(self._receive_commands(connection)))
            await self.engine.wait_until_finished()
        finally:
            for task in listener_tasks + subscriber_tasks:
                task.cancel()
            await asyncio.gather(*listener_tasks, *subscriber_tasks, return_exceptions=True)
            await self.engine.stop()

    async def _dispatch_updates(self, connection: PlayerConnection, queue: asyncio.Queue[MatchView]) -> None:
        websocket = connection.websocket
        try:
            await websocket.send_json(
                {
                    "type": "welcome",
                    "player": {
                        "id": connection.player.id,
                        "name": connection.player.name,
                        "color": connection.player.color.value,
                    },
                    "message": config.LOBBY_WELCOME_MESSAGE,
                }
            )
            while True:
                view = await queue.get()
                payload = view.serialise()
                payload["type"] = "state"
                await websocket.send_json(payload)
                if view.state.winner is not None:
                    return
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging hook
            await websocket.close(code=1011, reason=f"Server error: {exc}")
            raise
        finally:
            self.engine.unsubscribe(queue)

    async def _receive_commands(self, connection: PlayerConnection) -> None:
        websocket = connection.websocket
        try:
            while True:
                message = await websocket.receive_json()
                command = Command(
                    player_id=connection.player.id,
                    action=message.get("action", ""),
                    payload=message.get("payload", {}),
                    issued_at=time.time(),
                )
                self.engine.queue_command(command)
        except asyncio.CancelledError:
            raise
        except WebSocketDisconnect:
            return
        except Exception:
            await websocket.close(code=1008)

    async def wait(self) -> None:
        if self._runner is not None:
            await self._runner


class Matchmaker:
    """Pairs players into matches and manages the connection lifecycle."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._waiting: Optional[PlayerConnection] = None
        self._active_matches: List[Match] = []
        self._color_cycle = iter(PlayerColor)

    def _next_color(self) -> PlayerColor:
        try:
            return next(self._color_cycle)
        except StopIteration:
            self._color_cycle = iter(PlayerColor)
            return next(self._color_cycle)

    async def register(self, name: str, websocket: WebSocket) -> tuple[PlayerConnection, Match]:
        player = Player(id=str(uuid.uuid4()), name=name, color=self._next_color())
        connection = PlayerConnection(websocket=websocket, player=player)
        async with self._lock:
            if self._waiting is None:
                self._waiting = connection
            else:
                opponent = self._waiting
                self._waiting = None
                match = Match([opponent, connection])
                opponent.match_ready.set_result(match)
                connection.match_ready.set_result(match)
                self._active_matches.append(match)
                await match.start()
        match = await connection.match_ready
        return connection, match

    async def remove_match(self, match: Match) -> None:
        async with self._lock:
            with contextlib.suppress(ValueError):
                self._active_matches.remove(match)

    async def handle_disconnect(self, connection: PlayerConnection) -> None:
        async with self._lock:
            if self._waiting is connection:
                self._waiting = None
