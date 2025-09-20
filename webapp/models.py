"""Data models for the Nova Frontier RTS simulation.

The module defines serialisable dataclasses for all pieces of game state
exchanged between the server and the browser client.  A lightweight schema
allows us to document the wire protocol and keep the client entirely stateless;
all authoritative logic lives on the server.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple

from . import config

Vector2 = Tuple[float, float]
TileCoord = Tuple[int, int]


class PlayerColor(str, Enum):
    """Distinct colours assigned to players for rendering on the client."""

    BLUE = "#3b82f6"
    RED = "#ef4444"
    GREEN = "#22c55e"
    ORANGE = "#f97316"


@dataclass(slots=True)
class ResourceNode:
    """A deposit that can be harvested by player harvesters."""

    id: int
    position: TileCoord
    value_remaining: int = config.RESOURCE_NODE_VALUE

    def take(self, amount: int) -> int:
        """Remove up to ``amount`` credits and return the quantity gathered."""

        gathered = min(amount, self.value_remaining)
        self.value_remaining -= gathered
        return gathered

    def serialise(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "x": self.position[0],
            "y": self.position[1],
            "value": self.value_remaining,
        }


class UnitType(str, Enum):
    """High level unit archetypes used by the simulation."""

    HARVESTER = "harvester"
    INFANTRY = "infantry"


@dataclass(slots=True)
class Unit:
    """A mobile entity that can move, attack and harvest resources."""

    id: int
    owner_id: str
    unit_type: UnitType
    position: Vector2
    target_position: Optional[Vector2] = None
    target_unit: Optional[int] = None
    health: int = config.UNIT_MAX_HEALTH
    progress: float = 0.0
    cooldown: float = 0.0
    carrying: int = 0

    def serialise(self) -> Dict[str, object]:
        data = asdict(self)
        data.update({
            "x": self.position[0],
            "y": self.position[1],
            "target_position": self.target_position,
        })
        return data


@dataclass(slots=True)
class Base:
    """Player headquarters. Destroying it ends the match."""

    id: int
    owner_id: str
    position: TileCoord
    health: int = config.BASE_MAX_HEALTH
    cooldown: float = 0.0

    def serialise(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "x": self.position[0],
            "y": self.position[1],
            "health": self.health,
        }


@dataclass(slots=True)
class Player:
    """Runtime representation of a connected player."""

    id: str
    name: str
    color: PlayerColor
    credits: int = config.STARTING_CREDITS
    base: Optional[Base] = None
    units: Dict[int, Unit] = field(default_factory=dict)

    def serialise(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color.value,
            "credits": self.credits,
            "base": self.base.serialise() if self.base else None,
            "units": [unit.serialise() for unit in self.units.values()],
        }


@dataclass(slots=True)
class GameState:
    """All authoritative state for a single match."""

    players: Dict[str, Player]
    resource_nodes: Dict[int, ResourceNode]
    time_elapsed: float = 0.0
    winner: Optional[str] = None

    def serialise(self) -> Dict[str, object]:
        return {
            "players": {pid: player.serialise() for pid, player in self.players.items()},
            "resources": [node.serialise() for node in self.resource_nodes.values()],
            "time": self.time_elapsed,
            "winner": self.winner,
            "config": {
                "map": [config.MAP_WIDTH, config.MAP_HEIGHT],
                "tile_size": config.TILE_SIZE,
                "game_name": config.GAME_NAME,
            },
        }


@dataclass(slots=True)
class Command:
    """A player issued command that will be executed on the next tick."""

    player_id: str
    action: str
    payload: Dict[str, object]
    issued_at: float


@dataclass(slots=True)
class MatchView:
    """DTO used to push state updates to websocket clients."""

    state: GameState
    events: List[Dict[str, object]]

    def serialise(self) -> Dict[str, object]:
        return {
            "state": self.state.serialise(),
            "events": self.events,
        }
