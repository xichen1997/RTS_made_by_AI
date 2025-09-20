"""Data structures used by the RTS game state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .constants import Vec2


@dataclass
class PlayerState:
    """Runtime information tracked for a connected commander."""

    id: str
    name: str
    color: str
    credits: int
    rally_point: Optional[Vec2] = None
    income_per_tick: int = 0
    is_active: bool = True
    defeat_tick: Optional[int] = None


@dataclass
class StructureState:
    """Simple representation of an immobile structure such as the HQ."""

    id: str
    owner_id: str
    position: Vec2
    hp: float
    attack_cooldown: float = 0.0


@dataclass
class UnitState:
    """Dynamic combatant controlled by a player."""

    id: str
    owner_id: str
    unit_type: str
    position: Vec2
    hp: float
    target_position: Optional[Vec2] = None
    attack_cooldown: float = 0.0


@dataclass
class GameSnapshot:
    """Serializable view of the complete match state."""

    tick: int
    players: List[Dict[str, object]] = field(default_factory=list)
    structures: List[Dict[str, object]] = field(default_factory=list)
    units: List[Dict[str, object]] = field(default_factory=list)
    match_over: bool = False
    winner: Optional[str] = None


@dataclass
class Action:
    """Action requested by a player over the websocket connection."""

    player_id: str
    type: str
    payload: Dict[str, object]
