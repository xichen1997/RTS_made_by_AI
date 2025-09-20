"""Core data structures used by the RTS game simulation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Vector2:
    """Simple 2D vector with helpers for movement calculations."""

    x: float
    y: float

    def copy(self) -> "Vector2":
        return Vector2(self.x, self.y)

    def move_towards(self, destination: "Vector2", max_distance: float) -> None:
        """Move in-place towards ``destination`` by up to ``max_distance``."""
        dx = destination.x - self.x
        dy = destination.y - self.y
        distance_sq = dx * dx + dy * dy
        if distance_sq == 0 or max_distance <= 0:
            return
        if distance_sq <= max_distance * max_distance:
            self.x = destination.x
            self.y = destination.y
            return
        distance = distance_sq ** 0.5
        self.x += (dx / distance) * max_distance
        self.y += (dy / distance) * max_distance

    def distance_to(self, other: "Vector2") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return (dx * dx + dy * dy) ** 0.5

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Entity:
    """Base class for all interactive elements placed on the map."""

    id: str
    owner_id: Optional[str]
    kind: str
    position: Vector2
    max_hp: int
    hp: int

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> None:
        self.hp = max(self.hp - amount, 0)


@dataclass
class Unit(Entity):
    """A controllable combat or economic unit."""

    speed: float
    attack_damage: int
    attack_range: float
    attack_cooldown: float
    role: str
    current_cooldown: float = 0.0
    state: str = "idle"
    target_position: Optional[Vector2] = None
    target_entity_id: Optional[str] = None

    def reset_orders(self) -> None:
        self.state = "idle"
        self.target_position = None
        self.target_entity_id = None


@dataclass
class ProductionTask:
    """Represents a unit that is currently being produced by a building."""

    unit_type: str
    remaining: float


@dataclass
class Building(Entity):
    """Non-mobile structures that can produce new units."""

    buildable_units: List[str]
    production_queue: List[ProductionTask] = field(default_factory=list)


@dataclass
class ResourceNode:
    """Neutral field that continuously provides credits when harvested."""

    id: str
    position: Vector2
    remaining: float

    def harvest(self, amount: float) -> float:
        gathered = min(self.remaining, amount)
        self.remaining -= gathered
        return gathered


@dataclass
class PlayerState:
    """Tracks player-specific information such as resources and fog of war."""

    player_id: str
    name: str
    credits: int
    color: str
    units: Dict[str, Unit] = field(default_factory=dict)
    buildings: Dict[str, Building] = field(default_factory=dict)
    last_command_id: int = 0


@dataclass
class GameSnapshot:
    """Serializable representation of the world state sent to clients."""

    tick: int
    map_size: Tuple[int, int]
    players: Dict[str, Dict]
    units: List[Dict]
    buildings: List[Dict]
    resources: List[Dict]
    events: List[str]
